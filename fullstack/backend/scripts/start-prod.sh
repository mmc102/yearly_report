#! /usr/bin/env bash

set -e
set -x

# Run prestart script
/app/scripts/prestart.sh

# Start uvicorn with logging configuration
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-config /app/app/logging_config.json
