# m08_interior.py — M8 室内扩展（把 M3 教室样板扩展到 5 栋代表房间，手动 box + 复用 PBR 材质）
# 幂等：按前缀 "M8_" 清旧再重建；光源数据名也带 M8_ 一并清理。
# 不依赖 Archimesh（本环境无此扩展，M2/M3 已确认手动法最稳）。
# 设计判断：
#   M3 只在教学楼做了一间教室样板；M8 把"可进入室内"扩展到其余 5 栋的代表性房间——
#   行政楼办公室 / 宿舍楼宿舍 / 体育馆球场 / 食堂大厅 / 图书馆阅览室。
#   每间都铺可行走地板(抬离地面 0.14 防 z-fighting，满足 Walk Navigation 水平面要求)、
#   代表性程序化家具、一盏 AREA 补光(白昼靠 ribbon 窗天光 + 补光，避免室内死黑)。
#   上层的重复房间本期不做（原型级，先证明"每栋都能进"），留给 M9 或后续精修。
# 运行：
#   exec(compile(open(r"...campus_td/build/m08_interior.py").read(),"m08","exec"))
#   build_interiors()

import bpy
import mathutils

PREFIX = "M8_"
WALL_T = 0.4
FLOOR_TOP = 0.14          # 地板顶面 z（box 高 0.12，中心 0.08 -> 顶 0.14）
FLOOR_H = 3.9

# ---- 五栋楼几何（与 m04_buildings.py 对齐，来自 M8 坐标探针）----
#   center=(x,y) 平面中心；w/d = 外轮廓宽/进深；room = 房间类型
BUILDINGS = {
    "Admin":   dict(center=(-16.5, -15.0), w=13.0, d=9.0,  room="office",  floor="PBR_Tile"),
    "Dorm":    dict(center=(  0.0, -15.0), w=14.0, d=9.0,  room="dorm",   floor="PBR_Wood"),
    "Gym":     dict(center=( 15.0, -15.0), w=14.0, d=12.0, room="court",  floor="PBR_Wood"),
    "Canteen": dict(center=(-16.0,  -3.0), w=14.0, d=10.0, room="dining", floor="PBR_Tile"),
    "Library": dict(center=(  2.0,  -3.0), w=15.0, d=11.0, room="reading", floor="PBR_Wood"),
}

# ---- 入口开洞：每栋在南立面(WY-1，朝向校门)切一个真实门洞，便于 Walk Navigation + 人视英雄镜头看穿 ----
#   x = 门洞中心 x（避免与室内中柱书架冲突）；w = 门洞宽
ENTRY = {
    "Admin":   dict(x=-16.5, w=1.8),
    "Dorm":    dict(x=  0.0, w=1.6),
    "Gym":     dict(x= 15.0, w=3.6),
    "Canteen": dict(x=-16.0, w=3.0),
    "Library": dict(x=  5.0, w=2.4),   # 偏右，便于相机沿右书架通道看入
}


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
    """get-or-create 一个简洁 PBR 材质；若 M1 已建同名材质则只重设关键值（幂等）。"""
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


def zc(h):
    """给定物体高度 h，返回底边落在 FLOOR_TOP 时的中心 z。"""
    return FLOOR_TOP + h / 2.0


