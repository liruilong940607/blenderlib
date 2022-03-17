import bpy  # type: ignore
import bmesh  # type: ignore
import numpy as np  # type: ignore


def get_object_by_type(type: str, index: int = 0):
    """ Get an general object in the scene. """
    bpy.ops.object.select_by_type(type=type)
    obj = bpy.context.selected_objects[index]
    return obj


def get_mesh(index: int = 0):
    """ Get a mesh in the scene. """
    return get_object_by_type(type="MESH", index=index)


def get_armature(index: int = 0):
    """ Get a armature in the scene. """
    return get_object_by_type(type="ARMATURE", index=index)


def triangulate_mesh(mesh_obj):
    """ [Inplace] Convert the polygon (maybe tetragon) faces into triangles. """
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode="EDIT")
    mesh = mesh_obj.data
    bm = bmesh.from_edit_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.update_edit_mesh(mesh, True)
    bpy.ops.object.mode_set(mode="OBJECT")


def extract_bone_data(armature_obj, bone_name: str, rest_space: bool = False):
    """ Extract the rest (canonical) or pose state of a bone.
    
    :params rest_space: if set True, then return the bone in rest space,
        else return the bone in pose space. Default is False (pose space).
    :returns
        - matrix: [4, 4]. transformation matrix from bone to rest / pose space.
        - tail: [3,]. coordinate of the bone tail in the rest / pose space.
        - head: [3,]. coordinate of the bone head in the rest / pose space.
    """
    matrix_world = armature_obj.matrix_world
    if rest_space:
        bone = armature_obj.data.bones[bone_name]
        matrix = matrix_world @ bone.matrix_local
        tail = matrix_world @ bone.tail_local
        head = matrix_world @ bone.head_local
    else:
        bone = armature_obj.pose.bones[bone_name]
        matrix = matrix_world @ bone.matrix
        tail = matrix_world @ bone.tail
        head = matrix_world @ bone.head
    return matrix, tail, head
    

def extract_mesh_data(mesh_obj):
    """ Extract the mesh data in rest space. """
    verts = np.array(
        [(mesh_obj.matrix_world @ v.co) for v in mesh_obj.data.vertices])
    faces = np.array(
        [poly.vertices for poly in mesh_obj.data.polygons])
    # faces_uvs: (F, 3) LongTensor giving the index into verts_uvs
    #             for each face
    # verts_uvs: (F*3, 2) tensor giving the uv coordinates per vertex
    #             (a FloatTensor with values between 0 and 1).
    faces_uvs = np.array(
        [poly.loop_indices for poly in mesh_obj.data.polygons])
    verts_uvs = np.array(
        [(data.uv.x, data.uv.y) for data in mesh_obj.data.uv_layers.active.data])
    verts = verts.astype(np.float32)
    faces = faces.astype(np.int64)
    verts_uvs = verts_uvs.astype(np.float32)
    faces_uvs = faces_uvs.astype(np.int64)
    return verts, faces, verts_uvs, faces_uvs


def extract_verts_data(mesh_obj, armature_obj):
    """ Extract the sequence data of posed verts. """
    init_frame_id = bpy.context.scene.frame_current
    frame_start = int(armature_obj.animation_data.action.frame_range[0])
    frame_end = int(armature_obj.animation_data.action.frame_range[-1])
    
    verts = []
    for frame_id in range(frame_start, frame_end + 1):
        bpy.context.scene.frame_set(frame_id)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new()
        bm.from_object(mesh_obj, depsgraph)
        bm.verts.ensure_lookup_table()
        verts.append([(mesh_obj.matrix_world @ v.co) for v in bm.verts])
    verts = np.array(verts)

    # reset the frame 
    bpy.context.scene.frame_set(init_frame_id)
    return verts.astype(np.float32)


