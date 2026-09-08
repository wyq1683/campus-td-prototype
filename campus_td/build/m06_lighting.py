# m06_lighting.py — M6 电影级光照与后期（离线，无 HDRI）
# 离线无 HDRI 文件：用程序化渐变天穹球 (M6_SkyDome, 自发光渐变) 替代 flat/solid Background，
# 提供真实 3D 天空渐变 + 天空环境光；金色时刻 SUN 灯给主光与阴影；
# AgX 色调映射 + Compositor Glare(替代 EEVEE Bloom) 让防御塔发光环辉光；
# Compositor ColorBalance 做轻微色彩分级。build_lighting(mode) 幂等（按 M6_ 前缀清理）。
import bpy
import mathutils

PREFIX = "M6_"


def clear_all():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def _bsdf_of(mat):
    if mat is None or not mat.use_nodes:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def setup_world(mode):
    # 用 World shader 做程序化渐变天穹：既可见又提供环境光，比 mesh 天穹更稳
    sc = bpy.context.scene
    # 复用权威 "World"，避免天气里程碑每次 restore 把临时天光 world 删空后
    # 又 fallback 新建 World.001/World.002... 造成孤儿天光无限累积（自动化每小时跑一次会爆）。
    world = bpy.data.worlds.get("World")
    if world is None:
        world = sc.world
        if world is None:
            world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")  # ColorRamp
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tex.location = (-600, 0)
    sep.location = (-420, 0)
    ramp.location = (-240, 0)
    bg.location = (0, 0)
    out.location = (200, 0)
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])  # Z 为垂直方向
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # ColorRamp 默认 2 段；先重置两端位置
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 1.0

    if mode == "dusk":
        # 暮色：地平线橙、低空品红、高空紫、顶深空蓝
        ramp.color_ramp.elements[0].color = (0.96, 0.52, 0.32, 1.0)
        e1 = ramp.color_ramp.elements.new(0.45)
        e1.color = (0.80, 0.44, 0.54, 1.0)
        e2 = ramp.color_ramp.elements.new(0.72)
        e2.color = (0.42, 0.36, 0.62, 1.0)
        ramp.color_ramp.elements[1].color = (0.14, 0.18, 0.42, 1.0)
        bg.inputs["Strength"].default_value = 0.6
    else:
        # 白昼：地平线天蓝、中段蔚蓝、顶深蓝（降低苍白区，避免过曝显灰）
        ramp.color_ramp.elements[0].color = (0.55, 0.72, 0.90, 1.0)
        e1 = ramp.color_ramp.elements.new(0.55)
        e1.color = (0.35, 0.55, 0.85, 1.0)
        ramp.color_ramp.elements[1].color = (0.18, 0.38, 0.78, 1.0)
        bg.inputs["Strength"].default_value = 0.45
    return world


def make_sun(mode):
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object
    sun.name = PREFIX + "Sun"
    sun.data.name = PREFIX + "Sun"
    if mode == "dusk":
        # 低角度、暖橙、中强
        sun.location = (70.0, -90.0, 28.0)
        sun.data.energy = 3.8
        sun.data.color = (1.0, 0.55, 0.30)
        sun.data.angle = 0.012
        sun.data.shadow_soft_size = 3.0
    else:
        # 上午偏侧、暖白、中强
        sun.location = (60.0, -85.0, 55.0)
        sun.data.energy = 3.2
        sun.data.color = (1.0, 0.92, 0.80)
        sun.data.angle = 0.010
        sun.data.shadow_soft_size = 2.5
    # 让 -Z 指向原点（光照方向）
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return sun


def boost_tower_glow():
    # 防御塔发光环提亮，让 Compositor Glare 能抓到 → 电影感辉光
    boosted = []
    for mat in bpy.data.materials:
        if "glow" in mat.name.lower() and mat.use_nodes:
            for n in mat.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = 4.0
                    boosted.append(mat.name)
    return boosted


def quiet_old_lights():
    # 关掉 M0 原始 Sun（避免双日），保留 Fill 作柔光
    quieted = []
    for o in bpy.data.objects:
        if o.type == "LIGHT" and not o.name.startswith(PREFIX):
            if o.name == "Sun":
                o.data.energy = 0.0
                quieted.append(o.name)
    return quieted


