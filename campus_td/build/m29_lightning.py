# m29_lightning.py — 里程碑 M29：闪电抓拍（Lightning Flash Capture · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M29_ 前缀临时世界/物体（结束恢复），仅落盘 PNG。
# 思路：在已收官校园上叠加"雨夜 + 闪电"——暗调暴风冷蓝天光 + 细雨条纹 + 湿润反光地面，
#   于峰值瞬间叠加一道强方向性闪光（M29_FlashSun + 天光瞬时提亮 + 曝光微抬），抓拍一张戏剧化雷暴帧。
#   与 day / dusk / night(M24) / golden(M26) / snow(M27) / rain(M28) 形成第 7 种时段/天气氛围。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。结束恢复白昼基线（world/sun/exposure/flash）。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M29_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

# 闪电参数：建筑面仍 37% 饱和。决定性下调：弱闪光让建筑面回落可读（宁可偏暗也不全白）。
FLASH_ENERGY = 90.0
FLASH_WORLD_STRENGTH = 0.06
FLASH_EXPOSURE = -0.34


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 1) 配置 Cycles GPU (OptiX) ----
cpref = bpy.context.preferences.addons['cycles'].preferences
cpref.compute_device_type = 'OPTIX'
cpref.get_devices()
for d in cpref.devices:
    if d.type in ('OPTIX', 'CUDA'):
        d.use = True

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.view_settings.view_transform = 'AgX'

m06 = load(M06, "m06l")


def hide_previews():
    h = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            h.append((o, o.hide_render))
            o.hide_render = True
    return h


def show(h):
    for o, was in h:
        o.hide_render = was


# ---- 2) 以 day 为已知基线 ----
m06.build_lighting("day")


# ---- 3) 雨夜暴风冷蓝天光（闪电前为暗调；闪光时临时提亮）----
def make_rain_world():
    w = bpy.data.worlds.new("M29_RainWorld")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 1.0
    # 暗蓝灰天顶 → 略亮地平线（阴雨散射、低对比）
    ramp.color_ramp.elements[0].color = (0.09, 0.12, 0.17, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.18, 0.22, 0.28, 1.0)
    ramp.color_ramp.elements[1].color = (0.30, 0.34, 0.38, 1.0)
    bg.inputs["Strength"].default_value = 0.35
    return w


sc.world = make_rain_world()

sun = bpy.data.objects.get("M6_Sun")
if sun:
    sun.location = (40.0, -30.0, 50.0)
    sun.data.energy = 0.6
    sun.data.color = (0.60, 0.70, 0.90)
    sun.data.angle = 0.02
    sun.data.shadow_soft_size = 8.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = -0.3


# ---- 4) 闪电闪光灯（强方向性 SUN，置于场地一角高空，投影扫过校园）----
flash_lamp = bpy.data.lights.new(PREFIX + "FlashLamp", 'SUN')
flash_lamp.energy = FLASH_ENERGY
flash_lamp.color = (0.80, 0.86, 1.0)
flash_lamp.angle = 0.015
flash_lamp.shadow_soft_size = 2.0
flash_obj = bpy.data.objects.new(PREFIX + "FlashSun", flash_lamp)
bpy.context.collection.objects.link(flash_obj)
flash_obj.location = (55.0, 45.0, 95.0)
flash_obj.rotation_euler = (mathutils.Vector((0.0, 0.0, 0.0)) - flash_obj.location).to_track_quat("-Z", "Y").to_euler()


