# m08c_upper.py — M8C 上层重复房间扩展
# 目标：消灭"空壳楼"。M8 只建了每栋地面层，上层是空盒子——
#   从 ribbon 窗带/门洞看进去只能看到一层家具 + 一大片空，剖面关系不成立。
#   本步补上真实的楼层结构：楼板 + 上层简化家具 + 层间楼梯体量。
#
# 每栋（Gym 除外）逐层构建：
#   ① 楼板 (slab)：混凝土板厚 0.25，顶面落在 z = f * 3.9（即该层地面标高）；
#      沿 -x 侧留 1.45m 楼梯井槽（stair well），不做 Boolean，避免 headless 失败。
#   ② 上层简化家具：按房间类型 office/dorm/dining/reading 各放一组（原型级密度）。
#   ③ 楼梯体量 (stair)：单 box 斜置（绕 X 轴旋转 atan2(层高, 水平跑长)），
#      从 z=(f-1)*3.9 升到 z=f*3.9，读得出"跑梯"。
#
# 幂等：PREFIX="M8C_" 清旧再重建；只增几何，不动外壳(Bldg_*)与 M8 地面层。
# 运行：
#   exec(compile(open(r"...campus_td/build/m08c_upper.py").read(),"m08c","exec"))
#   build_upper()

import bpy
import math
import mathutils

PREFIX = "M8C_"
FLOOR_H = 3.9          # 层高（与 M2/M4 一致）
SLAB_T = 0.25          # 楼板厚
WELL = 1.45            # 楼梯井槽宽（沿 -x 侧留空）
STAIR_W = 1.3          # 梯段宽
STAIR_RUN = 3.2        # 梯段水平投影长
WALL_T = 0.4           # 外墙厚（与 M8 一致）

# 楼层数来自 M4：Admin 4F(15.6m) / Dorm 6F(23.4m) / Canteen 2F(7.8m) / Library 4F(15.6m)
# Gym 是 11.7m 通高单一体量球场（single_band 大玻璃），不加楼板——加了反而错。
BUILDINGS = {
    "Admin":   dict(center=(-16.5, -15.0), w=13.0, d=9.0,  floors=4, room="office"),
    "Dorm":    dict(center=(  0.0, -15.0), w=14.0, d=9.0,  floors=6, room="dorm"),
    "Canteen": dict(center=(-16.0,  -3.0), w=14.0, d=10.0, floors=2, room="dining"),
    "Library": dict(center=(  2.0,  -3.0), w=15.0, d=11.0, floors=4, room="reading"),
}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bdata_new(name)
    return m


def bdata_new(name):
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
    return removed


# ---------------------------------------------------------------------------
# 上层家具（z0 = 该层楼板顶面标高，家具底坐落其上）
# ---------------------------------------------------------------------------
def furnish_office(bname, cx, cy, iw, idp, z0, f, mats):
    objs = []
    for k, (dx, dy) in enumerate(((1.5, 1.0), (-2.0, -1.2))):
        d = add_box(PREFIX + "%s_F%d_Desk_%d" % (bname, f, k),
                    (1.6, 0.8, 0.75), (cx + dx, cy + dy, z0 + 0.375))
        set_mat(d, mats["wood"]); objs.append(d.name)
        offs = 1.1 if dy > 0 else -1.1
        c = add_box(PREFIX + "%s_F%d_Chair_%d" % (bname, f, k),
                    (0.6, 0.6, 0.5), (cx + dx, cy + dy + offs, z0 + 0.25))
        set_mat(c, mats["wood"]); objs.append(c.name)
    return objs


def furnish_dorm(bname, cx, cy, iw, idp, z0, f, mats):
    objs = []
    for k, dy in enumerate((-2.2, 2.2)):
        bed = add_box(PREFIX + "%s_F%d_Bed_%d" % (bname, f, k),
                      (2.0, 0.9, 0.5), (cx - 3.5, cy + dy, z0 + 0.25))
        set_mat(bed, mats["wood"]); objs.append(bed.name)
    for k, dx in enumerate((3.0, 4.8)):
        dk = add_box(PREFIX + "%s_F%d_Desk_%d" % (bname, f, k),
                     (1.2, 0.6, 0.75), (cx + dx, cy + 2.4, z0 + 0.375))
        set_mat(dk, mats["wood"]); objs.append(dk.name)
    return objs


def furnish_dining(bname, cx, cy, iw, idp, z0, f, mats):
    objs = []
    for i, dy in enumerate((-1.8, 1.8)):
        tb = add_box(PREFIX + "%s_F%d_Table_%d" % (bname, f, i),
                     (1.2, 0.8, 0.75), (cx + 1.5, cy + dy, z0 + 0.375))
        set_mat(tb, mats["wood"]); objs.append(tb.name)
        for j, s in enumerate((-1, 1)):
            bn = add_box(PREFIX + "%s_F%d_Bench_%d_%d" % (bname, f, i, j),
                         (1.2, 0.3, 0.45), (cx + 1.5, cy + dy + s * 0.65, z0 + 0.225))
            set_mat(bn, mats["wood"]); objs.append(bn.name)
    return objs


