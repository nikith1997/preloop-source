#!/bin/bash

# Remove codeartifact repos from pyproject.toml during runtime
poetry source remove preloop_main
poetry source remove pypi-store

# Install libraries in libs
if [ -n "$LIBRARIES" ]; then
    OLD_IFS="$IFS"
    IFS=',' 
    read -ra LIBRARIES <<< "$LIBRARIES"
    for lib in "${LIBRARIES[@]}"; do
        poetry add $lib
    done
    IFS="$OLD_IFS"
fi

while IFS='=' read -r key value; do
    export "$key"="$value"
done < <(echo "$ENV_VARS" | jq -r 'to_entries[] | "\(.key)=\(.value)"')

aws s3 cp $INFERENCE_SCRIPT_LOC /app/src/
poetry run gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:80
