#!/bin/bash

set -euo pipefail

if [ -z "$1" ]; then
    echo "Usage: $0 <tag>"
    exit 1
fi

TAG=$1

BUILDER_NAME="nginx-auto-ssl-builder"

if ! docker buildx inspect "$BUILDER_NAME" >/dev/null 2>&1; then
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --use >/dev/null
else
    docker buildx use "$BUILDER_NAME"
fi

docker buildx inspect --bootstrap >/dev/null

docker buildx build --platform linux/amd64,linux/arm64 \
    -t pswerlang/nginx-auto-ssl:$TAG \
    -t pswerlang/nginx-auto-ssl:latest \
    --push .