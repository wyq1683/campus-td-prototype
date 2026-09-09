# -*- coding: utf-8 -*-
"""
M45 · 运动场泛光灯塔（Sports Field Floodlight Towers · emissive banks + SPOT lights）
=================================================================================
项目已收官（M0–M44 ✅）。按「无未完成里程碑时自行增加改进项」新增 M45：
给中央室外运动场（M38 草皮/跑道、M39 球门、M40 球网、M41 看台）四角加装
**泛光灯塔**，让球场在夜间/黄昏被照亮，强化既有的夜战塔防电影感（M24 夜战 / M33 暴风夜）。

为什么做这个：
  - M44 楼牌让校园"可辨识"，但运动场在夜里仍是一片黑。真实高中的操场都有泛光灯塔，
    塔防夜战（M24/M33）更需要被照亮的战场。M43 已证明路灯暖池有效，本里程碑是
    "运动场专用强照明"的对应物。
  - 4 座塔 = 锥形金属杆 + 横臂 + 冷白自发光灯阵（Emission，白天也像点亮的灯具）
    + 4 盏 SPOT 灯指向球场中心（夜间把球场打亮）。零破坏其他物体。

坐标**从场景当前几何读取**（PLAN.md 铁律：M11 之后禁止硬编码建筑坐标）：
  - 球场范围 ← M38_Pitch（草皮）世界 AABB；兜底 (-3,0,15,8.5)
  - 4 角 = 球场 AABB 四角外扩 OUT=6m
  - 避障 ← 跳过落在任一 Bldg_* AABB（外扩 2m）内的候选角，避免灯塔插进楼里

避坑（沿用 PLAN.md 清单 + 历次经验）：
  - 顶层执行：MCP 用 exec(compile(open().read())) 跑，__name__ != "__main__"，逻辑不包 main()。
  - 不调 bpy.ops.*.mode_set（MCP exec 内 poll fail）；全部用 bmesh 直建。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M45_ 前缀，绝不 select_all+delete。
  - scale 烘进顶点：杆/臂/灯阵用 bmesh + Matrix 直接生成世界尺寸，物体 scale 保持 1。
  - Blender 5.2 Principled 输入名：Emission Color / Emission Strength（非旧版 Emission）。
  - 锥体 make_cylinder 用 radius1/radius2（M43 已踩过 `diameter1/diameter2` 改名坑）。
  - SPOT 灯用 Object.look_at(target) 把本地 -Z（光束方向）对准球场中心，自动带俯角。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M45_"

TOWER_H = 14.0      # 灯杆高（m）
POLE_R1 = 0.22      # 杆底半径（m）
POLE_R2 = 0.13      # 杆顶半径（m）
ARM_LEN = 2.2       # 横臂伸向球场（m）
BANK = (2.6, 1.4, 0.35)   # 灯阵盒尺寸（m）
OUT = 6.0           # 角点外扩（m）
BLD_MARGIN = 2.0    # 楼体避障外扩（m）
SPOT_ENERGY = 900.0 # SPOT 能量（夜间把球场打亮；白天因距离远≈可忽略）
SPOT_SIZE = 1.15    # 锥角（rad，全角≈66°，覆盖球场）
SPOT_BLEND = 0.25   # 锥边柔化

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
            bsdf.inputs["Base Color"].default_value = [0.20, 0.20, 0.23, 1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.45
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.9
    return m


def get_bank_mat():
    name = PREFIX + "LampBank"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = [0.85, 0.90, 1.0, 1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.3
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = [0.80, 0.88, 1.0, 1.0]
                bsdf.inputs["Emission Strength"].default_value = 4.0
    return m


def make_cylinder(name, r1, r2, h, seg=14):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=r1, radius2=r2, depth=h)
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


# ---------------------------------------------------------------- 球场范围（动态读 M38_Pitch，兜底硬编码）
pitch = [o for o in bpy.data.objects if o.name.startswith("M38_Pitch")]
if pitch:
    b = aabb(pitch[0])
    xmin, xmax, ymin, ymax = b[0], b[1], b[2], b[3]
else:
    xmin, xmax, ymin, ymax = -18.0, 12.0, -8.5, 8.5   # 兜底：球场半宽15/半深8.5 中心(-3,0)
fcx, fcy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
fw = (xmax - xmin) / 2.0
fd = (ymax - ymin) / 2.0

corners = [
    (xmin - OUT, ymin - OUT),
    (xmax + OUT, ymin - OUT),
    (xmin - OUT, ymax + OUT),
    (xmax + OUT, ymax + OUT),
]

# ---------------------------------------------------------------- 楼体避障 AABB
blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False


pts = [c for c in corners if not inside_building(c[0], c[1])]

# ---------------------------------------------------------------- 构建
n_removed = clear_old()
pole_mat = get_pole_mat()
bank_mat = get_bank_mat()

built = []
n_towers = 0
for (cx0, cy0) in pts:
    # 指向球场中心的方向（水平）
    dx, dy = fcx - cx0, fcy - cy0
    dl = math.hypot(dx, dy) or 1.0
    dx, dy = dx / dl, dy / dl

    # 灯杆（锥形）
    pm = Matrix.Translation(Vector((cx0, cy0, TOWER_H / 2.0)))
    pole = bpy.data.objects.new(PREFIX + "Pole", make_cylinder(PREFIX + "PoleMesh", POLE_R1, POLE_R2, TOWER_H))
    pole.matrix_world = pm
    pole.data.materials.append(pole_mat)
    bpy.context.scene.collection.objects.link(pole)
    built.append(pole.name)

    # 横臂（从杆顶伸向球场）
    arm_mid = Vector((cx0 + dx * ARM_LEN / 2.0, cy0 + dy * ARM_LEN / 2.0, TOWER_H))
    ang = math.atan2(dy, dx)
    arm_mat = (Matrix.Translation(arm_mid) @ Matrix.Rotation(ang, 4, "Z")
               @ Matrix.Diagonal(Vector((ARM_LEN, 0.16, 0.16, 1.0))))
    arm = bpy.data.objects.new(PREFIX + "Arm", make_box(PREFIX + "ArmMesh", (1, 1, 1)))
    arm.matrix_world = arm_mat
    arm.data.materials.append(pole_mat)
    bpy.context.scene.collection.objects.link(arm)
    built.append(arm.name)

    # 灯阵（自发光盒，挂在臂端、灯面正对球场中心）
    bx, by, bz = cx0 + dx * ARM_LEN, cy0 + dy * ARM_LEN, TOWER_H - 0.4
    bank = bpy.data.objects.new(PREFIX + "Bank", make_box(PREFIX + "BankMesh", (1, 1, 1)))
    bank.location = Vector((bx, by, bz))
    bank.scale = Vector((BANK[0], BANK[1], BANK[2]))
    bank.rotation_mode = "QUATERNION"
    d_bank = (Vector((fcx, fcy, 0.0)) - Vector((bx, by, bz))).normalized()
    bank.rotation_quaternion = d_bank.to_track_quat("Z", "Y")   # 灯面(+Z)朝球场中心（带俯角）
    bank.data.materials.append(bank_mat)
    bpy.context.scene.collection.objects.link(bank)
    built.append(bank.name)

    # SPOT 灯（夜间把球场打亮；Blender SPOT 沿本地 -Z 发射，故把 +Z 对准 -方向）
    lp = bpy.data.lights.new(PREFIX + "Spot", type="SPOT")
    lp.energy = SPOT_ENERGY
    lp.color = (0.85, 0.90, 1.0)
    lp.spot_size = SPOT_SIZE
    lp.spot_blend = SPOT_BLEND
    lp.use_shadow = True
    lp.shadow_soft_size = 2.5
    lpo = bpy.data.objects.new(PREFIX + "Spot", lp)
    lpo.location = Vector((bx, by, bz))
    lpo.rotation_mode = "QUATERNION"
    d_spot = (Vector((fcx, fcy, 0.0)) - Vector((bx, by, bz))).normalized()
    lpo.rotation_quaternion = (-d_spot).to_track_quat("Z", "Y")   # 光束(-Z)对准球场中心
    bpy.context.scene.collection.objects.link(lpo)
    built.append(lpo.name)

    n_towers += 1

# ---------------------------------------------------------------- 渲染设定（CYCLES GPU OptiX，与 M38..M44 一致）
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

# 活动相机：复用已验证的球场英雄机位（M39_Cam）做白昼验证
cam = bpy.data.objects.get("M39_Cam")
if cam is not None:
    sc.camera = cam
else:
    cam = bpy.data.objects.get("M19C_HeroDay")
    if cam is not None:
        sc.camera = cam

n_m45 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
n_total = len(bpy.data.objects)
result = {
    "milestone": "M45",
    "n_removed_old": n_removed,
    "n_towers": n_towers,
    "n_m45_objects": n_m45,
    "n_total_objects": n_total,
    "field": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "field_center": [round(fcx, 1), round(fcy, 1)],
    "tower_corners": [list(map(round, p)) for p in pts],
    "objects": built[:8],
}
print("M45_RESULT=" + repr(result))
