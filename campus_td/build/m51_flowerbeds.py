# -*- coding: utf-8 -*-
"""
M51 · 校园花坛与绿篱（Decorative Flower Beds & Hedges · 校园生活细节）
==========================================================================
项目已收官（M0–M50 ✅）。按「无未完成里程碑时自行增加改进项」新增 M51：
给 96m 校园加**花坛（建筑入口花箱）+ 内圈绿篱**，补全"有人生活"的温暖色彩——
当前校园混凝土/沥青/砖墙为主，缺近人尺度的绿植点缀，与 M43 路灯 / M48 长椅垃圾桶 /
M49 宣传栏 / M50 自行车道 共同构成可居住的校园生活带。

为什么做这个：
  - 绿篱沿内圈围墙（距墙 INSET=1.4m，在 M50 自行车道 3m 环线之内、不与之冲突）成环，
    像真实校园把操场/教学区用矮绿篱轻轻围合。
  - 花箱摆在每个楼朝中庭入口两侧（n 外推 2.8m、±t 各 2.2m，与 M48 入口垃圾桶错开），
    点缀彩色花簇，强化"课间有人逗留"的生活感。
  - 自成一体、零破坏其它物体：仅新建 M51_ 前缀物体，坐标全部从场景当前几何动态读取。

坐标**从场景当前几何读取**（M11 之后禁止硬编码）：
  - 校园范围 ← M11_Wall* AABB 并集。
  - 建筑入口 ← 每栋 Bldg_* 组 AABB 并集，楼中心→校园中心(0,0) 取外法线 n，入口 = 该面外推。
  - 绿篱采样点避障跳过 Bldg_* AABB（外扩）与南墙校门洞。

几何体（原型级、合并为单 mesh / 单物体，材质槽复用 + M51_ 前缀新材质）：
  - M51_Hedge ：沿 4 边内退环线采样的矮绿篱段（PBR_Grass 复用）。
  - M51_Planter：所有花箱的混凝土箱体 + 表土（PBR_Concrete 复用 / M51_Soil）。
  - M51_Flowers：所有花箱的绿茎（PBR_Grass）+ 彩色花冠（M51_Flower0..3 调色板）。

避坑（沿用 PLAN.md + M43..M50 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M51_，绝不 select_all+delete。
  - 材质：复用既有 PBR_Concrete / PBR_Grass（避免 M18 提过的"重建材质丢槽"）；
    新 M51_ 前缀材质仅本里程碑使用。
  - Blender 5.2 锥/柱用 radius1/radius2；Principled 输入名 Emission Color / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M51_"

# ---- 绿篱 ----
HEDGE_INSET = 1.4      # 距围墙内退（在自行车道 3m 环线之内）
HEDGE_SEG = 2.0        # 每段长（m，沿行进）
HEDGE_STEP = 2.5       # 采样步长（m，留 0.5m 缝，像修剪绿篱）
HEDGE_DEEP = 0.5
HEDGE_H = 0.6
GATE_HALF = 9.0        # 南墙校门半宽

# ---- 花箱（每楼入口两侧）----
PLANTER_N = 2.8        # 入口面外推（m），与 M48 垃圾桶(1.5m)错开
PLANTER_T = 2.2        # 沿切向 ± 偏移（m）
PLANTER_W = 0.6
PLANTER_D = 0.6
PLANTER_H = 0.45
SOIL_T = 0.08
BLOOM_N = 6            # 每箱花簇数
BLOOM_STEM = 0.28
BLOOM_R = 0.07
BLD_MARGIN = 0.5       # 楼体避障外扩

FLOWER_COLORS = [
    (0.78, 0.12, 0.18),   # red
    (0.95, 0.78, 0.15),   # yellow
    (0.55, 0.22, 0.62),   # purple
    (0.95, 0.85, 0.88),   # pink-white
]


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


def box(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Diagonal((sx, sy, sz, 1.0)))
    return bm


def cyl(r, h, seg=12):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=r, radius2=r, depth=h)
    return bm


def ico(r, sub=1):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return bm


def add_bm(dest, src, mat_idx):
    vmap = {}
    for v in src.verts:
        vmap[v] = dest.verts.new(v.co)
    for f in src.faces:
        nf = dest.faces.new([vmap[e] for e in f.verts])
        nf.material_index = mat_idx
    src.free()


def basis_mat(Xc, Yc, Zc, T):
    if not hasattr(T, "x"):
        T = Vector(T)
    return Matrix((
        (Xc.x, Yc.x, Zc.x, T.x),
        (Xc.y, Yc.y, Zc.y, T.y),
        (Xc.z, Yc.z, Zc.z, T.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


# ---------------------------------------------------------------- 材质
def get_concrete():
    m = bpy.data.materials.get("PBR_Concrete")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "Concrete")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.60, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.85
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
    return m


def get_grass():
    m = bpy.data.materials.get("PBR_Grass")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "Grass")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.18, 0.34, 0.12, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.9
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
    return m


def get_soil():
    name = PREFIX + "Soil"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.12, 0.08, 0.05, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.95
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
    return m


def get_flower(k):
    name = PREFIX + "Flower%d" % (k % 4)
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        c = FLOWER_COLORS[k % 4]
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.6
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (c[0], c[1], c[2], 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.18
    return m


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
CONC = get_concrete()
GRASS = get_grass()
SOIL = get_soil()
FLOWERS = [get_flower(i) for i in range(4)]

# 校园范围（M11_Wall 并集）
walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
if walls:
    wb = [aabb(o) for o in walls]
    xmin, xmax = min(b[0] for b in wb), max(b[1] for b in wb)
    ymin, ymax = min(b[2] for b in wb), max(b[3] for b in wb)
else:
    xmin, xmax, ymin, ymax = -48, 48, -48, 48
cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
up = Vector((0, 0, 1))
cc = Vector((cx, cy, 0.0))

blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y, margin=BLD_MARGIN):
    for b in blds:
        if (b[0] - margin) <= x <= (b[1] + margin) and \
           (b[2] - margin) <= y <= (b[3] + margin):
            return True
    return False


def in_gate_gap(x, y):
    return (y < (ymin + HEDGE_INSET + 3.0)) and (abs(x) < GATE_HALF)


# ---- 绿篱：4 边内退环线采样 ----
bm_hedge = bmesh.new()
hx0, hx1 = xmin + HEDGE_INSET, xmax - HEDGE_INSET
hy0, hy1 = ymin + HEDGE_INSET, ymax - HEDGE_INSET
loop = [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)]
n_hedge = 0
for k in range(4):
    A = Vector((loop[k][0], loop[k][1], 0.0))
    B = Vector((loop[(k + 1) % 4][0], loop[(k + 1) % 4][1], 0.0))
    seg = B - A
    seg_len = seg.length
    d = seg.normalized()
    t = HEDGE_STEP / 2.0
    while t <= seg_len - HEDGE_STEP / 2.0 + 1e-6:
        C = A + d * t
        if not inside_building(C.x, C.y) and not in_gate_gap(C.x, C.y):
            M = basis_mat(d, up.cross(d).normalized(), up,
                          C + up * (HEDGE_H / 2.0))
            sb = box(HEDGE_SEG, HEDGE_DEEP, HEDGE_H)
            sb.transform(M)
            add_bm(bm_hedge, sb, 0)
            n_hedge += 1
        t += HEDGE_STEP

# ---- 花箱：每栋楼入口两侧 ----
bm_planter = bmesh.new()
bm_flower = bmesh.new()
groups = {}
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        key = "_".join(o.name.split("_")[:2])
        groups.setdefault(key, []).append(o)

planter_pts = []
flower_count = 0
for key, objs in groups.items():
    bs = [aabb(o) for o in objs]
    bcx = (min(b[0] for b in bs) + max(b[1] for b in bs)) / 2.0
    bcy = (min(b[2] for b in bs) + max(b[3] for b in bs)) / 2.0
    bc = Vector((bcx, bcy, 0.0))
    n_dir = (cc - bc)
    n_dir.z = 0.0
    if n_dir.length < 1e-3:
        n_dir = Vector((0.0, 1.0, 0.0))
    n = n_dir.normalized()
    t = up.cross(n).normalized()
    corners = [(bsi[0], bsi[2]) for bsi in bs] + [(bsi[1], bsi[2]) for bsi in bs] + \
              [(bsi[0], bsi[3]) for bsi in bs] + [(bsi[1], bsi[3]) for bsi in bs]
    reach = max((Vector((cx2, cy2, 0.0)) - bc).dot(n) for cx2, cy2 in corners)
    for sgn in (-1, 1):
        P = bc + n * (reach + PLANTER_N) + t * (sgn * PLANTER_T)
        if inside_building(P.x, P.y):
            continue
        if in_gate_gap(P.x, P.y):
            continue
        planter_pts.append((P.x, P.y, P.z, n, t, sgn))
        # 箱体（混凝土）
        box_bm = box(PLANTER_W, PLANTER_D, PLANTER_H)
        box_bm.transform(Matrix.Translation((P.x, P.y, PLANTER_H / 2.0)))
        add_bm(bm_planter, box_bm, 0)
        # 表土（顶）
        soil_bm = box(PLANTER_W - 0.08, PLANTER_D - 0.08, SOIL_T)
        soil_bm.transform(Matrix.Translation((P.x, P.y, PLANTER_H - SOIL_T / 2.0)))
        add_bm(bm_planter, soil_bm, 1)
        # 花簇
        top_z = PLANTER_H + 0.02
        for fi in range(BLOOM_N):
            fx = (fi % 3 - 1) * 0.16
            fy = (fi // 3 - 0.5) * 0.18
            base = Vector((P.x + fx, P.y + fy, top_z))
            # 茎（绿）
            stem = cyl(0.012, BLOOM_STEM, 6)
            stem.transform(Matrix.Translation(base + up * (BLOOM_STEM / 2.0)))
            add_bm(bm_flower, stem, 0)
            # 花冠（彩色）
            bloom = ico(BLOOM_R, 1)
            bloom.transform(Matrix.Translation(base + up * (BLOOM_STEM + BLOOM_R * 0.6)))
            add_bm(bm_flower, bloom, 1 + (fi % 4))
            flower_count += 1

# ---------------------------------------------------------------- 落盘为物体
def mesh_to_obj(me_name, obj_name, bm, mats):
    me = bpy.data.meshes.new(me_name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(obj_name, me)
    for m in mats:
        o.data.materials.append(m)
    bpy.context.scene.collection.objects.link(o)
    return o

o_hedge = mesh_to_obj(PREFIX + "HedgeMesh", PREFIX + "Hedge", bm_hedge, [GRASS])
o_planter = mesh_to_obj(PREFIX + "PlanterMesh", PREFIX + "Planter", bm_planter, [CONC, SOIL])
o_flower = mesh_to_obj(PREFIX + "FlowerMesh", PREFIX + "Flowers", bm_flower,
                       [GRASS] + FLOWERS)

# ---------------------------------------------------------------- 相机
hero = bpy.data.objects.get("M19C_HeroDay")
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 1.6))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
if planter_pts:
    P = planter_pts[0]
    Pv = Vector((P[0], P[1], 0.0))
    n = P[3]; t = P[4]
    # 看向花箱：站在花箱外侧（+n 反向即朝外？花箱在楼外侧，校园侧是 -n 方向往校园）
    # 取从校园中心看向花箱的机位：campus center 一侧
    view_from = Pv - n * 3.0 + up * 1.4
    cam.location = view_from
    cam.data.lens = 35.0
    cam.rotation_euler = ((Pv + up * 0.4) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX，与 M43..M50 一致）
sc = bpy.context.scene
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
import os
os.makedirs(PREVIEW_DIR, exist_ok=True)
rendered = []
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
    sc.view_settings.exposure = 0.05
    # 1) 校园语境（英雄机位）
    if hero is not None:
        sc.camera = hero
        sc.render.filepath = PREVIEW_DIR + "/m51_flowerbeds_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
    # 2) 花箱特写（加临时补光，避免建筑阴影里看不清花；结束后清理，零孤儿对象）
    sc.camera = cam
    fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
    fill.energy = 140.0
    fill.color = (1.0, 0.95, 0.85)
    fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
    fill_obj.location = cam.location + up * 0.5
    bpy.context.scene.collection.objects.link(fill_obj)
    bpy.context.view_layer.update()
    sc.render.filepath = PREVIEW_DIR + "/m51_flowerbeds_closeup.png"
    bpy.ops.render.render(write_still=True)
    rendered.append(sc.render.filepath)
    fnm = fill_obj.name
    bpy.data.objects.remove(fill_obj, do_unlink=True)
    bpy.data.lights.remove(fill)
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

# ---------------------------------------------------------------- 统计
n_m51 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M51",
    "ok": True,
    "n_removed_old": n_removed,
    "n_hedge_segments": n_hedge,
    "n_planter_boxes": len(planter_pts),
    "n_flowers": flower_count,
    "n_m51_objects": n_m51,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "materials_reused": [CONC.name, GRASS.name],
    "materials_new": [SOIL.name] + [f.name for f in FLOWERS],
    "rendered": rendered,
}
print("M51_RESULT=" + repr(result))
