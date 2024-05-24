#!/bin/bash

curl 142.251.46.174
curl google.com

# Install libraries in libs
if [ -n "$LIBRARIES" ]; then
    OLD_IFS="$IFS"
    IFS=',' 
    read -ra LIBRARIES <<< "$LIBRARIES"
    for lib in "${LIBRARIES[@]}"; do
        poetry add $lib > /dev/null 2>&1
    done
    IFS="$OLD_IFS"
fi
# Loop through all environment variables
for var in $(compgen -e); do
    # Check for specific patterns or handle variables as needed
    # For example, if you're looking for a specific variable like SCRIPT_LOC
    if [[ $var == "SCRIPT_LOC" ]]; then
        # Perform the action for SCRIPT_LOC
        aws s3 cp ${!var} .
        script_name=$(basename ${!var})
        while IFS='=' read -r key value; do
            export "$key"="$value"
        done < <(echo "$ENV_VARS" | jq -r 'to_entries[] | "\(.key)=\(.value)"')
        if [[ $ML_MODEL_TRAINING == "True" ]]; then
            python $script_name 2> >(tee error.txt >&2) | tee output.txt
        else
            python $script_name 2> >(tee error.txt >&2) | tee output.txt
        fi
        export SCRIPT_EXIT_CODE=${PIPESTATUS[0]}
    fi
done

# Additional commands can be added as needed
