import bpy # type: ignore
import bmesh # type: ignore
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
        default=None,
        help="the hdri file path for lightning."
    )
    parser.add_argument(
        "--save_dir", 
        type=str, 
        default=None,
        help="the output directory."
    )
    parser.add_argument(
        "--n_cam", 
        type=int, 
        default=50,
        help="number of static cameras."
    )
    parser.add_argument(
        "--action_id", 
        type=int, 
        default=None,
        help="index of the action to be rendered."
    )
    parser.add_argument(
        "--cam_dist", 
        type=float, 
        default=2.0,
        help="Distance factor between the camera and the object."
    )
    args = parser.parse_args(argv)
    return args


def process_object():
    bpy.ops.object.select_by_type(type="ARMATURE")
    armature_obj = bpy.context.selected_objects[0]
    bpy.ops.object.select_by_type(type="MESH")
    mesh_obj = bpy.context.selected_objects[0]

    # Triangulate the mesh
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode="EDIT")
    mesh = mesh_obj.data
    bm = bmesh.from_edit_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.update_edit_mesh(mesh, True)
    bpy.ops.object.mode_set(mode="OBJECT")

    pose_data = dynamic.extract_joints(armature_obj)

    verts = dynamic.extract_verts(armature_obj, mesh_obj)
<<<<<<< HEAD
    rest_verts, faces, verts_uvs, faces_uvs = dynamic.extract_rest_verts(mesh_obj)

    weights = dynamic.extract_skinning_weights(armature_obj, mesh_obj)
    return pose_data, verts, rest_verts, weights, faces, verts_uvs, faces_uvs
=======
    rest_verts, faces = dynamic.extract_rest_verts(mesh_obj)

    weights = dynamic.extract_skinning_weights(armature_obj, mesh_obj)
    return pose_data, verts, rest_verts, weights, faces
>>>>>>> 7b1d01fb72862b24525c88bd6d4f6d04d2a2fc85


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
    # disable specularity
    bsdf.inputs[5].default_value = 0.

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
    
    if args.action_id is not None:
        # os.environ["CUDA_VISIBLE_DEVICES"]="%d" % (args.action_id % 10)
        os.environ["CUDA_VISIBLE_DEVICES"]="%d" % (4 + args.action_id % 6)

    # global settings
    utils.setup_random_seed(2392)
    if args.hdri_path is not None:
        utils.setup_render_engine_cycles(
            use_gpu=args.use_gpu, resolution=800, #resolution_percentage=20,
        )
        utils.setup_hdri_lighting(hdri_path=args.hdri_path, strength=1.8)
    else:
        utils.setup_render_engine_eevee(
            use_gpu=args.use_gpu, resolution=800, #resolution_percentage=20,
        )
        bpy.context.scene.world.light_settings.use_ambient_occlusion = False
        utils.setup_hdri_lighting(hdri_path=None, strength=5.0)
    fix_animal_texture()

    action_names = sorted(list(bpy.data.actions.keys()))
    if args.action_id is not None:
        if args.action_id >= len(action_names):
            print ("action id %d is out of range %d" % (args.action_id, len(action_names)))
            return
        action_names = [action_names[args.action_id]]

    # for loop on all actions
    for action_name in action_names:
        action = bpy.data.actions[action_name]

        save_dir = os.path.join(args.save_dir, obj_name, action_name)
        os.makedirs(save_dir, exist_ok=True)

        # if os.path.exists(
        #     os.path.join(save_dir, "meta_data.npz")
        # ):
        #     continue

        bpy.ops.object.select_by_type(type="ARMATURE")
        armature_obj = bpy.context.selected_objects[0]
        armature_obj.animation_data.action = action

        # extract meta info
<<<<<<< HEAD
        pose_data, verts, rest_verts, weights, faces, verts_uvs, faces_uvs = process_object()

        # boudning box of the action region
        bb_min = rest_verts.reshape(-1, 3).min(axis=0)
        bb_max = rest_verts.reshape(-1, 3).max(axis=0)
=======
        pose_data, verts, rest_verts, weights, faces = process_object()

        # boudning box of the action region
        bb_min = verts.reshape(-1, 3).min(axis=0)
        bb_max = verts.reshape(-1, 3).max(axis=0)
>>>>>>> 7b1d01fb72862b24525c88bd6d4f6d04d2a2fc85
        center = (bb_max + bb_min) / 2.0
        scale = (np.prod(bb_max - bb_min)) ** (1. / 3.)

        # setup cameras and anchor to be tracked to by the camera
        anchor, camera = setup_camera()
        # camera.location = [0., 2.0 * scale, 0.]
        camera.location = [0., args.cam_dist * scale, 0.]
<<<<<<< HEAD
        # anchor.location = center
=======
        anchor.location = center
>>>>>>> 7b1d01fb72862b24525c88bd6d4f6d04d2a2fc85

        # rotate the anchor and render
        rotation_eulers = np.concatenate([
            np.arcsin(np.random.uniform(low=-0.8, high=0.8, size=(args.n_cam, 1))),  # x
            np.zeros((args.n_cam, 1)),  # y
            np.random.random((args.n_cam, 1)) * 2 * np.pi,  # z
        ], axis=1) 

        frame_start = int(armature_obj.animation_data.action.frame_range[0])
        frame_end = int(armature_obj.animation_data.action.frame_range[-1])

        camera_data = {}        
        for frame_id in range(frame_start, frame_end + 1):
            bpy.context.scene.frame_set(frame_id)

            bpy.ops.object.select_by_type(type="ARMATURE")
            armature_obj = bpy.context.selected_objects[0]
            root_bone_pos = armature_obj.matrix_world @ armature_obj.pose.bones[2].head
            anchor.location = root_bone_pos

            camera_data[frame_id] = {}
            for cam_idx, euler in enumerate(rotation_eulers):
                camera_id = "cam_%03d" % cam_idx
                anchor.rotation_euler = euler    
                image_path = os.path.join(
                    save_dir, 
                    "image", 
                    camera_id, 
                    "%08d.png" % frame_id,
                )
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                bpy.context.scene.render.filepath = image_path
                bpy.ops.render.render(write_still=True)

                # NOTE: camera matrix must be written AFTER render 
                # because the view layer is updated lazily
                intrin, extrin = utils.get_intrin_extrin(camera, opencv_format=True)
                camera_data[frame_id][camera_id] = {
                    "intrin": intrin.tolist(), "extrin": extrin.tolist()
                }

        with open(os.path.join(save_dir, "camera.json"), "w") as fp:
            json.dump(camera_data, fp)

        np.savez(
            os.path.join(save_dir, "meta_data.npz"), 
            verts=verts, 
            rest_verts=rest_verts,
            faces=faces,
<<<<<<< HEAD
            verts_uvs=verts_uvs, 
            faces_uvs=faces_uvs,
=======
>>>>>>> 7b1d01fb72862b24525c88bd6d4f6d04d2a2fc85
            weights=weights,
            **pose_data
        )



if __name__ == "__main__":
    main()