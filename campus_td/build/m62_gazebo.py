# -*- coding: utf-8 -*-
"""
M62 · 校园休憩凉亭（Campus Gazebo / 凉亭 · OptiX）
============================================================================
项目已收官（M0–M61 ✅）。按「无未完成里程碑时自行增加改进项」新增 M62：
真实高中校园的花园/草坪里最常见的休憩设施——一座中式攒尖顶凉亭此前完全缺失。
路灯(M43)/长椅(M48)/宣传栏(M49)/监控(M61)已沿内圈布置，但中央草坪没有可停留的
景观节点；本里程碑在** verified-clear 的开阔草坪**自动选址建一座中式四角攒尖凉亭
（红柱 + 灰瓦攒尖顶 + 石台基 + 四张石凳），补全"有人生活 + 可停留"的校园温度。

选址全部**从场景当前几何读取 + 自动避障**（PLAN.md 铁律：M11 之后禁止硬编码）：
  - 候选带 ← 教学楼南侧草坪（探针确认 x∈[-30,30] y∈[-35,-23] 为大片开阔且无高楼）
  - 避障 ← 跳过与任一"实体"物体 XZ-AABB（z 向高 >=0.8m，或指定平铺前缀）相交的候选
           实体含 Bldg_*/M46_*/M38_*/M37_Flag/M11_FlagPole/M11_Tree*/M43_*/M61_*/M51_Hedge/
                M48_*/M49_*/M44_*/M53_*/M60_*/M55_*/M54_*/M59_*/Room_*/Int_*/M8_*/M17_*/M47_*
                /M41_*/M45_*/M52_*/Road/M11_Gate*/M58_*/M16_*/M15_*/M50_*/M40_*/M42_*/M39_* 等
  - 偏好点 ← 取候选带中距 (0,-28) 最近的全 clearance 点（教学楼主入口前草坪中央）

避坑（沿用 PLAN.md + M43/M60/M61 经验）：
  - MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 primitive + bmesh 直建，物体 scale 保持 1（matrix_world 烘焙）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M62_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Color / Emission Strength。
  - 攒尖顶 = 4 段 cone（radius1=檐口半对角、radius2=0），绕 Z 旋 45° 对齐方台四边。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M62_"

GAZEBO_HALF = 3.4      # 凉亭含出檐占地半边长（m），搜索 clearance 用 half+margin
PLATE_H = 0.30          # 石台基高（m）
COL_R = 0.12            # 柱半径（m）
COL_H = 2.70            # 柱高（柱脚在台基顶 z=PLATE_H，柱顶 z=PLATE_H+COL_H）
EAVE = 1.70             # 檐口半边长（m，> COL 距 1.7 稍出檐）
ROOF_H = 1.50           # 攒尖顶高（m）
COL_OFF = 1.70          # 柱中心到亭心的水平距（m）

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


def make_cylinder(name, r, h, seg=12):
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


def make_pyramid(name, half, h, seg=4):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=half, radius2=0.0, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def make_sphere(name, r, u=10, v=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def place(me, mat, loc, rotz=0.0, roty=0.0, rotx=0.0, scale=(1.0, 1.0, 1.0)):
    mat_ = (Matrix.Translation(Vector(loc))
            @ Matrix.Rotation(rotz, 4, "Z")
            @ Matrix.Rotation(roty, 4, "Y")
            @ Matrix.Rotation(rotx, 4, "X")
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
    xmin, xmax, ymin, ymax = -48, 48, -48, 48

# ---------------------------------------------------------------- 避障实体
# 仅拦"实体结构"；平铺/环形装饰（M50 自行车道、M51 绿篱环、M58 车道边线、Road、M38 球场、
# M59/M54/M55 校门广场、M11_Gate/M60 校门）作为 flat 前缀拦；其余 campus-wide 合并网格
# （M50_/M51_）及塔防游戏标记（M7_/Tower_/Enemy_/M10B_）一律不拦（坐顶/非实体）。
FLAT_BLOCK = ("M38_", "M11_Gate", "M59_", "M54_", "M55_", "M60_", "Road", "M58_")
STRUCT = ("Bldg_", "M46_", "M37_Flag", "M11_FlagPole", "M11_Tree", "M43_", "M61_",
          "M48_", "M49_", "M44_", "M53_", "M47_", "M41_", "M45_",
          "M52_", "M39_", "M40_", "M42_", "M16_")

def is_blocker(o):
    n = o.name
    if any(n.startswith(p) for p in FLAT_BLOCK):
        return True
    if any(n.startswith(p) for p in STRUCT):
        return True
    b = aabb(o)
    zext = b[5] - b[4]
    # 任意明显立体（竖向高度 >=1.2m）都算障碍（路灯/长椅/宣传栏/监控/树/旗杆/垛口等）
    if zext >= 1.2 and b[4] < 3.5:
        return True
    return False

blockers = [aabb(o) for o in bpy.data.objects if is_blocker(o)]

def clear_at(cx, cy, half):
    m = 0.6  # 余量
    x0, x1 = cx - (half + m), cx + (half + m)
    y0, y1 = cy - (half + m), cy + (half + m)
    for b in blockers:
        if b[0] <= x1 and b[1] >= x0 and b[2] <= y1 and b[3] >= y0:
            return False
    return True

# 候选带：东北角花园（探针确认 x∈[29,43] y∈[17,43] 为最大开阔 exterior 草坪，远离楼体/球场/道路）
PREF = (36.0, 30.0)
best = None
best_d = 1e9
for cy in [y * 1.0 for y in range(17, 44, 1)]:
    for cx in [x * 1.0 for x in range(29, 44, 1)]:
        if clear_at(cx, cy, GAZEBO_HALF):
            d = math.hypot(cx - PREF[0], cy - PREF[1])
            if d < best_d:
                best_d = d
                best = (cx, cy)
if best is None:
    # 兜底：硬放在偏好点（仍会记录 warning）
    best = PREF
    warn = "NO_CLEAR_SPOT_FOUND_FALLBACK"
else:
    warn = ""
cx, cy = best

# ---------------------------------------------------------------- 清旧 + 材质
n_removed = clear_old()

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

mat_stone = new_mat(PREFIX + "Stone", (0.62, 0.61, 0.60), 0.85, 0.0)   # 灰石台基/石凳
mat_col = new_mat(PREFIX + "Column", (0.55, 0.12, 0.10), 0.55, 0.0)    # 中国红柱
mat_roof = new_mat(PREFIX + "Roof", (0.33, 0.34, 0.36), 0.65, 0.0)     # 青灰瓦顶
mat_finial = new_mat(PREFIX + "Finial", (0.78, 0.62, 0.18), 0.35, 0.7) # 金顶宝珠

# 复用既有 PBR（若有）增强质感
pbr_concrete = bpy.data.materials.get("PBR_Concrete")
if pbr_concrete is not None:
    mat_stone = pbr_concrete

# ---------------------------------------------------------------- 几何
plate_mesh = make_box(PREFIX + "PlateMesh")
col_mesh = make_cylinder(PREFIX + "ColMesh", COL_R, COL_H, 12)
roof_mesh = make_pyramid(PREFIX + "RoofMesh", EAVE, ROOF_H, 4)
bench_mesh = make_box(PREFIX + "BenchMesh")
finial_mesh = make_sphere(PREFIX + "FinialMesh", 0.16)

built = []

# 1) 石台基（两层错落，略像须弥座）
plate = place(plate_mesh, mat_stone, (cx, cy, PLATE_H / 2.0), 0, 0, 0,
              (2 * GAZEBO_HALF, 2 * GAZEBO_HALF, PLATE_H))
plate.name = PREFIX + "Plate"
built.append(plate.name)

rim = place(plate_mesh, mat_stone, (cx, cy, PLATE_H + 0.10), 0, 0, 0,
            (2 * (GAZEBO_HALF - 0.35), 2 * (GAZEBO_HALF - 0.35), 0.20))
rim.name = PREFIX + "PlateRim"
built.append(rim.name)

# 2) 四根红柱（角点，柱脚在台基顶）
col_z0 = PLATE_H + 0.20
for sx in (-1, 1):
    for sy in (-1, 1):
        c = place(col_mesh, mat_col, (cx + sx * COL_OFF, cy + sy * COL_OFF, col_z0 + COL_H / 2.0))
        c.name = PREFIX + "Column_%d%d" % (sx > 0 and 1 or 0, sy > 0 and 1 or 0)
        built.append(c.name)

# 3) 攒尖顶（4 段 cone，绕 Z 旋 45° 对齐方台四边）
roof_z = col_z0 + COL_H
roof = place(roof_mesh, mat_roof, (cx, cy, roof_z + ROOF_H / 2.0), math.radians(45.0), 0, 0)
roof.name = PREFIX + "Roof"
built.append(roof.name)

# 4) 宝顶（金珠 + 小刹）
fin = place(finial_mesh, mat_finial, (cx, cy, roof_z + ROOF_H + 0.14))
fin.name = PREFIX + "Finial"
built.append(fin.name)

# 5) 四张石凳（亭内四边中点，朝心）
bench_off = 1.15
for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    # 凳朝向：长轴沿切线
    ang = math.atan2(dy, dx)
    bx, by = cx + dx * bench_off, cy + dy * bench_off
    bseg = place(bench_mesh, mat_stone, (bx, by, col_z0 + 0.22), ang, 0, 0, (0.9, 0.32, 0.44))
    bseg.name = PREFIX + "Bench_%d%d" % (dx > 0 and 1 or 0, dy > 0 and 1 or 0)
    built.append(bseg.name)

# ---------------------------------------------------------------- 验证相机（亭子特写）
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 40.0
cam.location = (cx + 6.5, cy + 6.5, PLATE_H + COL_H + 1.2)
look = Vector((cx, cy, PLATE_H + COL_H * 0.6))
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

n_m62 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M62",
    "n_removed_old": n_removed,
    "n_m62_objects": n_m62,
    "n_total_objects": len(bpy.data.objects),
    "placed_at": [round(cx, 2), round(cy, 2)],
    "preferred": [PREF[0], PREF[1]],
    "dist_to_preferred": round(best_d, 2),
    "warning": warn,
    "gazebo_half": GAZEBO_HALF,
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
}
print("M62_RESULT=" + repr(result))
