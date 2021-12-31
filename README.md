# Blenderlib

This is a blender toolbox for personal uses.

## Setup (Mac OS)

Installation can be done on Steam plantform.

#### Where are the files?

```
BLENDER_PKG=/Users/ruilongli/Library/Application\ Support/Steam/steamapps/common/Blender/Blender.app
BLENDER_EXE=${BLENDER_PKG}/Contents/MacOS/Blender
BLENDER_PKG_PY=${BLENDER_PKG}/Contents/Resources/2.93/python/
BLENDER_PY=${BLENDER_PKG_PY}/bin/python3.9
BLENDER_PIP=${BLENDER_PKG_PY}/bin/pip3.9
```

#### Install 3rd-party python packages

```
${BLENDER_PY} -m ensurepip
${BLENDER_PY} -m pip install pip
${BLENDER_PIP} install numpy scipy
```

#### Run blender python script

```
touch /tmp/blender_test.py
echo "import numpy; import scipy; print('done')" > /tmp/blender_test.py
${BLENDER_EXE} -b --python /tmp/blender_test.py --  
```
Note `-b` is for running the blender in background mode. Any python arguments can be put after `--` in the end.


## Rendering

```
bash scripts/run.sh \
  ./pylib/converter_alex.py \
  ./data/forest_and_friends/Bear_cub_full_RM.blend \
  --out_dir ./output2/ --light_env_dir ./data/hdri
```


```
bash scripts/run.sh pylib/converter.py ./data/forest_and_friends/Bear_cub_full_IP.blend --hdri_path=./data/hdri/air_museum_playground_4k.hdr
```