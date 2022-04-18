# Blenderlib

This is a blender toolbox for personal uses.

## Install 3rd-party python packages

```
# this script will set up three alias for blender:
# `blender`,  `blender_python`, `blender_pip`
source scripts/setup_paths.sh

# install whatever you want through pip
blender_python -m ensurepip
blender_python -m pip install pip
blender_pip install numpy scipy
```

## Ensure blender is installed

```
# this script will set up three alias for blender:
# `blender`,  `blender_python`, `blender_pip`
source scripts/setup_paths.sh

touch /tmp/blender_test.py
echo "print('success')" > /tmp/blender_test.py
blender -b --python /tmp/blender_test.py --  
```
Note `-b` is for running the blender in background mode. Any python arguments can be put after `--` in the end.


## Rendering without Shading

Here we render the subject with uniform lighting and disable any shading effects (by using EEVEE engine w/o ambiant occlusion). To render all actions for the subject with multi-threads (You might want to adjust the parameter `--cam_dist 3.0` for different subjects):
```
# [Wolf_cub_full_RM_2, Hare_male_full_RM]
SUBJECT_ID=Hare_male_full_RM
NUM_THREADS=5
printf '%s\n' {0..100} | xargs -P$NUM_THREADS -I {} \
bash scripts/run.sh \
    scripts/export_renderings.py \
    ./data/forest_and_friends/${SUBJECT_ID}.blend \
    --save_dir "./results/" \
    --use_gpu \
    --n_cam 20 \
    --cam_dist 3.0 \
    --action_id {}

bash scripts/run.sh \
    scripts/export_animation.py \
    ./data/forest_and_friends/${SUBJECT_ID}.blend \
    --save_dir "./results/"
```
Note: This does not seem to support headless rendering!! (Meaning you can't do it on a remote server)



## Rendering with Shading

Through setting the hdri file, it switchs to the Cycles engine with ray tracying to do the rendering. The lighting is more nature and shading effects are enabled. To render all actions for the subject with multi-threads:
```
# [Wolf_cub_full_RM_2, Hare_male_full_RM]
SUBJECT_ID=Hare_male_full_RM
NUM_THREADS=5
printf '%s\n' {1..100} | xargs -P$NUM_THREADS -I {} \
bash scripts/run.sh \
    scripts/export_renderings.py \
    ./data/forest_and_friends/${SUBJECT_ID}.blend \
    --save_dir "./results_shading/" \
    --use_gpu \
    --n_cam 20 \
    --cam_dist 3.0 \
    --action_id {} \
    --hdri_path ./data/hdri/air_museum_playground_4k.hdr
```
