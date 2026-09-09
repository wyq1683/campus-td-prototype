# -*- coding: utf-8 -*-
"""
M47 · 室外乒乓球台（Outdoor Ping-Pong Tables · 校园生活细节）
============================================================================
项目已收官（M0–M46 ✅）。按「无未完成里程碑时自行增加改进项」新增 M47：
给体育馆旁加一组**室外乒乓球台**——这是中国高中最标志性的课间活动设施，
当前校园有运动场(M38-42)、路灯(M43)、楼牌(M44)、泛光灯塔(M45)、自行车棚(M46)，
但学生下课后打乒乓球的场景从未出现，识别度与生活感缺一块。

为什么做这个：
  - 室外乒乓球台是中国高中/初中的"国民级"设施，成排摆在体育馆或教学楼旁空地。
  - 自成一体、零破坏其他物体，坐标全部从场景动态读取（PLAN.md 铁律）。

坐标**从场景当前几何读取**（M11 之后禁止硬编码）：
  - 目标楼 = Bldg_Gym（体育馆，缺则 Bldg_Teach / 首栋 Bldg_*）。
  - 朝向 = 楼中心指向校园中心(由 M11_Wall AABB 并集得)的方向 n（水平外法线）。
  - 球台成 2 行 × 3 列网格，摆在楼"朝中庭"那面外侧空地；若与其它楼 AABB /
    室外运动场(M38_Pitch) / 自行车棚(M46_)重叠则收紧间距(GAP 收敛)。

乒乓球台几何（接近 ITTF 标准，原型级）：
  - 台面 2.74m(长) × 1.525m(宽) × 0.04m(厚)，台高 0.76m。
  - 4 腿（金属）；台面深青绿 + 白色中线（沿长边）+ 白色球网（跨宽、台中、高 0.16m）。
  - 台体(台面+腿+中线)合并为单 mesh（2 材质：青绿台面 / 金属腿），球网为独立白色半透物体。

避坑（沿用 PLAN.md + M46 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部用 bmesh 直建（与 M46 一致）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M47_，绝不 select_all+delete。
  - 材质自建于 M47_ 前缀（不复用/重建 PBR_*，避免 M18 提到的"重建材质丢其它物体槽"）。
  - Blender 5.2 Principled 输入名：Base Color / Metallic / Roughness / Emission Strength；
    半透网用 blend_method='BLEND' + Alpha 输入（无 shadow_method 属性）。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M47_"

# 乒乓球台尺寸（m）
T_LEN = 2.74     # 长（沿本地 X）
T_WID = 1.525    # 宽（沿本地 Y）
T_TOP = 0.76     # 台高
T_THK = 0.04     # 台面厚
LEG_R = 0.06     # 腿截面
NET_H = 0.16     # 网高（台面之上）
NET_THK = 0.04

N_ROW_T = 3      # 沿 t（长边排开）列数
N_ROW_N = 2      # 沿 n（深度）行数
SPACING_T = 3.2  # 同行长边间距
SPACING_N = 3.6  # 深度行间距
GAP0 = 2.0       # 距楼面初始间距


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


def link(o):
    bpy.context.scene.collection.objects.link(o)


def basis_mat(Xc, Yc, Zc, T):
    if not hasattr(T, "x"):
        T = Vector(T)
    return Matrix((
        (Xc.x, Yc.x, Zc.x, T.x),
        (Xc.y, Yc.y, Zc.y, T.y),
        (Xc.z, Yc.z, Zc.z, T.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


def join_into(bm_dst, bm_src, mat_idx=0):
    vmap = {}
    for v in bm_src.verts:
        vmap[v] = bm_dst.verts.new(v.co)
    for f in bm_src.faces:
        nf = bm_dst.faces.new([vmap[e] for e in f.verts])
        nf.material_index = mat_idx
    bm_src.free()


def box_mesh(size):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
    return bm


def dir_to_R(d, up_hint=(0.0, 0.0, 1.0)):
    q = d.normalized().to_track_quat("Y", "Z")
    return q.to_matrix().to_4x4()


# ---------------------------------------------------------------- 材质
def mat(name, color, metal=0.0, rough=0.6, emit=0.0, alpha=None):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metal
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = rough
            if emit > 0.0 and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emit
            if alpha is not None and "Alpha" in bsdf.inputs:
                bsdf.inputs["Alpha"].default_value = alpha
                m.blend_method = "BLEND"
                m.use_backface_culling = False
    return m


# ---------------------------------------------------------------- 单张球台
def make_table(world_M, top_mat, leg_mat, line_mat):
    """台体(台面+腿+中线)合并为单 mesh，返回 (body_obj, net_obj)。"""
    bm = bmesh.new()
    # 台面
    tb = box_mesh((T_LEN, T_WID, T_THK))
    tb.transform(Matrix.Translation((0.0, 0.0, T_TOP)))
    join_into(bm, tb, mat_idx=0)
    # 白色中线（沿长边 X，跨宽 Y 中央，略高于台面）
    lb = box_mesh((T_LEN, 0.03, T_THK + 0.005))
    lb.transform(Matrix.Translation((0.0, 0.0, T_TOP)))
    join_into(bm, lb, mat_idx=2)
    # 4 腿（金属）
    for sx in (-1, 1):
        for sy in (-1, 1):
            lb2 = box_mesh((LEG_R, LEG_R, T_TOP))
            lb2.transform(Matrix.Translation((sx * (T_LEN / 2 - 0.12),
                                               sy * (T_WID / 2 - 0.12),
                                               T_TOP / 2.0)))
            join_into(bm, lb2, mat_idx=1)
    bm.transform(world_M)
    me = bpy.data.meshes.new(PREFIX + "TableMesh")
    bm.to_mesh(me)
    bm.free()
    body = bpy.data.objects.new(PREFIX + "Table", me)
    body.data.materials.append(top_mat)
    body.data.materials.append(leg_mat)
    body.data.materials.append(line_mat)
    link(body)

    # 球网（跨宽 Y，台中 X=0，白色半透）
    nb = box_mesh((NET_THK, T_WID, NET_H))
    nb.transform(Matrix.Translation((0.0, 0.0, T_TOP + NET_H / 2.0)))
    nb.transform(world_M)
    nme = bpy.data.meshes.new(PREFIX + "NetMesh")
    nb.to_mesh(nme)
    nb.free()
    net = bpy.data.objects.new(PREFIX + "Net", nme)
    net.data.materials.append(line_mat)
    link(net)
    return body, net


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()

TOP_MAT = mat(PREFIX + "Top", (0.10, 0.30, 0.34), metal=0.0, rough=0.45)
LEG_MAT = mat(PREFIX + "Leg", (0.40, 0.41, 0.43), metal=0.85, rough=0.4)
LINE_MAT = mat(PREFIX + "Line", (0.93, 0.94, 0.96), metal=0.0, rough=0.6, alpha=0.6)

# 选目标楼
groups = {}
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        key = "_".join(o.name.split("_")[:2])
        groups.setdefault(key, []).append(o)
target_key = None
for pref in ("Bldg_Gym", "Bldg_Teach", "Bldg_Canteen"):
    if pref in groups:
        target_key = pref
        break
if target_key is None and groups:
    target_key = sorted(groups)[0]
objs = groups.get(target_key, [])
if not objs:
    result = {"ok": False, "why": "no Bldg_* objects found"}
    print("M47_RESULT=" + repr(result))
    raise SystemExit(0)

bs = [aabb(o) for o in objs]
xmin, xmax = min(b[0] for b in bs), max(b[1] for b in bs)
ymin, ymax = min(b[2] for b in bs), max(b[3] for b in bs)
bcx, bcy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
zmaxb = max(b[5] for b in bs)

# 校园中心（M11_Wall 并集）
walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
if walls:
    wb = [aabb(o) for o in walls]
    ccx = (min(b[0] for b in wb) + max(b[1] for b in wb)) / 2.0
    ccy = (min(b[2] for b in wb) + max(b[3] for b in wb)) / 2.0
else:
    ccx, ccy = 0.0, 0.0
cc = Vector((ccx, ccy, 0.0))

# 外法线 n（楼中心 -> 校园中心，水平）
n_dir = (cc - Vector((bcx, bcy, 0.0)))
n_dir.z = 0.0
if n_dir.length < 1e-3:
    n_dir = Vector((0.0, 1.0, 0.0))
n = n_dir.normalized()
up = Vector((0, 0, 1))
t = up.cross(n).normalized()            # 长边方向（水平，沿楼长边）

# 楼沿 n 方向的"到达距离"
corners2d = [(xmin, ymin), (xmax, ymin), (xmin, ymax), (xmax, ymax)]
reach = max((Vector((cx, cy, 0.0)) - Vector((bcx, bcy, 0.0))).dot(n) for cx, cy in corners2d)

# 需避开的 AABB：其它楼 + 室外运动场 + 自行车棚
avoid = [aabb(o) for o in bpy.data.objects
         if (o.name.startswith("Bldg_") and not o.name.startswith(target_key))
         or o.name.startswith("M38_Pitch")
         or o.name.startswith("M46_")]


def cluster_centers(GAP):
    centers = []
    for j in range(N_ROW_N):
        for i in range(N_ROW_T):
            along_t = (i - (N_ROW_T - 1) / 2.0) * SPACING_T
            along_n = reach + GAP + 1.5 + j * SPACING_N
            c = Vector((bcx, bcy, 0.0)) + n * along_n + t * along_t
            centers.append(c)
    return centers


def cluster_fits(centers):
    xs, ys = [], []
    half_t = T_LEN / 2.0 + 0.3
    half_n = T_WID / 2.0 + 0.3
    for c in centers:
        # 台面长边沿 t、宽沿 n
        ct = c + t * half_t; cn = c + n * half_n
        cs = c - t * half_t; cw = c - n * half_n
        for p in (ct, cn, cs, cw):
            xs.append(p.x); ys.append(p.y)
    ax = [min(xs), max(xs), min(ys), max(ys)]
    for b in avoid:
        if not (ax[1] < b[0] or ax[0] > b[1] or ax[3] < b[2] or ax[2] > b[3]):
            return False
    return True


chosen_centers = None
for GAP in (GAP0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
    cs = cluster_centers(GAP)
    if cluster_fits(cs):
        chosen_centers = cs
        break
if chosen_centers is None:
    chosen_centers = cluster_centers(10.0)

# ---- 建台 ----
built = []
table_names = []
for idx, c in enumerate(chosen_centers):
    Xcol = t
    Ycol = n
    Zcol = up
    Rb = basis_mat(Xcol, Ycol, Zcol, (0, 0, 0))
    world_M = Matrix.Translation(c) @ Rb
    body, net = make_table(world_M, TOP_MAT, LEG_MAT, LINE_MAT)
    built.append(body.name)
    built.append(net.name)
    table_names.append(body.name)
    table_names.append(net.name)

# 网格中心（用于相机）
clx = sum(c.x for c in chosen_centers) / len(chosen_centers)
cly = sum(c.y for c in chosen_centers) / len(chosen_centers)
cluster_c = Vector((clx, cly, 0.0))

# ---- 相机：朝中庭一侧看入球台群 ----
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 2.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
cam.location = cluster_c + n * 8.0 + up * 3.2
cam.data.lens = 35.0
cam.rotation_euler = (cluster_c + up * 0.9 - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---- 渲染设定 ----
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
    sc.view_settings.exposure = 0.1
    sc.camera = cam
except Exception as e:
    built.append("RENDER_CFG_WARN:" + str(e))

n_m47 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M47",
    "ok": True,
    "target_building": target_key,
    "n_removed_old": n_removed,
    "n_tables": len(chosen_centers),
    "n_m47_objects": n_m47,
    "n_total_objects": len(bpy.data.objects),
    "cluster_center": [round(cluster_c.x, 1), round(cluster_c.y, 1)],
    "normal": [round(n.x, 2), round(n.y, 2)],
    "building_aabb": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1), round(zmaxb, 1)],
    "objects_sample": built[:12],
}
print("M47_RESULT=" + repr(result))
