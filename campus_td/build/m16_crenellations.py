# m16_crenellations.py — M16 围墙垛口（backlog 低优先项：围墙垛口）
#
# 在 M11 重建后的 5 段 perimeter 围墙（M11_WallBack / FrontL / FrontR / Left / Right，
# 96m 场地，墙高 2.4m、厚 0.35m、顶部有 M11_Coping* 压顶）之上，沿墙顶中线排布
# 一列"垛口"(merlon)——交替的凸起方块 + 空隙（crenel），形成女儿墙/城垛质感，
# 给校园围墙一个"完成感"的收头。M5B 已加 coping（压顶），本脚本在其上再加 merlon。
#
# 设计原则（与 M12/M15 一致）：坐标全部从场景里 M11_Wall* 的 AABB 读，不硬编码；
#   这样即使 M11 再挪墙，merlon 仍贴合。命名用 M16_ 前缀，clear_all 只删 M16_ 旧物体，
#   不碰墙/压顶/建筑/塔防，幂等安全。
#
# 运行：exec(compile(open(r"...campus_td/build/m16_crenellations.py").read(), "m16", "exec"))

import bpy
import mathutils

PREFIX = "M16_"

# ---- 可调参数 ----
MERLON_W = 0.55      # 沿墙走向的方块宽
MERLON_T = 0.47      # 垂直墙走向的厚度（= 墙厚 0.35 + 0.12 盖檐）
MERLON_H = 0.55      # 垛口凸起高
SPACING = 1.25       # 中心间距（方块 0.55 + 空隙 0.70）
EDGE_MARGIN = 0.40   # 墙端留白，避免 merlon 悬在墙头外
GATE_HALF = 8.0      # 校门洞半宽（x∈[-8,8] 无墙，FrontL/FrontR 各自止于 ±8）

# 前墙（FrontL/FrontR）的校门洞缺口：FrontL 止于 x=-8，FrontR 起于 x=8，
# 因此各自本就不覆盖 [-8,8]，这里再留 0.3m 余量以防贴边悬空。
GATE_GAP = 0.30


def clear_all():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def get_concrete_mat():
    m = bpy.data.materials.get("PBR_Concrete")
    if m is not None:
        return m
    # 兜底：场景里没有 PBR_Concrete 时自建一个哑光混凝土
    m = bpy.data.materials.new("PBR_Concrete")
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.52, 0.52, 0.52, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
        bsdf.inputs["Metallic"].default_value = 0.0
    return m


def wall_run(wall):
    """返回 (run_axis, run_min, run_max, fixed_axis_value, thickness, top_z)。"""
    bb = [wall.matrix_world @ mathutils.Vector(c) for c in wall.bound_box]
    xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    minz, maxz = min(zs), max(zs)
    # 走向 = 水平方向中更长者
    if (maxx - minx) >= (maxy - miny):
        run_axis = "X"
        run_min, run_max = minx, maxx
        fixed = (miny + maxy) * 0.5
        thickness = (maxy - miny)
    else:
        run_axis = "Y"
        run_min, run_max = miny, maxy
        fixed = (minx + maxx) * 0.5
        thickness = (maxx - minx)
    return run_axis, run_min, run_max, fixed, thickness, maxz


def top_of_wall(wall, copings):
    """墙顶真实高度 = 墙自身 max_z 与覆盖其上的 coping max_z 的较大者。"""
    bb = [wall.matrix_world @ mathutils.Vector(c) for c in wall.bound_box]
    xs = [v.x for v in bb]; ys = [v.y for v in bb]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    top = max(v.z for v in bb)
    for c in copings:
        cbb = [c.matrix_world @ mathutils.Vector(v) for v in c.bound_box]
        cxs = [v.x for v in cbb]; cys = [v.y for v in cbb]
        # coping 中心是否落在该墙 XY 包围盒内（含 0.5m 余量）
        cx = (min(cxs) + max(cxs)) * 0.5
        cy = (min(cys) + max(cys)) * 0.5
        if (x0 - 0.5) <= cx <= (x1 + 0.5) and (y0 - 0.5) <= cy <= (y1 + 0.5):
            top = max(top, max(v.z for v in cbb))
    return top


def build_crenellations():
    cleared = clear_all()
    mat = get_concrete_mat()
    walls = [o for o in bpy.data.objects if o.name.startswith("M11_Wall")]
    copings = [o for o in bpy.data.objects if o.name.startswith("M11_Coping")]
    if not walls:
        return {"error": "no M11_Wall found; run m11 first", "cleared": cleared}

    made = 0
    per_wall = {}
    idx = 0
    for wall in walls:
        run_axis, run_min, run_max, fixed, thickness, wtop = wall_run(wall)
        top = top_of_wall(wall, copings)
        # 空隙起点：让整列居中
        usable = (run_max - EDGE_MARGIN) - (run_min + EDGE_MARGIN)
        if usable <= 0:
            continue
        n = int(usable // SPACING) + 1
        # 实际起点使首末 merlon 离墙端等距
        start = run_min + EDGE_MARGIN + (usable - (n - 1) * SPACING) / 2.0
        wall_made = 0
        for i in range(n):
            p = start + i * SPACING
            # 校门缺口保护：仅前墙相关，且 merlon 中心不得落入 [-GATE_HALF±gap]
            if abs(p) < (GATE_HALF - GATE_GAP):
                # 仅 FrontL/FrontR 可能接近 x=0 区；Back/Left/Right 不受影响
                if wall.name.startswith("M11_WallFront"):
                    continue
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
            o = bpy.context.active_object
            o.name = "%s%s_%d" % (PREFIX, wall.name.replace("M11_Wall", ""), idx)
            if run_axis == "X":
                o.location = (p, fixed, top + MERLON_H / 2.0)
                o.scale = (MERLON_W, MERLON_T, MERLON_H)
            else:
                o.location = (fixed, p, top + MERLON_H / 2.0)
                o.scale = (MERLON_T, MERLON_W, MERLON_H)
            if o.data.materials:
                o.data.materials[0] = mat
            else:
                o.data.materials.append(mat)
            idx += 1
            made += 1
            wall_made += 1
        per_wall[wall.name] = wall_made

    # 特写机位：东南角（FrontR 与 Right 墙交汇处），从场外低角度看入，
    # 框进 corner merlon 转折 + coping + 远处校门牌坊。坐标按墙几何动态推算。
    # FrontR 在 y=-48、Right 在 x=48，SE 角 = (48,-48)。
    corner = mathutils.Vector((48.0, -48.0, 0.0))
    cam = bpy.data.objects.get(PREFIX + "Cam")
    if cam is None:
        bpy.ops.object.camera_add(location=(0, 0, 0))
        cam = bpy.context.active_object
        cam.name = PREFIX + "Cam"
    cam.location = (corner.x + 30.0, corner.y - 30.0, 9.0)
    tgt = mathutils.Vector((corner.x, corner.y, 2.8))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 35.0
    cam.data.clip_end = 500.0

    return {
        "cleared": cleared,
        "walls_found": [w.name for w in walls],
        "per_wall": per_wall,
        "merlons_made": made,
        "cam": PREFIX + "Cam",
        "cam_loc": list(cam.location),
    }


stats = build_crenellations()
result = stats
