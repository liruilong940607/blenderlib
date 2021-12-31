import bpy
import os
import sys
import argparse
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import dynamic
import utils


def parse_args():
    # Blender assumes all arguments before ' -- ' are Blender arguments.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--use_gpu", action="store_true", help="use gpu to render"
    )
    parser.add_argument(
        "--hdri_path", 
        type=str, 
        default="./data/hdri/air_museum_playground_4k.hdr",
        help="the hdri file path for lightning"
    )
    parser.add_argument(
        "--save_dir", 
        type=str, 
        default="./results/",
        help="the hdri file path for lightning"
    )
    args = parser.parse_args(argv)
    return args


def process_object():
    bpy.ops.object.select_by_type(type="ARMATURE")
    armature_obj = bpy.context.selected_objects[0]
    pose_data = dynamic.extract_joints(armature_obj)

    bpy.ops.object.select_by_type(type="MESH")
    mesh_obj = bpy.context.selected_objects[0]
    verts = dynamic.extract_verts(armature_obj, mesh_obj)
    return pose_data, verts


def setup_camera(scene_name: str = "Scene"):
    scene = bpy.data.scenes[scene_name]
    
    bpy.ops.object.empty_add()
    anchor = bpy.context.active_object
    
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.active_object
    scene.camera.parent = anchor

    cam_constraint = scene.camera.constraints.new(type="TRACK_TO")
    cam_constraint.track_axis = "TRACK_NEGATIVE_Z"
    cam_constraint.up_axis = "UP_Y"
    cam_constraint.use_target_z = True
    cam_constraint.target = anchor

    return anchor, scene.camera


def main():
    args = parse_args()
    
    obj_name = os.path.basename(os.path.splitext(bpy.data.filepath)[0])
    save_dir = os.path.join(args.save_dir, obj_name)
    os.makedirs(save_dir, exist_ok=True)

    # global settings
    utils.setup_random_seed(42)
    utils.setup_render_engine_cycles(
        use_gpu=args.use_gpu,
        # resolution_percentage=20,
    )
    utils.setup_hdri_lighting(hdri_path=args.hdri_path)

    # extract meta info
    pose_data, verts = process_object()

    # render images
    anchor, camera = setup_camera()
    camera.location = [0., 2., 0.]
    anchor.location = verts.reshape(-1, 3).mean(axis=0)
    for index in range(5):
        anchor.rotation_euler = np.random.random(3) * 2 * np.pi        
        bpy.context.scene.render.filepath = (
            os.path.join(save_dir, "%08d.png" % index)
        )
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()