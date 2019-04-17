#!/bin/bash
# local redis server, no authentication
docker run --name redis -p $REDIS_PORT:$REDIS_PORT -d redis:alpine

# if you want something public
# you can get free 30MB redis
# servers from redislabs.com