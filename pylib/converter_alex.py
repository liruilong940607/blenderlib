#  [BSD 2-CLAUSE LICENSE]
#
#  Copyright Alex Yu 2021
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
"""
RenderPeople Blender LBS model extraction & rendering script
Based on ShapeNet renderer by Vickie Ye, Matthew Tancik, Alex Yu
"""
import argparse
import glob
import json
import os
import os.path as osp
from random import choice
import shutil
import sys
from time import time
import typing

import bpy
import bmesh
from mathutils import Vector
import numpy as np
from numpy.random import Generator, MT19937, SeedSequence

root = osp.dirname(osp.abspath(__file__))
sys.path.append(root)

#  import materials


def print_info(*args):
    print("INFO:", *args, file=sys.stderr)


def add_grid(center_loc=(0.0, 0.0, 0.0), size=5.0, n_subdivisions=64, name=None):
    """
    Adds a rectangular grid with specified center_loc, orientation, dimensions, and name.
    (Very simple plane with no subdivisions, etc.)
    """
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=n_subdivisions,
        y_subdivisions=n_subdivisions,
        size=size,
        location=center_loc,
    )
    ground_obj = bpy.context.object
    if name is not None:
        ground_obj.name = name
    return ground_obj


def add_circle(
    location=(0.0, 0.0, 0.0), radius=3, vertices=32, fill_type="NGON", name=None
):
    bpy.ops.mesh.primitive_circle_add(
        vertices=vertices, radius=radius, location=location, fill_type=fill_type
    )
    obj = bpy.context.object
    if name is not None:
        obj.name = name
    return obj


def add_lamps():
    bpy.ops.object.light_add(type="SUN", location=(6, 2, 5))
    lamp = bpy.context.object
    lamp.rotation_euler = (-0.5, 0.5, 0)
    bpy.ops.object.light_add(type="SUN", location=(6, -2, 5))
    lamp = bpy.context.object
    lamp.rotation_euler = (-0.5, -0.5, 0)


def reset_to_canon(arm_obj):
    bpy.context.scene.frame_set(0)

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.loc_clear()
    bpy.ops.pose.rot_clear()
    bpy.ops.pose.scale_clear()
    bpy.ops.object.mode_set(mode='OBJECT')


def import_object(model_path):
    """Load object and get the vertex bounding box"""
    # Deselect all
    for o in bpy.data.objects:
        o.select_set(False)

    name = osp.basename(model_path)
    ext = osp.splitext(model_path)[1].lower()
    if ext == '.fbx':
        print_info("Loading FBX")
        bpy.ops.import_scene.fbx(filepath=model_path, automatic_bone_orientation=True)
    elif ext == '.obj':
        print_info("Loading OBJ")
        bpy.ops.import_scene.obj(filepath=model_path)
    elif ext == '.blend' or len(model_path) == 0:
        print_info("Use current Blender scene")
        #  bpy.ops.wm.open_mainfile(filepath=model_path)
    else:
        raise RuntimeError('Unsupported model extension ' + ext)

    bpy.ops.object.select_by_type(type="ARMATURE")
    selected_objs = bpy.context.selected_objects

    arm_obj = selected_objs[0]

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

    # Make a dummy root for scaling
    root_obj = bpy.data.objects.new("AnimalRenderRoot", None)
    mesh_root_obj = mesh_obj
    while mesh_root_obj.parent != None:
        mesh_root_obj = mesh_root_obj.parent
    dims = mesh_root_obj.dimensions
    bpy.context.scene.collection.objects.link(root_obj)

    mesh_root_obj.parent = root_obj
    arm_obj.parent = root_obj
    bpy.context.view_layer.objects.active = root_obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    scale = np.max(np.abs(dims))
    scale_factor = 2.0 / scale
    root_obj.scale *= scale_factor
    root_obj.location = np.array([0, 0, 0])
    bpy.context.view_layer.update()

    print_info('root', root_obj, 'arm', arm_obj, 'mesh', mesh_obj)

    print_info(root_obj.location, root_obj.scale)
    return root_obj, arm_obj, mesh_obj, scale_factor

def fix_animal_texture(model_path, mesh_obj):
    """
    Fix forest animal texture (since it is not automatically set)
    """
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

