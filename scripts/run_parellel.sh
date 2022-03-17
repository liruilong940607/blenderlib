#! /bin/bash

# NUM_THREADS=5
# printf '%s\n' {1..50} | xargs -P$NUM_THREADS -I {} \
# bash scripts/run.sh pylib/converter.py ./data/forest_and_friends/Hare_male_full_RM.blend \
#     --save_dir "./results_multi_action6/" \
#     --use_gpu \
#     --n_cam 20 \
#     --cam_dist 3.0 \
#     --action_id {}

NUM_THREADS=5
printf '%s\n' {1..70} | xargs -P$NUM_THREADS -I {} \
bash scripts/run.sh pylib/converter.py ./data/forest_and_friends/Wolf_cub_full_RM_2.blend \
    --save_dir "./results_multi_action6" \
    --use_gpu \
    --n_cam 20 \
    --cam_dist 3.0 \
    --action_id {}
