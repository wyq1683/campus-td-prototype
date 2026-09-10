# -*- coding: utf-8 -*-
"""
M68 · 校内主车道停车场车位标线 (Campus Driveway Parking Stalls)
============================================================================
项目已收官（M0–M67 ✅）。按「无未完成里程碑时自行增加改进项」新增 M68：
M67 的「下一步」候选之一 = "停车场车位标线（画在车道上零 3D 冲突）"。
场景中已存在由三块路面构成的校内主车道环线（Road / Road.001 / Road.002，
M58 沿其刷了蓝色边线、M67 中段铺了黄色减速带）。本里程碑在其中一条最长
直段上铺一组**白色垂直停车位标线**（两道长边白线 + 垂直分隔档 + 一个白 "P"
停车符号），像真实校内车道边的停车湾，让"可停车"可读。
与 M50/M58 同款：纯地面涂绘、全部落进路面 AABB 内、零实体结构、零碰撞风险。

坐标（M11 之后铁律，禁止硬编码）：
  - 全部从场景里当前 Road / Road.001 / Road.002 对象的世界 AABB 动态读取。
  - 任一路面对象缺失则优雅跳过（不报错、不空跑）。

设计（原型级、纯地面涂绘）：
  - 选定最长直段路面，按其长边方向在靠一侧画一条"停车湾"：
      * 两道与路平行的白色边线（界定停车湾区）；
      * 垂直分隔档（沿路长边每 ~2.6m 一道，呈梳齿状）；
      * 湾口画一个白色 "P" 停车符号（4 笔：竖干+上横+中横+右竖）。
  - 全部 thin box（高 0.04m）落在路顶之上（z = road_top + 0.05），不穿模、不 z-fight。
  - 白色标线材质 = 白底 + 极弱自发光（白天也清晰可读，与 M50/M58 同思路）。

避坑（沿用 PLAN.md + M50/M58/M67 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M68_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "M68_"
ROAD_NAMES = ("Road", "Road.001", "Road.002")

END_INSET = 1.0        # 沿路长边两端内退（m）
SIDE_INSET = 0.5       # 沿路宽边两端内退（m）
BAY_FRAC = 0.50        # 停车湾占路面宽边的一半（留另一侧作通车道）
STALL = 2.6            # 垂直停车位档间距（m，标准车位宽 ~2.5m）
LINE_W = 0.16          # 标线宽（m）
PAINT_H = 0.04         # 标线盒高（m）
Z_OFF = 0.05           # 标线中心离路顶高度（路顶 ~0.1 → 0.13 居中）
EMIT = 0.12            # 白色标线自发光（白天可读）


# ---------------------------------------------------------------- 工具
def world_aabb(o):
    try:
        if o.bound_box is None:
            return None
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        return (min(xs), min(ys), max(xs), max(ys), max(zs))
    except Exception:
        return None


def clear_old(prefix):
    removed = []
    names = [o.name for o in bpy.data.objects if o.name.startswith(prefix)]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None:
            continue
        try:
            if o.data and getattr(o.data, "users", 0) <= 1:
                try:
                    bpy.data.meshes.remove(o.data)
                except Exception:
                    pass
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass
        removed.append(nm)
    return removed


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


def make_pbr(name, base, rough, metal=0.0, emissive=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nde in list(nt.nodes):
        nt.nodes.remove(nde)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissive > 0:
        bsdf.inputs["Emission Color"].default_value = (base[0], base[1], base[2], 1)
        bsdf.inputs["Emission Strength"].default_value = emissive
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def paint_stroke(bm_all, cx, cy, dirx, diry, length, width, z, mat_idx):
    """在 XY 平面画一段薄 box 标线：沿 (dirx,diry) 长 length，垂直厚 width，中心高 z。"""
    d = Vector((dirx, diry, 0.0)).normalized()
    up = Vector((0.0, 0.0, 1.0))
    perp = up.cross(d).normalized()
    H = PAINT_H
    M = Matrix((
        (d.x * length, perp.x * width, up.x * H, cx),
        (d.y * length, perp.y * width, up.y * H, cy),
        (d.z * length, perp.z * width, up.z * H, z),
        (0.0, 0.0, 0.0, 1.0),
    ))
    prim = box_bm()
    prim.transform(M)
    add_bm(bm_all, prim, mat_idx)


def draw_P(bm_all, cx, cy, s, z, mat_idx):
    """白 "P" 停车符号（4 笔）。s = 字符尺寸；整体宽 ~0.8s、高 ~1.4s。"""
    half_w = 0.40 * s
    half_h = 0.70 * s
    # 竖干（左）：dir=(0,1)，length=1.4s，中心 x=cx-half_w
    paint_stroke(bm_all, cx - half_w, cy, 0.0, 1.0, 1.4 * s, LINE_W, z, mat_idx)
    # 上横：dir=(1,0)，length=0.8s，中心 y=cy+half_h
    paint_stroke(bm_all, cx, cy + half_h, 1.0, 0.0, 0.8 * s, LINE_W, z, mat_idx)
    # 中横：dir=(1,0)，length=0.8s，中心 y=cy
    paint_stroke(bm_all, cx, cy, 1.0, 0.0, 0.8 * s, LINE_W, z, mat_idx)
    # 右竖（上半环）：dir=(0,1)，length=0.7s，中心 x=cx+half_w，y=cy+half_h/2
    paint_stroke(bm_all, cx + half_w, cy + half_h / 2.0, 0.0, 1.0, 0.7 * s, LINE_W, z, mat_idx)


# ---------------------------------------------------------------- 主构建
removed = clear_old(PREFIX)
WHITE = make_pbr(PREFIX + "White", (0.92, 0.92, 0.90), 0.55, 0.0, emissive=EMIT)
bm_all = bmesh.new()

roads = [o for o in bpy.data.objects if o.name in ROAD_NAMES and world_aabb(o)]
# 选最长直段
best = None
for rd in roads:
    a = world_aabb(rd)
    longside = max(a[2] - a[0], a[3] - a[1])
    if best is None or longside > best[0]:
        best = (longside, rd, a)
if best is None:
    # 兜底：西段建一条
    result = {"milestone": "M68", "ok": False, "reason": "no Road objects found",
              "n_total": len(bpy.data.objects)}
    print("M68_RESULT=" + repr(result))
    raise SystemExit(0)

longside, rd, a = best
x0, y0, x1, y1, zmax = a
road_top = zmax
paint_z = road_top + Z_OFF
horizontal = (x1 - x0) >= (y1 - y0)

bay = None  # 记录几何供相机用
if horizontal:
    L = x1 - x0
    W = y1 - y0
    bx0 = x0 + END_INSET
    bx1 = x1 - END_INSET
    by0 = y0 + SIDE_INSET
    by1 = y0 + W * BAY_FRAC
    # 两道长边白线（沿 x）
    paint_stroke(bm_all, (bx0 + bx1) / 2.0, by0, 1.0, 0.0, (bx1 - bx0), LINE_W, paint_z, 0)
    paint_stroke(bm_all, (bx0 + bx1) / 2.0, by1, 1.0, 0.0, (bx1 - bx0), LINE_W, paint_z, 0)
    # 垂直分隔档（沿 y）
    n = int((bx1 - bx0) / STALL)
    for i in range(n + 1):
        x = bx0 + i * STALL
        paint_stroke(bm_all, x, (by0 + by1) / 2.0, 0.0, 1.0, (by1 - by0), LINE_W, paint_z, 0)
    # "P" 符号：湾口一端（x 较小侧），居中 y
    s = min(1.2, (by1 - by0) * 0.95 / 1.4)
    draw_P(bm_all, bx0 + 2.0, (by0 + by1) / 2.0, s, paint_z, 0)
    bay = {"cx": (bx0 + bx1) / 2.0, "cy": (by0 + by1) / 2.0, "cz": road_top,
           "orient": "h", "len": (bx1 - bx0)}
else:
    L = y1 - y0
    W = x1 - x0
    by0 = x0 + SIDE_INSET
    by1 = x0 + W * BAY_FRAC
    bx0 = y0 + END_INSET
    bx1 = y1 - END_INSET
    # 两道长边白线（沿 y）
    paint_stroke(bm_all, by0, (bx0 + bx1) / 2.0, 0.0, 1.0, (bx1 - bx0), LINE_W, paint_z, 0)
    paint_stroke(bm_all, by1, (bx0 + bx1) / 2.0, 0.0, 1.0, (bx1 - bx0), LINE_W, paint_z, 0)
    # 垂直分隔档（沿 x）
    n = int((bx1 - bx0) / STALL)
    for i in range(n + 1):
        y = bx0 + i * STALL
        paint_stroke(bm_all, (by0 + by1) / 2.0, y, 1.0, 0.0, (by1 - by0), LINE_W, paint_z, 0)
    s = min(1.2, (by1 - by0) * 0.95 / 1.4)
    draw_P(bm_all, (by0 + by1) / 2.0, bx0 + 2.0, s, paint_z, 0)
    bay = {"cx": (by0 + by1) / 2.0, "cy": (bx0 + bx1) / 2.0, "cz": road_top,
           "orient": "v", "len": (bx1 - bx0)}

# 落盘为单一 mesh 物体
me = bpy.data.meshes.new(PREFIX + "PaintMesh")
bm_all.to_mesh(me)
bm_all.free()
o_paint = bpy.data.objects.new(PREFIX + "Paint", me)
o_paint.data.materials.append(WHITE)
bpy.context.scene.collection.objects.link(o_paint)

# ---------------------------------------------------------------- 选址相机
# 中角度 3/4：从停车湾外侧（路面空侧）沿长边看入，构图清楚、不撞建筑。
# 相机离远些、高些，减少两侧楼墙在画面中的占比，让停车湾主体更突出。
# 对水平路段（x 长）：相机从南侧（y 更小）看向北；
# 对垂直路段（y 长）：相机从西侧（x 更小）看向东。
if bay["orient"] == "h":
    cam_loc = Vector((bay["cx"], bay["cy"] - 18.0, 14.0))
else:
    cam_loc = Vector((bay["cx"] - 18.0, bay["cy"], 14.0))
bpy.ops.object.camera_add(location=tuple(cam_loc))
cam = bpy.context.active_object
cam.name = PREFIX + "Cam"
cam.data.lens = 32.0
tgt = Vector((bay["cx"], bay["cy"], 0.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

n_m68 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M68",
    "ok": True,
    "n_removed_old": len(removed),
    "roads_found": [o.name for o in roads],
    "best_road": rd.name,
    "road_orient": bay["orient"],
    "bay_length": round(bay["len"], 2),
    "n_stall_dividers": n if 'n' in dir() else 0,
    "n_m68_objects": n_m68,
    "n_total_objects": len(bpy.data.objects),
}
print("M68_RESULT=" + repr(result))
