#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <tag>"
    exit 1
fi

TAG=$1

docker buildx build --platform linux/amd64,linux/arm64 -t pswerlang/nginx-auto-ssl:$TAG --push .
docker buildx build --platform linux/amd64,linux/arm64 -t pswerlang/nginx-auto-ssl:latest --push .