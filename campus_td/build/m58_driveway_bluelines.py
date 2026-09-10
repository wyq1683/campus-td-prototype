# -*- coding: utf-8 -*-
"""
M58 · 校内主车道蓝色边线 (Campus Main Driveway Blue Edge Lines)
============================================================================
项目已收官（M0–M57 ✅）。按「无未完成里程碑时自行增加改进项」新增 M58：
M57 的「下一步」首项候选之一 = "车道蓝色边线"。场景中已存在由三块路面构成的
校内主车道环线（Road / Road.001 / Road.002，沿 U 形路径走廊外侧、建筑之间），
但路面只有素色沥青、没有任何车道标线，看起来不像"可通车的车道"。
本里程碑给这条主车道沿其两条长边各刷一道**蓝色边线**（与 M50 自行车道蓝图标
呼应、但位置在车行道而非步道环），让"校内车道"可读。

坐标（M11 之后铁律，禁止硬编码）：
  - 全部从场景里当前 Road / Road.001 / Road.002 对象的世界 AABB 动态读取。
  - 任一路面对象缺失则优雅跳过（不报错、不空跑）。

设计（原型级、纯地面涂绘、零实体结构、零碰撞风险）：
  - 每条路面取 AABB，按长边方向在两条长边内退 INSET=0.3m 处各刷一道蓝线。
  - 蓝线沿长边每 1m 切一段 box 拼成单 mesh（便于按段跳过楼体 AABB，双保险），
    落于路面上方 z=0.12~0.16（路顶 z=0.1，不穿模、不 z-fighting）。
  - 蓝色边线材质 = 蓝底 + 极弱自发光（与 M50 LaneBlue 同色，白天也清晰可读）。

避坑（沿用 PLAN.md + M50 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M58_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M58_"
ROAD_NAMES = ("Road", "Road.001", "Road.002")   # 既有校内主车道环线
INSET = 0.30          # 蓝线距路缘内退（m）
LINE_W = 0.14         # 蓝线宽（m）
Z_PAIN = 0.14         # 蓝线中心离地高（盒高 0.04 → 0.12~0.16，路顶 0.1）
SEG = 1.0             # 沿线分段长（m）
BLD_MARGIN = 0.5      # 楼体避障外扩
GATE_HALF = 9.0       # 南墙校门半宽（路网不抵校门，仅作兜底）


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


def box_bm():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
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
    return Matrix((
        (d.x * L, perp.x * W, up.x * H, C.x),
        (d.y * L, perp.y * W, up.y * H, C.y),
        (d.z * L, perp.z * W, up.z * H, C.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


def get_blue():
    name = PREFIX + "LaneBlue"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.12, 0.34, 0.78, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.55
            bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.12, 0.34, 0.78, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.12
    return m


# ---------------------------------------------------------------- 楼体避障
blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
BLU = get_blue()
bm_blue = bmesh.new()
up = Vector((0.0, 0.0, 1.0))

roads = [bpy.data.objects.get(n) for n in ROAD_NAMES]
roads = [o for o in roads if o is not None]
n_lines_segs = 0
n_skipped = 0


def paint_line(p0, p1):
    """沿 p0→p1 每 SEG 米刷一段蓝线 box，遇楼体 AABB 跳过该段。"""
    global n_lines_segs, n_skipped
    d = p1 - p0
    L = d.length
    if L < 1e-3:
        return
    u = d.normalized()
    perp = up.cross(u).normalized()
    N = max(1, int(math.ceil(L / SEG)))
    seg = L / N
    for i in range(N):
        c = p0 + u * (seg * (i + 0.5))
        if inside_building(c.x, c.y):
            n_skipped += 1
            continue
        M = basis_scaled(u, perp, up, c + up * Z_PAIN, seg, LINE_W, 0.04)
        prim = box_bm()
        prim.transform(M)
        add_bm(bm_blue, prim, 0)
        n_lines_segs += 1


def paint_strip(o):
    """对一块路面 AABB：按长边方向在两条长边刷蓝线。"""
    b = aabb(o)
    x0, x1, y0, y1 = b[0], b[1], b[2], b[3]
    horizontal = (x1 - x0) >= (y1 - y0)
    if horizontal:
        for ey in (y0 + INSET, y1 - INSET):
            paint_line(Vector((x0, ey, 0.0)), Vector((x1, ey, 0.0)))
    else:
        for ex in (x0 + INSET, x1 - INSET):
            paint_line(Vector((ex, y0, 0.0)), Vector((ex, y1, 0.0)))


for o in roads:
    paint_strip(o)

# 落盘为单一 mesh 物体
me = bpy.data.meshes.new(PREFIX + "BlueEdgeMesh")
bm_blue.to_mesh(me)
bm_blue.free()
o_blue = bpy.data.objects.new(PREFIX + "BlueEdge", me)
o_blue.data.materials.append(BLU)
bpy.context.scene.collection.objects.link(o_blue)


# ---------------------------------------------------------------- 验证相机
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(-35.0, -30.0, 14.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
# 取景从道路上方沿南向 Road 俯视/平视，蓝线在画面中呈两条平行线清晰可读。
# 相机放在 Road 正上方偏南、z=12m，避开所有建筑和街道设施。
cam.location = (14.0, -18.0, 12.0)
cam.data.lens = 60.0
target = Vector((14.0, -13.0, 0.0))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定（与 M50..M57 一致）
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

n_m58 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M58",
    "ok": True,
    "n_removed_old": n_removed,
    "roads_found": [o.name for o in roads],
    "n_blue_segments": n_lines_segs,
    "n_skipped_in_building": n_skipped,
    "n_m58_objects": n_m58,
    "n_total_objects": len(bpy.data.objects),
}
print("M58_RESULT=" + repr(result))
