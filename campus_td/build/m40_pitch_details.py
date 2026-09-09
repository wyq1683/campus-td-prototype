# -*- coding: utf-8 -*-
"""
M40 · 足球场细节完善（Goal Nets + Center Spot + Penalty Spots）
================================================================
项目收官后新增「校园细节完善」里程碑，延续 M38（室外运动场）+ M39（球门/角旗/记分牌）。
当前室外足球场已有草皮、跑道、白线、球门框、角旗、记分牌，但：
  - 球门只有白框、背后没有网（不像真球场）；
  - 缺中点（center spot）与两侧罚球点（penalty spot），标线不完整。

本里程碑在 M39 球门几何之上补齐：
  ① 两座球门背后的半透明白色球网（开口面朝向球场，封闭背/顶/两侧 -> 可读作球网笼）。
  ② 中点（场地正中）+ 两侧罚球点（距各自球门线 11m），白色小圆点贴在草皮上。

坐标沿用 M38/M39：CX, CY = -3.0, 0.0；球场半宽 HALF_X=15.0（球门线 x∈{-18,12}），
HALF_Y=8.5；球门宽 7.32（半宽 3.66）、高 2.44；草皮顶面 z≈0.17。

避坑（沿用 PLAN.md 清单 + 历次 M 经验）：
  - 不调 mode_set（MCP exec 内会 poll fail）；primitive_*_add 在 OBJECT 模式即可。
  - 删旧物体先 nm=o.name 再 remove（防 ReferenceError，清单#16）。
  - 全部新增物体/材质/网格带 M40_ 前缀，幂等（先清旧 M40_ 再建），绝不触碰其它物体。
  - 顶层执行：MCP 用 exec(compile(open().read())) 跑，__name__!="__main__"，逻辑在顶层。
  - 半透材质：use_nodes + Principled Alpha=0.22 + blend_method='BLEND'，Cycles 下生效。
  - 复用已验证的 M39_Cam 作为预览相机（不新建相机物体，避免污染场景计数）。
"""
import bpy
import mathutils

PREFIX = "M40_"
CX, CY = -3.0, 0.0          # 广场中心（与 M38/M39 一致）
HALF_X, HALF_Y = 15.0, 8.5  # 球场半宽/半深
GOAL_HALF_W = 3.66          # 球门半宽
GOAL_H = 2.44               # 球门高
X_W = CX - HALF_X           # 西球门线 x = -18
X_E = CX + HALF_X           # 东球门线 x = 12
NET_DEPTH = 1.8             # 球网进深
GRASS_Z = 0.17             # 草皮顶面高度（与 M38 一致）


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


def get_net_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = [0.93, 0.96, 1.0, 1.0]
            bsdf.inputs["Roughness"].default_value = 0.35
            if "Alpha" in bsdf.inputs:
                bsdf.inputs["Alpha"].default_value = 0.22
        m.blend_method = "BLEND"
        m.use_backface_culling = False
    return m


def set_mat(o, mat):
    while len(o.data.materials) < 1:
        o.data.materials.append(None)
    o.data.materials[0] = mat


def add_spot(name, x, y):
    """草皮上的白色罚球/中点小圆点（薄圆柱 disk）。"""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.03, location=(x, y, GRASS_Z + 0.015))
    o = bpy.context.active_object
    o.name = name
    set_mat(o, spot_mat)
    return o


def make_net_for(x_line, dx, tag):
    """在球门线 x_line 背后建一座半透明球网笼；dx 指向球场内，网在 x_line-dx 反侧。"""
    # 网在球场外侧：西球门网朝 -x（x 更小），东球门网朝 +x（x 更大）
    x_far = x_line - dx * NET_DEPTH   # dx 为网朝外的反方向位移量（西 dx=+0.9 -> 实际网朝 -x）
    # 上面 dx 语义：M39 make_goal 里 dx 是网朝外的方向（西 -0.9 / 东 +0.9）
    # 这里统一：网外端 x_far = x_line + dx*NET_DEPTH
    x_far = x_line + dx * NET_DEPTH
    x_center = (x_line + x_far) * 0.5
    w = GOAL_HALF_W
    H = GOAL_H
    parts = []
    # 背板（垂直，远 x 端）
    parts.append(add_box(PREFIX + "Net%s_Back" % tag, (0.04, 2.0 * w, H), (x_far, 0.0, H / 2.0)))
    # 顶板（水平，顶端）
    parts.append(add_box(PREFIX + "Net%s_Top" % tag, (NET_DEPTH, 2.0 * w, 0.04), (x_center, 0.0, H)))
    # 两侧板（垂直，y=±w）
    for sgn in (1.0, -1.0):
        parts.append(add_box(PREFIX + "Net%s_Side%s" % (tag, int(sgn)), (NET_DEPTH, 0.04, H),
                             (x_center, sgn * w, H / 2.0)))
    for o in parts:
        set_mat(o, net_mat)
    return parts


# ----------------------------------------------------------------------------
clear_old()

net_mat = get_net_mat(PREFIX + "NetMat")
spot_mat = get_mat(PREFIX + "SpotMat", [0.95, 0.95, 0.95], rough=0.6, metallic=0.0)

built = []

# ---- ① 两座球门背后的半透明白色球网（西网朝 -x，东网朝 +x）----
# 注意：M39 make_goal 的 dx 语义（西 -0.9 / 东 +0.9）即网朝外方向，本处复用
built += make_net_for(X_W, -0.9, "W")
built += make_net_for(X_E, 0.9, "E")

# ---- ② 中点（场地正中）+ 两侧罚球点（距各自球门线 11m）----
built.append(add_spot(PREFIX + "CenterSpot", CX, CY))
# 西罚球点：距西球门线 11m 进场内 -> x = X_W + 11 = -7
built.append(add_spot(PREFIX + "PenSpotW", X_W + 11.0, CY))
# 东罚球点：距东球门线 11m 进场内 -> x = X_E - 11 = 1
built.append(add_spot(PREFIX + "PenSpotE", X_E - 11.0, CY))

# ---- 预览相机：复用已验证的 M39_Cam（不新建相机物体）----
cam = bpy.data.objects.get("M39_Cam")
if cam is not None:
    bpy.context.scene.camera = cam
else:
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
    "milestone": "M40",
    "n_m40_objects": n_obj,
    "goal_nets": 2,
    "back_top_side_panels_per_net": 4,
    "center_spot": 1,
    "penalty_spots": 2,
    "pitch_center": [CX, CY],
    "net_x_west": [X_W, X_W - 0.9 * NET_DEPTH],
    "net_x_east": [X_E, X_E + 0.9 * NET_DEPTH],
    "cam_used": cam.name,
    "n_total_after": len(bpy.data.objects),
}
print("M40_RESULT=" + repr(result))
