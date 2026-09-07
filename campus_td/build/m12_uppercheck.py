# m12_uppercheck.py — M12 上层补光量化校验（机位自适应 + 上下层对照）
#
# 背景：
#   M8D 给 12 个上层各加了一盏 AREA 灯（energy 200），但"200 合不合适"一直是
#   backlog 里的高优先级目视项 —— 没有可量化判据就永远确认不了。
#
#   雪上加霜：M11 总平重排把 7 栋楼整体挪走后，M8/M8B/M8C/M8D/M8E 所有渲染相机
#   都是按旧坐标硬编码的，现在全部指向空地。所以本脚本不再硬编码机位，
#   **从目标建筑的当前 AABB 动态算机位**，建筑再挪也不失效。
#
# 方法（把"目视确认"变成客观判据）：
#   同一栋 Library、同一个房间进深、同一支镜头，只差楼层：
#     A) 地面层 1F —— 已知合适（M8 补光 240/300，M8B 已调好）→ 基准
#     B) 上层 3F   —— 待测（M8D 补光 200）
#   两张图做亮度分布对比：若上层分位数显著低于地面层 → 偏暗；显著高于/触顶 → 过曝。
#
# 运行：exec(compile(open(r"...campus_td/build/m12_uppercheck.py").read(), "m12", "exec"))
#   渲染某一张：再追加一行  render_shot("upper")  /  render_shot("ground")

import bpy
import math
import mathutils

PREFIX = "M12_"

# 目标建筑 + 层高（与 m02/m04 一致）
TARGET_BLD = "Library"
FLOOR_H = 3.9
EYE_H = 1.55          # 站立视高
GROUND_FLOOR_Z = 0.0  # 1F 地面（M8 铺板后顶面略高于 0，误差可忽略）
UPPER_INDEX = 2       # M8D_Library_F2 -> 第 3 层，地面 z = 2*3.9 = 7.8
LENS = 20.0           # 广角，保证房间进深完整入画
SAMPLES = 96
RES = (1280, 720)

OUT = {
    "upper": r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m12_upper_F2.png",
    "ground": r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m12_ground_1F.png",
}


def bbox(objs):
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


def building_bbox(name):
    objs = [o for o in bpy.data.objects if o.name.startswith("Bldg_%s_" % name)]
    if not objs:
        return None
    return bbox(objs)


def get_cam(name):
    cam = bpy.data.objects.get(name)
    if cam is None:
        bpy.ops.object.camera_add(location=(0.0, 0.0, 2.0))
        cam = bpy.context.active_object
        cam.name = name
    return cam


def aim(cam, loc, tgt, lens=LENS):
    cam.location = loc
    cam.rotation_euler = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def place_cam(which):
    """按建筑当前 AABB 算机位：房间南侧朝北看，覆盖整个进深。"""
    bb = building_bbox(TARGET_BLD)
    if bb is None:
        return None
    mn, mx = bb
    cx, cy = 0.5 * (mn[0] + mx[0]), 0.5 * (mn[1] + mx[1])
    depth = my = mx[1] - mn[1]
    south_y = mn[1]

    # 两张必须**同一相对机位**才有可比性：都在房间内南侧、朝北看整个进深。
    # （初版让地面层站门外拍，画面混进门框背光暗部 -> 15% 死黑，纯构图差异不是亮度差异。）
    if which == "ground":
        fz = GROUND_FLOOR_Z
    else:
        fz = UPPER_INDEX * FLOOR_H
    loc = (cx, south_y + 1.8, fz + EYE_H)
    tgt = (cx, south_y + depth * 0.85, fz + EYE_H - 0.5)

    cam = get_cam(PREFIX + "Cam_" + which)
    aim(cam, loc, tgt)
    return cam, {"bbox": [round(v, 2) for v in mn + mx],
                 "loc": [round(v, 2) for v in loc],
                 "tgt": [round(v, 2) for v in tgt]}


def render_shot(which):
    sc = bpy.context.scene
    got = place_cam(which)
    if got is None:
        return {"ok": False, "why": "no building %s" % TARGET_BLD}
    cam, info = got

    hidden = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            hidden.append((o, o.hide_render))
            o.hide_render = True

    sc.camera = cam
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "CPU"
    except Exception:
        pass
    sc.cycles.samples = SAMPLES
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.filepath = OUT[which]
    bpy.ops.render.render(write_still=True)

    for o, was in hidden:
        o.hide_render = was

    # 同场景的对照灯参数一起回传，便于判读
    lights = {}
    for o in bpy.data.objects:
        if o.type == "LIGHT" and TARGET_BLD in o.name:
            lights[o.name] = {"e": round(o.data.energy, 1),
                               "z": round(o.matrix_world.translation.z, 2)}
    return {"ok": True, "shot": which, "cam": [round(v, 2) for v in cam.location],
            "info": info, "lights": lights, "file": OUT[which],
            "objects": len(bpy.data.objects)}


def build_cams():
    """只建相机不渲染，便于快速核对取景。"""
    out = {}
    for w in ("upper", "ground"):
        got = place_cam(w)
        out[w] = got[1] if got else None
    return out
