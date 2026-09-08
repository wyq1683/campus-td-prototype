# m25_atmosphere.py — 里程碑 M25：大气体积雾（Atmospheric Volumetric Fog / Morning Mist）
# 非破坏：不删/不改任何既有物体。仅新建 M25_ 前缀的体积雾盒 + 材质（持久化为电影级景深雾）。
# 思路：在 96m 校园上空罩一层低密度的 Principled Volume 雾盒，给白昼英雄机位加电影级大气景深，
#   远处楼体在雾中淡出、近处保持锐利，强化"可进入的真实校园"的体积感与晨雾氛围。
# 避坑（沿用 PLAN.md）：
#   - 体积材质走 ShaderNodeVolumePrincipled 的 Volume 输出接到 Material Output 的 Volume 输入；
#     不用 Surface，避免盒子被当成实心不透明体。
#   - 雾盒 hide_viewport=True（不污染艺术家视口），但 hide_render=False（渲染时仍包含）。
#   - 密度 0.012 偏低，仅作景深雾，不上 OOM（M20 实测 >2560×1440 才 OOM，本档 1920×1080 安全）。
# 渲染 Cycles GPU OptiX / 256 samples / 1920×1080 / AgX。
import bpy, mathutils, importlib.util, os, time

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT = BASE + r"/previews/m25_atmosphere.png"
PREFIX = "M25_"

HERO_LOC = (-52.0, -58.0, 48.0)
HERO_TGT = (0.0, -2.0, 6.0)


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

# ---- 2) 以 day 为基线（确保 M6_Sun / 天穹 / 辉光壳 存在）----
m06.build_lighting("day")


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


# ---- 3) 幂等清理旧 M25_ 物体/材质/相机 ----
for o in list(bpy.data.objects):
    if o.name.startswith(PREFIX):
        bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
    bpy.data.cameras.remove(c)
for mat in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
    bpy.data.materials.remove(mat)


# ---- 4) 建大气体积雾盒 ----
def make_fog_material():
    mat = bpy.data.materials.new(PREFIX + "FogMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    # 低密度晨雾：近处锐利、远处淡出，偏冷色
    vol.inputs["Density"].default_value = 0.012
    vol.inputs["Anisotropy"].default_value = 0.30
    vol.inputs["Color"].default_value = (0.80, 0.84, 0.88, 1.0)
    # 不发光、不加热力图；纯散射雾
    vol.inputs["Emission Strength"].default_value = 0.0
    return mat


fog_mat = make_fog_material()

# 体积雾盒：覆盖 96m 场地，从地面 0 到约 14m 高，罩住整片校园
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -3.0, 6.0))
fog = bpy.context.active_object
fog.name = PREFIX + "Fog"
fog.scale = (90.0, 90.0, 14.0)   # 全尺寸 90×90×14，z 跨 -1..13
fog.hide_viewport = True          # 不污染 3D 视口
fog.hide_render = False           # 但参与渲染
if fog.data.materials:
    fog.data.materials[0] = fog_mat
else:
    fog.data.materials.append(fog_mat)

# 体积步进取样：适度提高精度让雾过渡平滑（不显著增负）
try:
    sc.cycles.volume_step_rate = 1.5
except Exception:
    pass


# ---- 5) 相机：复用已验证英雄机位 M19C_HeroDay，缺失则自建 M25_Cam ----
cam = bpy.data.objects.get("M19C_HeroDay")
built_cam = False
if cam is None:
    cam_data = bpy.data.cameras.new(PREFIX + "HeroCam")
    cam_data.sensor_width = 36.0
    cam_data.lens = 35.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new(PREFIX + "HeroCam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = mathutils.Vector(HERO_LOC)
    cam.rotation_euler = (mathutils.Vector(HERO_TGT) - mathutils.Vector(HERO_LOC)).to_track_quat("-Z", "Y").to_euler()
    built_cam = True
sc.camera = cam


# ---- 6) 渲染配置 + 出图 ----
def cfg_samples():
    sc.cycles.device = 'GPU'
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.samples = 256
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'


hidden_stack = []
try:
    hidden_stack += hide_previews()
    cfg_samples()
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = OUT
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    t_render = time.time() - t0
finally:
    show(hidden_stack)

import os as _os
result = {
    "milestone": "M25",
    "device": sc.cycles.device,
    "compute_device_type": cpref.compute_device_type,
    "denoiser": sc.cycles.denoiser,
    "samples": sc.cycles.samples,
    "resolution": [1920, 1080],
    "fog_density": 0.012,
    "fog_box_dims": [90, 90, 14],
    "fog_persisted_hide_viewport": True,
    "reused_cam": ("M19C_HeroDay" if not built_cam else "M25_HeroCam"),
    "cam_loc": list(cam.location),
    "out": OUT,
    "size": _os.path.getsize(OUT) if _os.path.exists(OUT) else None,
    "time_s": round(t_render, 1),
    "n_obj_after": len(bpy.data.objects),
}
