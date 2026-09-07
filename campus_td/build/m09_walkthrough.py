# m09_walkthrough.py — M9 导航导出 + 整合：脚本化漫游相机（无人机俯瞰→西南下降→绕西侧→图书馆南门→阅览室）
# 幂等：按前缀 "M9_" 清旧再重建相机 + 关键帧。
# 设计判断：
#   这是 M9 最有价值的整合交付物——一段可进入校园的电影级漫游视频。
#   路径 6 个航点（无人机式下降 + 贴地通行）：
#     ① SW 抬高 z=14(-18,-12,14)俯瞰前区——高于食堂屋顶 7.8m/体育馆 11.7m，避免撞墙
#     ② 下降至西南开阔地(-12,-19,3)
#     ③ 沿 x=-9 绕过 Dorm 西墙北上至(-9,-11,2)——Dorm 西界 x=-7，x=-9 安全侧
#     ④ 走廊通行至图书馆南立面西南角外(-4,-9,1.7)
#     ⑤ 移至图书馆南门洞(x=5)外(5,-10,1.6)看穿门洞
#     ⑥ 进入阅览室(5,-7,1.6)看向阅读桌
#   关键帧穿插：仅 WP5→WP6 以 x=5 穿越门洞(宽 2.4，x∈[3.8,6.2])，证明"可进入"。
#   位置 BEZIER 缓动，旋转四元数 LINEAR(slerp，无翻滚)。
#   渲染由 blmcp_client.py 的 render_m09 用 EEVEE 输出 PNG 序列，再由 assemble_m09.py 合成 MP4。
# 运行：
#   exec(compile(open(r"...campus_td/build/m09_walkthrough.py").read(),"m09","exec"))
#   build_walkthrough()

import bpy
import mathutils

PREFIX = "M9_"

# (帧, 相机位置, 注视点) —— 6 段：无人机俯瞰 → 西南下降 → 绕西侧 → 图书馆南门 → 阅览室
# 几何约束：
#   - WP1 抬高到 z=14 (高于 Canteen 屋顶 7.8m / Gym 11.7m)，俯瞰前区；距离原点 25.8m 安全。
#   - WP1→WP2→WP3 自西西下降，全程 x≤-9 (Canteen 西界) 避免穿楼。
#   - WP3→WP4 在 Dorm 北(y>-10.5) + Canteen 东(x>-9) 的开阔走廊通行。
#   - WP4→WP5→WP6 沿 x=5 直线穿越图书馆南门洞(宽 2.4，x∈[3.8,6.2])。
WAYPOINTS = [
    (1,   (-18.0, -12.0, 14.0), ( 0.0, -10.0,  0.0)),  # SW 无人机俯瞰前区/食堂
    (28,  (-12.0, -19.0,  3.0), (-9.0, -15.0,  2.5)),  # 西南下降至食堂南侧开阔地
    (55,  ( -9.0, -11.0,  2.0), (-9.0,  -9.0,  1.8)),  # 沿 x=-9 绕过 Dorm 西墙北上
    (78,  ( -4.0,  -9.0,  1.7), ( 3.0,  -8.5,  1.4)),  # 走廊内接近图书馆南立面
    (100, (  5.0, -10.0,  1.6), ( 5.0,  -8.5,  1.2)),  # 图书馆南门洞(x=5)外 看穿门洞
    (120, (  5.0,  -7.0,  1.6), ( 5.0,  -3.0,  1.2)),  # 阅览室内(已穿门洞) 看阅读桌
]

FPS = 30
FRAME_END = 120
LENS_MM = 35.0


def clear_old():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)


def _fcurves_of(act):
    """跨版本取 Action 下的 FCurve 列表（Blender 5.2 新动画系统移除了 act.fcurves）。"""
    if act is None:
        return []
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    fcs = []
    for layer in getattr(act, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            cb = getattr(strip, "channelbag", None)
            if cb is not None:
                fcs.extend(getattr(cb, "fcurves", []) or [])
    return fcs


def build_walkthrough():
    sc = bpy.context.scene
    clear_old()

    cam_data = bpy.data.cameras.new(PREFIX + "Cam")
    cam_data.lens = LENS_MM
    cam_data.sensor_width = 36.0          # 全画幅等效，35mm 自然视场
    cam_data.clip_start = 0.1
    cam_data.clip_end = 200.0
    cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_mode = "QUATERNION"

    for f, loc, tgt in WAYPOINTS:
        cam.location = mathutils.Vector(loc)
        quat = (mathutils.Vector(tgt) - mathutils.Vector(loc)).to_track_quat("-Z", "Y")
        cam.rotation_quaternion = quat
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_quaternion", frame=f)

    # 插值：位置 BEZIER(缓动导游感)；旋转四元数 LINEAR(slerp，避免翻滚/插值畸变)
    act = cam.animation_data.action
    for fc in _fcurves_of(act):
        for kf in fc.keyframe_points:
            kf.interpolation = "LINEAR" if fc.data_path == "rotation_quaternion" else "BEZIER"

    sc.frame_start = 1
    sc.frame_end = FRAME_END
    sc.render.fps = FPS

    g = globals()
    g["result"] = {
        "m9": True,
        "camera": cam.name,
        "waypoints": [(f, list(loc), list(tgt)) for f, loc, tgt in WAYPOINTS],
        "frame_start": sc.frame_start,
        "frame_end": sc.frame_end,
        "fps": sc.render.fps,
        "lens_mm": LENS_MM,
        "scene_objects": len(bpy.data.objects),
    }
    return g["result"]
