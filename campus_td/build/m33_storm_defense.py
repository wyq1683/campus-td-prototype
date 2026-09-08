# m33_storm_defense.py — 里程碑 M33：暴风夜塔防作战渲染（Storm Night Defense · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M33_ 前缀临时世界/雨丝/湿地/塔基点光/相机；结束恢复全部状态。
# 思路：把已验证的 M28「雨夜」天气层 与 M24「夜间塔防发光」层 合成一帧——
#   暴风冷暗天光 + 细雨条纹 + 湿润反光地面 + 防御塔发光环/辉光壳提亮 + 塔基冷光池，
#   让 4 座防御塔在暴风雨夜中清晰可辨，凸显塔防主题。复用 M19C_HeroDay / M11_CamAerial 双机位。
# 渲染 Cycles GPU OptiX / 256 samples / 2560×1440 / AgX / 双视角。
# 曝光经验：沿用 M29 教训——湿地"湿而不镜面"(rough 0.18 / clearcoat 0.9) 避免把塔环反射成全屏高光；
#   天光保持暗(strength 0.26)让塔环成为主视觉，exp -0.10。
import bpy, mathutils, importlib.util, os, time, struct

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M33_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)


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


# ---- 2) 以 day 为已知基线（确保 M6_Sun / 天穹 / 辉光壳 存在）----
m06.build_lighting("day")

sun = bpy.data.objects.get("M6_Sun")

# ---- 3) 保存塔环/辉光壳发光强度（用于结束恢复）----
glow_saved = []
for mat in bpy.data.materials:
    if "glow" in mat.name.lower() and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                glow_saved.append((mat.name, n.inputs["Strength"].default_value))

halo_saved = []
for mat in bpy.data.materials:
    if mat.name.startswith("M6_HaloMat"):
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                halo_saved.append((mat.name, n.inputs["Strength"].default_value))


# ---- 4) 暴风冷暗夜天光 ----
def make_storm_world():
    w = bpy.data.worlds.new("M33_StormWorld")
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
    # 极暗冷蓝暴风天顶 → 略亮阴沉地平线（低对比、风雨散射）
    ramp.color_ramp.elements[0].color = (0.05, 0.06, 0.11, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.03, 0.04, 0.09, 1.0)
    ramp.color_ramp.elements[1].color = (0.07, 0.09, 0.13, 1.0)
    bg.inputs["Strength"].default_value = 0.26
    return w


sc.world = make_storm_world()

if sun:
    sun.location = (40.0, -30.0, 50.0)
    sun.data.energy = 0.7
    sun.data.color = (0.55, 0.68, 1.0)
    sun.data.angle = 0.02
    sun.data.shadow_soft_size = 6.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = -0.10

# ---- 5) 提亮塔防发光环 + 辉光壳（夜战主视觉）----
for mat in bpy.data.materials:
    if "glow" in mat.name.lower() and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                n.inputs["Strength"].default_value = 9.0
for mat in bpy.data.materials:
    if mat.name.startswith("M6_HaloMat"):
        for n in mat.node_tree.nodes:
            if n.type == "EMISSION":
                n.inputs["Strength"].default_value = 6.0


