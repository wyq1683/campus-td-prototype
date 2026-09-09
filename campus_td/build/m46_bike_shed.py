# -*- coding: utf-8 -*-
"""
M46 · 自行车棚（Bicycle Shed · metal canopy + bike racks + stylized bikes）
============================================================================
项目已收官（M0–M45 ✅）。按「无未完成里程碑时自行增加改进项」新增 M46：
给教学楼旁加一座**自行车棚**——这是真实高中最典型的校园生活细节之一，
当前场景里学生/教职工的自行车无处可停，识别度与生活感都缺一块。

为什么做这个：
  - 真实高中必有大面积自行车停放区（教学楼/宿舍楼下最集中）。当前校园只有
    路灯(M43)、楼牌(M44)、泛光灯塔(M45)，缺"人生活的痕迹"。
  - 自行车棚 = 金属柱 + 顶棚 + 后挡墙 + 2 排车架 + 若干简化自行车，自成
    一体、零破坏其他物体，且坐标全部从场景动态读取（PLAN.md 铁律）。

坐标**从场景当前几何读取**（M11 之后禁止硬编码）：
  - 目标楼 = Bldg_Teach（缺则 Bldg_Dorm，再缺则首栋 Bldg_*）。
  - 朝向 = 楼中心指向校园中心(由 M11_Wall AABB 并集得)的方向 n（水平外法线）。
  - 棚置于楼"朝中庭"那面外侧、贴楼、不插进楼里；若与其它楼 AABB 重叠则收紧间距。
  - 棚长边沿楼长边（t = up × n）铺开，自行车成 2 排停在车架上。

避坑（沿用 PLAN.md + M44/M45 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部用 bmesh 直建（与 M45 一致）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M46_，绝不 select_all+delete。
  - 材质自建于 M46_ 前缀（不复用/重建 PBR_*，避免 M18 提到的"重建材质丢其它物体槽"）。
  - Blender 5.2 Principled 输入名：Emission Color / Emission Strength。
  - 自行车用单 mesh 合并（仿 M17 课桌合并思路）：轮/架/座/把经 bmesh join_into
    合入同一 bmesh，每辆仅 1 个物体，控制总数。
  - 字体走 M44 验证过的 pick_font_once()（带字形尺寸自检）。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M46_"

SHED_LEN = 12.0      # 沿楼长边（m）
SHED_DEPTH = 3.2     # 沿外法线（m）
ROOF_H = 2.6         # 顶棚高（m）
GAP0 = 4.0           # 棚内缘距楼面初始间距（m）
N_ROWS = 2
N_PER_ROW = 6
ROW_OFF = 0.85       # 2 排相对棚中心的深度偏移（m）
BIKE_GAP = 0.05

# 自行车调色板（确定性，避免每帧乱色）
BIKE_PALETTE = [
    (0.78, 0.18, 0.18),  # 红
    (0.18, 0.42, 0.72),  # 蓝
    (0.20, 0.62, 0.32),  # 绿
    (0.85, 0.62, 0.12),  # 黄
    (0.80, 0.45, 0.15),  # 橙
    (0.15, 0.60, 0.62),  # 青
]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]
FONT_H_MIN, FONT_W_MIN = 0.55, 0.55


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


def set_mat(o, m):
    if o.data.materials:
        o.data.materials[0] = m
    else:
        o.data.materials.append(m)


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


def box_at(center, size, R, mat, name):
    bm = box_mesh(size)
    bm.transform(R)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    link(o)
    return o


def torus_mesh(major, minor, seg=16, ring=5):
    # Blender 5.2 bmesh 无 create_torus：用薄圆柱(=圆盘)近似车轮
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=seg, radius1=major, radius2=major, depth=2.0 * minor)
    return bm


def dir_to_R(d, up_hint=(0.0, 0.0, 1.0)):
    q = d.normalized().to_track_quat("Y", "Z")
    return q.to_matrix().to_4x4()


# ---------------------------------------------------------------- 材质
def mat(name, color, metal=0.0, rough=0.6, emit=0.0):
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
    return m


# 材质实例在 clear_old() 之后创建（见主构建段），避免被幂等清空删掉。


# ---------------------------------------------------------------- 自行车
def make_bike(world_M, frame_mat):
    bm = bmesh.new()
    up = Vector((0, 0, 1))
    # 2 轮（垂直圆，轴沿 X）：torus 默认轴 Z -> 绕 X 转 90° 使轴沿 Y 即竖直
    for hub in (Vector((0, -0.5, 0.30)), Vector((0, 0.5, 0.30))):
        tb = torus_mesh(0.30, 0.035)
        tb.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
        tb.transform(Matrix.Translation(hub))
        join_into(bm, tb, mat_idx=1)
    # 车架杆
    rear = Vector((0, -0.5, 0.30)); front = Vector((0, 0.5, 0.30))
    bb = Vector((0, 0.0, 0.32)); seat = Vector((0, -0.08, 0.62))
    head = Vector((0, 0.42, 0.52)); bar = Vector((0, 0.46, 0.78))
    for (p1, p2, th) in [(rear, bb, 0.04), (bb, head, 0.04), (bb, seat, 0.04),
                         (seat, head, 0.035), (head, bar, 0.03), (rear, seat, 0.035)]:
        d = p2 - p1
        cb = box_mesh((th, max(d.length, 1e-3), th))
        R = dir_to_R(d)
        cb.transform(Matrix.Translation((p1 + p2) / 2.0) @ R)
        join_into(bm, cb, mat_idx=0)
    # 座垫 + 车把
    sb = box_mesh((0.10, 0.18, 0.05)); sb.transform(Matrix.Translation(seat)); join_into(bm, sb, 0)
    hb = box_mesh((0.34, 0.04, 0.04)); hb.transform(Matrix.Translation(bar)); join_into(bm, hb, 0)
    # 烘焙世界变换
    bm.transform(world_M)
    me = bpy.data.meshes.new(PREFIX + "BikeMesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + "Bike", me)
    o.data.materials.append(frame_mat)
    o.data.materials.append(WHEEL_MAT)
    link(o)
    return o


# ---------------------------------------------------------------- 字体（复用 M44 管线）
def pick_font_once(text):
    tried = []
    n = max(1, len(text))
    for p in FONT_CANDIDATES:
        try:
            f = bpy.data.fonts.load(p)
        except Exception as e:
            tried.append({"file": p.split("\\")[-1], "ok": False, "err": str(e)[:60]})
            continue
        bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
        o = bpy.context.active_object
        o.data.body = text
        o.data.font = f
        o.data.size = 1.0
        o.data.align_x = "CENTER"
        bpy.context.view_layer.update()
        h_unit, w_unit = o.dimensions.y, o.dimensions.x
        bpy.data.objects.remove(o, do_unlink=True)
        ok = (h_unit >= FONT_H_MIN) and (w_unit >= n * FONT_W_MIN)
        tried.append({"file": p.split("\\")[-1], "ok": True,
                      "h": round(h_unit, 3), "w": round(w_unit, 3), "pass": bool(ok)})
        if ok:
            return f, h_unit, w_unit, tried
    return None, 0.0, 0.0, tried


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()

# 材质实例在 clear_old() 之后创建，避免被幂等清空删掉
POST_MAT = mat(PREFIX + "Post", (0.46, 0.47, 0.49), metal=0.9, rough=0.4)
ROOF_MAT = mat(PREFIX + "Roof", (0.74, 0.75, 0.77), metal=0.15, rough=0.7)
WALL_MAT = mat(PREFIX + "Wall", (0.62, 0.62, 0.63), metal=0.0, rough=0.85)
RACK_MAT = mat(PREFIX + "Rack", (0.30, 0.31, 0.33), metal=0.8, rough=0.5)
WHEEL_MAT = mat(PREFIX + "Wheel", (0.06, 0.06, 0.07), metal=0.0, rough=0.85)
FRAME_MATS = [mat(PREFIX + "Bike%d" % i, c, metal=0.6, rough=0.4)
              for i, c in enumerate(BIKE_PALETTE)]

# 选目标楼
groups = {}
for o in bpy.data.objects:
    if o.name.startswith("Bldg_"):
        key = "_".join(o.name.split("_")[:2])
        groups.setdefault(key, []).append(o)
target_key = None
for pref in ("Bldg_Teach", "Bldg_Dorm"):
    if pref in groups:
        target_key = pref
        break
if target_key is None and groups:
    target_key = sorted(groups)[0]
objs = groups.get(target_key, [])
if not objs:
    result = {"ok": False, "why": "no Bldg_* objects found"}
    print("M46_RESULT=" + repr(result))
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
t = up.cross(n).normalized()            # 棚长边方向（水平，沿楼长边）

# 楼沿 n 方向的"到达距离"
corners2d = [(xmin, ymin), (xmax, ymin), (xmin, ymax), (xmax, ymax)]
reach = max((Vector((cx, cy, 0.0)) - Vector((bcx, bcy, 0.0))).dot(n) for cx, cy in corners2d)

# 间距收敛：避免与其它楼重叠
other_blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_") and not o.name.startswith(target_key)]
GAP = GAP0
placed = False
chosen = None
for GAP in (GAP0, 3.0, 2.0, 1.5):
    sc_xy = Vector((bcx, bcy, 0.0)) + n * (reach + SHED_DEPTH / 2.0 + GAP)
    # 棚 AABB（xy）
    half_l = SHED_LEN / 2.0
    half_d = SHED_DEPTH / 2.0
    # 四角
    pts = [sc_xy + t * half_l + n * half_d, sc_xy + t * half_l - n * half_d,
           sc_xy - t * half_l + n * half_d, sc_xy - t * half_l - n * half_d]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    ax = [min(xs), max(xs), min(ys), max(ys)]
    overlap = False
    for b in other_blds:
        if not (ax[1] < b[0] or ax[0] > b[1] or ax[3] < b[2] or ax[2] > b[3]):
            overlap = True
            break
    if not overlap:
        chosen = sc_xy
        placed = True
        break
if chosen is None:
    chosen = Vector((bcx, bcy, 0.0)) + n * (reach + SHED_DEPTH / 2.0 + 1.5)

shed_c = Vector((chosen.x, chosen.y, 0.0))

# ---- 结构：6 柱 + 顶棚 + 后挡墙 ----
R_id = basis_mat(up, t, n, (0, 0, 0))  # 轴对齐用单位阵即可
built = []
# 6 根柱
post_xs = [-SHED_LEN / 2.0, 0.0, SHED_LEN / 2.0]
post_ns = [-SHED_DEPTH / 2.0 + 0.15, SHED_DEPTH / 2.0 - 0.15]
for px in post_xs:
    for pn in post_ns:
        p = shed_c + t * px + n * pn + up * (ROOF_H / 2.0)
        o = box_at(p, (0.12, 0.12, ROOF_H), Matrix.Identity(4), POST_MAT, PREFIX + "Post")
        built.append(o.name)
# 顶棚（略外伸）
roof_c = shed_c + up * ROOF_H
o = box_at(roof_c, (SHED_LEN + 0.4, SHED_DEPTH + 0.4, 0.12), Matrix.Identity(4), ROOF_MAT, PREFIX + "Roof")
built.append(o.name)
# 后挡墙（远离楼一侧 = -n）
wall_c = shed_c - n * (SHED_DEPTH / 2.0) + up * 0.7
o = box_at(wall_c, (SHED_LEN, 0.12, 1.4), Matrix.Identity(4), WALL_MAT, PREFIX + "Wall")
built.append(o.name)

# ---- 2 排车架（沿 t，朝向用 R 旋转 +Y->t）----
R_t = dir_to_R(t)
rack_cz = [0.25, 0.7]
for row in (-1, 1):
    for cz in rack_cz:
        rc = shed_c + t.cross(up).normalized() * (row * ROW_OFF) + up * cz
        # 用 box_mesh + R_t：长度沿 Y
        bm = box_mesh((0.05, SHED_LEN - 1.0, 0.05))
        bm.transform(R_t)
        me = bpy.data.meshes.new(PREFIX + "RackMesh")
        bm.to_mesh(me)
        bm.free()
        ro = bpy.data.objects.new(PREFIX + "Rack", me)
        ro.data.materials.append(RACK_MAT)
        ro.matrix_world = Matrix.Translation(rc)
        link(ro)
        built.append(ro.name)

# ---- 自行车（2 排 × N_PER_ROW）----
Xc = t.cross(up).normalized()   # 排分离方向（= 深度方向 n 的等价）
side = Xc
bike_names = []
for ri, row in enumerate((-1, 1)):
    for i in range(N_PER_ROW):
        along = -SHED_LEN / 2.0 + 1.0 + i * (SHED_LEN - 2.0) / max(1, N_PER_ROW - 1)
        pos = shed_c + t * along + side * (row * ROW_OFF) + up * 0.0
        # 自行车朝向：本地 +Y(前) -> t；+Z->up；+X -> side
        Xcol = side
        Ycol = t
        Zcol = up
        Rb = basis_mat(Xcol, Ycol, Zcol, (0, 0, 0))
        world_M = Matrix.Translation(pos) @ Rb
        fmat = FRAME_MATS[(ri * N_PER_ROW + i) % len(FRAME_MATS)]
        bo = make_bike(world_M, fmat)
        bike_names.append(bo.name)
built.extend(bike_names)

# ---- 招牌「自行车棚」挂在后挡墙外侧（-n 面）----
font, h_unit, w_unit, _tried = pick_font_once("自行车棚")
sign_info = None
if font is not None:
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    txt.name = PREFIX + "SignText"
    td = txt.data
    td.body = "自行车棚"
    td.font = font
    td.align_x = "CENTER"; td.align_y = "CENTER"
    size = 0.7 / h_unit
    td.size = size
    td.extrude = 0.03
    face_pt = shed_c - n * (SHED_DEPTH / 2.0 + 0.08) + up * 2.0
    d = -n
    X = up.cross(d); Y = up; Z = d
    rot = basis_mat(X, Y, Z, face_pt)
    txt.matrix_world = rot
    set_mat(txt, mat(PREFIX + "SignText", (0.93, 0.94, 0.96), emit=0.35))
    bpy.context.view_layer.update()
    built.append(txt.name)
    sign_info = {"size": round(size, 3), "face": [round(v, 2) for v in face_pt]}

# ---- 相机：开放侧（+n，朝中庭）看入棚内 ----
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 2.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
cam.location = shed_c + n * (SHED_DEPTH / 2.0 + 7.0) + up * 2.0
cam.data.lens = 35.0
cam.rotation_euler = (shed_c + up * 1.3 - cam.location).to_track_quat("-Z", "Y").to_euler()
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
    sc.view_settings.exposure = 0.0
    sc.camera = cam
except Exception as e:
    built.append("RENDER_CFG_WARN:" + str(e))

n_m46 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M46",
    "ok": True,
    "target_building": target_key,
    "n_removed_old": n_removed,
    "n_bikes": len(bike_names),
    "n_m46_objects": n_m46,
    "n_total_objects": len(bpy.data.objects),
    "shed_center": [round(shed_c.x, 1), round(shed_c.y, 1)],
    "normal": [round(n.x, 2), round(n.y, 2)],
    "building_aabb": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1), round(zmaxb, 1)],
    "sign": sign_info,
    "objects_sample": built[:10],
}
print("M46_RESULT=" + repr(result))