def merge_animations(arm_obj):
    """
    Merge multiple animations into one track
    """
    print_info('** Merging animation actions')
    assert arm_obj.animation_data is not None, 'Armature must have animation data'
    anim = arm_obj.animation_data
    action = anim.action
    BASE_TRACK_NAME = 'AnimalRenderBaseAnim'
    base_track = anim.nla_tracks.new()
    curr_frm = 1
    if action is not None:
        print_info('Pushing down current action')
        base_track.name = BASE_TRACK_NAME
        base_track.strips.new(action.name, curr_frm, action)
        base_track.mute = False
        curr_frm += int(base_track.strips[0].action_frame_end)
        anim.action = None
    print_info('Merging NLA tracks')
    for i, track in enumerate(anim.nla_tracks):
        if track.name == BASE_TRACK_NAME:
            continue
        track.lock = False
        strip = track.strips[0]
        action = strip.action
        new_strip = base_track.strips.new(action.name + '-' + str(i), curr_frm, action)
        curr_frm += int(new_strip.action_frame_end)
        track.strips.remove(strip)
        track.mute = True
    return 1, curr_frm


def parent_obj_to_camera(b_camera, root_obj, origin=(0, 0, 0)):
    b_empty = bpy.data.objects.new("Empty", None)
    b_empty.location = origin
    #  b_empty.parent = root_obj
    b_camera.parent = b_empty  # setup parenting

    scn = bpy.context.scene
    scn.collection.objects.link(b_empty)
    bpy.context.view_layer.objects.active = b_empty
    return b_empty


def add_cam_tracking_constraint(camera, root_obj, lookat):
    cam_constraint = camera.constraints.new(type="TRACK_TO")
    cam_constraint.track_axis = "TRACK_NEGATIVE_Z"
    cam_constraint.up_axis = "UP_Y"
    cam_constraint.use_target_z = True
    track_to = parent_obj_to_camera(camera, root_obj, lookat)
    cam_constraint.target = track_to
    return track_to


def add_camera(camera_loc, root_obj, lookat):
    """Choose a camera view to the scene pointing towards lookat"""
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    bpy.context.scene.camera = camera
    print_info("CAMERA LOC", camera_loc)
    camera.location = camera_loc + lookat

    track_to = add_cam_tracking_constraint(camera, root_obj, lookat)
    bpy.context.view_layer.update()
    return camera, track_to


def setup_light_env(rot_vec_rad=(0, 0, 0), scale=(1, 1, 1)):
    engine = bpy.context.scene.render.engine
    assert engine == "CYCLES", "Rendering engine is not Cycles"

    world = bpy.context.scene.world
    world.use_nodes = True
    node_tree = world.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    bg_node = nodes.new("ShaderNodeBackground")
    links.new(bg_node.outputs["Background"], nodes["World Output"].inputs["Surface"])

    # Environment map
    texcoord_node = nodes.new("ShaderNodeTexCoord")
    env_node = nodes.new("ShaderNodeTexEnvironment")
    mapping_node = nodes.new("ShaderNodeMapping")
    links.new(texcoord_node.outputs["Generated"], mapping_node.inputs["Vector"])
    links.new(mapping_node.outputs["Vector"], env_node.inputs["Vector"])
    links.new(env_node.outputs["Color"], bg_node.inputs["Color"])


def load_hdri(filepath, strength):
    nodes = bpy.context.scene.world.node_tree.nodes

    env_node = nodes["Environment Texture"]
    env_node.image = bpy.data.images.load(filepath, check_existing=True)

    bg_node = nodes["Background"]
    bg_node.inputs["Strength"].default_value = strength
    print_info("LIGHT STRENGTH:", strength)


def select_devices(device_type, gpus):
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = device_type
    bpy.context.scene.cycles.device = "GPU"
    for dev_type in preferences.get_device_types(bpy.context):
        preferences.get_devices_for_type(dev_type[0])
        for device in preferences.devices:
            device.use = False
    preferences.get_devices_for_type(device_type)
    sel_devices = [
        device for device in preferences.devices if device.type == device_type
    ]
    print_info(len(sel_devices), gpus)
    for idx in gpus:
        sel_devices[idx].use = True
    for device in sel_devices:
        print(
            "Device {} of type {} found, use {}".format(
                device.name, device.type, device.use
            )
        )


