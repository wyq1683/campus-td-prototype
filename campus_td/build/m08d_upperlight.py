# m08d_upperlight.py — M8D 上层房间补光
# 背景：M8C 给 4 栋楼建了 12 个上层（楼板 + 家具 + 楼梯），但 M8B 只调了地面层 5 盏 AREA 灯，
#   上层完全没有补光 → 从 ribbon 窗看进去只有"结构剪影"，读不出材质与家具。
# 目标：每个上层补一盏 AREA 灯，让上层从"结构可读"升到"材质可读"。
#
# 参数选择：
#   energy = 200（低于地面层 240）：上层四周均有 ribbon 窗，天然光进光量大于地面层，
#     且从室外看是"透过玻璃"观察，过高会在玻璃上形成过曝亮块。
#   size  = 0.7 × (内净宽, 内净深)：与 M8B 地面层同一套口径，保证整栋楼光照语言一致。
#   高度  = 该层地面 + 3.4m（与 M8 地面层 `FLOOR_TOP + 3.4` 一致），距本层顶板 0.5m。
#   平面  = 楼板中心（cx + WELL/2，即避开 -x 侧 1.45m 楼梯井槽），与 M8C 楼板对齐。
#
# 幂等：PREFIX="M8D_" 清旧再重建（对象 + 灯光数据）；只加灯，不动任何几何。
# 运行：
#   exec(compile(open(r"...campus_td/build/m08d_upperlight.py").read(),"m08d","exec"))
#   build_upper_light()

import bpy
import mathutils

PREFIX = "M8D_"
FLOOR_H = 3.9          # 层高（与 M2/M4/M8C 一致）
WELL = 1.45            # 楼梯井槽宽（与 M8C 一致）
WALL_T = 0.4           # 外墙厚
ENERGY = 200.0         # 上层补光能量（地面层为 240）
CLEAR = 3.4            # 灯具距本层地面高度

# 与 M8C 同一份楼层表（Gym 通高单一体量，无上层）
BUILDINGS = {
    "Admin":   dict(center=(-16.5, -15.0), w=13.0, d=9.0,  floors=4),
    "Dorm":    dict(center=(  0.0, -15.0), w=14.0, d=9.0,  floors=6),
    "Canteen": dict(center=(-16.0,  -3.0), w=14.0, d=10.0, floors=2),
    "Library": dict(center=(  2.0,  -3.0), w=15.0, d=11.0, floors=4),
}


def bldg_center(bname, fallback):
    """从场景里 `Bldg_<B>_*` 的 AABB 中心读该楼**当前**位置，不硬编码。

    ⚠ 同源真 bug（2026-09-07 M15 暴露）：M11 总平重排后 BUILDINGS[...]["center"] 失效，
      本步若用硬编码 center 放上层补光，灯会落在旧坐标、与 M8C 楼板错位。
      改读当前外壳中心后，两种情况（未 M11 / 已 M11）都对齐。
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
    for lt in [l for l in bpy.data.lights if l.name.startswith(PREFIX)]:
        bpy.data.lights.remove(lt)
    return removed


def add_fill(name, cx, cy, cz, sx, sy, energy):
    lt = bpy.data.lights.get(name)
    if lt is None:
        lt = bpy.data.lights.new(name, type="AREA")
    lt.energy = energy
    lt.shape = "RECTANGLE"
    lt.size = sx
    lt.size_y = sy
    lamp = bpy.data.objects.get(name)
    if lamp is None:
        lamp = bpy.data.objects.new(name, lt)
        bpy.context.collection.objects.link(lamp)
    lamp.location = (cx, cy, cz)
    lamp.rotation_euler = (0.0, 0.0, 0.0)   # 局部 -Z 朝下
    return lamp.name


def build_upper_light():
    removed = clear_old()
    made = {}
    total = 0
    for bname, b in BUILDINGS.items():
        cx, cy = bldg_center(bname, b["center"])
        iw = b["w"] - 2 * WALL_T
        idp = b["d"] - 2 * WALL_T
        sx = round(0.7 * iw, 2)
        sy = round(0.7 * idp, 2)
        n = 0
        for f in range(1, b["floors"]):
            z0 = f * FLOOR_H
            nm = PREFIX + "%s_F%d" % (bname, f)
            add_fill(nm, cx + WELL / 2.0, cy, z0 + CLEAR, sx, sy, ENERGY)
            n += 1
            total += 1
        made[bname] = {"floors": b["floors"], "lights": n, "size": (sx, sy), "energy": ENERGY}
    g = globals()
    g["result"] = {
        "m8d": True,
        "removed_old": len(removed),
        "buildings": made,
        "total_lights": total,
        "scene_objects": len(bpy.data.objects),
        "total_scene_lights": len([o for o in bpy.data.objects if o.type == "LIGHT"]),
    }
    return g["result"]


build_upper_light()