def furnish_reading(bname, cx, cy, iw, idp, z0, f, mats):
    objs = []
    for j, sx in enumerate((cx - iw / 2.0 + 0.8, cx + iw / 2.0 - 0.8)):
        sh = add_box(PREFIX + "%s_F%d_Shelf_%d" % (bname, f, j),
                     (1.0, 0.3, 2.0), (sx, cy - 2.0, z0 + 1.0))
        set_mat(sh, mats["wood"]); objs.append(sh.name)
    tb = add_box(PREFIX + "%s_F%d_Table_0" % (bname, f),
                 (1.4, 0.8, 0.75), (cx, cy + 1.5, z0 + 0.375))
    set_mat(tb, mats["wood"]); objs.append(tb.name)
    return objs


ROOM_FUNCS = {
    "office": furnish_office,
    "dorm": furnish_dorm,
    "dining": furnish_dining,
    "reading": furnish_reading,
}


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def bldg_center(bname, fallback):
    """从场景里 `Bldg_<B>_*` 的 AABB 中心读该楼**当前**位置，不硬编码。

    ⚠ 为什么必须动态读（2026-09-07 M15 时发现的真 bug）：
      M11 总平重排把 7 栋楼整体挪过，本文件顶部的 `BUILDINGS[...]["center"]`
      （如 Admin=(-16.5,-15)）早已失效，实测新位置是 (-38, 31)。
      更糟的是 M11 的 delta 是「外壳 AABB 中心 → 目标中心」算的：外壳一直在位，
      所以 delta=0，**M8C 重建出来的构件永远挪不回去** —— 只要把 M08C 和 M11
      放进同一条渲染链，内部构件就会留在旧坐标、把建筑 AABB 撑大，
      M11 的 verify() 立刻报 10 对 clash + 路径净距归零。
      （此前 render_m08* 不含 M11、render_m11 不含 M08C，所以一直没暴露。）
    改成本函数后：未 M11 的场景读到旧坐标（与常量一致，行为不变），
      M11 过的场景读到新坐标 —— 两种情况都对。
    """
    xs, ys = [], []
    for o in bpy.data.objects:
        if not o.name.startswith("Bldg_%s" % bname):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            xs.append(w.x)
            ys.append(w.y)
    if not xs:
        return fallback
    return ((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5)


def build_upper():
    removed = clear_old()
    mats = {
        "wood": pbr("PBR_Wood", (0.32, 0.22, 0.14), 0.6),
        "conc": pbr("PBR_Concrete", (0.36, 0.36, 0.36), 0.85),
    }
    built = {}
    total = 0
    for bname, b in BUILDINGS.items():
        cx, cy = bldg_center(bname, b["center"])
        iw = b["w"] - 2 * WALL_T
        idp = b["d"] - 2 * WALL_T
        n_slab = n_stair = n_furn = 0
        for f in range(1, b["floors"]):
            z0 = f * FLOOR_H
            # ① 楼板：留 -x 侧 WELL 宽楼梯井槽（宽 iw-WELL，中心右移 WELL/2）
            s = add_box(PREFIX + "%s_Slab_%d" % (bname, f),
                        (iw - WELL, idp, SLAB_T),
                        (cx + WELL / 2.0, cy, z0 - SLAB_T / 2.0))
            set_mat(s, mats["conc"]); n_slab += 1; total += 1
            # ② 上层简化家具
            objs = ROOM_FUNCS[b["room"]](bname, cx, cy, iw, idp, z0, f, mats)
            n_furn += len(objs); total += len(objs)
            # ③ 楼梯体量：单 box 斜置，从 (f-1) 层升到 f 层
            slope = math.sqrt(STAIR_RUN ** 2 + FLOOR_H ** 2)
            st = add_box(PREFIX + "%s_Stair_%d" % (bname, f),
                         (STAIR_W, slope, 0.18),
                         (cx - iw / 2.0 + 0.8, cy, (f - 1) * FLOOR_H + FLOOR_H / 2.0))
            st.rotation_euler = (math.atan2(FLOOR_H, STAIR_RUN), 0.0, 0.0)
            set_mat(st, mats["conc"]); n_stair += 1; total += 1
        built[bname] = {
            "floors": b["floors"],
            "room": b["room"],
            "slabs": n_slab,
            "stairs": n_stair,
            "furniture": n_furn,
        }
    g = globals()
    g["result"] = {
        "m8c": True,
        "removed_old": len(removed),
        "buildings": built,
        "total_new": total,
        "scene_objects": len(bpy.data.objects),
        "floor_h": FLOOR_H,
    }
    return g["result"]


build_upper()