def set_cycles(args):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    cycles = scene.cycles

    cycles.use_progressive_refine = True
    cycles.samples = args.n_samples
    cycles.max_bounces = 8
    cycles.caustics_reflective = True
    cycles.caustics_refractive = False
    cycles.diffuse_bounces = 8
    cycles.glossy_bounces = 4
    cycles.volume_bounces = 0

    # Avoid grainy renderings (fireflies)
    world = bpy.data.worlds["World"]
    world.cycles.sample_as_light = True
    cycles.blur_glossy = 2.0
    cycles.sample_clamp_indirect = 10.0

    world.use_nodes = True

    if args.use_gpu:
        if args.gpus is not None:
            select_devices("CUDA", args.gpus)
        bpy.context.preferences.addons[
            "cycles"
        ].preferences.compute_device_type = "CUDA"
        bpy.context.scene.cycles.device = "GPU"
        # BUG the following needs to be called to register preference update
        devices = bpy.context.preferences.addons["cycles"].preferences.get_devices()

    bpy.context.scene.render.use_persistent_data = True
    bpy.context.scene.world.cycles.sample_map_resolution = 1024
    bpy.context.scene.view_layers[0].cycles.use_denoising = True

    scene.render.tile_x = 256 if args.use_gpu else 16
    scene.render.tile_y = 256 if args.use_gpu else 16
    scene.render.resolution_x = args.res
    scene.render.resolution_y = args.res
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = str(args.color_depth)


def set_eevee(args):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    print_info(scene.render.engine)
    args.nobg = True

    scene.render.resolution_x = args.res
    scene.render.resolution_y = args.res
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = str(args.color_depth)


def hide_objects(obj_names):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        obj.select_set(obj.name in obj_names)
    for sel in bpy.context.selected_objects:
        sel.hide = True


def delete_objects(obj_names):
    for obj in bpy.data.objects:
        obj.select_set(obj.name in obj_names)
    bpy.ops.object.delete()

    # Remove meshes, textures, materials, etc to avoid memory leaks.
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)

    bpy.context.view_layer.update()


def global_setup(args):
    # Clear all existing objects
    if not args.object.endswith('.blend') and not len(args.object) == 0:
        delete_objects([obj.name for obj in bpy.data.objects])

    bpy.context.scene.use_nodes = True

    if args.use_eevee:
        print("USING EEVEE")
        set_eevee(args)
        add_lamps()
    else:
        set_cycles(args)
        _add_background_layer()
        setup_light_env()

    setup_global_render(args)


def check_intersecting(bbs, loc):
    x, y = loc
    for bb in bbs:
        bmin, bmax = bb
        if x > bmin[0] and x < bmax[0] and y >= bmin[1] and y <= bmax[1]:
            return True
    return False


def choose_random_obj_loc(bbs, rng, lo=-2, hi=2, attempts=20):
    for _ in range(attempts):
        loc = rng.uniform(lo, hi, size=2)
        if not check_intersecting(bbs, loc):
            return loc
    return None


def get_posed_mesh_verts(mesh_obj):
    """
    Get vertices of current posed mesh
    """
    mworld = mesh_obj.matrix_world
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(mesh_obj, depsgraph)
    bm.verts.ensure_lookup_table()
    verts = np.array([mworld @ v.co for v in bm.verts])
    return verts

def setup_scene(args, model_dir, rng):
    """set up the scene according to the args provided"""
    root_obj, arm_obj, mesh_obj, scale_factor = import_object(model_dir)
    reset_to_canon(arm_obj)
    fix_animal_texture(model_dir, mesh_obj)

    bpy.context.view_layer.update()
    mesh = mesh_obj.data

    verts = get_posed_mesh_verts(mesh_obj)

    nontri = sum((len(mesh.polygons[i].vertices) != 3 for i
                  in range(len(mesh.polygons))))
    assert not nontri

    faces = np.array([mesh.polygons[i].vertices for i in range(len(mesh.polygons))])

    # Use bone 1 location
    lookat = arm_obj.matrix_world @ arm_obj.pose.bones[1].head
    camera_loc = np.array((0.0, 4.0, 0.0))

    # point camera in between objects added
    camera, track_to = add_camera(camera_loc, root_obj, lookat)
    view_dist = np.linalg.norm(camera_loc)

    root_bone_pos = arm_obj.matrix_world @ arm_obj.pose.bones[2].head
    root_bone_pos[2] -= 0.1
    track_to.location = root_bone_pos

    return root_obj, arm_obj, mesh_obj, camera, track_to, \
           view_dist, lookat, verts, faces, scale_factor


