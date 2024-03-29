import bpy  # type: ignore


def setup_cuda_device():
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "CUDA"
    bpy.context.scene.cycles.device = "GPU"
    # The following needs to be called to register preference update
    # See https://developer.blender.org/T71172
    for device_type in preferences.get_device_types(bpy.context):
        preferences.get_devices_for_type(device_type[0])
    for device in preferences.devices:
        device.use = (device.type == "CUDA")
        print(
            "Device {} of type {} found, set use to {}.".format(
                device.name, device.type, device.use
            )
        )


def setup_render_engine_eevee(
    resolution: int = 512,
    resolution_percentage: float = 100.0,
    color_depth: int = 16,
    use_gpu: bool = False,
):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"

    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = resolution_percentage
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = str(color_depth)
    scene.render.film_transparent = True

    if use_gpu:
        setup_cuda_device()

    world = bpy.data.worlds["World"]
    world.use_nodes = True
    scene.use_nodes = True

        
def setup_render_engine_cycles(
    n_samples: int = 256,
    resolution: int = 512,
    resolution_percentage: float = 100.0,
    color_depth: int = 16,
    use_gpu: bool = False,
):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    cycles = scene.cycles
    cycles.use_progressive_refine = True
    cycles.samples = n_samples
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

    if use_gpu:
        setup_cuda_device()

    world.use_nodes = True
    scene.use_nodes = True

    bpy.context.scene.render.use_persistent_data = True
    bpy.context.scene.world.cycles.sample_map_resolution = 1024
    bpy.context.scene.view_layers[0].cycles.use_denoising = True

    scene.render.tile_x = 256 if use_gpu else 16
    scene.render.tile_y = 256 if use_gpu else 16
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = resolution_percentage
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = str(color_depth)
    scene.render.film_transparent = True


def setup_hdri_lighting(
    hdri_path: str = None, 
    strength: float = 1.0, 
):
    scene = bpy.context.scene
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    bg_node = nodes['Background']
    bg_node.inputs["Strength"].default_value = strength
    if hdri_path is not None:
        assert scene.render.engine == "CYCLES"
        env_node = nodes.new("ShaderNodeTexEnvironment")
        env_node.image = bpy.data.images.load(hdri_path, check_existing=True)
        links.new(env_node.outputs["Color"], bg_node.inputs["Color"])
