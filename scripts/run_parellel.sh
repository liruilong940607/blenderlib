#! /bin/bash

NUM_THREADS=40
printf '%s\n' {1..2} | shuf | xargs -P$NUM_THREADS -I {} \
bash scripts/run.sh pylib/converter.py $HOME/data/forest_and_friends/Hare_male_full_RM.blend \
    --save_dir "./results_multi_action4/" \
    --use_gpu \
    --n_cam 20 \
    --cam_dist 2.5 \
    --action_id {}
#     # --hdri_path=$HOME/data/hdri/air_museum_playground_4k.hdr \

# NUM_THREADS=20
# printf '%s\n' {1..70} | shuf | xargs -P$NUM_THREADS -I {} \
# bash scripts/run.sh pylib/converter.py $HOME/data/forest_and_friends/Wolf_cub_full_RM_2.blend \
#     --save_dir "./results_multi_action3" \
#     --use_gpu \
#     --n_cam 20 \
#     --cam_dist 2.5 \
#     --action_id {}
    # --hdri_path=$HOME/data/hdri/air_museum_playground_4k.hdr \
