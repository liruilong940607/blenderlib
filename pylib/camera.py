import bpy  # type: ignore
import numpy as np  # type: ignore


def extract_camera_data(camera_obj, opencv_format=False):
    """ Extract camera data from the scene. """
    render = bpy.context.scene.render
    resolution_x = render.resolution_x * render.resolution_percentage / 100.0
    resolution_y = render.resolution_y * render.resolution_percentage / 100.0
    aspect_ratio = resolution_x / resolution_y

    fx = 0.5 * resolution_x / np.tan(0.5 * camera_obj.data.angle)
    fy = 0.5 * resolution_x / np.tan(0.5 * camera_obj.data.angle) * aspect_ratio
    cx = 0.5 * resolution_x
    cy = 0.5 * resolution_y

    intrin = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float32)
    extrin = np.array(camera_obj.matrix_world.inverted())
    if opencv_format:
        # camera system in blender and opencv is different.
        # see: https://stackoverflow.com/questions/64977993/applying-opencv-pose-estimation-to-blender-camera
        mat = np.array(
            [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]], 
            dtype=extrin.dtype
        )
        extrin = mat @ extrin
    return intrin, extrin