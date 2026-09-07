# m11_masterplan.py — M11 总平重排：场地扩容 + 建筑重排 + 场地重建
#
# 背景（两个既有场景硬伤）：
#   1) 超界：Ground 只有 46x46m，但 Bldg_Teach 实测 65x17m、Bldg_Lab 49x15m，
#      两者各有 20~28m 探出场地，且互相穿插约 21m x 15m。
#      7 栋楼总占地 ~2682 m² / 场地 2116 m² = 覆盖率 127%，物理上不可能摆下。
#      根因不是计算 bug，是 M0 定的 46m 地面从没随建筑量扩过。
#   2) 路径穿楼：塔防 U 形路径（南腿 y=-13、东腿 x=16、北腿 y=13）穿过
#      Admin / Dorm / Gym / Teach / Lab 的 footprint。
#
# 解法（保住 M7/M10/M10B/M10C 全部既有工作）：
#   - 路径几何一个坐标都不改（仍是 102m 三段 U 形）-> M10 平衡数值、M10B 建塔位、
#     M10C WebGL 原型全部保持有效。
#   - 场地扩到 96x96m（半边 G=48），把 7 栋楼重排到 U 形路径之外的
#     北带 / 南带 / 东带 / 西带，四周留 2m 退线。
#   - 旧 M5_ / M5B_ 场地物件是按 46m 硬编码的，整体重建。
#
# 幂等：只删 M5_ / M5B_ / M11_ 前缀；建筑只做平移不改结构。
#   delta 由「当前外壳 AABB 中心 -> 目标中心」算出，所以重复运行结果收敛（delta->0）。
#
# !! 踩过的坑（v1 事故，勿复发）!!
#   v1 用「子串匹配 + 按建筑顺序逐个 apply」决定哪些对象跟着挪：
#   Teach 规则含 "Stair_"，把 M8C_Admin_Stair_1 / M8C_Dorm_Stair_2 一起吃掉，
#   等轮到 Admin/Dorm 规则时这些楼梯又吃第二份 delta -> 相对本楼整体偏移，
#   7 栋楼 AABB 被撑大 3~4 倍、互相穿插。
#   修正：改「前缀优先级归属 owner()，一个对象只属于一栋楼，只吃一份 delta」。
#
# 运行：exec(compile(open(r"...campus_td/build/m11_masterplan.py").read(), "m11", "exec"))

import bpy
import math
import mathutils

PREFIX = "M11_"

# ---------------- 总平参数（集中可调） ----------------
SITE_G = 48.0        # 地面半边长 -> 96 x 96 m
SETBACK = 2.0        # 建筑离围墙最小退线
PATH_CLEAR = 4.0     # 建筑离路径中心线最小净距（校验用）
WALL_H, WALL_T = 2.4, 0.35
GATE_HALF = 8.0      # 南向校门洞半宽

# 目标中心 (x, y)：全部落在 U 形路径走廊之外
MASTERPLAN = {
    "Teach":   (0.0,  -29.0),   # 南带·主教学楼正对校门
    "Lab":     (0.0,   31.0),   # 北带中
    "Admin":   (-38.0, 31.0),   # 北带西
    "Library": (-38.0, 12.0),   # 西带北
    "Dorm":    (-38.0, -4.0),   # 西带中
    "Gym":     (32.0,   6.0),   # 东带北
    "Canteen": (36.0, -10.0),   # 东带南
}
ORDER = ["Teach", "Lab", "Admin", "Library", "Dorm", "Gym", "Canteen"]

# 树阵（确定性布点，避开校门轴 x[-10,10] 与路径走廊）
TREES = [
    (-34, -43), (-24, -43), (-14, -43), (14, -43), (24, -43), (34, -43),
    (-20, 43), (-10, 43), (0, 43), (10, 43), (20, 43),
    (45, -20), (45, -14), (45, 0), (45, 6), (45, 14),
    (-33, 22), (-33, 4),
    (-14, -4), (6, -4), (6, 4), (-14, 4),
]

BEDS = [(-30, -33), (30, -33), (-30, -25), (30, -25)]


