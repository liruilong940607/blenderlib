#!/usr/bin/env bash
#To set up those alias globally, plz run this file with the command `source setup_paths.sh`

shopt -s expand_aliases

# BLENDER_PKG=\
# "/home/ruilongli/installation/blender-2.93.0-stable+blender-v293-release.84da05a8b806-linux.x86_64-release/"
# alias blender="${BLENDER_PKG}/blender"

# BLENDER_PKG_PY="${BLENDER_PKG}/2.93/python/"

BLENDER_PKG=\
"/Users/ruilongli/Library/Application\ Support/Steam/steamapps/common/Blender/Blender.app"
alias blender="${BLENDER_PKG}/Contents/MacOS/Blender"

BLENDER_PKG_PY="${BLENDER_PKG}/Contents/Resources/2.93/python/"

alias blender_python="${BLENDER_PKG_PY}/bin/python3.9"
alias blender_pip="${BLENDER_PKG_PY}/bin/pip3.9"

if blender_pip > /dev/null; then
  :
else
  echo "* First time running. Setting up pip."
  blender_python -m ensurepip
  blender_python -m pip install pip
fi

echo "* Below alias are set: "
echo "* blender,  blender_python, blender_pip"
