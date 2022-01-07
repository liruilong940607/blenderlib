#! /bin/bash

DATA_DIR="/home/ruilongli/data/forest_and_friends"

for file in $DATA_DIR/*
do  
    ext="${file#*.}"
    if [ "${ext}" == "blend" ]
    then
        echo ${file}
        CUDA_VISIBLE_DEVICES=8,9 bash scripts/run.sh pylib/converter.py ${file} \
            --hdri_path="${HOME}/data/hdri/air_museum_playground_4k.hdr" \
            --n_cam=1 \
            --use_gpu
    fi
done