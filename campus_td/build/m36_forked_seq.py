# m36_forked_seq.py — 里程碑 M36：分叉电弧多帧序列（Forked Lightning Sequence · OptiX）
# 非破坏：不删/不改任何既有物体。仅新建 M36_ 前缀临时世界/物体（结束恢复），仅落盘 PNG/MP4。
#
# 定位：把 M32（多帧闪电序列，但电弧是 12 段直线）与 M34（程序化分叉/树状闪电，但只有单帧）合流，
#   并在物理真实性上再进一步——按真实雷击的三段式放电过程给出**三组不同的电弧几何**：
#     ① 梯级先导（stepped leader）：主通道尚未击穿时的暗淡细通道，仅 charge 帧可见；
#        关键：先导与主回击**共用同一条通道折线**（同 rng 路径），符合"回击沿先导电离通道返回"的物理；
#     ② 主回击（return stroke）：完整分叉主干 + 支络，最亮，仅 peak 帧可见；
#     ③ 二次放电（subsequent stroke）：另一处、另一 seed 的独立分叉闪电，仅 flick 帧可见
#        （M32 的缺陷是峰帧/二次帧复用同一道电弧，看起来像同一道闪两次）。
#   雨夜底层沿用 M28/M29/M33 已验证配方；峰值曝光沿用 M29 获胜参数（energy90/world0.06/exp-0.34，零过曝）。
#
# 渲染 Cycles GPU OptiX / 256 samples / 1920×1080(英雄序列) + 2560×1440(鸟瞰峰帧) / AgX。
# 复用 M19C_HeroDay / M11_CamAerial 机位。结束恢复白昼基线（world/sun/exposure）。
# 全部几何用 bmesh 直建（create_cone 等径 = 圆柱；无 create_cylinder），彻底规避 MCP exec 内 mode_set。
import bpy, mathutils, importlib.util, os, time, random
import bmesh

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M36_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

# 闪电序列：每帧 (tag, flash_sun_energy, world_strength, exposure, 可见电弧组)
# 组名 None / "leader" / "main" / "sec"
# 时间线：预暗 → 梯级先导 → 主回击峰 → 余辉 → 二次放电 → 衰减 → 残光
# 经验收敛：M36v1 energy90→v2 62→v3 32（M29 6 轮调参经验：AgX 高光压缩区 meanLum>120+bright%>40
#   会被强制拉白 → 必须把整帧亮度压在 100 左右，靠电弧自发光强度而非闪光能量体现"被照亮"）
FRAMES = [
    ("pre",    0.0,  0.04, -0.36, None),
    ("charge",  7.0, 0.04, -0.34, "leader"),
    ("peak",   32.0, 0.05, -0.34, "main"),
    ("glow",   12.0, 0.07, -0.28, None),
    ("flick",  20.0, 0.05, -0.32, "sec"),
    ("decay",   8.0, 0.05, -0.30, None),
    ("resid",   3.0, 0.04, -0.33, None),
]

SEED_MAIN = 36
SEED_SEC = 361
MAX_BRANCH = 4          # 每道闪电最多派生分叉数（M34 的隐式计数导致分叉偏少，此处显式）


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


# ---- 3) 雨夜暴风冷蓝天光 ----
def make_storm_world():
    w = bpy.data.worlds.new(PREFIX + "StormWorld")
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
    ramp.color_ramp.elements[0].color = (0.09, 0.12, 0.17, 1.0)
    e1 = ramp.color_ramp.elements.new(0.5)
    e1.color = (0.18, 0.22, 0.28, 1.0)
    ramp.color_ramp.elements[1].color = (0.30, 0.34, 0.38, 1.0)
    bg.inputs["Strength"].default_value = 0.05
    return w


storm_world = make_storm_world()
sc.world = storm_world

sun = bpy.data.objects.get("M6_Sun")
if sun:
    sun.location = (40.0, -30.0, 50.0)
    sun.data.energy = 0.6
    sun.data.color = (0.55, 0.68, 1.0)
    sun.data.angle = 0.02
    sun.data.shadow_soft_size = 8.0
    direction = mathutils.Vector((0.0, 0.0, 0.0)) - sun.location
    sun.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = -0.34


