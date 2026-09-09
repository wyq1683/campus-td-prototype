# -*- coding: utf-8 -*-
"""
M49 · 校园宣传栏 / 公告栏（Campus Bulletin Boards · 校园生活细节）
==========================================================================
项目已收官（M0–M48 ✅）。按「无未完成里程碑时自行增加改进项」新增 M49：
给 96m 校园外围步行道加一排**室外宣传栏（公告栏）**——中国高中/初中校园的
"国民级"设施（校务栏、通知栏、光荣榜、卫生评比），当前有长椅垃圾桶(M48)、
路灯(M43)、楼牌(M44)、自行车棚(M46)、乒乓球台(M47)，但"看通知公告"的场景从没出现。

为什么做这个：
  - 宣传栏沿外围步行道（与 M43 路灯 / M48 长椅同一条 walkway）成排，补足"有人生活"
    的可居住感；同时是电影级校园里最常被学生围观的细节。
  - 复用 M14/M44 验证过的 CJK 字体管线 pick_font()（带字形尺寸自检，换机器不静默出空匾）。
  - 自成一体、零破坏其他物体，坐标全部从场景当前几何动态读取（PLAN.md 铁律）。

坐标**从场景当前几何读取**（M11 之后禁止硬编码）：
  - 候选点 ← M11_Wall* AABB 并集内退 WALK_INSET（与 M43/M48 同一条 walkway，肉眼一致）。
  - 面朝校园中心（背靠围墙）；避障跳过 Bldg_* AABB（外扩）与南墙校门洞。
  - 上限 4 块，每块不同标签（校园公告/通知栏/光荣榜/卫生评比）。

几何体（原型级、框架合并为单 mesh / 单物体 + 玻璃面 + CJK 字）：
  - 框架 = 2 金属立柱 + 顶棚 + 深色背板（合并为 1 物体，2 材质：金属 0 / 背板 1）。
  - 玻璃面 = 半透自发光弱覆盖（M49_Glass，透明 Transmission，保护版面）。
  - CJK 文字 = pick_font 选中字体、按目标字高反算 size、正对校园中心、Emission 保阴影面可读。

避坑（沿用 PLAN.md + M43/44/46/48 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部用 bmesh 直建 + bpy.ops.object.text_add（与 M44 一致）。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M49_，绝不 select_all+delete。
  - 材质自建于 M49_ 前缀（复用既有 PBR_Metal，避免 M18 提过的"重建材质丢槽"）。
  - Blender 5.2 Principled 输入名：Base Color / Metallic / Roughness / Transmission Weight / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

PREFIX = "M49_"

# ---- 布局 ----
WALK_INSET = 6.0      # 距围墙内退（与 M43/M48 同一条 walkway）
BOARD_SPACING = 26.0
MAX_BOARDS = 4
BLD_MARGIN = 1.6      # 楼体避障外扩
GATE_HALF = 9.0       # 南墙校门半宽

# ---- 尺寸 (m) ----
POST_H = 2.40         # 立柱高
POST_T = 0.10         # 立柱厚
ROOF_T = 0.12         # 顶棚厚
ROOF_D = 0.55         # 顶棚进深（沿 Y）
BOARD_Z = 1.50        # 背板中心离地高
BD_T = 0.06           # 背板厚
TEXT_H = 0.46         # 目标字高
TEXT_MAX_W = 4.0      # 文字最大宽度（超则回缩）

# 每块不同标签
LABELS = ["校园公告", "通知栏", "光荣榜", "卫生评比"]

# 字体候选链（沿用 M14/44 实测：首选 simhei 最饱满；VF/Deng/SimSunExtB 本机坏）
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]
FONT_H_MIN = 0.55
FONT_W_MIN = 0.55


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
def get_metal():
    m = bpy.data.materials.get("PBR_Metal")
    if m is None:
        m = bpy.data.materials.get(PREFIX + "Metal")
        if m is None:
            m = bpy.data.materials.new(PREFIX + "Metal")
            m.use_nodes = True
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.30, 0.31, 0.32, 1.0)
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.45
                if "Metallic" in bsdf.inputs:
                    bsdf.inputs["Metallic"].default_value = 0.85
    return m


def get_board_mat():
    m = bpy.data.materials.get(PREFIX + "Board")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "Board")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.045, 0.05, 0.055, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.7
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
    return m


def get_glass_mat():
    m = bpy.data.materials.get("PBR_Glass")
    if m is None:
        m = bpy.data.materials.get(PREFIX + "Glass")
        if m is None:
            m = bpy.data.materials.new(PREFIX + "Glass")
            m.use_nodes = True
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.80, 0.88, 0.92, 1.0)
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.06
                if "Metallic" in bsdf.inputs:
                    bsdf.inputs["Metallic"].default_value = 0.0
                if "Transmission Weight" in bsdf.inputs:
                    bsdf.inputs["Transmission Weight"].default_value = 0.9
                if "IOR" in bsdf.inputs:
                    bsdf.inputs["IOR"].default_value = 1.45
    return m


def get_text_mat():
    m = bpy.data.materials.get(PREFIX + "Text")
    if m is None:
        m = bpy.data.materials.new(PREFIX + "Text")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.90, 1.0)
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.5
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = 0.4
    return m


# ---------------------------------------------------------------- CJK 字体自检
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


# ---------------------------------------------------------------- 单块宣传栏
def build_board(idx, label, p, Xc, Yc, Zc, metal, boardm, glassm, textm, font, h_unit):
    up = Zc
    # 朝向旋转矩阵：本地 +Z -> Yc（版面正对校园中心），+Y -> 世界上，+X = up×Yc（字不镜像、字顶朝上）
    X = up.cross(Yc)
    Y = up
    Z = Yc
    rot = Matrix((
        (X.x, X.y, X.z, 0.0),
        (Y.x, Y.y, Y.z, 0.0),
        (Z.x, Z.y, Z.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    world_M = Matrix.Translation(p) @ rot

    # ---- CJK 文字（先建，量尺寸定背板）----
    bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
    txt = bpy.context.active_object
    txt.name = PREFIX + "Text%d" % idx
    td = txt.data
    td.body = label
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    size = TEXT_H / h_unit
    td.size = size
    td.extrude = 0.02
    td.bevel_depth = 0.004
    td.bevel_resolution = 1
    bpy.context.view_layer.update()
    if txt.dimensions.x > TEXT_MAX_W:
        size *= TEXT_MAX_W / txt.dimensions.x
        td.size = size
        bpy.context.view_layer.update()
    bw = txt.dimensions.x + 0.6
    bh = txt.dimensions.y + 0.7
    txt.matrix_world = Matrix.Translation(p + Yc * (BD_T / 2.0 + 0.06) + Zc * BOARD_Z) @ rot
    if txt.data.materials:
        txt.data.materials[0] = textm
    else:
        txt.data.materials.append(textm)
    bpy.context.view_layer.update()

    # ---- 框架（立柱 + 顶棚 + 背板）合并单 mesh ----
    bm = bmesh.new()
    # 背板（深色，材质 1）
    bb = box(bw, BD_T, bh)
    bb.transform(Matrix.Translation((0.0, 0.0, BOARD_Z)))
    add_bm(bm, bb, 1)
    # 两立柱（金属，材质 0）
    for sx in (-1.0, 1.0):
        post = box(POST_T, POST_T, POST_H)
        post.transform(Matrix.Translation((sx * (bw / 2.0 - 0.10), 0.0, POST_H / 2.0)))
        add_bm(bm, post, 0)
    # 顶棚（金属，材质 0，沿 Y 进深 ROOF_D，向内外两侧略微出檐）
    roof = box(bw + 0.30, ROOF_D, ROOF_T)
    roof.transform(Matrix.Translation((0.0, 0.0, POST_H + ROOF_T / 2.0)))
    add_bm(bm, roof, 0)
    bm.transform(world_M)
    me = bpy.data.meshes.new(PREFIX + "FrameMesh%d" % idx)
    bm.to_mesh(me)
    bm.free()
    frame = bpy.data.objects.new(PREFIX + "Board%d" % idx, me)
    frame.data.materials.append(metal)
    frame.data.materials.append(boardm)
    bpy.context.scene.collection.objects.link(frame)

    # ---- 玻璃面（半透覆盖，材质 2）----
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -9999.0))
    glass = bpy.context.active_object
    glass.name = PREFIX + "Glass%d" % idx
    glass.scale = (bw - 0.10, 0.02, bh - 0.10)
    glass.matrix_world = Matrix.Translation(p + Yc * (BD_T / 2.0 + 0.02) + Zc * BOARD_Z) @ rot
    if glass.data.materials:
        glass.data.materials[0] = glassm
    else:
        glass.data.materials.append(glassm)
    bpy.context.view_layer.update()

    return {
        "label": label,
        "base": [round(p.x, 1), round(p.y, 1), round(p.z, 1)],
        "normal": [round(Yc.x, 2), round(Yc.y, 2), 0.0],
        "board_w": round(bw, 2), "board_h": round(bh, 2),
        "text_size": round(size, 3),
        "text_dim": [round(txt.dimensions.x, 2), round(txt.dimensions.y, 2)],
    }


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
METAL = get_metal()
BOARDM = get_board_mat()
GLASSM = get_glass_mat()
TEXTM = get_text_mat()

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

blds = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]


def inside_building(x, y):
    for b in blds:
        if (b[0] - BLD_MARGIN) <= x <= (b[1] + BLD_MARGIN) and \
           (b[2] - BLD_MARGIN) <= y <= (b[3] + BLD_MARGIN):
            return True
    return False


def in_gate_gap(x, y):
    return (y < yi0 + 3.0) and (abs(x) < GATE_HALF)


# 候选点（沿内矩形四边，步长 BOARD_SPACING，上限 MAX_BOARDS）
cands = []
for y in (yi0, yi1):
    L = xi1 - xi0
    n = max(1, int(round(L / BOARD_SPACING)))
    for i in range(n + 1):
        cands.append((xi0 + L * i / n, y))
for x in (xi0, xi1):
    L = yi1 - yi0
    n = max(1, int(round(L / BOARD_SPACING)))
    for i in range(1, n):
        cands.append((x, yi0 + L * i / n))

board_pts = []
for (x, y) in cands:
    if inside_building(x, y):
        continue
    if in_gate_gap(x, y):
        continue
    board_pts.append((x, y))
    if len(board_pts) >= MAX_BOARDS:
        break

# 字体自检
font, h_unit, w_unit, tried = pick_font_once(LABELS[0])
if font is None:
    result = {"ok": False, "why": "no usable CJK font", "tried": tried,
              "n_total_objects": len(bpy.data.objects)}
    print("M49_RESULT=" + repr(result))
    raise SystemExit(0)

built = []
for i, (x, y) in enumerate(board_pts):
    label = LABELS[i % len(LABELS)]
    p = Vector((x, y, 0.0))
    out = (p - cc)
    out.z = 0.0
    if out.length < 1e-3:
        out = Vector((0.0, 1.0, 0.0))
    out = out.normalized()
    Yc = -out                       # 版面正对校园中心（背靠围墙）
    Xc = up.cross(Yc).normalized()  # 沿墙切向 = 宣传栏长边
    Zc = up
    info = build_board(i + 1, label, p, Xc, Yc, Zc, METAL, BOARDM, GLASSM, TEXTM, font, h_unit)
    built.append(info)

# ---- 相机：看入第一块宣传栏 ----
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    bpy.ops.object.camera_add(location=(0.0, 0.0, 2.0))
    cam = bpy.context.active_object
    cam.name = PREFIX + "Cam"
if board_pts:
    bp = Vector((board_pts[0][0], board_pts[0][1], 0.0))
    out = (bp - cc)
    out.z = 0.0
    if out.length < 1e-3:
        out = Vector((0.0, 1.0, 0.0))
    out = out.normalized()
    inward = -out
    cam.location = bp + inward * 5.0 + up * 1.9
    cam.data.lens = 35.0
    cam.rotation_euler = ((bp + up * 1.5) - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---- 渲染设定（确定性，与 M43..M48 一致）----
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
    sc.view_settings.exposure = 0.12
    sc.camera = cam
except Exception as e:
    built.append("RENDER_CFG_WARN:" + str(e))

n_m49 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M49",
    "ok": True,
    "n_removed_old": n_removed,
    "n_boards": len(built),
    "n_m49_objects": n_m49,
    "n_total_objects": len(bpy.data.objects),
    "campus": [round(xmin, 1), round(xmax, 1), round(ymin, 1), round(ymax, 1)],
    "board_points": len(board_pts),
    "font": {"used": font.name, "tried": tried},
    "boards": built,
}
print("M49_RESULT=" + repr(result))
