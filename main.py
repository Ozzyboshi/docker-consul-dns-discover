#!/usr/bin/python

import consul
from jinja2 import Environment, PackageLoader
import os
from subprocess import call
import signal
import sys
import time

SERIAL_FILE="serial.txt"
env = Environment(loader=PackageLoader('bind', 'templates'))
POLL_TIMEOUT=5

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

def get_consul_addr():
    if "CONSUL_HOST" not in os.environ:
        print "CONSUL_HOST not set"
        sys.exit(1)

    consul_host = os.environ["CONSUL_HOST"]
    if not consul_host:
        print "CONSUL_HOST not set"
        sys.exit(1)

    port = 8500
    host = consul_host

    if ":" in consul_host:
        host, port = consul_host.split(":")

    return host, port

def get_services():

    host, port = get_consul_addr()
    client = consul.Consul(host=host, port=int(port))
    index, data = client.kv.get('dns/', recurse = True)
    services = {}
    
    if "NAME_SERVER" not in os.environ:
        print "NAME_SERVER not set"
        sys.exit(1)
    
    name_server = os.environ["NAME_SERVER"]
    if not name_server:
        print "NAME_SERVER not set"
        sys.exit(1)
        
    if "EMAIL_SERVER" not in os.environ:
        print "EMAIL_SERVER not set"
        sys.exit(1)
    
    email_server = os.environ["EMAIL_SERVER"]
    if not email_server:
        print "EMAIL_SERVER not set"
        sys.exit(1)
    
    for i in data:

        if i['Key'].count("/") != 2:
            continue
        
        ignore, service, container = i['Key'].split("/")
        
        endpoints = services.setdefault(service, dict(port="", backends=[],email=email_server,name=name_server))

        index, ip = client.kv.get('dns/'+service+'/'+container)
        addr=ip['Value']
        endpoints["backends"].append(dict(name=name_server, addr=addr))
        port='80'
        if "HOST_SERVE_PORT" in os.environ:
            port=os.environ["HOST_SERVE_PORT"]
        endpoints["port"] = port
    return services

def generate_config(services,templatefile):
	
    sn=generate_serialnumber()
	
    template = env.get_template(templatefile)
    with open("/data/bind/lib/"+list(services)[0]+".cfg", "w") as f:
        f.write(template.render(services=services,sn=sn))

def generate_serialnumber():
	
	serialnumber=''
	
	try:
		fo = open(SERIAL_FILE, "r")
		serialnumber=fo.read(10)
	except IOError: 
		serialnumber=''

	current_date = time.strftime("%Y%m%d")
	counter=0
	
	if serialnumber[:8]==current_date :
		counter = int(''.join(str(serialnumber[8])).join(str(serialnumber[9])))+1
				
	sn=current_date+str(counter).zfill(2)
	fo = open(SERIAL_FILE, "w+")
	fo.write(sn)
	fo.close()
	
	return sn

if __name__ == "__main__":

    # get template from arguments if set
    template='bind.cfg.tmpl';
    if len(sys.argv)>1:
        template=sys.argv[1]

    current_services = {}
    while True:
        try:
            services = get_services()

            if not services or services == current_services:
                time.sleep(POLL_TIMEOUT)
                continue            
            
            print "config changed. reload bind"
            generate_config(services,template)
            ret = call(["./reload-bind.sh"])
            if ret != 0:
                print "reloading bind returned: ", ret
                time.sleep(POLL_TIMEOUT)
                continue
            current_services = services

        except Exception, e:
            print "Error:", e

        time.sleep(POLL_TIMEOUT)
