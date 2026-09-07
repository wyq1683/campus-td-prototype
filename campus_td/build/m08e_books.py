# m08e_books.py — M8E 书架"书条"精修
# 问题：M8 的 `M8_Library_Books_%d_%d` 是一整块单色薄板（0.9 × 0.06 × 1.8），
#   从人视看就是一块红棕色平板——完全读不出"书"。书架因此像空木格子。
# 目标：把整块平板换成**多色书条**——每格若干本不同颜色/宽度的书，
#   摆在书架**前脸(-y 侧)**，从图书馆南门洞人视看进去能读出"书架里排着书"。
#
# 构造（每个书架）：4 层 × 3 本 = 12 本；6 个书架共 72 本。
#   书条尺寸：宽 0.26–0.30（沿 x）· 进深 0.20（沿 y）· 高 0.30（沿 z）。
#   摆在书架前脸：书条 y 中心 = 书架 y − 0.05（占书架 0.3 进深的前半，朝向 -y 相机）。
#   层高 0.45，最底层离地 0.19，最高层顶 1.84 < 书架顶 2.14，不穿帮。
# 配色：6 色确定性调色板（不用 random，保证跨运行可复现），
#   索引 = `(书架序号*5 + 层*3 + 本*2) % 6`，相邻不同色。
#
# 幂等：PREFIX="M8E_" 清旧再重建；同时删除被取代的 `M8_Library_Books_*` 整块板。
#   ⚠️ 必须在 M8 `build_interiors()` 之后运行（M8 重建会重新生成那 6 块平板）。
# 运行：
#   exec(compile(open(r"...campus_td/build/m08e_books.py").read(),"m08e","exec"))
#   build_books()

import bpy
import mathutils

PREFIX = "M8E_"
FLOOR_TOP = 0.14        # 与 M8 一致（地板顶面标高）
WALL_T = 0.4

# ---- 图书馆几何（与 m08_interior.py room_reading 对齐）----
W, D = 15.0, 11.0
IW = W - 2 * WALL_T        # 14.2
IDP = D - 2 * WALL_T       # 10.2
SHELF_W, SHELF_D, SHELF_H = 1.0, 0.3, 2.0               # 书架本体（M8 已建）

# 图书馆**当前**平面中心：M11 重排后外壳挪到 (-38, 12)，旧常量 (2.0,-3.0) 失效，
# 书架 x/y 偏移必须相对当前中心算，否则书条会落在旧坐标（与 m08c/m08 同源 bug）。
LIB_FALLBACK = (2.0, -3.0)


def bldg_center(bname, fallback):
    """从场景里 `Bldg_<B>_*` 的 AABB 中心读该楼**当前**位置，不硬编码。"""
    xs, ys = [], []
    for o in bpy.data.objects:
        if not o.name.startswith("Bldg_%s" % bname):
            continue
        for c in o.bound_box:
            wpt = o.matrix_world @ mathutils.Vector(c)
            xs.append(wpt.x)
            ys.append(wpt.y)
    if not xs:
        return fallback
    return ((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5)

# ---- 书条参数 ----
ROWS = 4                    # 每书架层数
ROW_H = 0.45                # 层高
BOOK_H = 0.30               # 书高
BOOK_D = 0.20               # 书进深
WIDTHS = (0.28, 0.30, 0.26)  # 每层三本书的宽度
GAP = 0.02                  # 书间缝
Y_OFF = -0.05               # 前脸偏移（朝 -y 相机）

# 6 色确定性调色板：暗红 / 藏青 / 橄榄 / 墨绿 / 米黄 / 紫褐
PALETTE = [
    (0.55, 0.20, 0.16),
    (0.20, 0.30, 0.45),
    (0.45, 0.38, 0.20),
    (0.25, 0.35, 0.25),
    (0.60, 0.50, 0.30),
    (0.35, 0.25, 0.35),
]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    return m


def pbr(name, base, rough, metal=0.0):
    m = get_mat(name)
    if m.use_nodes:
        nt = m.node_tree
        bs = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bs is None:
            bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
        bs.inputs["Roughness"].default_value = rough
        try:
            bs.inputs["Metallic"].default_value = metal
        except Exception:
            pass
    return m


def set_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_box(name, size, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    # 删除被取代的 M8 整块单色书板（M8 重建会再生成，故 M8E 必须在其后运行）
    for o in list(bpy.data.objects):
        if o.name.startswith("M8_Library_Books_"):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    return removed


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def build_books():
    removed = clear_old()
    cx, cy = bldg_center("Library", LIB_FALLBACK)
    # 书架偏移相对当前中心算（M11 重排后中心变了，偏移不变）
    SHELF_XS = (cx - IW / 2.0 + 0.8, cx + IW / 2.0 - 0.8)
    SHELF_YS = (cy - 3.5, cy - 0.5, cy + 2.5)
    mats = [pbr(PREFIX + "Book_%d" % i, PALETTE[i], 0.7) for i in range(len(PALETTE))]
    made = 0
    for j, sx in enumerate(SHELF_XS):
        for i, sy in enumerate(SHELF_YS):
            s_idx = j * len(SHELF_YS) + i
            for r in range(ROWS):
                z_bottom = FLOOR_TOP + 0.05 + r * ROW_H
                zc = z_bottom + BOOK_H / 2.0
                cursor = sx - 0.43
                for k, bw in enumerate(WIDTHS):
                    xc = cursor + bw / 2.0
                    cursor += bw + GAP
                    ci = (s_idx * 5 + r * 3 + k * 2) % len(mats)
                    o = add_box(PREFIX + "Book_%d_%d_%d_%d" % (j, i, r, k),
                                (bw, BOOK_D, BOOK_H), (xc, sy + Y_OFF, zc))
                    set_mat(o, mats[ci])
                    made += 1
    g = globals()
    g["result"] = {
        "m8e": True,
        "removed_old": len(removed),
        "shelves": len(SHELF_XS) * len(SHELF_YS),
        "rows_per_shelf": ROWS,
        "books_per_row": len(WIDTHS),
        "books_made": made,
        "palette_size": len(PALETTE),
        "scene_objects": len(bpy.data.objects),
    }
    return g["result"]


build_books()