def setup_global_render(args):
    scene = bpy.context.scene
    scene.render.filepath = "/tmp/{}".format(time())  # throw away the composite

    _add_object_output(scene)

    scene.render.film_transparent = True
    if not args.nobg:  # render bg separately
        _add_background_output(scene)

    if not args.nodepth:
        _add_depth_output(scene)


def _render_single(filepath, camera, args):
    scene = bpy.context.scene
    scene.camera = camera

    file_prefixes = [
        _update_node_filepath(filepath, scene, "Object File Output", "obj"),
    ]
    if not args.nobg:
        file_prefixes.append(
            _update_node_filepath(filepath, scene, "Env File Output", "env")
        )
    if not args.nodepth:
        file_prefixes.append(
            _update_node_filepath(filepath, scene, "Depth File Output", "depth")
        )

    bpy.ops.render.render(write_still=True)
    return file_prefixes


def _move_files(dirname, file_prefixes):
    # for all the file prefixes, just move them from the blender rendered file the desired name
    for prefix in file_prefixes:
        matching = glob.glob("{}_*".format(osp.join(dirname, prefix)))
        if len(matching) != 1:
            raise NotImplementedError
        ext = osp.splitext(matching[0])[1]
        base, viewid, render_type = prefix.split('_')
        base = base + '_' + viewid
        render_type_dir = "" if render_type == "obj" else render_type + '/'
        output = "{}/{}{}{}".format(dirname, render_type_dir, base, ext)
        shutil.move(matching[0], output)


def _update_node_filepath(filepath, scene, node_name, prefix):
    outnode = scene.node_tree.nodes[node_name]
    fname = "{}_{}".format(osp.basename(filepath), prefix)
    outnode.base_path = osp.dirname(filepath)
    outnode.file_slots[0].path = fname + "_"
    return fname


def _add_compositing(scene):
    tree = scene.node_tree
    alpha_node = tree.nodes.new("CompositorNodeAlphaOver")
    composite_node = tree.nodes["Composite"]
    #     composite_node.use_alpha = False
    #     tree.links.new(tree.nodes["Render Layers"].outputs["Alpha"], alpha_node.inputs["Fac"])
    tree.links.new(
        tree.nodes["Render Layers"].outputs["Image"], alpha_node.inputs[1]
    )  # image 1
    tree.links.new(
        tree.nodes["Background Render Layers"].outputs["Image"], alpha_node.inputs[2]
    )  # image 2
    tree.links.new(alpha_node.outputs["Image"], composite_node.inputs["Image"])


def _add_object_output(scene):
    result_socket = scene.node_tree.nodes["Render Layers"].outputs["Image"]
    outnode = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    outnode.name = "Object File Output"
    scene.node_tree.links.new(result_socket, outnode.inputs["Image"])


def _add_background_output(scene):
    result_socket = scene.node_tree.nodes["Background Render Layers"].outputs["Env"]
    bg_file_output = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    bg_file_output.name = "Env File Output"
    scene.node_tree.links.new(result_socket, bg_file_output.inputs["Image"])


def _add_alpha_output(scene):
    result_socket = scene.node_tree.nodes["Render Layers"].outputs["Alpha"]
    alpha_file_output = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    alpha_file_output.name = "Alpha File Output"
    scene.node_tree.links.new(result_socket, alpha_file_output.inputs["Image"])


def _add_depth_output(scene):
    result_socket = scene.node_tree.nodes["Render Layers"].outputs["Depth"]
    depth_file_output = scene.node_tree.nodes.new("CompositorNodeOutputFile")
    depth_file_output.name = "Depth File Output"
    depth_file_output.format.file_format = "OPEN_EXR"
    depth_file_output.format.color_depth = "32"
    scene.node_tree.links.new(result_socket, depth_file_output.inputs["Image"])