# ---- 5) 湿润反光地面材质 + 覆盖层 ----
def make_wet_material():
    mat = bpy.data.materials.new(PREFIX + "WetMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    # 闪电帧：湿地改为"湿但不镜面"——提高糙度、降清漆，避免近镜面把闪光反射成全屏饱和高光
    outn.inputs["Roughness"].default_value = 0.32
    outn.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.02, 0.03, 0.05, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.0
    if "Clearcoat" in outn.inputs:
        outn.inputs["Clearcoat"].default_value = 0.35
    if "Clearcoat Roughness" in outn.inputs:
        outn.inputs["Clearcoat Roughness"].default_value = 0.3
    return mat


wet_mat = make_wet_material()

n_ground = 0
ground = bpy.data.objects.get("Ground")
if ground is not None:
    gsn = ground.copy()
    gsn.data = ground.data.copy()
    gsn.name = PREFIX + "GroundWet"
    gsn.location.z += 0.05
    bpy.context.collection.objects.link(gsn)
    gsn.data.materials.clear()
    gsn.data.materials.append(wet_mat)
    n_ground = 1


# ---- 6) 雨丝材质（冷色微自发光）----
def make_rain_material():
    mat = bpy.data.materials.new(PREFIX + "RainMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.62, 0.72, 0.90, 1.0)
    outn.inputs["Roughness"].default_value = 0.4
    outn.inputs["Metallic"].default_value = 0.0
    outn.inputs["Alpha"].default_value = 0.55
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.35, 0.45, 0.65, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.5
    mat.blend_method = 'BLEND'
    return mat


rain_mat = make_rain_material()


# ---- 7) 雨丝实例模板（细长圆柱，略带风斜）----
streak = bpy.data.meshes.new(PREFIX + "StreakMesh")
bstreak = bpy.data.objects.new(PREFIX + "RainStreak", streak)
bpy.context.collection.objects.link(bstreak)
bpy.context.view_layer.objects.active = bstreak
bstreak.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=1.8, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
bstreak.data.materials.clear()
bstreak.data.materials.append(rain_mat)
bstreak.rotation_euler = (0.18, 0.0, 0.05)
bstreak.scale = (1.0, 1.0, 1.0)
bstreak.location = (0.0, 0.0, -500.0)
bstreak.hide_viewport = True
bstreak.hide_render = True


# ---- 8) 雨丝粒子发射体（覆盖全校园的体积）----
emit = bpy.data.objects.new(PREFIX + "RainEmitter", bpy.data.meshes.new(PREFIX + "EmitMesh"))
bpy.context.collection.objects.link(emit)
bpy.context.view_layer.objects.active = emit
emit.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
bpy.ops.object.mode_set(mode='OBJECT')
emit.scale = (110.0, 110.0, 30.0)
emit.location = (0.0, 0.0, 15.0)
mod = emit.modifiers.new(PREFIX + "RainPS", 'PARTICLE_SYSTEM')
ps = emit.particle_systems[0]
pset = ps.settings
pset.count = 1600
pset.frame_start = 1
pset.frame_end = 1
pset.lifetime = 2000
pset.emit_from = 'VOLUME'
pset.distribution = 'RAND'
pset.physics_type = 'NO'
pset.particle_size = 1.0
pset.render_type = 'OBJECT'
pset.instance_object = bstreak
pset.brownian_factor = 0.0
pset.normal_factor = 0.0
pset.use_modifier_stack = False
n_particles = pset.count

eminvis = bpy.data.materials.new(PREFIX + "EmitInvis")
eminvis.use_nodes = True
ent = eminvis.node_tree
ent.nodes.clear()
tn = ent.nodes.new("ShaderNodeBsdfTransparent")
ep = ent.nodes.new("ShaderNodeOutputMaterial")
ent.links.new(tn.outputs["BSDF"], ep.inputs["Surface"])
emit.data.materials.clear()
emit.data.materials.append(eminvis)
sc.frame_set(1)


# ---- 9) 相机复用 ----
def get_cam(name, loc, tgt, lens=35.0, fallback=True):
    c = bpy.data.objects.get(name)
    if c is not None:
        return c, False
    if not fallback:
        return None, False
    cam_data = bpy.data.cameras.new(PREFIX + name)
    cam_data.sensor_width = 36.0
    cam_data.lens = lens
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new(PREFIX + name, cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = mathutils.Vector(loc)
    cam.rotation_euler = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam, True


hero_cam, hero_built = get_cam("M19C_HeroDay", HERO_LOC, HERO_TGT, 35.0)
aerial_cam, aerial_built = get_cam("M11_CamAerial", AERIAL_LOC, AERIAL_TGT, 35.0)


# ---- 10) 渲染配置 + 出图（闪光态）----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


def flash_on():
    # 峰值闪光：天光瞬时提亮 + 曝光微抬（闪光灯本身已强方向性）
    for w in bpy.data.worlds:
        if w.name == "M29_RainWorld":
            for n in w.node_tree.nodes:
                if n.type == 'BACKGROUND':
                    n.inputs["Strength"].default_value = FLASH_WORLD_STRENGTH
    sc.view_settings.exposure = FLASH_EXPOSURE


def render_shot(cam, out_path):
    sc.camera = cam
    sc.render.resolution_x = 2560
    sc.render.resolution_y = 1440
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = out_path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


hidden_stack = []
shots = {}
try:
    hidden_stack += hide_previews()
    cfg_samples()
    flash_on()
    shots["hero"] = (os.path.join(OUT_DIR, "m29_lightning_hero.png"),
                     render_shot(hero_cam, os.path.join(OUT_DIR, "m29_lightning_hero.png")))
    shots["aerial"] = (os.path.join(OUT_DIR, "m29_lightning_aerial.png"),
                       render_shot(aerial_cam, os.path.join(OUT_DIR, "m29_lightning_aerial.png")))
finally:
    show(hidden_stack)


# ---- 11) 恢复白昼基线（不残留 M29_ 物体 / 世界 / 材质 / 网格 / 灯光）----
def restore():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)
    for me in [me for me in bpy.data.meshes if me.name.startswith(PREFIX)]:
        bpy.data.meshes.remove(me)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    for lt in [lt for lt in bpy.data.lights if lt.name.startswith(PREFIX)]:
        bpy.data.lights.remove(lt)
    try:
        m06.build_lighting("day")
    except Exception as _e:
        print("restore build_lighting warning:", _e)
    for w in [w for w in bpy.data.worlds if w.name.startswith(PREFIX)]:
        bpy.data.worlds.remove(w)


restore()

if sc.world is None:
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w


import os as _os
result = {
    "milestone": "M29",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "flash_energy": FLASH_ENERGY,
    "flash_world_strength": FLASH_WORLD_STRENGTH,
    "flash_exposure": FLASH_EXPOSURE,
    "wet_ground_overlay": n_ground,
    "rain_particles": n_particles,
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M29_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M29_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M29_RESULT=" + repr(result))
