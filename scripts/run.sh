#! /bin/bash

source "$(dirname -- "$0")/setup_paths.sh"

PYTHON_CLI=$1
PYTHON_ARGS=${@:2}

echo ""
echo "* Running script ${PYTHON_CLI} with arguments (${PYTHON_ARGS})"
blender -b --python ${PYTHON_CLI} -- ${PYTHON_ARGS}
