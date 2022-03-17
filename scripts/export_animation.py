import bpy # type: ignore
import os
import sys
import argparse
import numpy as np # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylib"))
import animation # type: ignore


def parse_args():
    # Blender assumes all arguments before ' -- ' are Blender arguments.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--save_dir", 
        type=str, 
        default=None,
        help="the output directory."
    )
    args = parser.parse_args(argv)
    return args


def main():
    args = parse_args()
    obj_name = os.path.basename(os.path.splitext(bpy.data.filepath)[0])
    
    action_names = sorted(list(bpy.data.actions.keys()))
    
    # for loop on all actions
    for action_name in action_names:
        save_dir = os.path.join(args.save_dir, obj_name, action_name)
        os.makedirs(save_dir, exist_ok=True)
        # apply action
        action = bpy.data.actions[action_name]
        armature_obj = animation.get_armature(index=0)
        armature_obj.animation_data.action = action
        # extract data
        animation_data = animation.extract_all_data()
        np.savez(
            os.path.join(save_dir, "meta_data.npz"), **animation_data,
        )



if __name__ == "__main__":
    main()