# ---- 6) 湿润反光地面材质（湿而不镜面，避免塔环反射全屏高光）----
def make_wet_material():
    mat = bpy.data.materials.new(PREFIX + "WetMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(outn.outputs["BSDF"], outp.inputs["Surface"])
    outn.inputs["Base Color"].default_value = (0.03, 0.04, 0.06, 1.0)
    outn.inputs["Roughness"].default_value = 0.18
    outn.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in outn.inputs:
        outn.inputs["Emission Color"].default_value = (0.02, 0.03, 0.05, 1.0)
        outn.inputs["Emission Strength"].default_value = 0.0
    if "Clearcoat" in outn.inputs:
        outn.inputs["Clearcoat"].default_value = 0.9
    if "Clearcoat Roughness" in outn.inputs:
        outn.inputs["Clearcoat Roughness"].default_value = 0.12
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


# ---- 7) 雨丝材质（冷色微自发光，暗背景中读出纤细条纹）----
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


# ---- 8) 雨丝实例模板（细长圆柱，略带风斜）----
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
bstreak.rotation_euler = (0.18, 0.0, 0.08)   # 暴风斜雨
bstreak.scale = (1.0, 1.0, 1.0)
bstreak.location = (0.0, 0.0, -500.0)
bstreak.hide_viewport = True
bstreak.hide_render = True


# ---- 9) 雨丝粒子发射体（覆盖全校园的体积）----
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
pset.count = 2000
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


# ---- 10) 塔基冷光池（让塔在地面投出冷光，呼应 M24 夜战布光）----
towers = [o for o in bpy.data.objects if o.name.startswith("Tower_") and o.type == 'MESH']
n_tlights = 0
for i, o in enumerate(towers):
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    cx = sum(v.x for v in bb) / 8.0
    cy = sum(v.y for v in bb) / 8.0
    cz = sum(v.z for v in bb) / 8.0
    bpy.ops.object.light_add(type='POINT')
    pl = bpy.context.object
    pl.name = f"{PREFIX}TLight_{i}"
    pl.data.name = f"{PREFIX}TLight_{i}"
    pl.location = (cx, cy, cz + 0.5)
    pl.data.energy = 120.0
    pl.data.color = (0.7, 0.8, 1.0)
    pl.data.shadow_soft_size = 2.0
    try:
        pl.data.cutoff_distance = 45.0
    except Exception:
        pass
    n_tlights += 1


# ---- 11) 相机复用（已验证机位，不新建不破坏）----
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


# ---- 12) 渲染配置 + 出图 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


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


def pil_stats(path):
    try:
        from PIL import Image
        import numpy as _np
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
        a = _np.asarray(im).astype(_np.float32)
        mean = a.mean()
        r = a[:, :, 0].mean(); g = a[:, :, 1].mean(); b = a[:, :, 2].mean()
        over = (a > 248).mean() * 100.0
        dark = (a.mean(axis=2) < 8).mean() * 100.0
        nonblack = (a.mean(axis=2) > 4).mean() * 100.0
        return {"mean": round(mean, 1), "meanRGB": [round(r, 1), round(g, 1), round(b, 1)],
                "over_pct": round(over, 2), "dark_pct": round(dark, 2), "nonblack_pct": round(nonblack, 1)}
    except Exception as _e:
        return {"error": str(_e)}


hidden_stack = []
shots = {}
try:
    hidden_stack += hide_previews()
    cfg_samples()
    hero_out = os.path.join(OUT_DIR, "m33_storm_defense_hero.png")
    aerial_out = os.path.join(OUT_DIR, "m33_storm_defense_aerial.png")
    shots["hero"] = (hero_out, render_shot(hero_cam, hero_out))
    shots["aerial"] = (aerial_out, render_shot(aerial_cam, aerial_out))
    shots["stats"] = {
        "hero": pil_stats(hero_out),
        "aerial": pil_stats(aerial_out),
    }
finally:
    show(hidden_stack)


# ---- 13) 恢复全部状态（仅落盘 PNG，不残留 M33_ 物体 / 世界 / 材质）----
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
    try:
        m06.build_lighting("day")
    except Exception as _e:
        print("restore build_lighting warning:", _e)
    for w in [w for w in bpy.data.worlds if w.name.startswith(PREFIX)]:
        bpy.data.worlds.remove(w)
    if "M33_StormWorld" in bpy.data.worlds:
        bpy.data.worlds.remove(bpy.data.worlds["M33_StormWorld"])
    # 恢复塔环/辉光壳发光强度
    for mn, val in glow_saved:
        m = bpy.data.materials.get(mn)
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = val
    for mn, val in halo_saved:
        m = bpy.data.materials.get(mn)
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = val


restore()

if sc.world is None:
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w

import os as _os
result = {
    "milestone": "M33",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [2560, 1440],
    "wet_ground_overlay": n_ground,
    "rain_particles": n_particles,
    "towers_lit": n_tlights,
    "shots": {k: {
        "out": v[0],
        "size": _os.path.getsize(v[0]) if _os.path.exists(v[0]) else None,
        "time_s": round(v[1], 1),
    } for k, v in shots.items() if k != "stats"},
    "stats": shots.get("stats", {}),
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else "M33_M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else "M33_M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
}
print("M33_RESULT=" + repr(result))
