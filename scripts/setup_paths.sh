
#! /bin/bash
#To set up those alias globally, plz run this file with the command `source setup_paths.sh`

shopt -s expand_aliases

BLENDER_PKG="/Users/ruilongli/Library/Application\ Support/Steam/steamapps/common/Blender/Blender.app"
alias blender="${BLENDER_PKG}/Contents/MacOS/Blender"

BLENDER_PKG_PY="${BLENDER_PKG}/Contents/Resources/2.93/python/"
alias blender_python="${BLENDER_PKG_PY}/bin/python3.9"
alias blender_pip="${BLENDER_PKG_PY}/bin/pip3.9"

blender_python -m ensurepip
blender_python -m pip install pip

echo "* Below alias are set: "
echo "* blender,  blender_python, blender_pip"