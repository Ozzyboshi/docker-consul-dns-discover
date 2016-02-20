#!/bin/bash

docker exec --tty=false bind rndc reconfig && docker exec --tty=false bind rndc reload