# ---------------- 归属判定（一个对象只属于一栋楼） ----------------
def owner(name):
    """前缀优先级归属：显式前缀优先，杜绝 M8C_X_Stair 被通用关键字抢走。"""
    if name.startswith(PREFIX) or name.startswith("Mat_Preview_"):
        return None
    for b in ORDER:
        for pre in ("Bldg_%s_" % b, "M8C_%s_" % b, "M8D_%s_" % b,
                    "M8_%s_" % b, "Furn_%s_" % b):
            if pre in name:
                return b
    if "M8E_Book" in name:      # 图书馆书条
        return "Library"
    if "Int_" in name or "Stair_" in name:   # M3 教学楼层内构件
        return "Teach"
    return None


# ---------------- 基础工具 ----------------
def get_mat(name, color=(0.8, 0.8, 0.8)):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    if m.use_nodes:
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    else:
        m.diffuse_color = color
    return m


def set_mat(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def add_cyl(name, r, h, loc, seg=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=seg, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def add_ico(name, r, loc, subdiv=3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def clear_old():
    """只删场地相关前缀；建筑/塔防/路径一概不动。"""
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith("M5_") or o.name.startswith("M5B_") or o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


# ---------------- 1) 场地扩容 ----------------
def expand_ground():
    g = bpy.data.objects.get("Ground")
    if g is None:
        return {"ok": False, "why": "no Ground"}
    before = [round(v, 2) for v in g.dimensions]
    # 地面 mesh 是 46m 的平面，scale=1 -> 按当前实测尺寸缩放到 2*SITE_G（幂等）
    k = (2.0 * SITE_G) / max(g.dimensions.x, 1e-6)
    g.scale.x *= k
    g.scale.y *= k
    bpy.context.view_layer.update()
    after = [round(v, 2) for v in g.dimensions]
    return {"ok": True, "before": before, "after": after, "k": round(k, 5),
            "loc": [round(g.location.x, 2), round(g.location.y, 2)]}


# ---------------- 2) 建筑重排 ----------------
def bbox2(objs):
    mn = [1e9, 1e9]; mx = [-1e9, -1e9]
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            mn[0] = min(mn[0], w[0]); mx[0] = max(mx[0], w[0])
            mn[1] = min(mn[1], w[1]); mx[1] = max(mx[1], w[1])
    return mn[0], mn[1], mx[0], mx[1]


def move_buildings():
    """以「外壳 AABB 中心 -> 目标中心」求 delta，整组（含室内/上层/补光/书条）同步平移。"""
    groups = {b: [] for b in ORDER}
    for o in bpy.data.objects:
        b = owner(o.name)
        if b is not None:
            groups[b].append(o)

    log = {}
    for b in ORDER:
        tx, ty = MASTERPLAN[b]
        grp = groups[b]
        shell = [o for o in grp if o.name.startswith("Bldg_%s_" % b)]
        if not shell or not grp:
            log[b] = {"n": len(grp), "skipped": True}
            continue
        x0, y0, x1, y1 = bbox2(shell)
        cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        dx, dy = tx - cx, ty - cy
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            for o in grp:
                o.location.x += dx
                o.location.y += dy
            bpy.context.view_layer.update()
        nx0, ny0, nx1, ny1 = bbox2(shell)
        log[b] = {"n": len(grp),
                  "lights": len([o for o in grp if o.type == "LIGHT"]),
                  "shell_center": [round(cx, 3), round(cy, 3)],
                  "delta": [round(dx, 4), round(dy, 4)],
                  "bbox": [round(nx0, 2), round(ny0, 2), round(nx1, 2), round(ny1, 2)]}
    return log


# ---------------- 3) 场地重建 ----------------
def make_tree(name, x, y, seed, wood, leaf):
    trunk = add_cyl(name + "_Trunk", 0.3, 4.0, (x, y, 2.0), seg=8)
    set_mat(trunk, wood)
    can = add_ico(name + "_Canopy", 2.6, (x, y, 5.4), subdiv=3)
    set_mat(can, leaf)
    # 两颗卫星球让冠形不规则（确定性 LCG，跨运行可复现）
    for k in range(2):
        r = ((seed * 9301 + k * 49297 + 233280) % 233280) / 233280.0
        a = r * 6.2831853
        sat = add_ico(name + "_Sat%d" % k, 1.5 + 0.4 * r,
                      (x + 1.7 * math.cos(a), y + 1.7 * math.sin(a), 4.9 + 0.7 * r),
                      subdiv=2)
        set_mat(sat, leaf)
    return 4


def build_site():
    brick = get_mat("PBR_Brick")
    concrete = get_mat("PBR_Concrete")
    dark = get_mat("PBR_Concrete_Dark", (0.18, 0.18, 0.20))
    wood = get_mat("PBR_Wood")
    leaf = get_mat("PBR_Leaf", (0.18, 0.42, 0.16))
    soil = get_mat("PBR_Soil", (0.22, 0.15, 0.10))
    red = get_mat("M5_FlagRed", (0.72, 0.12, 0.10))
    built = []

    # 1) 内庭院广场（U 形路径围合区 x[-22,16] y[-13,13]）
    court = add_box(PREFIX + "PlazaCourt", (38.0, 26.0, 0.1), (-3.0, 0.0, 0.05))
    set_mat(court, brick)
    # 2) 校前广场（校门 y=-48 <-> 主教学楼 y=-37.5）
    front = add_box(PREFIX + "PlazaFront", (76.0, 8.0, 0.1), (0.0, -42.0, 0.05))
    set_mat(front, brick)
    built.append("Plaza x2")

    # 3) 围墙：南向 (y=-48) 留 x[-8,8] 门洞
    add_box(PREFIX + "WallBack", (2 * SITE_G, WALL_T, WALL_H), (0.0, SITE_G, WALL_H / 2.0))
    add_box(PREFIX + "WallLeft", (WALL_T, 2 * SITE_G, WALL_H), (-SITE_G, 0.0, WALL_H / 2.0))
    add_box(PREFIX + "WallRight", (WALL_T, 2 * SITE_G, WALL_H), (SITE_G, 0.0, WALL_H / 2.0))
    seg = SITE_G - GATE_HALF                       # 40.0
    add_box(PREFIX + "WallFrontL", (seg, WALL_T, WALL_H),
            (-(GATE_HALF + seg / 2.0), -SITE_G, WALL_H / 2.0))
    add_box(PREFIX + "WallFrontR", (seg, WALL_T, WALL_H),
            ((GATE_HALF + seg / 2.0), -SITE_G, WALL_H / 2.0))
    for o in bpy.data.objects:
        if o.name.startswith(PREFIX + "Wall"):
            set_mat(o, concrete)
    # 压顶：直接读墙的 dimensions，不硬编码墙高
    ci = 0
    for o in [x for x in bpy.data.objects if x.name.startswith(PREFIX + "Wall")]:
        cap = add_box(PREFIX + "Coping%d" % ci,
                      (o.dimensions.x + 0.3, o.dimensions.y + 0.3, 0.25),
                      (o.location.x, o.location.y, o.dimensions.z + 0.125))
        set_mat(cap, dark)
        ci += 1
    built.append("Wall x5 + Coping x%d" % ci)

    # 4) 校门牌坊：双柱 + 额枋 + 匾（匾必须 y < 门枋前脸才可见）
    for sx in (-1, 1):
        p = add_box(PREFIX + "GatePillar%d" % sx, (1.4, 1.4, 6.0),
                    (sx * (GATE_HALF - 1.0), -SITE_G + 0.6, 3.0))
        set_mat(p, brick)
    lintel = add_box(PREFIX + "GateLintel", (2 * GATE_HALF + 2.0, 1.6, 1.4),
                     (0.0, -SITE_G + 0.6, 6.6))
    set_mat(lintel, concrete)
    plaque = add_box(PREFIX + "GatePlaque", (6.0, 0.12, 1.2), (0.0, -SITE_G - 0.35, 6.6))
    set_mat(plaque, dark)
    built.append("Gate")

    # 5) 旗杆 + 红旗（内庭院广场中轴）
    pole = add_cyl(PREFIX + "FlagPole", 0.22, 12.0, (-3.0, 0.0, 6.0), seg=12)
    set_mat(pole, get_mat("PBR_Metal"))
    flag = add_box(PREFIX + "Flag", (3.6, 0.1, 2.2), (-1.2, 0.0, 11.0))
    set_mat(flag, red)
    built.append("Flag")

    # 6) 花坛
    for i, (bx, by) in enumerate(BEDS):
        body = add_box(PREFIX + "Bed%d" % i, (4.0, 1.6, 0.6), (bx, by, 0.35))
        set_mat(body, brick)
        top = add_box(PREFIX + "BedSoil%d" % i, (3.8, 1.4, 0.12), (bx, by, 0.68))
        set_mat(top, soil)
    built.append("Beds x%d" % len(BEDS))

    # 7) 树阵
    n = 0
    for i, (tx, ty) in enumerate(TREES):
        n += make_tree(PREFIX + "Tree%d" % i, tx, ty, i + 7, wood, leaf)
    built.append("Trees x%d (%d obj)" % (len(TREES), n))

    return built


def build_cam():
    """鸟瞰相机：96m 场地要整幅入画。

    低角度（初版 (-86,-132,118)）会被 65m 长的主教学楼整条挡住内庭院 —— .stat 显示
    非天空像素 64%，构图失败。改为 45° 等高俯视 + 35mm：
      水平距 140m、高 140m、总距 198m；垂直 FOV 32.2° -> 可视高 114m，
      场地投影 96*cos45 + 楼高 24*sin45 ≈ 85m，留有余量。
    """
    cam = bpy.data.objects.get(PREFIX + "CamAerial")
    if cam is None:
        cam_data = bpy.data.cameras.new(PREFIX + "CamAerial")
        cam = bpy.data.objects.new(PREFIX + "CamAerial", cam_data)
        bpy.context.scene.collection.objects.link(cam)
    cam.location = (-99.0, -99.0, 140.0)
    target = mathutils.Vector((0.0, 0.0, 0.0))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 35.0
    bpy.context.scene.camera = cam
    return [round(v, 2) for v in cam.location]


# ---------------- 4) 校验 ----------------
def path_samples(step=2.0):
    pts, x = [], -22.0
    while x < 16.0:
        pts.append((x, -13.0)); x += step
    pts.append((16.0, -13.0))
    y = -13.0
    while y < 13.0:
        pts.append((16.0, y)); y += step
    pts.append((16.0, 13.0))
    x = 16.0
    while x > -22.0:
        pts.append((x, 13.0)); x -= step
    pts.append((-22.0, 13.0))
    return pts


def dist_pt_box(px, py, b):
    dx = max(b[0] - px, 0.0, px - b[2])
    dy = max(b[1] - py, 0.0, py - b[3])
    return (dx * dx + dy * dy) ** 0.5


def verify():
    boxes = {}
    for b in ORDER:
        objs = [o for o in bpy.data.objects if owner(o.name) == b]
        if objs:
            boxes[b] = bbox2(objs)

    # (a) 场地边界
    oob = []
    for b, bx in boxes.items():
        m = max(abs(bx[0]), abs(bx[1]), abs(bx[2]), abs(bx[3]))
        if m > SITE_G - SETBACK:
            oob.append({"b": b, "max_abs": round(m, 2), "limit": SITE_G - SETBACK})

    # (b) 两两重叠
    names = sorted(boxes)
    clash = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, c = boxes[names[i]], boxes[names[j]]
            if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
                clash.append([names[i], names[j]])

    # (c) 路径净距
    worst = {}
    for b, bx in boxes.items():
        worst[b] = round(min(dist_pt_box(px, py, bx) for px, py in path_samples()), 2)
    path_bad = [b for b, d in worst.items() if d < PATH_CLEAR]

    return {"boxes": {k: [round(v, 2) for v in b] for k, b in boxes.items()},
            "out_of_bounds": oob, "clash": clash,
            "path_min_dist": worst, "path_violations": path_bad,
            "all_ok": (not oob) and (not clash) and (not path_bad)}


def main():
    removed = clear_old()
    gr = expand_ground()
    mv = move_buildings()
    built = build_site()
    cam = build_cam()
    vf = verify()
    result = {"m11": True, "removed": len(removed), "ground": gr,
              "moved": mv, "built": built, "cam": cam, "verify": vf,
              "objects": len(bpy.data.objects)}
    print("M11 result:", result)
    return result


result = main()
