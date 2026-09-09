# -*- coding: utf-8 -*-
"""
M38 · 室外运动场（Soccer Pitch + Running Track + Markings）
============================================================
项目收官后新增「校园细节完善」里程碑。原始 scope 的"操场（跑道+球场）"从未在
户外落地（仅有 M8 室内体育馆球场线）。本脚本在中央广场 PlazaCourt 之上叠加一座
真实可辨的室外运动场：绿色足球场 + 红色塑胶跑道环 + 白色场地标线，全部以
M38_ 前缀新建、幂等（先清旧 M38_ 再建），绝不触碰/删除其余物体。

几何策略（Z 为 up，地面在 XY 平面，与场景一致）：
  plaza top ≈ 0.10
  M38_Track (red)   size(37,25,0.04) @ z=0.12  -> top 0.14
  M38_Pitch (grass) size(31,17,0.06) @ z=0.17  -> 0.14..0.20  (红色跑道环露在四周 ~3-4m)
  M38_Line_* (white)@ z=0.22  (球场线 + 跑道分道线，高于草皮)
  M38_CenterCircle   torus major 2.5 / minor 0.10 @ z=0.22

避坑（沿用 PLAN.md 清单）：
  - 不调 mode_set（MCP exec 内会 poll fail）；primitive_*_add 在 OBJECT 模式即可。
  - 删旧物体先 nm=o.name 再 remove（防 ReferenceError，清单#16）。
  - 草皮复用既有 PBR_Grass（节点材质，按名指派，不重建），无则降级绿。
  - 全部新增材质/网格带 M38_ 前缀，隔离不污染其它命名。
  - **顶层执行**：MCP 用 exec(compile(open().read())) 跑，__name__!="__main__"，
    故本脚本所有逻辑在顶层执行，result 在顶层赋值（参照 m37_flag.py 写法）。
"""
import bpy
import mathutils

PREFIX = "M38_"
CX, CY = -3.0, 0.0  # 广场中心（由 PlazaCourt AABB 推算：X[-22,16]->-3, Y[-13,13]->0）


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


clear_old()

grass = bpy.data.materials.get("PBR_Grass")
track_mat = get_mat(PREFIX + "TrackMat", [0.50, 0.10, 0.09], rough=0.92, metallic=0.0)
line_mat = get_mat(PREFIX + "LineMat", [0.92, 0.92, 0.92], rough=0.5, metallic=0.0)

# 红色塑胶跑道环（整块略小于广场，露出一圈砖边）
track = add_box(PREFIX + "Track", (37.0, 25.0, 0.04), (CX, CY, 0.12))
track.data.materials.append(track_mat)

# 绿色足球场草皮（复用 PBR_Grass），坐落跑道环内形成红边
pitch = add_box(PREFIX + "Pitch", (31.0, 17.0, 0.06), (CX, CY, 0.17))
if grass:
    pitch.data.materials.append(grass)
else:
    pitch.data.materials.append(get_mat(PREFIX + "GrassMat", [0.18, 0.42, 0.16], rough=0.95))

# -------- 白色球场标线（z=0.22，高于草皮顶 0.20）--------
ZL = 0.22
half_x, half_y = 15.0, 8.5  # 球场半宽/半深
lines = []
lines.append(add_box(PREFIX + "Line_TouchA", (31.0, 0.16, 0.02), (CX, CY + half_y, ZL)))
lines.append(add_box(PREFIX + "Line_TouchB", (31.0, 0.16, 0.02), (CX, CY - half_y, ZL)))
lines.append(add_box(PREFIX + "Line_GoalA", (0.16, 17.0, 0.02), (CX + half_x, CY, ZL)))
lines.append(add_box(PREFIX + "Line_GoalB", (0.16, 17.0, 0.02), (CX - half_x, CY, ZL)))
lines.append(add_box(PREFIX + "Line_Half", (0.16, 17.0, 0.02), (CX, CY, ZL)))
lines.append(add_box(PREFIX + "Line_PenA", (0.16, 12.0, 0.02), (CX + 10.0, CY, ZL)))
lines.append(add_box(PREFIX + "Line_PenB", (0.16, 12.0, 0.02), (CX - 10.0, CY, ZL)))

bpy.ops.mesh.primitive_torus_add(major_radius=2.5, minor_radius=0.10,
                                 location=(CX, CY, ZL), rotation=(0, 0, 0))
circ = bpy.context.active_object
circ.name = PREFIX + "CenterCircle"
lines.append(circ)

for sgn in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.08,
                                     location=(CX + sgn * 10.0, CY, ZL),
                                     rotation=(0, 0, 0))
    arc = bpy.context.active_object
    arc.name = PREFIX + "PenArc_%d" % sgn
    lines.append(arc)

for o in lines:
    while len(o.data.materials) < 1:
        o.data.materials.append(None)
    o.data.materials[0] = line_mat

# -------- 红色跑道分道线（把 3~4m 红边分成两道）--------
lane_z = 0.16
band_x = (half_x + 37.0 / 2.0) / 2.0
band_y = (half_y + 25.0 / 2.0) / 2.0
lanes = []
lanes.append(add_box(PREFIX + "Lane_VL", (0.10, 25.0, 0.02), (CX + band_x, CY, lane_z)))
lanes.append(add_box(PREFIX + "Lane_VR", (0.10, 25.0, 0.02), (CX - band_x, CY, lane_z)))
lanes.append(add_box(PREFIX + "Lane_HT", (37.0, 0.10, 0.02), (CX, CY + band_y, lane_z)))
lanes.append(add_box(PREFIX + "Lane_HB", (37.0, 0.10, 0.02), (CX, CY - band_y, lane_z)))
for o in lanes:
    while len(o.data.materials) < 1:
        o.data.materials.append(None)
    o.data.materials[0] = line_mat

# -------- 专用预览相机（东南 3/4 俯角框住全场）--------
cam_data = bpy.data.cameras.new(PREFIX + "Cam")
cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (16.0, 32.0, 22.0)
tgt = mathutils.Vector((CX, CY, 0.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 30.0
bpy.context.scene.camera = cam

# -------- 验证探针（顶层 result）--------
n_obj = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M38",
    "n_m38_objects": n_obj,
    "pitch_size": [31.0, 17.0],
    "track_size": [37.0, 25.0],
    "center": [CX, CY],
    "cam_loc": list(cam.location),
    "used_grass": grass is not None,
    "n_total_after": len(bpy.data.objects),
}
print("M38_RESULT=" + repr(result))
