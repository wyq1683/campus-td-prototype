# -*- coding: utf-8 -*-
"""
M63 · 校园垃圾分类收集亭（Waste Sorting Station · OptiX）
============================================================================
项目已收官（M0–M62 ✅）。按「无未完成里程碑时自行增加改进项」新增 M63：
真实高中校园 2026 标配的"四分类垃圾分类收集亭"此前完全缺失（M48 只做了普通垃圾桶）。
路灯(M43)/长椅(M48)/宣传栏(M49)/监控(M61)/凉亭(M62)已就位，但缺少最贴近"校园文明"
的环保设施节点。本里程碑在 **verified-clear 的开阔草坪**自动选址建一座四分类垃圾亭
（混凝土基座 + 金属立柱 + 浅色顶篷 + 背板 + 4 色分类垃圾桶 + "垃圾分类" 中文标识），
补全"绿色校园"的可信度。

选址全部**从场景当前几何读取 + 自动避障**（PLAN.md 铁律：M11 之后禁止硬编码）：
  - 候选扫描 ← 全园 interior 网格（围墙内退 9m），跳过距凉亭(36,30)>11m 外 / 距前广场(0,-45)>9m 内、
            dc 不在 [12,42] 的格，取 dc 最小（最居中、可达）的全 clearance 点。
  - 避障 ← 复用 M62 is_blocker：Bldg_*/M46_*/M37_Flag/M11_FlagPole/M11_Tree*/M43_*/M61_*/M48_*/M49_*/
           M44_*/M53_*/M47_*/M41_*/M45_*/M52_*/M16_* 等实体 + M38_/M11_Gate/M59_/M54_/M55_/M60_/Road/M58_ 平铺禁区。
           注意排除 campus-wide 合并网格 M50_/M51_（AABB 跨全园会误判）+ 塔防标记 M7_/Tower_/Enemy_/M10B_。

避坑（沿用 PLAN.md + M43/M56–M62 经验）：
  - MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建，物体 scale 保持 1（matrix_world 烘焙）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M63_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Color / Emission Strength。
  - CJK 标识复用 M54 的 up.cross(d) 基（X=up×d, rot=(X,up,d)），保证字正立、正面朝校园中心。
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

PREFIX = "M63_"

HALF_W = 2.1          # 亭身半宽（X，m）
HALF_D = 1.0          # 亭身半深（Y，m）
BASE_H = 0.12         # 基座厚（m）
POST_R = 0.05         # 立柱半径（m）
POST_H = 2.20         # 立柱高（m）
ROOF_H = 0.10         # 顶篷厚（m）
ROOF_Z = BASE_H + POST_H + ROOF_H / 2.0   # 顶篷中心高 ≈ 2.37

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
FLAT_BLOCK = ("M38_", "M11_Gate", "M59_", "M54_", "M55_", "M60_", "Road", "M58_")
STRUCT = ("Bldg_", "M46_", "M37_Flag", "M11_FlagPole", "M11_Tree", "M43_", "M61_",
          "M48_", "M49_", "M44_", "M53_", "M47_", "M41_", "M45_",
          "M52_", "M39_", "M40_", "M42_", "M16_")
SKIP = ("M7_", "Tower_", "Enemy_", "M10B_", "M50_", "M51_")


def is_blocker(o):
    n = o.name
    if any(n.startswith(p) for p in SKIP):
        return False
    if any(n.startswith(p) for p in FLAT_BLOCK):
        return True
    if any(n.startswith(p) for p in STRUCT):
        return True
    b = aabb(o)
    zext = b[5] - b[4]
    if zext >= 1.2 and b[4] < 3.5:
        return True
    return False


blockers = [aabb(o) for o in bpy.data.objects if is_blocker(o)]


def clear_at(cx, cy, half):
    m = 0.6
    x0, x1 = cx - (half + m), cx + (half + m)
    y0, y1 = cy - (half + m), cy + (half + m)
    for b in blockers:
        if b[0] <= x1 and b[1] >= x0 and b[2] <= y1 and b[3] >= y0:
            return False
    return True


# 候选扫描：取最居中（dc 最小）的全 clearance 点
best = None
best_d = 1e9
for gy in range(int(ymin) + 9, int(ymax) - 8, 4):
    for gx in range(int(xmin) + 9, int(xmax) - 8, 4):
        if not clear_at(gx, gy, 2.3):
            continue
        dg = math.hypot(gx - 36.0, gy - 30.0)
        df = math.hypot(gx, gy + 45.0)
        if dg < 11 or df < 9:
            continue
        dc = math.hypot(gx, gy)
        if dc < 12 or dc > 42:
            continue
        if dc < best_d:
            best_d = dc
            best = (float(gx), float(gy))
if best is None:
    best = (1.0, 17.0)
    warn = "NO_CLEAR_SPOT_FOUND_FALLBACK"
else:
    warn = ""
cx, cy = best
# 正面法线：朝向校园中心 (0,0)
d = Vector((-cx, -cy, 0.0))
d.normalize()
up = Vector((0.0, 0.0, 1.0))
rotz = math.atan2(cx, -cy)   # 局部 +Y 对齐到 d

def P(lx, ly, lz, mesh, mat, scale=(1, 1, 1), rz=rotz):
    ca, sa = math.cos(rz), math.sin(rz)
    wx = cx + lx * ca - ly * sa
    wy = cy + lx * sa + ly * ca
    return place(mesh, mat, (wx, wy, lz), rotz=rz, scale=scale)

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


mat_base = bpy.data.materials.get("PBR_Concrete") or new_mat(PREFIX + "Base", (0.66, 0.65, 0.63), 0.85)
mat_post = bpy.data.materials.get("PBR_Metal") or new_mat(PREFIX + "Post", (0.70, 0.72, 0.75), 0.35, 0.7)
mat_roof = new_mat(PREFIX + "Roof", (0.82, 0.83, 0.85), 0.55)
mat_panel = new_mat(PREFIX + "Panel", (0.88, 0.89, 0.90), 0.6)
mat_board = new_mat(PREFIX + "Board", (0.96, 0.96, 0.95), 0.5)
mat_text = new_mat(PREFIX + "Text", (0.12, 0.12, 0.13), 0.6)
# 四分类标准色（中国）：可回收蓝 / 厨余绿 / 有害红 / 其他灰
mat_blue  = new_mat(PREFIX + "BinBlue",  (0.12, 0.34, 0.78), 0.6)
mat_green = new_mat(PREFIX + "BinGreen", (0.15, 0.55, 0.20), 0.6)
mat_red   = new_mat(PREFIX + "BinRed",   (0.80, 0.12, 0.12), 0.6)
mat_gray  = new_mat(PREFIX + "BinGray",  (0.42, 0.43, 0.46), 0.6)
mat_lid   = new_mat(PREFIX + "Lid",      (0.30, 0.31, 0.33), 0.5)

# ---------------------------------------------------------------- 几何
mesh_base = make_box(PREFIX + "BaseMesh")
mesh_post = make_cylinder(PREFIX + "PostMesh", POST_R, POST_H, 10)
mesh_box  = make_box(PREFIX + "BoxMesh")
mesh_bin  = make_box(PREFIX + "BinMesh")
mesh_lid  = make_box(PREFIX + "LidMesh")

built = []

# 1) 混凝土基座
base = P(0, 0, BASE_H / 2.0, mesh_base, mat_base, (2 * HALF_W + 0.2, 2 * HALF_D + 0.2, BASE_H))
base.name = PREFIX + "Base"
built.append(base.name)

# 2) 四根金属立柱（角点）
for sx in (-1, 1):
    for sy in (-1, 1):
        p = P(sx * (HALF_W - 0.15), sy * (HALF_D - 0.15), BASE_H + POST_H / 2.0,
              mesh_post, mat_post)
        p.name = PREFIX + "Post_%d%d" % (sx > 0 and 1 or 0, sy > 0 and 1 or 0)
        built.append(p.name)

# 3) 顶篷（浅色，略出檐）
roof = P(0, 0, ROOF_Z, mesh_box, mat_roof, (2 * HALF_W + 0.5, 2 * HALF_D + 0.5, ROOF_H))
roof.name = PREFIX + "Roof"
built.append(roof.name)

# 4) 背板 + 两侧矮挡板（围合垃圾桶）
back = P(0, -(HALF_D - 0.04), BASE_H + 0.85, mesh_box, mat_panel, (2 * HALF_W + 0.2, 0.08, 1.7))
back.name = PREFIX + "BackPanel"
built.append(back.name)
for sx in (-1, 1):
    sp = P(sx * (HALF_W - 0.04), 0, BASE_H + 0.75, mesh_box, mat_panel, (0.08, 1.5, 1.7))
    sp.name = PREFIX + "SidePanel_%d" % (sx > 0 and 1 or 0)
    built.append(sp.name)

# 5) 四色分类垃圾桶（蓝/绿/红/灰，沿前排）
bin_mats = [mat_blue, mat_green, mat_red, mat_gray]
bin_xs = [-1.35, -0.45, 0.45, 1.35]
for i, (bx, bm_) in enumerate(zip(bin_xs, bin_mats)):
    body = P(bx, 0.2, BASE_H + 0.425, mesh_bin, bm_, (0.8, 0.7, 0.85))
    body.name = PREFIX + "Bin%d_Body" % i
    built.append(body.name)
    lid = P(bx, 0.2, BASE_H + 0.85 + 0.04, mesh_lid, mat_lid, (0.84, 0.74, 0.08))
    lid.name = PREFIX + "Bin%d_Lid" % i
    built.append(lid.name)

# 6) 标识底板（前侧，朝中心）
board = P(0, HALF_D - 0.04, 1.55, mesh_box, mat_board, (3.2, 0.06, 0.5))
board.name = PREFIX + "SignBoard"
built.append(board.name)

# ---------------------------------------------------------------- CJK 标识
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55


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
        o.data.align_y = "CENTER"
        bpy.context.view_layer.update()
        h_unit, w_unit = o.dimensions.y, o.dimensions.x
        bpy.data.objects.remove(o, do_unlink=True)
        ok = (h_unit >= FONT_H_MIN) and (w_unit >= n * FONT_W_MIN)
        tried.append({"file": p.split("\\")[-1], "ok": True, "h": round(h_unit, 3), "w": round(w_unit, 3), "pass": bool(ok)})
        if ok:
            return f, h_unit, w_unit, tried
    return None, 0.0, 0.0, tried


def place_cjk(text, face_pt, dvec, upvec, mat, target_h=0.34, out_off=0.04):
    font, h_unit, w_unit, _t = pick_font_once(text)
    if font is None:
        return None
    X = upvec.cross(dvec)
    rot = Matrix((
        (X.x, X.y, X.z, 0.0),
        (upvec.x, upvec.y, upvec.z, 0.0),
        (dvec.x, dvec.y, dvec.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    td = txt.data
    td.body = text
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = target_h / h_unit
    td.extrude = 0.01
    txt.matrix_world = Matrix.Translation(face_pt + dvec * out_off) @ rot
    txt.data.materials.append(mat)
    bpy.context.view_layer.update()
    return txt


# 标识正面点：亭前、离地 1.55m
front_pt = Vector((cx, cy, 0.0)) + d * (HALF_D + 0.12) + Vector((0.0, 0.0, 1.55))
sign = place_cjk("垃圾分类", front_pt, d, up, mat_text, target_h=0.34, out_off=0.05)
if sign is not None:
    sign.name = PREFIX + "SignText"
    built.append(sign.name)

# ---------------------------------------------------------------- 验证相机（亭子特写）
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 40.0
# 取景：站于正前方 4.5m、眼高 2.0m，看向亭身中心略偏下（桶身/标识高度），填满画面
cam_loc = Vector((cx, cy, 0.0)) + d * 4.5 + Vector((0.0, 0.0, 2.0))
cam.location = cam_loc
cam.rotation_euler = (Vector((cx, cy, 1.15)) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定（确定性，仅设定，渲染独立脚本执行）
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

n_m63 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M63",
    "n_removed_old": n_removed,
    "n_m63_objects": n_m63,
    "n_total_objects": len(bpy.data.objects),
    "placed_at": [round(cx, 2), round(cy, 2)],
    "front_normal": [round(d.x, 3), round(d.y, 3)],
    "warning": warn,
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "sign_text": (sign is not None),
}
print("M63_RESULT=" + repr(result))