def _add_background_layer():
    scene = bpy.context.scene
    bpy.ops.scene.view_layer_add()
    new_layer_name = [key for key in scene.view_layers.keys() if key.endswith(".001")][
        0
    ]
    bg_view_layer = scene.view_layers[new_layer_name]
    bg_view_layer.name = "Background Layer"
    bg_view_layer.use_ao = False
    bg_view_layer.use_solid = False
    bg_view_layer.use_strand = False
    bg_view_layer.use_pass_combined = False
    bg_view_layer.use_pass_z = False
    bg_view_layer.use_pass_environment = True

    bpy.context.window.view_layer = scene.view_layers[0]

    # make new render layers and output node
    bg_render_layers = scene.node_tree.nodes.new(type="CompositorNodeRLayers")
    bg_render_layers.name = "Background Render Layers"
    bg_render_layers.layer = bg_view_layer.name

def _get_bone_rotation(bone):
    """
    Given a PoseBone object, get its rotation rel the parent in a
    form compatible with our more basic LBS implementations.
    """
    if bone.parent is None:
        M = bone.matrix.to_3x3()
    M = bone.parent.matrix.to_3x3().transposed() @ bone.matrix.to_3x3()

    return M


def save_obj(vertices, triangles, path, vert_rgb=None):
    """
    Save OBJ file, optionally with vertex colors.
    This version is faster than PyMCubes and supports color.
    Taken from PIFu.
    :param vertices (N, 3)
    :param triangles (N, 3)
    :param vert_rgb (N, 3) rgb
    """
    file = open(path, "w")
    if vert_rgb is None:
        # No color
        for v in vertices:
            file.write("v %.4f %.4f %.4f\n" % (v[0], v[1], v[2]))
    else:
        # Color
        for idx, v in enumerate(vertices):
            c = vert_rgb[idx]
            file.write(
                "v %.4f %.4f %.4f %.4f %.4f %.4f\n"
                % (v[0], v[1], v[2], c[0], c[1], c[2])
            )
    for f in triangles:
        f_plus = f + 1
        file.write("f %d %d %d\n" % (f_plus[0], f_plus[1], f_plus[2]))
    file.close()

def extract_mesh_info(mesh_obj, arm_obj, verts, faces, out_dir):
    """
    Stores basic triangle mesh (only verts+faces) in trimesh.obj
    Stores SMPL-like model format with v_template weights etc in model.npz
    """
    print_info("* Extracting mesh info")
    mesh = mesh_obj.data

    save_obj(verts, faces, osp.join(out_dir, "trimesh.obj"))
    mesh_data = {
        'v_template': verts.astype(
            np.float32),
        'f': faces.astype(np.uint32),
    }
    n_verts = verts.shape[0]

    # *** EXTRACT BONE NAMES ***
    bones = arm_obj.pose.bones
    # Remove base and helper bones
    useless_indies = [0, 1] + [i for i, bone in enumerate(bones) if \
                               'helper' in bone.name.lower()]


    bones = [bone for i, bone in enumerate(bones) if i not in useless_indies]
    bone_names = [bone.name for bone in bones]
    bone_name_map = {name:i for i, name in enumerate(bone_names)}

    # Only keep bones with associated vertex group (kills root & end bones)
    vg_names = [vg.name for vg in mesh_obj.vertex_groups]
    vg_name_map = {name:i for i, name in enumerate(vg_names)}
    for i in useless_indies:
        if arm_obj.pose.bones[i].name in vg_name_map:
            print("WARNING: Expected bone 0 to be useless root/helper bone, "
                  "but it has some (possibly empty) vertex group")

    vg_to_bone_map = [bone_name_map.get(name, None) for name in vg_names]

    n_joints = len(bone_names)
    print([bone.name for bone in bones])

    mesh_data['joint2num'] = vg_name_map

    # *** EXTRACT J (joint positions; not using joint regressor obviously) ***
    bone_loca = np.array([arm_obj.matrix_world @ bone.head for bone in bones])
    mesh_data['J'] = bone_loca.astype(np.float32)

    # *** EXTRACT KINTREE ***
    NO_PARENT = 2**32 - 1  # Weird SMPL legacy, probably they meant to use uint32
    def find_parent(b):
        if b.parent is None:
            return NO_PARENT
        #  elif b.parent.name in bone_name_map.keys():
        #      return bone_name_map[b.parent.name]
        #  else:
            #  return find_parent(b.parent)
        return bone_name_map.get(b.parent.name, NO_PARENT)
    parent_table = [find_parent(bone) for bone in bones]
    kintree_table : np.array = np.stack([np.array(parent_table),
                                 np.arange(len(bones))])
    kintree_table[0, 0] = NO_PARENT
    print(kintree_table)
    #  good_map = kintree_table[1, 1:] > kintree_table[0, 1:]
    #  print(good_map.astype(np.int32))
    #  print([(j, vg_names[j]) for j in range(len(good_map)) if good_map[j] == 0])

    assert (kintree_table[1, 1:] > kintree_table[0, 1:]).all(), "Bones must be topo sorted"
    mesh_data['kintree_table'] = kintree_table.astype(np.int64)

    # *** EXTRACT LBS WEIGHTS ***
    weights = np.zeros((n_verts, n_joints), dtype=np.float32)
    for i in range(n_verts):
        for grp in mesh.vertices[i].groups:
            bone_id = vg_to_bone_map[grp.group]
            if bone_id is not None:
                weights[i, bone_id] = grp.weight
    mesh_data["weights"] = weights

    print_info("n_verts :", n_verts, "n_faces :", faces.shape[0],
               "n_joints :", n_joints, "weights :", weights.shape)

    # *** SAVE ***
    np.savez(osp.join(out_dir, "model.npz"),
             **mesh_data)
    return bones, parent_table

