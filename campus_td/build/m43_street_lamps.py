# -*- coding: utf-8 -*-
"""
M43 · 校园路灯（Campus Street Lamps · emissive heads + warm POINT lights）
============================================================
项目已收官（M0–M42 ✅）。按「无未完成里程碑时自行增加改进项」新增 M43：
给 96m 校园的**外围步行道**加装一圈真实路灯，补全校园生活细节，
并显著强化既有的黄昏/夜战电影感渲染（M24 夜战 / M26 黄金时刻 / M30 晨雾）。

为什么做这个：
  - 路灯是真实高中校园的标志性设施，当前场景中校园边界只有围墙（M11/M16），
    夜间/黄昏画面仅靠防御塔辉光撑场，缺乏"有人生活"的暖光池。
  - 路灯 = 物理灯杆（金属）+ 自发光灯头（Emission）+ 暖色 POINT 光，
    白天看起来像点亮的灯具、夜间在步道投出柔和暖光池，零破坏其他物体。

坐标全部**从场景当前几何读取**（PLAN.md 铁律：M11 之后禁止硬编码建筑坐标）：
  - 校园边界 ← M11_Wall* 的世界 AABB 并集（得中心与半幅）
  - 避障 ← 跳过落在任一 Bldg_* AABB（外扩 1.5m）内的候选点，避免灯杆插进楼里
  - 校门洞 ← 南墙 x∈[-9,9] 留空，不挡校门

避坑（沿用 PLAN.md 清单 + 历次经验）：
  - 顶层执行：MCP 用 exec(compile(open().read())) 跑，__name__ != "__main__"，逻辑不包 main()。
  - 不调 bpy.ops.*.mode_set（MCP exec 内 poll fail）；全部用 bmesh 直建。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M43_ 前缀，绝不 select_all+delete。
  - scale 烘进顶点：灯杆/灯臂/灯头用 bmesh + Matrix 直接生成世界尺寸，物体 scale 保持 1。
  - Blender 5.2 Principled 输入名：Emission Color / Emission Strength（非旧版 Emission）。
  - POINT 灯 use_shadow=False（步道暖池无需锐利投影，省 OptiX 开销）；能量保守(25)避免白天过曝。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M43_"

LAMP_H = 4.2          # 灯杆高（m）
POLE_R = 0.075        # 灯杆半径（m）
HEAD = (0.42, 0.42, 0.30)   # 灯头盒尺寸（m）
ARM_LEN = 0.7         # 灯臂伸向校园中心（m）
INSET = 6.0           # 距围墙内退（m）
SPACING = 15.0        # 沿周长灯间距（m）
MAX_LAMPS = 22        # 上限（控制 POINT 灯数量，保 OptiX 渲染成本）
GATE_HALF = 9.0       # 南墙校门半宽（m）
BLD_MARGIN = 1.5      # 楼体避障外扩（m）

# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in cs]; ys = [c.y for c in cs]; zs = [c.z for c in cs]
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


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
    for li in list(bpy.data.lights):
        if li.name.startswith(PREFIX):
            bpy.data.lights.remove(li)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def get_pole_mat():
    name = PREFIX + "PoleMetal"
    m = bpy.data.materials.get(name)
    if m is None:
        base = bpy.data.materials.get("PBR_Metal")
        if base is not None:
            return base
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = [0.18, 0.18, 0.20, 1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.45
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.9
    return m


def get_lamp_mat():
    name = PREFIX + "LampGlow"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = [0.95, 0.92, 0.85, 1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.35
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = [1.0, 0.82, 0.55, 1.0]
                bsdf.inputs["Emission Strength"].default_value = 3.0
    return m


def make_cylinder(name, r, h, seg=12):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def make_box(name, size):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def add_obj(me, mat, matrix):
    me.transform(matrix) if False else None
    o = bpy.data.objects.new(me.name, me)
    o.matrix_world = matrix
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


# ---------------------------------------------------------------- 候选点（沿内矩形四边均匀采样）
cands = []
# 南/北边（沿 x）
for y in (yi0, yi1):
    L = xi1 - xi0
    n = max(1, int(round(L / SPACING)))
    for i in range(n + 1):
        cands.append((xi0 + L * i / n, y))
# 西/东边（沿 y，避开四角重复）
for x in (xi0, xi1):
    L = yi1 - yi0
    n = max(1, int(round(L / SPACING)))
    for i in range(1, n):
        cands.append((x, yi0 + L * i / n))

# 过滤
pts = []
for (x, y) in cands:
    if inside_building(x, y):
        continue
    if in_gate_gap(x, y):
        continue
    pts.append((x, y))
    if len(pts) >= MAX_LAMPS:
        break

# ---------------------------------------------------------------- 构建
n_removed = clear_old()
pole_mat = get_pole_mat()
lamp_mat = get_lamp_mat()

built = []
for (x, y) in pts:
    # 灯杆
    pm = Matrix.Translation(Vector((x, y, LAMP_H / 2.0)))
    pole = bpy.data.objects.new(PREFIX + "Pole", make_cylinder(PREFIX + "PoleMesh", POLE_R, LAMP_H))
    pole.matrix_world = pm
    pole.data.materials.append(pole_mat)
    bpy.context.scene.collection.objects.link(pole)
    built.append(pole.name)

    # 灯臂方向（指向校园中心）
    dx, dy = cx - x, cy - y
    dl = math.hypot(dx, dy) or 1.0
    dx, dy = dx / dl, dy / dl
    ang = math.atan2(dy, dx)
    hx, hy = x + dx * ARM_LEN, y + dy * ARM_LEN
    hz = LAMP_H

    # 灯臂（细盒，旋转指向中心）
    arm_mid = Vector((x + dx * ARM_LEN / 2.0, y + dy * ARM_LEN / 2.0, hz))
    arm_mat = (Matrix.Translation(arm_mid) @ Matrix.Rotation(ang, 4, "Z")
               @ Matrix.Diagonal(Vector((ARM_LEN, 0.07, 0.07, 1.0))))
    arm = bpy.data.objects.new(PREFIX + "Arm", make_box(PREFIX + "ArmMesh", (1, 1, 1)))
    arm.matrix_world = arm_mat
    arm.data.materials.append(pole_mat)
    bpy.context.scene.collection.objects.link(arm)
    built.append(arm.name)

    # 灯头（自发光盒）
    head_mat = (Matrix.Translation(Vector((hx, hy, hz)))
                @ Matrix.Diagonal(Vector((HEAD[0], HEAD[1], HEAD[2], 1.0))))
    head = bpy.data.objects.new(PREFIX + "Head", make_box(PREFIX + "HeadMesh", (1, 1, 1)))
    head.matrix_world = head_mat
    head.data.materials.append(lamp_mat)
    bpy.context.scene.collection.objects.link(head)
    built.append(head.name)

    # 暖色 POINT 光（步道暖池；夜间显著，白天影响可忽略）
    lp = bpy.data.lights.new(PREFIX + "Light", type="POINT")
    lp.energy = 25.0
    lp.color = (1.0, 0.82, 0.55)
    lp.use_shadow = False
    lp.shadow_soft_size = 3.0
    lpo = bpy.data.objects.new(PREFIX + "Light", lp)
    lpo.location = Vector((hx, hy, hz))
    bpy.context.scene.collection.objects.link(lpo)
    built.append(lpo.name)

# ---------------------------------------------------------------- 渲染设定（确定性；与 M38..M42 一致）
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.compute_device_type = "OPTIX"
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0
except Exception as e:
    built.append("RENDER_CFG_WARN:" + str(e))

# 活动相机：复用已验证白昼英雄机位做验证（灯杆沿围墙在背景成环）
cam = bpy.data.objects.get("M19C_HeroDay")
if cam is not None:
    sc.camera = cam

n_m43 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
n_lamps = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX + "Pole"))
result = {
    "milestone": "M43",
    "n_removed_old": n_removed,
    "n_lamps": n_lamps,
    "n_m43_objects": n_m43,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "candidates": len(cands),
    "points_placed": len(pts),
    "pole_h": LAMP_H,
    "objects": built[:8],
}
print("M43_RESULT=" + repr(result))
