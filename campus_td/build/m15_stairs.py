# m15_stairs.py — M15 楼梯改 Array 真实踏步（补实 M8C 的"斜板楼梯"）
#
# 背景：M8C 的楼梯是**单块斜置 box**（1.3m 宽 × 斜长 5.045 × 厚 0.18），坡度 50.6°，
#   纯示意体量 —— 看不出踏步，也比真实楼梯陡得多（真实约 30~35°）。当时注释就写着
#   "读得出跑梯"即可，属已知欠账。本轮按 backlog 换成带 Array 修改器的真实踏步。
#
# 设计取舍（先算账再动手）：
#   - 层高 FLOOR_H=3.9m。楼梯井槽只有 1.45m 宽（沿 -x 侧），**只能放单跑 1.3m 宽**，
#     双跑（2×1.2+井）放不下 → 单跑直梯。
#   - 单跑 3.9m 按舒适公式 2h+d≈0.63 取 h=0.177 / d=0.28 → **22 级、跑长 6.16m、
#     坡度 32.3°**（原 50.6° 太陡）。22 级略超"每段 ≤18 级"的规范上限，但这是唯一
#     能在 1.45m 井宽 + 8~12m 进深里放下的解，原型场景接受。
#   - 组成：梯段底板(斜板) + Array 踏步(22 级) + 两侧斜扶手。不做立柱（省对象）。
#
# ⚠ 两个必须遵守的约定：
#   1. **坐标全部从场景里的旧楼梯对象读，不硬编码**。M11 总平重排把 7 栋楼整体挪过，
#      M8C 脚本里的 center 常量（如 Admin=(-16.5,-15)）早已失效 —— 实测新位置是
#      (-43.3, 31.005)。跟 M12 机位自适应同一思路：不猜坐标，读当前值。
#   2. **命名避开 "Stair_" / "Int_"**。M11 的 owner() 见到含 "Stair_" 的名字会判给
#      Teach 并挪走它 —— 本脚本改用 Slope / Steps / Rail，且 M15 必须排在 M11 之后跑
#      （M15_* 不被 owner() 识别，M11 不会挪它们，跑反了就会错位）。
#
# 幂等：只删 M15_* 前缀 + 逐个替换 M8C_*_Stair_*（删一个建一个，不整体清场）。
# 运行：exec(compile(open(r"...campus_td/build/m15_stairs.py").read(), "m15", "exec"))

import bpy
import math
import re
import mathutils

PREFIX = "M15_"

# ---- 可调参数 ----
FLOOR_H = 3.9           # 层高（与 M2/M4/M8C 一致）
N_STEP = 22             # 踏步数
STEP_D = 0.28           # 踏步深（水平）
STEP_H = FLOOR_H / N_STEP   # 踏步高 = 0.1773
RUN = N_STEP * STEP_D       # 水平投影长 = 6.16
STAIR_W = 1.3           # 梯段宽（沿用 M8C）
SLOPE_T = 0.18          # 梯段底板厚
DROP = 0.26             # 底板沿法线下沉量（让踏步锯齿露在底板之上）
RAIL_H = 0.9            # 扶手高出斜面的法向距离
RAIL_T = 0.06           # 扶手截面

PAT = re.compile(r"^M8C_(\w+)_Stair_(\d+)$")


def get_mat(name, color, rough):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = rough
    return m


