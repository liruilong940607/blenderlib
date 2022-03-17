import bpy  # type: ignore
import bmesh  # type: ignore
import numpy as np


def extract_rest_joints(armature, bone_name):
    """Extract the **rest** state of the joints.
    
    The `rest_matrix` is canonical -> world rest state.
    """
    bone = armature.data.bones[bone_name]
    matrix_world = armature.matrix_world
    rest_matrix = matrix_world @ bone.matrix_local
    rest_loc_tail = matrix_world @ bone.tail_local
    rest_loc_head = matrix_world @ bone.head_local
    return rest_matrix, rest_loc_tail, rest_loc_head
    
    
def extract_pose_joints(armature, bone_name):
    """Extract the **pose** state of the joints.
    
    The `pose_matrix` is canonical -> world pose state
    """
    bone = armature.pose.bones[bone_name]
    matrix_world = armature.matrix_world
    pose_matrix = matrix_world @ bone.matrix
    return pose_matrix


def extract_joints(armature):
    """Extract both the **rest, pose** state of the joints.
    
    The `pose_matrix` is world rest state -> world pose state.
    Usage:
        ```
        pose_loc = pose_matrix @ rest_matrix.inverse() @ rest_loc
        ```
    Note the above line is essentially the same as this:
        ```
        pose_loc = armature.matrix_world @ armature.pose.bones[bone_name].tail
        ```
    """
    init_frame_id = bpy.context.scene.frame_current

    data = {
        "names": [],  # bone names. [n_bones,]
        "parents": [],   # parent bone names. [n_bones,]
        "rest_loc_tail": [],  # bone tail world location in the rest state. [n_bones, 3]
        "rest_loc_head": [],  # bone head world location in the rest state. [n_bones, 3]
        "rest_matrix": [],  # bone matrix (4 x 4) for bone -> rest state (canonical). [n_bones, 4, 4]
        "pose_matrix": [],  # bone matrix (4 x 4) for bone -> pose state (view space). [n_frames, n_bones, 4, 4]
    }    
    frame_start = int(armature.animation_data.action.frame_range[0])
    frame_end = int(armature.animation_data.action.frame_range[-1])
    
    # rest state
    for bone in armature.data.bones:
        bone_name = bone.name
        bone_parent_name = None if bone.parent is None else bone.parent.name
        rest_matrix, rest_loc_tail, rest_loc_head = extract_rest_joints(armature, bone_name)
        data["names"].append(bone_name)
        data["parents"].append(bone_parent_name)
        data["rest_loc_tail"].append(rest_loc_tail)
        data["rest_loc_head"].append(rest_loc_head)
        data["rest_matrix"].append(rest_matrix)
    # pose state
    for frame_id in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame_id)
        data["pose_matrix"].append([])
        for bone in armature.data.bones:
            bone_name = bone.name
            pose_matrix = extract_pose_joints(armature, bone_name)
            pose_matrix = pose_matrix
            data["pose_matrix"][-1].append(pose_matrix)
    for key, value in data.items():
        data[key] = np.array(value)

    # reset the frame 
    bpy.context.scene.frame_set(init_frame_id)
    return data


def extract_verts(armature, mesh):
    init_frame_id = bpy.context.scene.frame_current

    frame_start = int(armature.animation_data.action.frame_range[0])
    frame_end = int(armature.animation_data.action.frame_range[-1])
    
    verts = []
    for frame_id in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame_id)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new()
        bm.from_object(mesh, depsgraph)
        bm.verts.ensure_lookup_table()
        verts.append([(mesh.matrix_world @ v.co) for v in bm.verts])
    verts = np.array(verts)

    # reset the frame 
    bpy.context.scene.frame_set(init_frame_id)
    return verts.astype(np.float32)

def extract_rest_verts(mesh):
    verts = np.array([(mesh.matrix_world @ v.co) for v in mesh.data.vertices])
    faces = np.array([poly.vertices for poly in mesh.data.polygons])
    
    # faces_uvs: (F, 3) LongTensor giving the index into verts_uvs
    #             for each face
    # verts_uvs: (F*3, 2) tensor giving the uv coordinates per vertex
    #             (a FloatTensor with values between 0 and 1).
    faces_uvs = np.array([poly.loop_indices for poly in mesh.data.polygons])
    verts_uvs = np.array([(data.uv.x, data.uv.y) for data in mesh.data.uv_layers.active.data])
                
    return verts.astype(np.float32), faces.astype(np.int64), verts_uvs.astype(np.float32), faces_uvs.astype(np.int64)


def extract_skinning_weights(armature, mesh, normalize=True):
    n_verts = len(mesh.data.vertices)
    n_bones = len(armature.data.bones)
    
    vg_names = [vg.name for vg in mesh.vertex_groups]
    bone_names = [bone.name for bone in armature.data.bones]
    vg_to_bone_map = [
        bone_names.index(vg_name) if vg_name in bone_names else None
        for vg_name in vg_names
    ]

    weights = np.zeros((n_verts, n_bones), dtype=np.float32)
    for i in range(n_verts):
        for grp in mesh.data.vertices[i].groups:
            bone_id = vg_to_bone_map[grp.group]
            if bone_id is not None:
                weights[i, bone_id] = grp.weight
    if normalize:
        weights = weights / weights.sum(axis=1, keepdims=True)
    return weights
