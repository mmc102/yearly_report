#! /usr/bin/env bash
set -euo pipefail
pwd && docker build --platform linux/amd64 --build-arg VITE_API_URL=$VITE_API_URL -t $ECR_REGISTRY/$ECR_REPOSITORY/$IMAGE_NAME:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_REPOSITORY/$IMAGE_NAME:latest -f Dockerfile .