def process_one(
    args,
    model_path,
    out_dir,
    rng,
):
    """Entry point for processing a single object."""
    print_info(out_dir, osp.isdir(out_dir))
    if (
        osp.isdir(out_dir)
        and len(os.listdir(out_dir)) >= args.n_train_poses
        and not args.overwrite
    ):
        print_info("images already written for {}".format(out_dir))
        return False
    os.makedirs(out_dir, exist_ok=True)
    print_info("saving outputs to {}".format(out_dir))

    root_obj, arm_obj, mesh_obj, camera, track_to, view_dist, \
            lookat, verts, faces, scale_factor = \
            setup_scene(args, model_path, rng)
    ani_fstart, ani_fend = merge_animations(arm_obj)
    scene = bpy.context.scene
    scene.frame_start = ani_fstart
    scene.frame_end = ani_fend

    print_info("VIEW_DIST", view_dist)

    bones, parent_table = extract_mesh_info(mesh_obj, arm_obj, verts, faces, out_dir)

    if args.norend:
        print_info("STOP after mesh extraction because --norend specified")
        return
    print_info('* Rendering')
    print_info('Animation frame', ani_fstart, 'to', ani_fend)

    scene.frame_set(0)
    root_bone_init_pos = arm_obj.matrix_world @ arm_obj.pose.bones[2].head
    root_bone_init_pos[2] -= 0.1

    model_ids = [osp.basename(model_path)]
    def render_views(n_poses, out_split, f_start, f_end, f_offset=0, randomize=True,
            randomize_order=False, views_per_pose=1):
        """
        Helper to render a set of views.
        """
        if n_poses <= 0:
            return
        print_info("* Rendering split :", out_split, "poses :", n_poses, "views/pose :", views_per_pose)
        out_subdir = osp.join(out_dir, out_split)
        os.makedirs(out_subdir, exist_ok=True)
        if not args.nobg:
            os.makedirs(osp.join(out_subdir, "env"), exist_ok=True)
        if not args.nodepth:
            os.makedirs(osp.join(out_subdir, "depth"), exist_ok=True)
        n_views = n_poses * views_per_pose

        # Binned uniform azimuth
        euler_zs = 2.0 * np.pi * np.arange(views_per_pose) / views_per_pose
        euler_zs = np.tile(euler_zs, n_poses)
        if randomize:
            euler_zs += rng.uniform(2.0 * np.pi / views_per_pose, size=(n_views,))

        # Archimedes elevation (do not allow too low)
        if randomize:
            _pxs = rng.uniform(-0.25, 1.0, size=(n_views,))
        else:
            _pxs = np.linspace(-0.25, 1.0, n_views)
        euler_xs = np.arcsin(_pxs)

        if randomize_order:
            ordering = np.random.permutation(n_views)
        else:
            ordering = np.arange(n_views)

        # 0 camera roll
        euler_ys = np.zeros(n_views)

        euler_all : np.array = np.vstack([euler_xs, euler_ys, euler_zs])

        frames = []
        files = []

        f_step = (f_end - f_start) // n_poses

        frame_id = f_start
        if f_step == 0:
            # Still frame
            scene.frame_set(f_start)
            f_offset = int(f_step * f_offset)

        poses_aa = []
        for i in range(n_views):
            if i > 0:
                bpy.context.scene.world.cycles.sampling_method = "MANUAL"
            if i % 100 == 0:
                print(i, 'of', n_views)
            pose_id, view_id = divmod(i, views_per_pose)

            if f_step != 0 and view_id == 0:
                frame_id = f_start + f_step * pose_id + f_offset
                scene.frame_set(frame_id)

            rot_euler = euler_all[:, ordering[i]]
            track_to.rotation_euler = rot_euler
            root_bone_pos = arm_obj.matrix_world @ arm_obj.pose.bones[2].head
            root_bone_pos[2] -= 0.1
            track_to.location = root_bone_pos

            file_name_with_id = "{:03d}_{:03d}".format(pose_id, view_id)
            filepath = osp.join(out_subdir, file_name_with_id)
            files.extend(_render_single(filepath, camera, args))
            # NOTE: camera matrix must be written AFTER render because the view layer is updated lazily
            camera_matrix = np.array(camera.matrix_world).tolist()
            frame_data = {
                "transform_matrix":camera_matrix,
                "file_path": filepath,
                "frame_id": frame_id,
            }

            # Extract extra data & put in ... .npz
            Jt = np.array([arm_obj.matrix_world @ bone.head for bone in bones])
            wtr = np.array([b.matrix_channel for b in bones])
            wtr[:, :3, 3] = Jt  # Weird hack
            pose = [
                    b.parent.matrix_channel.to_3x3().transposed() @
                    b.matrix_channel.to_3x3()
                    #  b.parent.matrix_basis.to_3x3().transposed() @
                    #  b.matrix_basis.to_3x3()

                    #  b.parent.matrix_channel.to_3x3().transposed() @
                    #  b.matrix_channel.to_3x3()
                    #  if parent_table[i] < len(bones) else
                    #  b.matrix_channel.to_3x3()
                    for i, b in enumerate(bones)]
            pose_q = [m.to_quaternion() for m in pose]
            pose_aa = [q.axis * q.angle for q in pose_q]
            poses_aa.append(np.array(pose_aa))

            frame_extra_data = {
                "pose_mat": np.array(pose),
                "pose": np.array(pose_aa),  # Axis-angle
                "joint2world": wtr,
                "trans": np.array(root_bone_pos - root_bone_init_pos),
                "v": get_posed_mesh_verts(mesh_obj),
                "J": Jt,
                "frame_id": frame_id,
            }

            npz_path = osp.join(out_subdir, file_name_with_id + ".npz")
            np.savez(npz_path, ** frame_extra_data)

            frames.append(frame_data)

        _move_files(out_subdir, files)

        with open(osp.join(out_dir, "transforms_{}.json".format(out_split)), "w") as f:
            json.dump({"frames": frames, "model_ids": model_ids, "camera_angle_x": camera.data.angle_x },
                    f, indent=1, separators=(",", ":"))
        #  poses_aa = np.stack(poses_aa, axis=0)
        #  np.save(osp.join(out_dir, 'pose_ani.npy'), poses_aa)
    ani_split1 = ani_fstart + (ani_fend - ani_fstart) // 2
    ani_split2 = ani_fstart + 2 * (ani_fend - ani_fstart) // 3

    render_views(args.n_train_poses, "train_repose", ani_fstart, ani_split1,
            randomize=True, randomize_order=False, views_per_pose=args.n_views_per_pose_train)
    #
    #  #  render_views(args.n_train_views, "train", 0, 0, randomize=True)
    #
    render_views(args.n_val_poses, "val_repose", ani_split1 + 1, ani_split2,
            randomize=True, randomize_order=False, views_per_pose=args.n_views_per_pose_val)
    render_views(args.n_train_poses, "val_samepose", ani_fstart,
            ani_split1, randomize=True, randomize_order=False,
            views_per_pose=args.n_views_per_pose_val)
    #
    #  #  render_views(args.n_val_views, "val", 0, 0, randomize=True)

    # ani_fend - ani_fstart + 1
    render_views(120, "test_traj", ani_fstart,
                 ani_fend + 1, randomize=False)

    render_views(args.n_test_poses, "test_repose", ani_split2 + 1, ani_fend,
            randomize=True, randomize_order=False, views_per_pose=args.n_views_per_pose_test)
    render_views(args.n_train_poses, "test_samepose", ani_fstart,
            ani_split1, randomize=True, randomize_order=False,
            views_per_pose=args.n_views_per_pose_test)

    #  render_views(args.n_test_views, "test", 0, 0, randomize=False)

    return True