def extract_skeleton_data(armature_obj, rest_space: bool = False):
    """ Extract the skeleton data in rest / pose space. """
    if rest_space:
        bnames, bnames_parent, matrixs, tails, heads = [], [], [], [], []
        for bone in armature_obj.data.bones:
            bname = bone.name
            bname_parent = None if bone.parent is None else bone.parent.name
            matrix, tail, head = extract_bone_data(
                armature_obj=armature_obj, bone_name=bname, rest_space=True
            )
            bnames.append(bname)
            bnames_parent.append(bname_parent)
            matrixs.append(matrix)
            tails.append(tail)
            heads.append(head)
        bnames, bnames_parent, matrixs, tails, heads = (
            np.array(bnames), np.array(bnames_parent), 
            np.array(matrixs), np.array(tails), np.array(heads)
        )
        return bnames, bnames_parent, matrixs, tails, heads
    
    else:
        init_frame_id = bpy.context.scene.frame_current
        frame_start = int(armature_obj.animation_data.action.frame_range[0])
        frame_end = int(armature_obj.animation_data.action.frame_range[-1])
        
        matrixs, tails, heads = [], [], []
        for frame_id in range(frame_start, frame_end + 1):
            bpy.context.scene.frame_set(frame_id)
            matrixs.append([])
            tails.append([])
            heads.append([])
            for bone in armature_obj.data.bones:
                bname = bone.name
                matrix, tail, head = extract_bone_data(
                    armature_obj=armature_obj, bone_name=bname, rest_space=False
                )
                matrixs[-1].append(matrix)
                tails[-1].append(tail)
                heads[-1].append(head)
        matrixs, tails, heads = (
            np.array(matrixs), np.array(tails), np.array(heads)
        )
        # reset the frame 
        bpy.context.scene.frame_set(init_frame_id)
        return matrixs, tails, heads


def extract_skinning_weights_data(armature_obj, mesh_obj, normalize=True):
    """ Extract the skinning weights data. """
    n_verts = len(mesh_obj.data.vertices)
    n_bones = len(armature_obj.data.bones)
    
    vg_names = [vg.name for vg in mesh_obj.vertex_groups]
    bone_names = [bone.name for bone in armature_obj.data.bones]
    vg_to_bone_map = [
        bone_names.index(vg_name) if vg_name in bone_names else None
        for vg_name in vg_names
    ]

    weights = np.zeros((n_verts, n_bones), dtype=np.float32)
    for i in range(n_verts):
        for grp in mesh_obj.data.vertices[i].groups:
            bone_id = vg_to_bone_map[grp.group]
            if bone_id is not None:
                weights[i, bone_id] = grp.weight
    if normalize:
        weights = weights / weights.sum(axis=1, keepdims=True)
    return weights


def extract_all_data():
    """ Extract all useful data from the animation. """
    # get the mesh and armature objects in the scene    
    armature_obj = get_armature(index=0)
    mesh_obj = get_mesh(index=0)
    triangulate_mesh(mesh_obj)

    ##########################
    ## Data in the rest space
    ##########################
    # extract bone data.
    bnames, bnames_parent, rest_matrixs, rest_tails, rest_heads = (
        extract_skeleton_data(armature_obj, rest_space=True)
    )
    # extract mesh data.
    rest_verts, faces, verts_uvs, faces_uvs = extract_mesh_data(mesh_obj)
    # extract skinning weights data
    lbs_weights = extract_skinning_weights_data(
        armature_obj, mesh_obj, normalize=True
    )

    ##########################
    ## Data in the pose space
    ##########################
    # extract posed bone data.
    pose_matrixs, pose_tails, pose_heads = extract_skeleton_data(
        armature_obj, rest_space=False
    )
    # extract posed mesh data.
    pose_verts = extract_verts_data(mesh_obj, armature_obj)

    return {
        "bnames": bnames,  # [n_bones,]
        "bnames_parent": bnames_parent,  # [n_bones,]
        "rest_matrixs": rest_matrixs,  # [n_bones, 4, 4]
        "rest_tails": rest_tails,  # [n_bones, 3]
        "rest_heads": rest_heads,  # [n_bones, 3]
        "rest_verts": rest_verts,  # [n_verts, 3]
        "faces": faces,  # [n_faces, 3]
        "verts_uvs": verts_uvs,  # [n_faces*3, 3]
        "faces_uvs": faces_uvs,  # [n_faces, 3]
        "lbs_weights": lbs_weights,  # [n_verts, n_bones]
        "pose_matrixs": pose_matrixs,  # [n_frames, n_bones, 4, 4]
        "pose_tails": pose_tails,  # [n_frames, n_bones, 3]
        "pose_heads": pose_heads,  # [n_frames, n_bones, 3]
        "pose_verts": pose_verts,  # [n_frames, n_verts, 3]
    }