def bldg_center(bname, fallback):
    """从场景里 `Bldg_<B>_*` 的 AABB 中心读该楼**当前**位置，不硬编码。

    ⚠ 为什么必须动态读（2026-09-07 M15 暴露的真 bug，与 m08c 同源）：
      M11 总平重排把 7 栋楼整体挪过，本文件 BUILDINGS[...]["center"]（如 Admin=(-16.5,-15)）
      早已失效，实测新位置是 (-38, 31)。M11 的 delta 按外壳 AABB 中心算、外壳在位则
      delta=0，所以本步若用硬编码 center 重建室内，构件会留在旧坐标、把建筑 AABB 撑大，
      M11 的 verify() 立刻报 10 对 clash + 路径净距归零，且室内家具/灯/门洞全错位。
      改成本函数后：未 M11 的场景读到旧坐标（与常量一致，行为不变），
      M11 过的场景读到新坐标 —— 两种情况都对，且整条链可重入。
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


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    # 清理上一轮 m06/m08 生成的发光体辉光壳（M11 重排后吊灯已挪位，旧壳会悬空错位）
    for o in list(bpy.data.objects):
        if o.name.startswith("M6_Halo_M8_") or o.name.startswith("M8_Halo_"):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    for cu in [c for c in bpy.data.curves if c.name.startswith(PREFIX)]:
        bpy.data.curves.remove(cu)
    for lt in [l for l in bpy.data.lights if l.name.startswith(PREFIX)]:
        bpy.data.lights.remove(lt)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    return removed


def cut_entry(bname, door_x, door_w, door_h=3.0):
    """在南立面 WY-1 切一个矩形门洞；幂等（同会话内用 custom prop 标记）。"""
    wall = bpy.data.objects.get("Bldg_%s_WY-1" % bname)
    if wall is None:
        return False
    if wall.get("m8_entry"):
        return True
    wy = wall.location.y
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(door_x, wy, door_h / 2.0))
    cutter = bpy.context.active_object
    cutter.name = "Cut_M8_%s_entry" % bname
    cutter.scale = (door_w, 0.8, door_h)
    cutter.hide_render = True
    cutter.hide_viewport = True
    mod = wall.modifiers.new("Bool_M8_%s_entry" % bname, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    wall.select_set(True)
    bpy.context.view_layer.objects.active = wall
    ok = False
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ok = True
    except Exception as e:
        print("cut_entry warn:", bname, e)
    bpy.data.objects.remove(cutter, do_unlink=True)
    if ok:
        wall["m8_entry"] = True
    return ok


def add_fill(name, cx, cy, cz, energy=180.0, size=5.0):
    lt = bpy.data.lights.get(PREFIX + name)
    if lt is None:
        lt = bpy.data.lights.new(PREFIX + name, type="AREA")
    lt.energy = energy
    lt.size = size
    lt.shape = "RECTANGLE"
    lt.size_y = size
    lamp = bpy.data.objects.get(PREFIX + name)
    if lamp is None:
        lamp = bpy.data.objects.new(PREFIX + name, lt)
        bpy.context.collection.objects.link(lamp)
    lamp.location = (cx, cy, cz)
    return lamp.name


# ---------------------------------------------------------------------------
# 房间生成器
# ---------------------------------------------------------------------------
def room_office(b, mats):
    cx, cy = b["center"]
    iw, id = b["w"] - 2 * WALL_T, b["d"] - 2 * WALL_T
    objs = []
    f = add_box(PREFIX + "Admin_Floor", (iw, id, 0.12), (cx, cy, 0.08))
    set_mat(f, mats["tile"]); objs.append(f.name)
    # 办公桌 + 椅
    d = add_box(PREFIX + "Admin_Desk", (1.6, 0.8, 0.75), (cx - 2.0, cy + 1.0, zc(0.75)))
    set_mat(d, mats["wood"]); objs.append(d.name)
    ch = add_box(PREFIX + "Admin_Chair", (0.6, 0.6, 0.5), (cx - 2.0, cy + 2.1, zc(0.5)))
    set_mat(ch, mats["wood"]); objs.append(ch.name)
    # 文件柜（金属）
    cab = add_box(PREFIX + "Admin_Cabinet", (0.6, 0.6, 1.1), (cx + 4.2, cy + 2.5, zc(1.1)))
    set_mat(cab, mats["metal"]); objs.append(cab.name)
    # 沙发
    so = add_box(PREFIX + "Admin_Sofa", (1.8, 0.8, 0.7), (cx + 3.2, cy - 2.6, zc(0.7)))
    set_mat(so, mats["wood"]); objs.append(so.name)
    # 低隔断（砖，暗示办公室分隔）
    pa = add_box(PREFIX + "Admin_Part", (0.2, id * 0.5, 1.6), (cx - 4.6, cy, 0.8 + FLOOR_TOP))
    set_mat(pa, mats["brick"]); objs.append(pa.name)
    return objs


def room_dorm(b, mats):
    cx, cy = b["center"]
    iw, id = b["w"] - 2 * WALL_T, b["d"] - 2 * WALL_T
    objs = []
    f = add_box(PREFIX + "Dorm_Floor", (iw, id, 0.12), (cx, cy, 0.08))
    set_mat(f, mats["wood"]); objs.append(f.name)
    # 两张床（沿 y 分两侧）
    for k, yy in enumerate((cy - 2.2, cy + 2.2)):
        bed = add_box(PREFIX + "Dorm_Bed_%d" % k, (2.0, 0.9, 0.5), (cx - 3.5, yy, zc(0.5)))
        set_mat(bed, mats["wood"]); objs.append(bed.name)
        mat = add_box(PREFIX + "Dorm_Mattress_%d" % k, (1.9, 0.8, 0.18), (cx - 3.5, yy, FLOOR_TOP + 0.5 + 0.09))
        set_mat(mat, mats["tile"]); objs.append(mat.name)
    # 两组衣柜 + 书桌 + 椅
    for k, xx in enumerate((cx + 3.0, cx + 4.8)):
        wd = add_box(PREFIX + "Dorm_Wardrobe_%d" % k, (0.6, 1.0, 2.0), (xx, cy - 2.5, zc(2.0)))
        set_mat(wd, mats["wood"]); objs.append(wd.name)
        dk = add_box(PREFIX + "Dorm_Desk_%d" % k, (1.2, 0.6, 0.75), (xx, cy + 2.4, zc(0.75)))
        set_mat(dk, mats["wood"]); objs.append(dk.name)
        ch = add_box(PREFIX + "Dorm_Chair_%d" % k, (0.5, 0.5, 0.45), (xx, cy + 3.1, zc(0.45)))
        set_mat(ch, mats["wood"]); objs.append(ch.name)
    return objs


def room_court(b, mats):
    cx, cy = b["center"]
    iw, id = b["w"] - 2 * WALL_T, b["d"] - 2 * WALL_T
    objs = []
    f = add_box(PREFIX + "Gym_Floor", (iw, id, 0.12), (cx, cy, 0.08))
    set_mat(f, mats["wood"]); objs.append(f.name)
    # 球场线（白条，贴地）
    for i, off in enumerate((-id / 2 + 1.0, 0.0, id / 2 - 1.0)):
        ln = add_box(PREFIX + "Gym_Line_X_%d" % i, (iw - 1.0, 0.1, 0.04), (cx, cy + off, FLOOR_TOP + 0.02))
        set_mat(ln, mats["line"]); objs.append(ln.name)
    for i, off in enumerate((-iw / 2 + 1.5, iw / 2 - 1.5)):
        ln = add_box(PREFIX + "Gym_Line_Y_%d" % i, (0.1, id - 1.0, 0.04), (cx + off, cy, FLOOR_TOP + 0.02))
        set_mat(ln, mats["line"]); objs.append(ln.name)
    # 两侧看台（阶梯 box，混凝土）
    for side in (-1, 1):
        base_x = cx + side * (iw / 2 - 0.6)
        for s in range(3):
            step = add_box(PREFIX + "Gym_Bleacher_%d_%d" % (side, s),
                           (1.2, id - 1.0, 0.5), (base_x, cy, FLOOR_TOP + 0.25 + s * 0.5))
            set_mat(step, mats["conc"]); objs.append(step.name)
    # 篮板 + 篮筐（一端）
    board = add_box(PREFIX + "Gym_Backboard", (1.8, 0.1, 1.05), (cx, cy - id / 2 + 0.4, 3.1))
    set_mat(board, mats["tile"]); objs.append(board.name)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.05,
                                     location=(cx, cy - id / 2 + 0.9, 2.7))
    rim = bpy.context.active_object
    rim.name = PREFIX + "Gym_Rim"
    set_mat(rim, mats["metal"]); objs.append(rim.name)
    return objs


def room_dining(b, mats):
    cx, cy = b["center"]
    iw, id = b["w"] - 2 * WALL_T, b["d"] - 2 * WALL_T
    objs = []
    f = add_box(PREFIX + "Canteen_Floor", (iw, id, 0.12), (cx, cy, 0.08))
    set_mat(f, mats["tile"]); objs.append(f.name)
    # 取餐台（沿 -x 墙）
    cnt = add_box(PREFIX + "Canteen_Counter", (0.8, id * 0.8, 1.0),
                  (cx - iw / 2 + 0.6, cy, zc(1.0)))
    set_mat(cnt, mats["conc"]); objs.append(cnt.name)
    # 4 人桌 + 长凳 + 吊灯（环形排布）
    for i, yy in enumerate((cy - 2.6, cy - 0.6, cy + 1.4, cy + 3.4)):
        tb = add_box(PREFIX + "Canteen_Table_%d" % i, (1.2, 0.8, 0.75), (cx + 1.5, yy, zc(0.75)))
        set_mat(tb, mats["wood"]); objs.append(tb.name)
        for s in (-1, 1):
            bn = add_box(PREFIX + "Canteen_Bench_%d_%d" % (i, s), (1.2, 0.3, 0.45),
                         (cx + 1.5, yy + s * 0.65, zc(0.45)))
            set_mat(bn, mats["wood"]); objs.append(bn.name)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(cx + 1.5, yy, 2.6))
        pd = bpy.context.active_object
        pd.name = PREFIX + "Canteen_Pendant_%d" % i
        set_mat(pd, mats["glow"]); objs.append(pd.name)
    return objs


def room_reading(b, mats):
    cx, cy = b["center"]
    iw, id = b["w"] - 2 * WALL_T, b["d"] - 2 * WALL_T
    objs = []
    f = add_box(PREFIX + "Library_Floor", (iw, id, 0.12), (cx, cy, 0.08))
    set_mat(f, mats["wood"]); objs.append(f.name)
    # 书架阵列（仅两侧靠墙；中柱书架已移除以保留中央通道便于 Walk Navigation + 人视镜头）
    shelf_xs = (cx - iw / 2 + 0.8, cx + iw / 2 - 0.8)
    for j, sx in enumerate(shelf_xs):
        for i, yy in enumerate((cy - 3.5, cy - 0.5, cy + 2.5)):
            sh = add_box(PREFIX + "Library_Shelf_%d_%d" % (j, i), (1.0, 0.3, 2.0), (sx, yy, zc(2.0)))
            set_mat(sh, mats["wood"]); objs.append(sh.name)
            bk = add_box(PREFIX + "Library_Books_%d_%d" % (j, i), (0.9, 0.06, 1.8), (sx, yy, FLOOR_TOP + 1.0))
            set_mat(bk, mats["book"]); objs.append(bk.name)
    # 阅读桌 + 椅（中心区）
    for i, yy in enumerate((cy - 1.5, cy + 1.5)):
        tb = add_box(PREFIX + "Library_Table_%d" % i, (1.4, 0.8, 0.75), (cx, yy, zc(0.75)))
        set_mat(tb, mats["wood"]); objs.append(tb.name)
        for s in (-1, 1):
            ch = add_box(PREFIX + "Library_Chair_%d_%d" % (i, s), (0.5, 0.5, 0.45),
                         (cx, yy + s * 0.65, zc(0.45)))
            set_mat(ch, mats["wood"]); objs.append(ch.name)
    return objs


ROOM_FUNCS = {
    "office": room_office,
    "dorm": room_dorm,
    "court": room_court,
    "dining": room_dining,
    "reading": room_reading,
}


def _make_halos():
    """给 M8 发光体（食堂吊灯 glow 材质）套叠加辉光壳，模拟 Bloom。

    m06 的 make_tower_halos 在本步之前运行，会包住上一轮的旧吊灯位置；
    这里在 M8 重建后补包，保证辉光跟随当前吊灯（M11 重排后吊灯已挪到新坐标）。
    壳名 M8_Halo_* 与 M8_ 同前缀，随 m08.clear_old 一起清理、可重入。
    """
    made = []
    for o in list(bpy.data.objects):
        if o.type != "MESH" or not o.name.startswith("M8_"):
            continue
        mats = list(o.data.materials) if hasattr(o.data, "materials") else []
        is_glow = any((m is not None and m.name and "glow" in m.name.lower()) for m in mats)
        if not is_glow:
            continue
        dup = o.copy()
        dup.data = o.data.copy()
        dup.name = "M8_Halo_" + o.name
        if any(x.name == dup.name for x in bpy.data.objects):
            continue
        mat = bpy.data.materials.new("M8_HaloMat")
        mat.use_nodes = True
        try:
            mat.blend_method = "ADD"
        except Exception:
            pass
        mat.use_backface_culling = False
        nt = mat.node_tree
        nt.nodes.clear()
        emis = nt.nodes.new("ShaderNodeEmission")
        outn = nt.nodes.new("ShaderNodeOutputMaterial")
        emis.inputs["Color"].default_value = (1.0, 0.92, 0.6, 1.0)
        emis.inputs["Strength"].default_value = 2.8
        nt.links.new(emis.outputs["Emission"], outn.inputs["Surface"])
        dup.data.materials.clear()
        dup.data.materials.append(mat)
        dup.scale = (o.scale.x * 1.25, o.scale.y * 1.25, o.scale.z * 1.25)
        bpy.context.collection.objects.link(dup)
        made.append(dup.name)
    return made


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def build_interiors():
    removed = clear_old()
    mats = {
        "wood":  pbr("PBR_Wood",   (0.32, 0.22, 0.14), 0.6),
        "conc":  pbr("PBR_Concrete", (0.36, 0.36, 0.36), 0.85),
        "tile":  pbr("PBR_Tile",   (0.78, 0.78, 0.76), 0.4),
        "brick": pbr("PBR_Brick",  (0.45, 0.28, 0.24), 0.9),
        "metal": pbr("PBR_Metal",  (0.70, 0.72, 0.75), 0.35, 1.0),
        "line":  pbr(PREFIX + "Line", (0.95, 0.95, 0.95), 0.5),
        "book":  pbr(PREFIX + "Books", (0.55, 0.20, 0.16), 0.7),
        "glow":  pbr(PREFIX + "Glow", (1.0, 0.85, 0.5), 0.3),
    }
    built = {}
    total = 0
    for bname, b in BUILDINGS.items():
        old_cx, old_cy = b["center"]
        cx, cy = bldg_center(bname, (old_cx, old_cy))
        # 用当前坐标覆盖，room_* 内统一读 b["center"]（保持函数签名不变）
        b["center"] = (cx, cy)
        objs = ROOM_FUNCS[b["room"]](b, mats)
        # 室内补光（白昼靠 ribbon 窗天光 + 一盏 AREA 防死黑）
        cz = 3.4 if b["room"] != "court" else 6.0
        fill = add_fill(bname, cx, cy, FLOOR_TOP + cz, energy=160.0, size=5.0)
        # 南立面切门洞（真实入口，便于 Walk Navigation + 人视镜头看穿）
        # 门洞 x 取「相对中心偏移」而非绝对坐标：M11 重排后中心变了，偏移不变
        e = ENTRY[bname]
        door_x = cx + (e["x"] - old_cx)
        door_ok = cut_entry(bname, door_x, e["w"])
        built[bname] = {
            "room": b["room"],
            "objects": len(objs),
            "fill": fill,
            "entry": (round(door_x, 2), e["w"], door_ok),
        }
        total += len(objs) + 1
    # 重建发光体辉光壳（跟随 M11 重排后的吊灯位置）
    halos = _make_halos()
    g = globals()
    g["result"] = {
        "m8": True,
        "removed_old": len(removed),
        "buildings": built,
        "total_objects": total,
        "halos": halos,
        "scene_objects": len(bpy.data.objects),
        "floor_top": FLOOR_TOP,
    }
    return g["result"]
