import bpy # type: ignore
import os
import sys
import argparse
import json
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
        help="the hdri file path for lightning."
    )
    parser.add_argument(
        "--save_dir", 
        type=str, 
        default="./results/",
        help="the output directory."
    )
    parser.add_argument(
        "--n_cam", 
        type=int, 
        default=3,
        help="number of static cameras."
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
    rest_verts = dynamic.extract_rest_verts(mesh_obj)
    return pose_data, verts, rest_verts


def setup_camera():
    scene = bpy.context.scene
    
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


def fix_animal_texture():
    """
    Fix forest animal texture (since it is not automatically set)
    """
    from utils import print_info
    import os.path as osp
    model_path = bpy.data.filepath
    print (model_path)

    bpy.ops.object.select_by_type(type="MESH")
    mesh_obj = bpy.context.selected_objects[0]

    dirname, basename = osp.split(model_path)
    texture_path = osp.join(dirname, 'textures')
    print_info('** Fixing forest animal texture')
    print_info('Finding textures in', texture_path)

    spl = basename.split('_')[:-1]
    get_tex_type = lambda x: osp.splitext(x)[0][len(basename_match):].lower()
    files_in_dir = os.listdir(texture_path)

    texture_paths = {}
    while len(texture_paths) == 0 and len(spl) > 0:
        basename_match = '_'.join(spl) + '_'
        texture_paths = {get_tex_type(x): osp.join(texture_path, x) for x in
                    files_in_dir if x.startswith(basename_match)}
        spl = spl[:-1]

    print_info('Found', len(texture_paths), 'textures:', texture_paths)
    assert 'color' in texture_paths.keys(), "Couldn't find color texture"

    images = {}
    for tname in texture_paths:
        images[tname] = bpy.data.images.load(texture_paths[tname], check_existing=False)
    del texture_paths

    mat = mesh_obj.material_slots[0].material
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    tex_color_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_color_node.image = images['color']
    mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_color_node.outputs['Color'])

    if 'normal' in images:
        print_info('normal map found')
        normal_map_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
        mat.node_tree.links.new(bsdf.inputs['Normal'], normal_map_node.outputs['Normal'])
        tex_normal_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_normal_node.image = images['normal']
        mat.node_tree.links.new(normal_map_node.inputs['Color'], tex_normal_node.outputs['Color'])
    else:
        print_info('normal map NOT found')

    if 'metall' in images:
        print_info('metallic map found')
        tex_metall_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_metall_node.image = images['metall']
        mat.node_tree.links.new(bsdf.inputs['Metallic'], tex_metall_node.outputs['Color'])
    else:
        print_info('metallic map NOT found')

    # Disable specular effects
    bsdf.inputs['Specular'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.69


def main():
    args = parse_args()
    obj_name = os.path.basename(os.path.splitext(bpy.data.filepath)[0])
    save_dir = os.path.join(args.save_dir, obj_name)
    os.makedirs(save_dir, exist_ok=True)

    # global settings
    utils.setup_random_seed(42)
    utils.setup_render_engine_cycles(
        use_gpu=args.use_gpu, # resolution_percentage=20,
    )
    utils.setup_hdri_lighting(hdri_path=args.hdri_path)
    fix_animal_texture()

    # extract meta info
    pose_data, verts, rest_verts = process_object()

    # setup cameras and anchor to be tracked to by the camera
    anchor, camera = setup_camera()
    camera.location = [0., 2., 0.]
    anchor.location = verts.reshape(-1, 3).mean(axis=0)
    
    # rotate the anchor and render
    rotation_eulers = np.random.random((args.n_cam, 3)) * 2 * np.pi
    camera_data = {}

    bpy.ops.object.select_by_type(type="ARMATURE")
    armature_obj = bpy.context.selected_objects[0]
    frame_start = int(armature_obj.animation_data.action.frame_range[0])
    frame_end = 10 # int(armature_obj.animation_data.action.frame_range[-1])
    
    for frame_idx in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame_idx)
        frame_id = "%08d.png" % frame_idx
        for cam_idx, euler in enumerate(rotation_eulers):
            camera_id = "cam_%03d" % cam_idx
            anchor.rotation_euler = euler    
            image_path = os.path.join(
                save_dir, 
                "image", 
                camera_id, 
                frame_id,
            )
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            bpy.context.scene.render.filepath = image_path
            bpy.ops.render.render(write_still=True)

            # NOTE: camera matrix must be written AFTER render 
            # because the view layer is updated lazily
            intrin, extrin = utils.get_intrin_extrin(camera, opencv_format=True)
            camera_data[camera_id] = {
                "intrin": intrin.tolist(), "extrin": extrin.tolist()
            }

    with open(os.path.join(save_dir, "camera.json"), "w") as fp:
        json.dump(camera_data, fp)

    np.savez(
        os.path.join(save_dir, "meta_data.npz"), 
        verts=verts, 
        rest_verts=rest_verts,
        **pose_data
    )



if __name__ == "__main__":
    main()