# -*- coding: utf-8 -*-
"""
M48 · 校园长椅垃圾桶（Campus Benches & Trash Bins · 校园生活细节）
============================================================================
项目已收官（M0–M47 ✅）。按「无未完成里程碑时自行增加改进项」新增 M48：
给校园加**室外长椅 + 垃圾桶**——中国高中/初中的"国民级"生活设施，
当前有运动场(M38-42)、路灯(M43)、楼牌(M44)、泛光灯塔(M45)、自行车棚(M46)、
乒乓球台(M47)，但学生课间坐着聊天、随手丢垃圾的"有人生活"场景从没出现。

为什么做这个：
  - 长椅沿外围步行道（M43 路灯同一条 walkway）成排，垃圾桶摆在每栋楼入口、
    运动场边——补全"生活痕迹"，强化电影级校园的可居住感。
  - 自成一体、零破坏其他物体，坐标全部从场景当前几何动态读取（PLAN.md 铁律）。

坐标**从场景当前几何读取**（M11 之后禁止硬编码）：
  - 步行道内框 ← M11_Wall* AABB 并集内退 INSET（与 M43 同一条 walkway，肉眼一致）。
  - 长椅面朝校园中心（背靠围墙）；避障跳过 Bldg_* AABB（外扩）与南墙校门洞。
  - 垃圾桶 ← 每栋 Bldg_* 朝中庭那面的入口处（楼中心→校园中心方向 n，外推 1.5m）；
    另在室外运动场(M38_Pitch)两角补 2 个，方便看球丢瓶。

几何体（原型级、合并为单 mesh / 单物体）：
  - 长椅：木坐板 4 条 + 木靠背 3 条（复用 PBR_Wood）+ 金属两端支撑架 + 上下横档
    （M48_Frame，深金属色），合并为 1 物体（2 材质：木 0 / 金属 1）。
  - 垃圾桶：绿身圆柱 + 深绿盖 + 底座，合并为 1 物体（2 材质：身 0 / 盖底座 1）。

避坑（沿用 PLAN.md + M43/M46/M47 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部用 bmesh 直建（与 M43/46/47 一致）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M48_，绝不 select_all+delete。
  - 材质自建于 M48_ 前缀（复用既有 PBR_Wood / PBR_Metal，避免 M18 提过的"重建材质丢槽"）。
  - Blender 5.2 Principled 输入名：Base Color / Metallic / Roughness / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M48_"

# ---- 长椅尺寸 (m) ----
SEAT_LEN = 1.7      # 长（沿本地 X）
SEAT_DEPTH = 0.55   # 深（沿本地 Y）
SEAT_H = 0.45       # 坐高
SLAT_T = 0.045      # 板厚
BACK_H = 0.45       # 靠背高
FRAME_T = 0.08      # 支架厚

# ---- 垃圾桶尺寸 (m) ----
BIN_R = 0.26
BIN_H = 0.78
BIN_LID_R = 0.30

# ---- 布局 ----
WALK_INSET = 6.0    # 距围墙内退（与 M43 同一条 walkway）
BENCH_SPACING = 18.0
MAX_BENCHES = 16
BLD_MARGIN = 1.6    # 楼体避障外扩
GATE_HALF = 9.0     # 南墙校门半宽


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


def cyl(r, h, seg=16):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=r, radius2=r, depth=h)
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
def get_wood():
    m = bpy.data.materials.get("PBR_Wood")
    if m is None:
        m = bpy.data.materials.get(PREFIX + "Wood")
        if m is None:
            m = bpy.data.materials.new(PREFIX + "Wood")
            m.use_nodes = True
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.20, 0.13, 0.07, 1.0)
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.72
                if "Metallic" in bsdf.inputs:
                    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def get_frame():
    m = bpy.data.materials.get(PREFIX + "Frame")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "Frame")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.05, 0.06, 0.06, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.5
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.7
    return m


def get_bin_body():
    m = bpy.data.materials.get(PREFIX + "BinBody")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "BinBody")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.08, 0.24, 0.13, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.7
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.1
    return m


def get_bin_lid():
    m = bpy.data.materials.get(PREFIX + "BinLid")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "BinLid")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.04, 0.14, 0.08, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.6
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.1
    return m


# ---------------------------------------------------------------- 长椅（合并单 mesh）
def make_bench(world_M, wood_mat, frame_mat):
    bm = bmesh.new()
    # 坐板 4 条（木）
    for sy in (-0.18, -0.06, 0.06, 0.18):
        sb = box(SEAT_LEN, 0.10, SLAT_T)
        sb.transform(Matrix.Translation((0.0, sy, SEAT_H)))
        add_bm(bm, sb, 0)
    # 靠背 3 条（木，位于 -Y 背侧）
    for bz in (0.50, 0.64, 0.78):
        bb = box(SEAT_LEN, 0.09, SLAT_T)
        bb.transform(Matrix.Translation((0.0, -SEAT_DEPTH / 2.0 - 0.02, bz)))
        add_bm(bm, bb, 0)
    # 两端支架（金属）
    for ex in (-SEAT_LEN / 2.0, SEAT_LEN / 2.0):
        eb = box(FRAME_T, 0.55, SEAT_H + 0.05)
        eb.transform(Matrix.Translation((ex, 0.0, (SEAT_H + 0.05) / 2.0)))
        add_bm(bm, eb, 1)
    # 下横档（金属，连两端）
    rb = box(SEAT_LEN, FRAME_T, FRAME_T)
    rb.transform(Matrix.Translation((0.0, 0.0, 0.06)))
    add_bm(bm, rb, 1)
    # 靠背顶横档（金属）
    rb2 = box(SEAT_LEN, FRAME_T, FRAME_T)
    rb2.transform(Matrix.Translation((0.0, -SEAT_DEPTH / 2.0 - 0.02, 0.80)))
    add_bm(bm, rb2, 1)

    bm.transform(world_M)
    me = bpy.data.meshes.new(PREFIX + "BenchMesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + "Bench", me)
    o.data.materials.append(wood_mat)
    o.data.materials.append(frame_mat)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 垃圾桶（合并单 mesh）
def make_bin(world_M, body_mat, lid_mat):
    bm = bmesh.new()
    body = cyl(BIN_R, BIN_H, 16)
    body.transform(Matrix.Translation((0.0, 0.0, BIN_H / 2.0 + 0.04)))
    add_bm(bm, body, 0)
    base = cyl(BIN_LID_R, 0.04, 16)
    base.transform(Matrix.Translation((0.0, 0.0, 0.02)))
    add_bm(bm, base, 1)
    lid = cyl(BIN_LID_R, 0.05, 16)
    lid.transform(Matrix.Translation((0.0, 0.0, BIN_H + 0.04 + 0.025)))
    add_bm(bm, lid, 1)
    bm.transform(world_M)
    me = bpy.data.meshes.new(PREFIX + "BinMesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + "Bin", me)
    o.data.materials.append(body_mat)
    o.data.materials.append(lid_mat)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
WOOD = get_wood()
FRAME = get_frame()
BINB = get_bin_body()
BINL = get_bin_lid()

# 校园范围（M11_Wall 并集）
walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
if walls:
    wb = [aabb(o) for o in walls]
    xmin, xmax = min(b[0] for b in wb), max(b[1] for b in wb)
    ymin, ymax = min(b[2] for b in wb), max(b[3] for b in wb)
else:
    xmin, xmax, ymin, ymax = -48, 48, -48, 48
cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
xi0, xi1 = xmin + WALK_INSET, xmax - WALK_INSET
yi0, yi1 = ymin + WALK_INSET, ymax - WALK_INSET

up = Vector((0, 0, 1))
cc = Vector((cx, cy, 0.0))

# 楼体避障 AABB
blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False


def in_gate_gap(x, y):
    return (y < yi0 + 3.0) and (abs(x) < GATE_HALF)


# ---- 长椅候选点（沿内矩形四边，步长 BENCH_SPACING）----
cands = []
for y in (yi0, yi1):
    L = xi1 - xi0
    n = max(1, int(round(L / BENCH_SPACING)))
    for i in range(n + 1):
        cands.append((xi0 + L * i / n, y))
for x in (xi0, xi1):
    L = yi1 - yi0
    n = max(1, int(round(L / BENCH_SPACING)))
    for i in range(1, n):
        cands.append((x, yi0 + L * i / n))

bench_pts = []
for (x, y) in cands:
    if inside_building(x, y):
        continue
    if in_gate_gap(x, y):
        continue
    bench_pts.append((x, y))
    if len(bench_pts) >= MAX_BENCHES:
        break

benches = []
for (x, y) in bench_pts:
    p = Vector((x, y, 0.0))
    out = (p - cc)
    out.z = 0.0
    if out.length < 1e-3:
        out = Vector((0.0, 1.0, 0.0))
    out = out.normalized()
    Xc = up.cross(out).normalized()   # 沿墙切向 = 长椅长边
    Yc = out                          # 背靠围墙（朝外）
    Zc = up
    Rb = basis_mat(Xc, Yc, Zc, (0, 0, 0))
    world_M = Matrix.Translation(p) @ Rb
    benches.append(make_bench(world_M, WOOD, FRAME).name)

# ---- 垃圾桶：每栋楼入口 + 运动场两角 ----
bin_pts = []
groups = {}
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        key = "_".join(o.name.split("_")[:2])
        groups.setdefault(key, []).append(o)
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
    corners = [(bsi[0], bsi[2]) for bsi in bs] + [(bsi[1], bsi[2]) for bsi in bs] + \
              [(bsi[0], bsi[3]) for bsi in bs] + [(bsi[1], bsi[3]) for bsi in bs]
    reach = max((Vector((cx2, cy2, 0.0)) - bc).dot(n) for cx2, cy2 in corners)
    ent = bc + n * (reach + 1.5)
    bin_pts.append((ent.x, ent.y))

# 室外运动场两角（M38_Pitch AABB）
pitch = [aabb(o) for o in bpy.data.objects if o.name.startswith("M38_Pitch")]
if pitch:
    pb = pitch[0]
    for sx in (-1, 1):
        bx = pb[0] + (pb[1] - pb[0]) / 2.0 + sx * (pb[1] - pb[0]) / 2.0 * 0.0
        # 放在运动场长边外侧中点
        bx = (pb[0] if sx < 0 else pb[1])
        by = (pb[2] + pb[3]) / 2.0
        bin_pts.append((bx + (sx * -0.5), by))

bins = []
for (x, y) in bin_pts:
    if inside_building(x, y):
        continue
    p = Vector((x, y, 0.0))
    world_M = Matrix.Translation(p)
    bins.append(make_bin(world_M, BINB, BINL).name)

# ---- 相机：看入第一组长椅 ----
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 2.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
if bench_pts:
    bp = Vector((bench_pts[0][0], bench_pts[0][1], 0.0))
    out = (bp - cc)
    out.z = 0.0
    if out.length < 1e-3:
        out = Vector((0.0, 1.0, 0.0))
    out = out.normalized()
    cam.location = bp + out * 4.0 + up * 1.8
    cam.data.lens = 35.0
    cam.rotation_euler = ((bp + up * 0.5) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---- 渲染设定（确定性，与 M43..M47 一致）----
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
    sc.view_settings.exposure = 0.15
    sc.camera = cam
except Exception as e:
    benches.append("RENDER_CFG_WARN:" + str(e))

n_m48 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M48",
    "ok": True,
    "n_removed_old": n_removed,
    "n_benches": len(benches),
    "n_bins": len(bins),
    "n_m48_objects": n_m48,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "bench_points": len(bench_pts),
    "bin_points": len(bin_pts),
    "bench_sample": benches[:6],
    "bin_sample": bins[:6],
}
print("M48_RESULT=" + repr(result))