def set_mat(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


def add_box(name, size, loc, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    o.rotation_euler = rot
    return o


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def shell_y(bname):
    """该栋外壳（含楼板）的 y 范围 —— 用来断言楼梯没捅出楼外。"""
    lo, hi = None, None
    for o in bpy.data.objects:
        if not (o.name.startswith("Bldg_%s" % bname) or o.name.startswith("M8C_%s" % bname)):
            continue
        for c in o.bound_box:
            wy = (o.matrix_world @ mathutils.Vector(c)).y
            lo = wy if lo is None else min(lo, wy)
            hi = wy if hi is None else max(hi, wy)
    return lo, hi


def build_one(stair_obj, mats):
    """用真实踏步替换一段斜板楼梯。返回该段的几何断言。"""
    m = PAT.match(stair_obj.name)
    bname, floor = m.group(1), int(m.group(2))
    cx, cy, cz = stair_obj.location.x, stair_obj.location.y, stair_obj.location.z
    z0 = cz - FLOOR_H * 0.5          # 本段起始楼面标高
    tag = "%s%s_%d" % (PREFIX, bname, floor)

    # 斜面几何
    angle = math.atan2(FLOOR_H, RUN)
    slope_len = math.hypot(RUN, FLOOR_H)
    sin_a, cos_a = math.sin(angle), math.cos(angle)

    # 删旧斜板（先记名再删）
    old = stair_obj.name
    bpy.data.objects.remove(stair_obj, do_unlink=True)

    # ① 梯段底板：沿法线下沉 DROP，让上面的踏步锯齿露出来
    cy_s = cy + DROP * sin_a
    cz_s = z0 + FLOOR_H * 0.5 - DROP * cos_a
    slope = add_box(tag + "_Slope", (STAIR_W, slope_len, SLOPE_T),
                    (cx, cy_s, cz_s), (angle, 0.0, 0.0))
    set_mat(slope, mats["conc"])

    # ② 踏步：单级 box + Array 常量偏移 (0, STEP_D, STEP_H)
    #    第 1 级中心 = 起始楼面 + 半级高，前沿贴在 cy - RUN/2
    first = (cx, cy - RUN * 0.5 + STEP_D * 0.5, z0 + STEP_H * 0.5)
    tread = add_box(tag + "_Steps", (STAIR_W, STEP_D, STEP_H), first)
    arr = tread.modifiers.new("M15_Steps", "ARRAY")
    arr.count = N_STEP
    arr.use_relative_offset = False
    arr.use_constant_offset = True
    arr.constant_offset_displace = (0.0, STEP_D, STEP_H)
    set_mat(tread, mats["tread"])

    # ③ 两侧扶手：沿斜面法线抬高 RAIL_H
    rails = []
    for side, sgn in (("L", -1.0), ("R", 1.0)):
        rx = cx + sgn * (STAIR_W * 0.5 + 0.05)
        ry = cy - RAIL_H * sin_a
        rz = z0 + FLOOR_H * 0.5 + RAIL_H * cos_a
        r = add_box(tag + "_Rail_%s" % side, (RAIL_T, slope_len, RAIL_T),
                    (rx, ry, rz), (angle, 0.0, 0.0))
        set_mat(r, mats["rail"])
        rails.append(r.name)

    # ---- 几何断言 ----
    top_z = z0 + N_STEP * STEP_H                 # 最后一级顶面标高
    land_z = z0 + FLOOR_H                        # 应抵达的上层楼面
    y_lo = cy - RUN * 0.5
    y_hi = cy + RUN * 0.5
    sy_lo, sy_hi = shell_y(bname)
    return {
        "old": old,
        "floor": floor,
        "z0": round(z0, 3),
        "top_z": round(top_z, 3),
        "landing_z": round(land_z, 3),
        "landing_ok": abs(top_z - land_z) < 1e-6,
        "angle_deg": round(math.degrees(angle), 2),
        "run": round(RUN, 3),
        "y_range": [round(y_lo, 2), round(y_hi, 2)],
        "shell_y": None if sy_lo is None else [round(sy_lo, 2), round(sy_hi, 2)],
        "in_shell": (sy_lo is None) or (y_lo >= sy_lo - 1e-6 and y_hi <= sy_hi + 1e-6),
        "steps": N_STEP,
        "made": [slope.name, tread.name] + rails,
    }


def build():
    removed = clear_old()
    mats = {
        "conc": get_mat("PBR_Concrete", (0.36, 0.36, 0.36), 0.85),
        "tread": get_mat("M15_TreadConc", (0.46, 0.46, 0.45), 0.7),
        "rail": get_mat("M15_RailMetal", (0.52, 0.52, 0.55), 0.35),
    }
    # 先收集再逐个替换（迭代时不能删集合元素）
    targets = [o for o in bpy.data.objects if PAT.match(o.name)]
    built = {}
    for o in targets:
        bname = PAT.match(o.name).group(1)
        built.setdefault(bname, []).append(build_one(o, mats))

    bpy.context.view_layer.update()
    per = {}
    for b, lst in built.items():
        per[b] = {
            "n": len(lst),
            "all_land_ok": all(d["landing_ok"] for d in lst),
            "all_in_shell": all(d["in_shell"] for d in lst),
            "angle_deg": lst[0]["angle_deg"],
        }
    return {
        "m15": True,
        "removed_old_prefix": len(removed),
        "replaced": sum(len(v) for v in built.values()),
        "per_building": per,
        "detail": built,
        "all_ok": all(v["all_land_ok"] and v["all_in_shell"] for v in per.values()),
        "objects": len(bpy.data.objects),
    }


def build_cam():
    """特写机位：站在 Dorm 第 1 段楼梯侧面看踏步轮廓（机位由楼梯 AABB 推算）。"""
    o = bpy.data.objects.get(PREFIX + "Dorm_1_Steps")
    if o is None:
        return None
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs = [v.x for v in bb]
    ys = [v.y for v in bb]
    zs = [v.z for v in bb]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    cz = (min(zs) + max(zs)) * 0.5
    cam = bpy.data.objects.get(PREFIX + "Cam")
    if cam is None:
        bpy.ops.object.camera_add(location=(cx, cy, cz))
        cam = bpy.context.active_object
        cam.name = PREFIX + "Cam"
    # 站梯段东侧、略高，斜看向梯段中段
    cam.location = (cx + 4.2, cy - 1.0, cz + 1.4)
    cam.data.lens = 28.0
    target = mathutils.Vector((cx, cy, cz))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return [round(v, 2) for v in cam.location]


def main():
    r = build()
    r["cam"] = build_cam()
    print("M15 result:", r)
    return r


result = main()
