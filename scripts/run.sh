#! /bin/bash
# CUDA_VISIBLE_DEVICES=4,5,6,7,8,9 bash scripts/run.sh pylib/converter.py $HOME/data/forest_and_friends/Bear_cub_full_IP.blend --hdri_path=$HOME/data/hdri/air_museum_playground_4k.hdr --use_gpu


source "$(dirname -- "$0")/setup_paths.sh"

PYTHON_CLI=$1
FBX_FILE=$2
PYTHON_ARGS=${@:3}

echo ""
echo "* Running script ${PYTHON_CLI} on FBX (${FBX_FILE}) with arguments (${PYTHON_ARGS})"
blender -noaudio -b "${FBX_FILE}" --python "${PYTHON_CLI}" -- ${PYTHON_ARGS}