def parse_args():
    # Blender assumes all arguments before ' -- ' are Blender arguments.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--use_eevee", action="store_true", help="use eevee faster renderer")
    parser.add_argument("--root_dir", default="")
    parser.add_argument(
        "--object",
        default="",
        help="FBX to extract and render. --root_dir will be prepended.",
    )
    parser.add_argument(
        "--light_env_dir",
        default="hdri",
        help="which hdri to use. --root_dir will be prepended",
    )
    parser.add_argument("--light_strength_min", type=float, default=1.5, help="min hdri strength")
    parser.add_argument("--light_strength_max", type=float, default=2.0, help="max hdri strength")
    parser.add_argument(
        "--out_dir",
        default="rp_rendering/forest",
        help="Where to save the result",
    )
    parser.add_argument(
        "--n_train_poses", type=int, default=1, help="number of training poses to use per object"
    )
    parser.add_argument(
        "--n_val_poses", type=int, default=10, help="number of val poses to use per object"
    )
    parser.add_argument(
        "--n_test_poses", type=int, default=25, help="number of test poses to use per object"
    )
    parser.add_argument(
        "--n_views_per_pose_train", type=int, default=5, help="number of views to render per pose"
    )
    parser.add_argument(
        "--n_views_per_pose_test", type=int, default=10, help="number of views to render per pose"
    )
    parser.add_argument(
        "--n_views_per_pose_val", type=int, default=4, help="number of views to render per pose (for val set)"
    )
    parser.add_argument(
        "--norend",
        action="store_true",
        help="select to skip rendering entirely",
    )
    parser.add_argument(
        "--nodepth", action="store_true", help="select to render the depth map"
    )
    parser.add_argument(
        "--nobg",
        action="store_true",
        help="select to not render the background layer",
    )
    parser.add_argument(
        "--res", type=int, default=512, help="size of image to be rendered"
    )
    parser.add_argument(
        "--n_samples", type=int, default=256, help="number of pbr samples"
    )
    parser.add_argument(
        "--color_depth", type=int, default=16, help="color bits per channel"
    )
    parser.add_argument(
        "--use_gpu",
        action="store_true",
        default=False,
        help="use gpu",
    )
    parser.add_argument(
        "--gpus",
        nargs="*",
        type=int,
        help="GPUs to use",
    )
    parser.add_argument("--model_dirs", nargs="*")
    parser.add_argument("--overwrite", action="store_true", default=False)
    args = parser.parse_args(argv)

    if args.root_dir:
        args.object = osp.join(args.root_dir, args.object)
        args.light_env_dir = osp.join(args.root_dir, args.light_env_dir)
        args.out_dir = osp.join(args.root_dir, args.out_dir)
    print(args)
    return args


def main():
    """Launch rendering.

    Example Usage:
        blender --background --python convert_render_animal.py --

    """
    args = parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    global_setup(args)

    hdr_paths = glob.glob(osp.join(args.light_env_dir, "*.hdr"))
    print("Found {} hdri environment maps".format(len(hdr_paths)))

    rng = np.random.default_rng(seed=1929)

    # To allow loop through multiple files
    for _ in range(1):
        if not args.use_eevee:
            load_hdri(rng.choice(hdr_paths),
                    rng.uniform(args.light_strength_min, args.light_strength_max))

        model_path = args.object or bpy.data.filepath
        basename = osp.basename(osp.splitext(model_path)[0])
        out_dir = osp.join(args.out_dir, basename)
        print('output dir:', out_dir)
        process_one(args, model_path, out_dir, rng)
    print("** RP extract & render finished **")


if __name__ == "__main__":
    main()
