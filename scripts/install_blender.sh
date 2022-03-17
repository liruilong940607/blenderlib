#! /bin/bash
BLENDER_VER="blender-2.93.0-linux64"
wget https://mirror.clarkson.edu/blender/release/Blender2.93/$BLENDER_VER.tar.xz
tar -xvf $BLENDER_VER.tar.xz
rm $BLENDER_VER.tar.xz
cd $BLENDER_VER/2.*/python/bin/
./python3.7m -m ensurepip
./pip3 install numpy scipy