#!/bin/bash

docker exec -it bind rndc reconfig && docker exec -it bind rndc reload
