# -*- coding: utf-8 -*-
"""
M39 · 运动场球门 · 角旗 · 记分牌（Goals, Corner Flags, Scoreboard）
=====================================================================
项目收官后新增「校园细节完善」里程碑，直接延续 M38（室外运动场）。M38 已在中央广场
PlazaCourt 之上铺好足球场草皮(31x17m)+红色跑道环+白色标线，但只有球场线、没有球门/
角旗/记分牌等可辨识的"比赛设施"。本里程碑补齐这些设施，让室外运动场一眼可辨为足球场。

几何策略（Z 为 up，地面在 XY 平面，与场景一致；坐标沿用 M38 的广场中心）：
  CX, CY = -3.0, 0.0   （广场中心，由 PlazaCourt AABB 推算 X[-22,16]->-3 / Y[-13,13]->0）
  球场半宽 half_x=15.0 / 半深 half_y=8.5  -> 两端球门线在 x = CX∓15.0 = {-18, 12}

设施：
  ① 两个球门（白框）：两端球门线各一座。每座 = 2 立柱(垂直) + 横梁(沿 Y) + 2 后撑杆(斜)
     + 后底杆(沿 Y)，构成可辨识的 3D 球门框（不透明度材质，避免半透叠加问题）。
  ② 4 面角旗：球场 4 角，细杆 + 小旗面（亮色 box）。
  ③ 1 块记分牌：西球门后方 (x≈-21) 立于双腿 + 暗色面板 + 自发光屏（夜晚/黄昏也发光）。

避坑（沿用 PLAN.md 清单 + 历次 M 经验）：
  - 不调 mode_set（MCP exec 内会 poll fail）；primitive_*_add 在 OBJECT 模式即可。
  - 删旧物体先 nm=o.name 再 remove（防 ReferenceError，清单#16）。
  - 全部新增物体/材质/网格带 M39_ 前缀，幂等（先清旧 M39_ 再建），绝不触碰其它物体。
  - **顶层执行**：MCP 用 exec(compile(open().read())) 跑，__name__!="__main__"，故所有逻辑
    在顶层执行，result 在顶层赋值（参照 m37_flag.py / m38_sports_field.py 写法）。
  - 圆柱朝向用 mathutils 的 rotation_difference 把局部 +Z 对齐到目标方向，避免手动欧拉角退化。
  - 不建额外 POINT 灯：记分牌屏用自发光（Emission Strength），白天是亮面板、夜晚/黄昏自然发光，
    不污染白昼基线(M19C)也不增加永久点光源。
"""
import bpy
import mathutils

PREFIX = "M39_"
CX, CY = -3.0, 0.0          # 广场中心（与 M38 一致）
HALF_X, HALF_Y = 15.0, 8.5  # 球场半宽/半深（与 M38 一致）

GOAL_HALF_W = 3.66          # 球门宽 7.32m -> 半宽
GOAL_H = 2.44               # 球门高
POST_R = 0.06               # 球门框杆半径
X_W = CX - HALF_X           # 西球门线 x = -18
X_E = CX + HALF_X           # 东球门线 x = 12


# ----------------------------------------------------------------------------
def clear_old():
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    for me in list(bpy.data.meshes):
        if me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)


