# -*- coding: utf-8 -*-
"""
M50 · 自行车道划线（Bicycle Lane Markings · 校园生活细节）
==========================================================================
项目已收官（M0–M49 ✅）。按「无未完成里程碑时自行增加改进项」新增 M50：
给 96m 校园外围步行道（与 M43 路灯 / M48 长椅 / M49 宣传栏同一条 walkway）
铺一圈**自行车道划线**——白色虚线中心线 + 蓝色自行车图示，与既有 M46 自行车棚
形成闭环（"有车棚、有车道"的校园生活细节）。

为什么做这个：
  - M46 已建自行车棚，但校园里从没出现"自行车道"指示，停车与骑行缺一条视觉线索。
  - 纯加性、零破坏其它物体：地面薄层涂绘（z 0~0.04），不增任何实体结构。
  - 坐标全部从场景当前几何动态读取（PLAN.md 铁律），不硬编码建筑坐标。

几何（原型级、两块合并单 mesh）：
  - M50_White：沿内圈步行道（距围墙 LOOP_INSET=3m 的矩形环线）的白色虚线中心线
    （DASH=1.6 / GAP=1.4，单位 travel 方向长条），落在楼体 AABB 或校门洞处自动跳过。
  - M50_Blue：环线上每隔 ~14m 一枚蓝色自行车俯视图示（2 轮 + 车架），同样自动避让。

避坑（沿用 PLAN.md + M43/46/48/49 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M50_，绝不 select_all+delete。
  - Blender 5.2 锥/柱用 radius1/radius2；Principled 输入名 Emission Color / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M50_"

LOOP_INSET = 3.0      # 距围墙的内退（步行道中线）
DASH = 1.6            # 虚线长（m，沿行进方向）
GAP = 1.4             # 虚线间隔（m）
DASH_W = 0.12         # 虚线宽（m）
Z_PAIN = 0.02         # 涂绘中心离地高（盒高 0.04 → 0~0.04）
ICON_EVERY = 14.0     # 自行车图示间隔（m）
GATE_HALF = 9.0       # 南墙校门半宽
BLD_MARGIN = 0.5      # 楼体避障外扩


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
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def box_bm(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Diagonal((sx, sy, sz, 1.0)))
    return bm


def add_bm(dest, src, mat_idx):
    vmap = {}
    for v in src.verts:
        vmap[v] = dest.verts.new(v.co)
    for f in src.faces:
        nf = dest.faces.new([vmap[e] for e in f.verts])
        nf.material_index = mat_idx
    src.free()


def basis_scaled(d, perp, up, C, L, W, H):
    # 本地 X=d(行进) Y=perp Z=up，尺寸 (L,W,H)，中心 C
    return Matrix((
        (d.x * L, perp.x * W, up.x * H, C.x),
        (d.y * L, perp.y * W, up.y * H, C.y),
        (d.z * L, perp.z * W, up.z * H, C.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


# ---------------------------------------------------------------- 材质
def get_white():
    name = PREFIX + "PaintWhite"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.92, 0.92, 0.88, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.55
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.85, 0.85, 0.80, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.12
    return m


def get_blue():
    name = PREFIX + "LaneBlue"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.12, 0.34, 0.78, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.55
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.12, 0.34, 0.78, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.12
    return m


# ---------------------------------------------------------------- 校园范围
walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
wboxes = [aabb(o) for o in walls]
if wboxes:
    xmin = min(b[0] for b in wboxes); xmax = max(b[1] for b in wboxes)
    ymin = min(b[2] for b in wboxes); ymax = max(b[3] for b in wboxes)
else:
    xmin, xmax, ymin, ymax = -48, 48, -48, 48
cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
Lx0, Lx1 = xmin + LOOP_INSET, xmax - LOOP_INSET
Ly0, Ly1 = ymin + LOOP_INSET, ymax - LOOP_INSET
up = Vector((0.0, 0.0, 1.0))

blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False


def in_gate_gap(x, y):
    return (y < (ymin + LOOP_INSET + 3.0)) and (abs(x) < GATE_HALF)


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
WHT = get_white()
BLU = get_blue()

bm_white = bmesh.new()
bm_blue = bmesh.new()

# 环线 4 边（顺时针）
loop = [(Lx0, Ly0), (Lx1, Ly0), (Lx1, Ly1), (Lx0, Ly1)]
n_dash = 0
n_icon = 0
skipped = 0

for k in range(4):
    A = Vector((loop[k][0], loop[k][1], 0.0))
    B = Vector((loop[(k + 1) % 4][0], loop[(k + 1) % 4][1], 0.0))
    seg = B - A
    seg_len = seg.length
    d = seg.normalized()
    perp = up.cross(d).normalized()
    # 白色虚线中心线
    t = DASH / 2.0
    while t <= seg_len - DASH / 2.0 + 1e-6:
        C = A + d * t
        if not inside_building(C.x, C.y) and not in_gate_gap(C.x, C.y):
            M = basis_scaled(d, perp, up, C + up * Z_PAIN, DASH, DASH_W, 0.04)
            prim = box_bm(1.0, 1.0, 1.0)
            prim.transform(M)
            add_bm(bm_white, prim, 0)
            n_dash += 1
        else:
            skipped += 1
        t += (DASH + GAP)
    # 蓝色自行车图示
    n_seg = max(1, int(round(seg_len / ICON_EVERY)))
    for i in range(n_seg):
        tt = seg_len * (i + 0.5) / n_seg
        Q = A + d * tt
        if inside_building(Q.x, Q.y) or in_gate_gap(Q.x, Q.y):
            skipped += 1
            continue
        # 本地坐标（X=行进 d，Y=perp）：俯视自行车
        rear = Q + d * (-0.30) + up * 0.025
        front = Q + d * (0.30) + up * 0.025
        top = Q + d * 0.0 + perp * 0.16 + up * 0.025
        handle = Q + d * 0.28 + perp * 0.18 + up * 0.025
        # 车轮（圆柱，轴沿 Z）
        for wc in (rear, front):
            wbm = bmesh.new()
            bmesh.ops.create_cone(wbm, cap_ends=True, cap_tris=False,
                                  segments=14, radius1=0.20, radius2=0.20, depth=0.05)
            wbm.transform(Matrix.Translation(wc))
            add_bm(bm_blue, wbm, 0)
        # 车架（细杆）
        for (p1, p2) in ((rear, top), (top, front), (top, handle), (front, handle)):
            v = p2 - p1
            L = v.length
            dd = v.normalized()
            pp = up.cross(dd).normalized()
            M = basis_scaled(dd, pp, up, (p1 + p2) / 2.0, L, 0.04, 0.05)
            prim = box_bm(1.0, 1.0, 1.0)
            prim.transform(M)
            add_bm(bm_blue, prim, 0)
        n_icon += 1

# 落盘为物体
def mesh_to_obj(me_name, obj_name, bm, mat):
    me = bpy.data.meshes.new(me_name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(obj_name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o

o_white = mesh_to_obj(PREFIX + "WhiteMesh", PREFIX + "White", bm_white, WHT)
o_blue = mesh_to_obj(PREFIX + "BlueMesh", PREFIX + "Blue", bm_blue, BLU)

# ---------------------------------------------------------------- 相机（验证用）
hero = bpy.data.objects.get("M19C_HeroDay")
# 特写相机：找第一个自行车图示附近低视角，确认涂绘可读
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 1.5))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
# 取一个靠南的图示点附近作为特写目标：南边线中点
cc_target = Vector(((Lx0 + Lx1) / 2.0, Ly0, 0.0))
if inside_building(cc_target.x, cc_target.y) or in_gate_gap(cc_target.x, cc_target.y):
    cc_target = Vector((Lx0 + 4.0, Ly0, 0.0))
cam.location = cc_target + Vector((0.0, -3.2, 1.3))
cam.data.lens = 35.0
cam.rotation_euler = (cc_target + Vector((0, 0, 0.2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定（与 M43..M49 一致）
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
    sc.camera = cam
except Exception as e:
    n_removed = n_removed  # noop

n_m50 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M50",
    "ok": True,
    "n_removed_old": n_removed,
    "n_dashes": n_dash,
    "n_icons": n_icon,
    "n_skipped": skipped,
    "n_m50_objects": n_m50,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "loop_rect": [round(Lx0, 1), round(Lx1, 1), round(Ly0, 1), round(Ly1, 1)],
    "materials": [WHT.name, BLU.name],
}
print("M50_RESULT=" + repr(result))