# ---- 4) 闪电闪光灯（强方向性 SUN，逐帧改 energy）----
flash_lamp = bpy.data.lights.new(PREFIX + "FlashLamp", 'SUN')
flash_lamp.energy = 0.0
flash_lamp.color = (0.80, 0.86, 1.0)
flash_lamp.angle = 0.015
flash_lamp.shadow_soft_size = 2.0
flash_obj = bpy.data.objects.new(PREFIX + "FlashSun", flash_lamp)
bpy.context.collection.objects.link(flash_obj)
flash_obj.location = (55.0, 45.0, 95.0)
flash_obj.rotation_euler = (mathutils.Vector((0.0, 0.0, 0.0)) - flash_obj.location).to_track_quat("-Z", "Y").to_euler()


# ---- 5) 湿润地面（湿而不镜面：规避 M29 全屏高光教训）----
def make_wet_material():
    mat = bpy.data.materials.new(PREFIX + "WetMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.32
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Clearcoat" in bsdf.inputs:
        bsdf.inputs["Clearcoat"].default_value = 0.35
    if "Clearcoat Roughness" in bsdf.inputs:
        bsdf.inputs["Clearcoat Roughness"].default_value = 0.3
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


# ---- 6) 雨丝 ----
def make_rain_material():
    mat = bpy.data.materials.new(PREFIX + "RainMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.62, 0.72, 0.90, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Alpha"].default_value = 0.55
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (0.35, 0.45, 0.65, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.5
    mat.blend_method = 'BLEND'
    return mat


def make_cylinder_mesh(name, radius, depth, segs=6):
    """bmesh 直建圆柱：create_cone 等径即圆柱（Blender 5.2 无 bmesh create_cylinder）。"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                          radius1=radius, radius2=radius, depth=depth)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


rain_mat = make_rain_material()
streak_mesh = make_cylinder_mesh(PREFIX + "StreakMesh", 0.012, 1.8, 5)
bstreak = bpy.data.objects.new(PREFIX + "RainStreak", streak_mesh)
bpy.context.collection.objects.link(bstreak)
bstreak.data.materials.clear()
bstreak.data.materials.append(rain_mat)
bstreak.rotation_euler = (0.18, 0.0, 0.05)
bstreak.location = (0.0, 0.0, -500.0)
bstreak.hide_viewport = True
bstreak.hide_render = True

emit_cube = bpy.data.meshes.new(PREFIX + "EmitMesh")
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bm.to_mesh(emit_cube)
bm.free()
emit = bpy.data.objects.new(PREFIX + "RainEmitter", emit_cube)
bpy.context.collection.objects.link(emit)
emit.scale = (110.0, 110.0, 30.0)
emit.location = (0.0, 0.0, 15.0)
emit.modifiers.new(PREFIX + "RainPS", 'PARTICLE_SYSTEM')
pset = emit.particle_systems[0].settings
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


# ---- 7) 程序化分叉闪电（三组：先导 / 主回击 / 二次放电）----
def make_bolt_material(suffix, emis, base):
    mat = bpy.data.materials.new(PREFIX + "BoltMat_" + suffix)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = base
        bsdf.inputs["Emission Strength"].default_value = emis
    mat.blend_method = 'OPAQUE'
    return mat


def add_bolt_segment(group, a, b, mat, r):
    vec = b - a
    length = vec.length
    if length < 1e-4:
        return None
    me = make_cylinder_mesh(PREFIX + group + "_Seg", max(r, 0.02), length, 5)
    o = bpy.data.objects.new(PREFIX + group + "_Seg", me)
    bpy.context.collection.objects.link(o)
    o.location = (a + b) / 2.0
    o.rotation_euler = vec.to_track_quat("-Z", "Y").to_euler()
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.hide_render = True
    o.hide_viewport = True
    return o


def bolt_channel(top, bot, rng, trunk=11, displace=5.0):
    """递归中点位移生成主通道折线（中段位移最大、两端收敛）。"""
    pts = [top.lerp(bot, i / trunk) for i in range(trunk + 1)]
    for i in range(1, trunk):
        f = 1.0 - abs((i / trunk) - 0.5) * 1.2
        off = mathutils.Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        pts[i] += off * displace * max(f, 0.15)
    return pts


def trunk_segments(pts, r0=0.16, taper=0.6):
    """仅主干（先导用）。"""
    n = len(pts) - 1
    return [(pts[i], pts[i + 1], r0 * (1 - i / n * taper)) for i in range(n)]


def branch_segments(pts, rng, displace=5.0, max_branch=MAX_BRANCH):
    """沿主通道中段随机派生分叉支络（带次级位移、半径骤减）。显式计数，避免 M34 隐式判据致分叉偏少。"""
    segs = []
    n = len(pts) - 1
    nb = 0
    for i in range(1, n - 1):
        if nb >= max_branch:
            break
        if rng.random() < 0.5:
            dir_main = (pts[i + 1] - pts[i - 1]).normalized()
            dev = mathutils.Euler((rng.uniform(-1.1, 1.1), rng.uniform(-1.1, 1.1), rng.uniform(-1.1, 1.1)))
            bdir = dir_main.copy()
            bdir.rotate(dev)
            blen = rng.uniform(7.0, 17.0)
            bend = pts[i] + bdir * blen
            bs = rng.randint(3, 6)
            bpts = [pts[i].lerp(bend, j / bs) for j in range(bs + 1)]
            for k in range(1, bs):
                boff = mathutils.Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                bpts[k] += boff * displace * 0.35
            for k in range(bs):
                segs.append((bpts[k], bpts[k + 1], 0.06))
            nb += 1
    return segs, nb


mat_leader = make_bolt_material("Leader", 1.5, (0.55, 0.70, 1.0, 1.0))    # 先导：暗淡偏蓝
mat_main = make_bolt_material("Main", 8.0, (0.82, 0.91, 1.0, 1.0))        # 主回击：最亮近白（M36v3 由 16→8，配合 flash 32 控住高光）
mat_sec = make_bolt_material("Sec", 5.0, (0.78, 0.88, 1.0, 1.0))          # 二次放电：略暗

# 主回击：3 道（中庭偏前 / 东南 / 西南），与 M34 同布局，保证英雄+鸟瞰均有可见主干
MAIN_ROOTS = [
    (mathutils.Vector((-10.0, 22.0, 86.0)), mathutils.Vector((-6.0, -4.0, 14.0))),
    (mathutils.Vector((36.0, -28.0, 82.0)), mathutils.Vector((12.0, -14.0, 13.0))),
    (mathutils.Vector((-42.0, -18.0, 84.0)), mathutils.Vector((-26.0, -30.0, 13.0))),
]
# 二次放电：另一处（东北 / 正南），独立 seed → 与主回击**不是同一道**
SEC_ROOTS = [
    (mathutils.Vector((30.0, 34.0, 88.0)), mathutils.Vector((18.0, 10.0, 13.5))),
    (mathutils.Vector((-24.0, -46.0, 80.0)), mathutils.Vector((-14.0, -34.0, 13.0))),
]

rng_main = random.Random(SEED_MAIN)
rng_sec = random.Random(SEED_SEC)

leader_objs, main_objs, sec_objs = [], [], []
n_branch_main = n_branch_sec = 0

# 主回击 + 先导：先导复用**第一道主通道的同一折线**（回击沿先导电离通道返回，物理正确）
first_channel = None
for idx, (top, bot) in enumerate(MAIN_ROOTS):
    pts = bolt_channel(top, bot, rng_main)
    if idx == 0:
        first_channel = pts
    for (a, b, r) in trunk_segments(pts):
        o = add_bolt_segment("MainBolt", a, b, mat_main, r)
        if o:
            main_objs.append(o)
    bsegs, nb = branch_segments(pts, rng_main)
    n_branch_main += nb
    for (a, b, r) in bsegs:
        o = add_bolt_segment("MainBolt", a, b, mat_main, r)
        if o:
            main_objs.append(o)

# 先导：同通道、更细（半径 ~1/3）、无分叉、暗淡
for (a, b, r) in trunk_segments(first_channel, r0=0.055, taper=0.5):
    o = add_bolt_segment("Leader", a, b, mat_leader, r)
    if o:
        leader_objs.append(o)

# 二次放电
for (top, bot) in SEC_ROOTS:
    pts = bolt_channel(top, bot, rng_sec)
    for (a, b, r) in trunk_segments(pts, r0=0.13):
        o = add_bolt_segment("SecBolt", a, b, mat_sec, r)
        if o:
            sec_objs.append(o)
    bsegs, nb = branch_segments(pts, rng_sec, max_branch=3)
    n_branch_sec += nb
    for (a, b, r) in bsegs:
        o = add_bolt_segment("SecBolt", a, b, mat_sec, r)
        if o:
            sec_objs.append(o)

BOLT_GROUPS = {"leader": leader_objs, "main": main_objs, "sec": sec_objs}


# ---- 8) 相机复用 ----
def get_cam(name, loc, tgt, lens=35.0):
    c = bpy.data.objects.get(name)
    if c is not None:
        return c, False
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


# ---- 9) 渲染配置 + 逐帧出图 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


def set_frame(f):
    tag, energy, world_strength, exp, group = f
    flash_lamp.energy = energy
    for n in storm_world.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs["Strength"].default_value = world_strength
    sc.view_settings.exposure = exp
    for gname, objs in BOLT_GROUPS.items():
        vis = (gname == group)
        for o in objs:
            o.hide_render = not vis
            o.hide_viewport = not vis


def render_shot(cam, out_path, w, h):
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
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
    for f in FRAMES:
        tag = f[0]
        set_frame(f)
        out = os.path.join(OUT_DIR, "m36_forked_seq_%s.png" % tag)
        dt = render_shot(hero_cam, out, 1920, 1080)
        shots[tag] = {"out": out, "time_s": round(dt, 1),
                      "size": os.path.getsize(out) if os.path.exists(out) else None}
    # 鸟瞰峰帧（额外 still，2560×1440）—— 与 v3 序列帧一致
    set_frame(("peak", 32.0, 0.05, -0.34, "main"))
    out_a = os.path.join(OUT_DIR, "m36_forked_seq_aerial_peak.png")
    dt = render_shot(aerial_cam, out_a, 2560, 1440)
    shots["aerial_peak"] = {"out": out_a, "time_s": round(dt, 1),
                            "size": os.path.getsize(out_a) if os.path.exists(out_a) else None}
finally:
    show(hidden_stack)


# ---- 10) 恢复白昼基线（不残留任何 M36_ 数据块）----
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
    "milestone": "M36",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "frames": len(FRAMES),
    "seq_res": [1920, 1080],
    "aerial_res": [2560, 1440],
    "wet_ground_overlay": n_ground,
    "rain_particles": n_particles,
    "bolt_segments": {"leader": len(leader_objs), "main": len(main_objs), "sec": len(sec_objs)},
    "branches": {"main": n_branch_main, "sec": n_branch_sec},
    "leader_shares_main_channel": True,
    "shots": {k: {"out": v["out"], "size": v["size"], "time_s": v["time_s"]} for k, v in shots.items()},
    "hero_cam_reused": ("M19C_HeroDay" if not hero_built else PREFIX + "M19C_HeroDay"),
    "aerial_cam_reused": ("M11_CamAerial" if not aerial_built else PREFIX + "M11_CamAerial"),
    "n_obj_after_restore": len(bpy.data.objects),
    "restored_world": sc.world.name,
    "residual_M36_objs": len([o for o in bpy.data.objects if o.name.startswith(PREFIX)]),
    "n_worlds": len(bpy.data.worlds),
}
print("M36_RESULT=" + repr(result))