def setup_color_mgmt(mode):
    sc = bpy.context.scene
    sc.view_settings.view_transform = "AgX"
    # 优先高对比 look；没有则降级
    for look in ("AgX - High Contrast", "AgX - Medium High Contrast", "AgX - Medium Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            pass
    if mode == "dusk":
        sc.view_settings.exposure = 0.20
    else:
        sc.view_settings.exposure = -0.15


def setup_compositor():
    sc = bpy.context.scene
    sc.use_nodes = True
    sc.render.film_transparent = False
    sc.render.use_compositing = True
    ng = sc.compositing_node_group
    if ng is None:
        ng = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
        try:
            sc.compositing_node_group = ng
        except Exception:
            pass
    nt = ng
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    grade = nt.nodes.new("CompositorNodeColorBalance")
    rl.location = (-400, 0)
    glare.location = (-150, 0)
    grade.location = (100, 0)
    # Glare（替代 EEVEE Bloom）：仅亮部（塔发光环）起辉，柔和大光晕
    glare.glare_type = "BLOOM"
    glare.quality = "HIGH"
    glare.threshold = 0.85
    glare.size = 9
    glare.mix = 0.85
    # 色彩分级：轻微提饱和 + 增益（属性名在 5.x 可能变化，逐项防御）
    try:
        grade.saturation = 1.12
    except Exception:
        pass
    try:
        grade.gain = (1.05, 1.05, 1.05)
    except Exception:
        try:
            grade.inputs["Gain"].default_value = (1.05, 1.05, 1.05)
        except Exception:
            pass
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], grade.inputs["Image"])
    # Blender 5.x：CompositorNodeComposite 已移除，节点树末端即隐式输出，无需 Composite 节点
    return True


def setup_denoiser():
    sc = bpy.context.scene
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPEN_IMAGE_DENOISE"
    except Exception:
        pass


def build_lighting(mode="day"):
    mode = "dusk" if mode == "dusk" else "day"
    sc = bpy.context.scene
    # Blender 5.2 合成器已移除 CompositorNodeComposite 输出节点，无法用 Glare 做 Bloom；
    # 关闭合成器，改用程序化 World 天穹 + 场景内叠加辉光壳模拟 Bloom
    sc.use_nodes = False
    sc.render.use_compositing = False
    cleared = clear_all()
    world = setup_world(mode)
    sun = make_sun(mode)
    boosted = boost_tower_glow()
    halos = make_tower_halos()
    quieted = quiet_old_lights()
    setup_color_mgmt(mode)
    setup_denoiser()
    result = {
        "mode": mode,
        "cleared": cleared,
        "world": world.name,
        "sun": sun.name,
        "tower_glow_boosted": boosted,
        "tower_halos": halos,
        "old_lights_quieted": quieted,
        "view_transform": sc.view_settings.view_transform,
        "bloom": "in-scene additive halo (compositor Glare blocked in 5.2)",
    }
    return result


def make_tower_halos():
    # 给防御塔发光环套一层放大 1.25× 的叠加(ADD)发光壳，模拟 Bloom 辉光（离线无合成器）
    halos = []
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.name.startswith(PREFIX):
            continue
        if o.name.startswith("Mat_Preview_"):
            continue
        mats = list(o.data.materials) if hasattr(o.data, "materials") else []
        is_glow = any((m is not None and "glow" in m.name.lower()) for m in mats)
        if not is_glow:
            continue
        dup = o.copy()
        dup.data = o.data.copy()
        dup.name = PREFIX + "Halo_" + o.name
        mat = bpy.data.materials.new(PREFIX + "HaloMat")
        mat.use_nodes = True
        try:
            mat.blend_method = "ADD"
        except Exception:
            pass
        mat.use_backface_culling = False
        nt = mat.node_tree
        nt.nodes.clear()
        emis = nt.nodes.new("ShaderNodeEmission")
        outn = nt.nodes.new("ShaderNodeOutputMaterial")
        emis.inputs["Color"].default_value = (1.0, 0.92, 0.6, 1.0)
        emis.inputs["Strength"].default_value = 2.8
        nt.links.new(emis.outputs["Emission"], outn.inputs["Surface"])
        dup.data.materials.clear()
        dup.data.materials.append(mat)
        dup.scale = (o.scale.x * 1.25, o.scale.y * 1.25, o.scale.z * 1.25)
        try:
            dup.visible_shadow = False
        except Exception:
            pass
        bpy.context.collection.objects.link(dup)
        halos.append(dup.name)
    return halos


# 模块被 exec 时默认构建白昼；render 脚本会显式调用 build_lighting(mode)
if "bpy" in globals():
    pass
