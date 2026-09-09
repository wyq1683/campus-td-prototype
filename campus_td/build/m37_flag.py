# m37_flag.py — 里程碑 M37：校门迎风校旗（Waving School Flag · OptiX）
# 非破坏（永久细节，零破坏既有物体）：
#   - 新建 M37_Flag（细分网格布旗，顶点风波动画）+ M37_FlagMat（校色双色旗，程序化节点）
#     + M37_Cam（校旗特写机位）。这些 M37_ 物体**持久化留存**（校园常驻细节）。
#   - 仅把旧的静止扁平板 M11_Flag（8 顶点 box / M5_FlagRed）设 hide_render 隐藏（不删除、可逆）。
#   - 复用 M11_FlagPole 作为旗杆挂载点（只读其世界坐标，不修改它）。
#   - 光照用黄金时刻（暖调，呼应「晨光中学」主题）；结束经 m06.build_lighting('day') 恢复白昼基线。
# 全部几何用 bmesh / from_pydata 直建，规避 MCP exec 内 mode_set。
import bpy, mathutils, importlib.util, os, time, math
import bmesh

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews"
PREFIX = "M37_"

# ---- 由场景读旗杆挂载点（不硬编码）----
pole = bpy.data.objects.get("M11_FlagPole")
if pole is not None:
    _pt = pole.matrix_world.translation
    POLE_X = float(_pt.x)
    POLE_TOP_Z = float(_pt.z) + float(pole.dimensions.z) / 2.0
else:
    POLE_X = -3.0
    POLE_TOP_Z = 12.0

FLAG_W = 3.6          # 沿 +X 宽（与旧 M11_Flag 一致）
FLAG_H = 2.2          # 沿 -Z 高
Z_TOP = POLE_TOP_Z - 0.15   # 旗顶略低于杆顶
NX, NY = 30, 20       # 细分段数（平滑风波）

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)
AERIAL_LOC = (0.0, -2.0, 120.0)
AERIAL_TGT = (0.0, 0.0, 0.0)

NAVY = (0.05, 0.09, 0.24, 1.0)
GOLD = (0.93, 0.78, 0.20, 1.0)
GOLD_EMBLEM = (1.0, 0.86, 0.30, 1.0)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---- 1) Cycles GPU (OptiX) ----
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


# ---- 2) 白昼基线 ----
m06.build_lighting("day")


# ---- 3) 黄金时刻暖调天光 ----
def make_golden_world():
    w = bpy.data.worlds.new(PREFIX + "GoldenWorld")
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
    rc = ramp.color_ramp
    rc.elements[0].position = 0.0
    rc.elements[0].color = (0.20, 0.26, 0.45, 1.0)     # 深蓝天穹
    rc.elements[1].position = 1.0
    rc.elements[1].color = (0.95, 0.80, 0.62, 1.0)     # 暖橙地平线
    e = rc.elements.new(0.55)
    e.color = (0.62, 0.55, 0.55, 1.0)                  # 蜜桃中带
    bg.inputs["Strength"].default_value = 0.55
    return w


# ---- 3) 白昼光照（保校旗 navy+gold 真实显色；黄金时刻暖光把校色染褐） ----
m06.build_lighting("day")


# ---- 4) 校色双色旗材质（程序化：navy 旗杆侧 + gold 旗面）----
def build_flag_material():
    mat = bpy.data.materials.new(PREFIX + "FlagMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])
    try:
        tex = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tex.outputs["UV"], sep.inputs["Vector"])
        # 旗杆侧 navy / 旗面 gold 硬切（UV.x）
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        rc = ramp.color_ramp
        rc.elements[0].position = 0.0
        rc.elements[0].color = NAVY
        rc.elements[1].position = 1.0
        rc.elements[1].color = GOLD
        a = rc.elements.new(0.33)
        a.color = NAVY
        b = rc.elements.new(0.33)
        b.color = GOLD
        # 双色旗面：navy 旗杆侧 + gold 旗面（ColorRamp 直连 Base Color）
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        # 轻微织物法线（Noise → Bump）
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 42.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.012
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        # 轻微织物法线
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 42.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.012
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    except Exception as _me:
        # 节点 API 异常时回退为纯金色旗面（仍是有效校旗）
        bsdf.inputs["Base Color"].default_value = GOLD
        print("flag_material_fallback:", _me)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Sheen" in bsdf.inputs:
        bsdf.inputs["Sheen"].default_value = 0.25
    return mat


# ---- 5) 清除旧的 M37_（幂等），建新旗 ----
def clear_old():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
    for me in [m for m in bpy.data.meshes if m.name.startswith(PREFIX)]:
        bpy.data.meshes.remove(me)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)


clear_old()

FLAG_BASE = []
FLAG_IJ = []
FLAG_MESH = None


def build_flag_geometry():
    global FLAG_MESH
    verts = []
    ij = []
    for j in range(NY + 1):
        for i in range(NX + 1):
            u = i / NX
            v = j / NY
            x = POLE_X + u * FLAG_W
            z = Z_TOP - (1.0 - v) * FLAG_H
            y = 0.0
            verts.append((x, y, z))
            ij.append((i, j, u, v))
    faces = []
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i
            b = a + 1
            c = a + (NX + 1)
            d = c + 1
            faces.append((a, b, d, c))
    me = bpy.data.meshes.new(PREFIX + "FlagGeo")
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for idx, (i, j, u, v) in enumerate(ij):
        uv.data[idx].uv = (u, v)
    me.update()
    FLAG_BASE.extend(verts)
    FLAG_IJ.extend(ij)
    FLAG_MESH = me
    return me


