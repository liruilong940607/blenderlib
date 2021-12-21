#! /bin/bash

source "$(dirname -- "$0")/setup_paths.sh"

PYTHON_CLI=$1
FBX_FILE=$2
PYTHON_ARGS=${@:3}

echo ""
echo "* Running script ${PYTHON_CLI} on FBX (${FBX_FILE}) with arguments (${PYTHON_ARGS})"
blender -noaudio -b "${FBX_FILE}" --python "${PYTHON_CLI}" -- ${PYTHON_ARGS}
