#! /usr/bin/env bash
set -euo pipefail

docker build --platform linux/amd64 -t $ECR_REGISTRY/$ECR_REPOSITORY/$IMAGE_NAME:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_REPOSITORY/$IMAGE_NAME:latest -f Dockerfile .
