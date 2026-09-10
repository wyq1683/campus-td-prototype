# -*- coding: utf-8 -*-
"""
M61 · 校园监控立杆（CCTV Security Camera Poles · OptiX）
============================================================================
项目已收官（M0–M60 ✅）。按「无未完成里程碑时自行增加改进项」新增 M61：
真实高中最典型的"平安校园"设施——周界安保监控摄像头，当前场景完全没有。
路灯(M43)/长椅(M48)/宣传栏(M49)都已沿内圈 6m 步行道布置，本里程碑把监控立杆
**间隔插值**到它们中间（不与任何已有周界设施重叠），补全"有人生活 + 安全校园"
的可信度。

坐标全部**从场景当前几何读取**（PLAN.md 铁律：M11 之后禁止硬编码建筑坐标）：
  - 校园边界 ← M11_Wall* 世界 AABB 并集（得中心与半幅）
  - 候选点 ← 与 M43 同款内圈 6m 矩形环，但**相位偏移 +7.5m**（落在 M43 路灯之间）
  - 避障 ← 跳过落在任一 Bldg_* AABB（外扩 1.5m）内的候选点；跳过南墙校门洞 x∈[-9,9]
  - 周界去重 ← 跳过距任一 M43_Pole / M48_* / M49_* 世界 XY < 2.8m 的候选（不撞路灯/长椅/宣传栏）

每根立杆（原型级、零破坏其它物体）：
  - 镀锌金属杆（高 4.5m，复用 PBR_Metal）
  - 顶部短臂伸向校园中心 + 摄像机头（深色塑料盒，正面朝中心）+ 暗色玻璃镜头 + 红色状态 LED
  - 顶部小太阳能板（深蓝，倾斜，区分于路灯的暖光头）
  - 杆身中部接线盒

避坑（沿用 PLAN.md + M43/M60 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 primitive + bmesh 直建，物体 scale 保持 1（matrix_world 烘焙）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M61_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Color / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M61_"

POLE_H = 4.5          # 立杆高（m）
POLE_R = 0.06         # 立杆半径（m）
ARM_LEN = 0.36        # 摄像机臂伸向校园中心（m）
INSET = 6.0           # 距围墙内退（m），同 M43
SPACING = 15.0        # 沿周长间距（m），同 M43
PHASE = 7.5           # 相位偏移，使立杆落在 M43 路灯之间
MAX_POLES = 20        # 上限
GATE_HALF = 9.0       # 南墙校门半宽（m）
BLD_MARGIN = 1.5      # 楼体避障外扩（m）
AVOID = 2.8           # 与已有周界设施（路灯/长椅/宣传栏）的最小净距（m）

# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs), max(c.x for c in cs),
            min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs)]


def clear_old():
    n = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
    for me in list(bpy.data.meshes):
        if me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def make_cylinder(name, r, h, seg=10):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def make_box(name):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def place(me, mat, loc, rotz=0.0, roty=0.0, scale=(1.0, 1.0, 1.0)):
    mat_ = (Matrix.Translation(Vector(loc))
            @ Matrix.Rotation(rotz, 4, "Z")
            @ Matrix.Rotation(roty, 4, "Y")
            @ Matrix.Diagonal(Vector((scale[0], scale[1], scale[2], 1.0))))
    o = bpy.data.objects.new(me.name, me)
    o.matrix_world = mat_
    if mat is not None:
        o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 校园范围
walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
wboxes = [aabb(o) for o in walls]
if wboxes:
    xmin = min(b[0] for b in wboxes); xmax = max(b[1] for b in wboxes)
    ymin = min(b[2] for b in wboxes); ymax = max(b[3] for b in wboxes)
else:
    xmin, xmax, ymin, ymax = -48, 48, -48, 48   # 兜底：96m 场地
cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
xi0, xi1 = xmin + INSET, xmax - INSET
yi0, yi1 = ymin + INSET, ymax - INSET

# ---------------------------------------------------------------- 楼体避障 AABB
blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]

def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False

def in_gate_gap(x, y):
    return (y < yi0 + 3.0) and (abs(x) < GATE_HALF)

# ---------------------------------------------------------------- 已有周界设施 XY（去重用）
occ_xy = []
for o in bpy.data.objects:
    if o.name.startswith(("M43_Pole", "M48_", "M49_")):
        occ_xy.append((o.matrix_world.translation.x, o.matrix_world.translation.y))

def near_occupant(x, y):
    for (ox, oy) in occ_xy:
        if math.hypot(x - ox, y - oy) < AVOID:
            return True
    return False

# ---------------------------------------------------------------- 候选点（相位偏移 +7.5m，落在路灯之间）
cands = []
for y in (yi0, yi1):
    L = xi1 - xi0
    n = max(1, int(round(L / SPACING)))
    x = xi0 + PHASE
    while x <= xi1 + 1e-6:
        cands.append((x, y))
        x += SPACING
for x in (xi0, xi1):
    L = yi1 - yi0
    n = max(1, int(round(L / SPACING)))
    yy = yi0 + PHASE
    while yy <= yi1 + 1e-6:
        cands.append((x, yy))
        yy += SPACING

pts = []
for (x, y) in cands:
    if inside_building(x, y):
        continue
    if in_gate_gap(x, y):
        continue
    if near_occupant(x, y):
        continue
    pts.append((x, y))
    if len(pts) >= MAX_POLES:
        break

# ---------------------------------------------------------------- 清旧 + 材质
n_removed = clear_old()

# 镀锌金属杆：复用既有 PBR_Metal（浅金属灰）
pole_mat = bpy.data.materials.get("PBR_Metal")

def new_mat(name, base, rough, metal=0.0, emit=0.0, emit_col=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = base + (1.0,)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit > 0.0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (emit_col or base) + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m

cam_body = new_mat(PREFIX + "CamBody", (0.12, 0.12, 0.13), 0.6, 0.0)   # 深色塑料机壳
lens_mat = new_mat(PREFIX + "Lens", (0.02, 0.02, 0.03), 0.05, 0.1)     # 近黑玻璃镜头
solar_mat = new_mat(PREFIX + "Solar", (0.03, 0.05, 0.12), 0.3, 0.2)    # 深蓝太阳能板
led_mat = new_mat(PREFIX + "LED", (1.0, 0.10, 0.05), 0.4, 0.0, 2.0, (1.0, 0.10, 0.05))  # 红色状态 LED

# ---------------------------------------------------------------- 主构建
pole_mesh = make_cylinder(PREFIX + "PoleMesh", POLE_R, POLE_H)
box_mesh = make_box(PREFIX + "BoxMesh")
lens_mesh = make_cylinder(PREFIX + "LensMesh", 1.0, 1.0)   # 单位圆柱，靠 scale 定尺寸
led_mesh = make_box(PREFIX + "LedMesh")

built = []
first_pole = None
for (x, y) in pts:
    # 指向校园中心的单位方向（水平）
    dx, dy = cx - x, cy - y
    dl = math.hypot(dx, dy) or 1.0
    dx, dy = dx / dl, dy / dl
    ang = math.atan2(dy, dx)

    # 立杆（中心 z = POLE_H/2）
    pole = place(pole_mesh, pole_mat, (x, y, POLE_H / 2.0), 0.0, 0.0, (1.0, 1.0, 1.0))
    pole.name = PREFIX + "Pole"
    built.append(pole.name)

    top = POLE_H
    head_ct = Vector((x + dx * ARM_LEN, y + dy * ARM_LEN, top - 0.25))
    arm_ct = Vector((x + dx * ARM_LEN / 2.0, y + dy * ARM_LEN / 2.0, top - 0.25))

    # 摄像机臂（沿 dir）
    arm = place(box_mesh, pole_mat, arm_ct, ang, 0.0, (ARM_LEN, 0.05, 0.05))
    arm.name = PREFIX + "Arm"
    built.append(arm.name)

    # 摄像机头（深色盒，正面朝中心）
    head = place(box_mesh, cam_body, head_ct, ang, 0.0, (0.30, 0.22, 0.20))
    head.name = PREFIX + "Head"
    built.append(head.name)

    # 镜头（暗玻璃圆柱，轴沿 dir，置于头正面）
    lens_ct = Vector((x + dx * (ARM_LEN + 0.16), y + dy * (ARM_LEN + 0.16), top - 0.25))
    lens = place(lens_mesh, lens_mat, lens_ct, ang, math.radians(90.0), (0.06, 0.06, 0.06))
    lens.name = PREFIX + "Lens"
    built.append(lens.name)

    # 状态 LED（头侧面小红点）
    led_ct = Vector((x + dx * ARM_LEN + dy * 0.10, y + dy * ARM_LEN - dx * 0.10, top - 0.10))
    led = place(led_mesh, led_mat, led_ct, ang, 0.0, (0.04, 0.04, 0.04))
    led.name = PREFIX + "LED"
    built.append(led.name)

    # 接线盒（杆身中部）
    jb_ct = Vector((x, y, POLE_H * 0.78))
    jb = place(box_mesh, cam_body, jb_ct, ang, 0.0, (0.12, 0.10, 0.18))
    jb.name = PREFIX + "JBox"
    built.append(jb.name)

    # 顶部太阳能板（深蓝，倾斜 ~25°）
    solar_ct = Vector((x, y, top + 0.22))
    solar = place(box_mesh, solar_mat, solar_ct, ang, math.radians(25.0), (0.46, 0.02, 0.28))
    solar.name = PREFIX + "Solar"
    built.append(solar.name)

    if first_pole is None:
        first_pole = (x, y, dx, dy)

# ---------------------------------------------------------------- 验证相机（首根立杆特写）
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 35.0
if first_pole is not None:
    fx, fy, fdx, fdy = first_pole
    cam.location = (fx + fdx * 4.2, fy + fdy * 4.2, 3.4)
    look = Vector((fx, fy, 4.1))
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定（确定性）
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    try:
        sc.cycles.compute_device_type = "OPTIX"
    except Exception:
        pass
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0
except Exception:
    pass

n_m61 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M61",
    "n_removed_old": n_removed,
    "n_poles": len(pts),
    "n_m61_objects": n_m61,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "candidates": len(cands),
    "points_placed": len(pts),
    "avoid_radius": AVOID,
    "occupants_used": len(occ_xy),
}
print("M61_RESULT=" + repr(result))