def set_flag_phase(t):
    """顶点风波动画：旗杆侧(u=0)钉死，振幅随 u 增大；含主波+次级波+重力下垂。"""
    A = 0.34
    freq = 2.4
    speed = 2.2
    for idx, (i, j, u, v) in enumerate(FLAG_IJ):
        bx, by, bz = FLAG_BASE[idx]
        amp = A * u
        dy = amp * math.sin(freq * u * math.pi * 2 - speed * t) \
            + 0.35 * amp * math.sin(2.3 * freq * u * math.pi * 2 - 1.7 * speed * t + 0.8)
        dz = 0.12 * amp * math.sin(freq * u * math.pi * 2 - speed * t + 1.5)
        droop = 0.10 * FLAG_H * u * u
        FLAG_MESH.vertices[idx].co = (bx, by + dy, bz + dz - droop)
    FLAG_MESH.update()


flag_mat = build_flag_material()
build_flag_geometry()
flag = bpy.data.objects.new(PREFIX + "Flag", FLAG_MESH)
bpy.context.collection.objects.link(flag)
flag.data.materials.clear()
flag.data.materials.append(flag_mat)
# 隐藏旧的静止扁平板（不删除、可逆）
old_flag = bpy.data.objects.get("M11_Flag")
if old_flag is not None:
    old_flag.hide_render = True
    old_flag.hide_viewport = True


# ---- 6) 相机 ----
def get_cam(name, loc, tgt, lens=35.0):
    c = bpy.data.objects.get(name)
    if c is not None:
        return c, False
    cd = bpy.data.cameras.new(PREFIX + name)
    cd.sensor_width = 36.0
    cd.lens = lens
    cd.clip_start = 0.1
    cd.clip_end = 1000.0
    cam = bpy.data.objects.new(PREFIX + name, cd)
    bpy.context.collection.objects.link(cam)
    cam.location = mathutils.Vector(loc)
    cam.rotation_euler = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam, True


hero_cam, _ = get_cam("M19C_HeroDay", HERO_LOC, HERO_TGT, 35.0)
aerial_cam, _ = get_cam("M11_CamAerial", AERIAL_LOC, AERIAL_TGT, 35.0)
flag_cam, _ = get_cam("M37_FlagCam",
                      (POLE_X + 5.0, -14.0, Z_TOP - FLAG_H * 0.5 - 1.6),
                      (POLE_X + FLAG_W * 0.4, 0.0, Z_TOP - FLAG_H * 0.5), 45.0)


# ---- 7) 渲染 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


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
    # 静止帧：金币冻结风波（t=0）
    set_flag_phase(0.0)
    out_hero = os.path.join(OUT_DIR, "m37_flag_hero.png")
    dt = render_shot(hero_cam, out_hero, 2560, 1440)
    shots["hero"] = {"out": out_hero, "time_s": round(dt, 1), "size": os.path.getsize(out_hero) if os.path.exists(out_hero) else None}

    out_aerial = os.path.join(OUT_DIR, "m37_flag_aerial.png")
    dt = render_shot(aerial_cam, out_aerial, 2560, 1440)
    shots["aerial"] = {"out": out_aerial, "time_s": round(dt, 1), "size": os.path.getsize(out_aerial) if os.path.exists(out_aerial) else None}

    out_close = os.path.join(OUT_DIR, "m37_flag_closeup.png")
    dt = render_shot(flag_cam, out_close, 1920, 1080)
    shots["closeup"] = {"out": out_close, "time_s": round(dt, 1), "size": os.path.getsize(out_close) if os.path.exists(out_close) else None}

    # 迎风飘动循环序列（无缝：t 跨一个完整周期 2π/speed）
    NLOOP = 16
    FPS = 12
    T = 2.0 * math.pi / 2.2
    loop_frames = []
    for k in range(NLOOP):
        tk = k * T / NLOOP
        set_flag_phase(tk)
        out_l = os.path.join(OUT_DIR, "m37_flag_loop_%03d.png" % k)
        dt = render_shot(flag_cam, out_l, 1280, 720)
        loop_frames.append(out_l)
        shots["loop_%03d" % k] = {"out": out_l, "time_s": round(dt, 1),
                                  "size": os.path.getsize(out_l) if os.path.exists(out_l) else None}
    # 回到冻结风波，让常驻旗在其它渲染里也呈自然垂坠
    set_flag_phase(0.0)
finally:
    show(hidden_stack)


# ---- 8) 恢复白昼基线（保留 M37_ 常驻旗/相机/材质）----
try:
    m06.build_lighting("day")
except Exception as _e:
    print("restore warning:", _e)
# 删除黄金时刻临时 world
for w in [w for w in bpy.data.worlds if w.name.startswith(PREFIX)]:
    bpy.data.worlds.remove(w)

if sc.world is None:
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    sc.world = w

import os as _os
result = {
    "milestone": "M37",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "pole_x": POLE_X,
    "pole_top_z": round(POLE_TOP_Z, 2),
    "flag_w": FLAG_W, "flag_h": FLAG_H,
    "flag_verts": len(FLAG_BASE),
    "old_flag_hidden": old_flag is not None,
    "shots": {k: {"out": v["out"], "size": v["size"], "time_s": v["time_s"]} for k, v in shots.items()},
    "loop_frames": len(loop_frames),
    "loop_fps": FPS,
    "n_obj_after": len(bpy.data.objects),
    "restored_world": sc.world.name,
    "residual_M37_objs": len([o for o in bpy.data.objects if o.name.startswith(PREFIX)]),
}
print("M37_RESULT=" + repr(result))