def add_cylinder(name, radius, length, center, dir_vec):
    """在 center 处建一根半径 radius、长度 length 的圆柱，局部 +Z 对齐到 dir_vec。"""
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=center)
    o = bpy.context.active_object
    o.name = name
    z = mathutils.Vector((0.0, 0.0, 1.0))
    d = mathutils.Vector(dir_vec)
    if d.length < 1e-6:
        d = z
    q = z.rotation_difference(d.normalized())
    o.rotation_euler = q.to_euler()
    return o


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def get_mat(name, fallback_color, rough=0.8, metallic=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = fallback_color + [1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = rough
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
    return m


def get_emissive(name, color, strength):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color + [1.0]
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color + [1.0]
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = strength
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.5
    return m


def set_mat(o, mat):
    while len(o.data.materials) < 1:
        o.data.materials.append(None)
    o.data.materials[0] = mat


def make_goal(x_line, dx, tag):
    """在球门线 x_line 建一座球门；dx = 球门后方方向（网在 x_line+dx 一侧）。"""
    w, H, r = GOAL_HALF_W, GOAL_H, POST_R
    parts = []
    # 立柱（垂直）
    parts.append(add_cylinder(PREFIX + "Goal%s_PostA" % tag, r, H, (x_line, w, H / 2.0),
                              (0.0, 0.0, 1.0)))
    parts.append(add_cylinder(PREFIX + "Goal%s_PostB" % tag, r, H, (x_line, -w, H / 2.0),
                              (0.0, 0.0, 1.0)))
    # 横梁（沿 Y）
    parts.append(add_cylinder(PREFIX + "Goal%s_Bar" % tag, r, 2.0 * w, (x_line, 0.0, H),
                              (0.0, 1.0, 0.0)))
    # 后撑杆（斜）+ 后底杆（沿 Y）
    for sgn in (1.0, -1.0):
        top = mathutils.Vector((x_line, sgn * w, H))
        bot = mathutils.Vector((x_line + dx, sgn * w, 0.0))
        mid = (top + bot) * 0.5
        d = bot - top
        parts.append(add_cylinder(PREFIX + "Goal%s_Stay%s" % (tag, int(sgn)), r, d.length, mid, d))
    parts.append(add_cylinder(PREFIX + "Goal%s_BaseBar" % tag, r, 2.0 * w,
                              (x_line + dx, 0.0, 0.0), (0.0, 1.0, 0.0)))
    for o in parts:
        set_mat(o, goal_mat)
    return parts


# ----------------------------------------------------------------------------
clear_old()

goal_mat = get_mat(PREFIX + "GoalMat", [0.90, 0.90, 0.92], rough=0.4, metallic=0.0)
flag_mat = get_mat(PREFIX + "FlagMat", [0.85, 0.20, 0.12], rough=0.6, metallic=0.0)
board_mat = get_mat(PREFIX + "BoardMat", [0.12, 0.12, 0.14], rough=0.7, metallic=0.0)
screen_mat = get_emissive(PREFIX + "ScreenMat", [0.18, 0.42, 0.95], strength=2.2)
pole_mat = get_mat(PREFIX + "PoleMat", [0.55, 0.57, 0.60], rough=0.6, metallic=0.2)

built = []

# ---- ① 两个球门（网在球场外侧：西球门网朝 -x，东球门网朝 +x）----
built += make_goal(X_W, -0.9, "W")
built += make_goal(X_E, 0.9, "E")

# ---- ② 4 面角旗（球场四角）----
for (cx_c, cy_c) in [(X_W, HALF_Y), (X_W, -HALF_Y), (X_E, HALF_Y), (X_E, -HALF_Y)]:
    pole = add_cylinder(PREFIX + "CornerPole_%.0f_%.0f" % (cx_c, cy_c), 0.03, 1.6,
                        (cx_c, cy_c, 0.8), (0.0, 0.0, 1.0))
    set_mat(pole, pole_mat)
    built.append(pole)
    flag = add_box(PREFIX + "CornerFlag_%.0f_%.0f" % (cx_c, cy_c), (0.55, 0.02, 0.36),
                   (cx_c + 0.28, cy_c, 1.45))
    set_mat(flag, flag_mat)
    built.append(flag)

# ---- ③ 记分牌（西球门后方 x≈-21，双腿 + 暗面板 + 自发光屏）----
X_SB = -21.0
sb_legs = []
for sgn in (1.0, -1.0):
    leg = add_cylinder(PREFIX + "Board_Leg%s" % int(sgn), 0.08, 2.2,
                       (X_SB, sgn * 1.8, 1.1), (0.0, 0.0, 1.0))
    set_mat(leg, pole_mat)
    built.append(leg)
    sb_legs.append(leg)
panel = add_box(PREFIX + "Board_Panel", (0.25, 4.0, 1.6), (X_SB, 0.0, 2.4))
set_mat(panel, board_mat)
built.append(panel)
screen = add_box(PREFIX + "Board_Screen", (0.06, 3.2, 1.0), (X_SB + 0.16, 0.0, 2.4))
set_mat(screen, screen_mat)
built.append(screen)

# ---- 专用预览相机（东南 3/4 俯角，框住球场与两端球门）----
cam_data = bpy.data.cameras.new(PREFIX + "Cam")
cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (10.0, 26.0, 15.0)
tgt = mathutils.Vector((CX - 2.0, 0.0, 1.5))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 35.0
bpy.context.scene.camera = cam

# ---- 验证探针（顶层 result）----
n_obj = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M39",
    "n_m39_objects": n_obj,
    "goals": 2,
    "corner_flags": 4,
    "scoreboard": 1,
    "pitch_center": [CX, CY],
    "goal_lines_x": [X_W, X_E],
    "cam_loc": list(cam.location),
    "n_total_after": len(bpy.data.objects),
}
print("M39_RESULT=" + repr(result))
