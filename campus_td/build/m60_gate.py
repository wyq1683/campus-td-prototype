# -*- coding: utf-8 -*-
"""
M60 · 校门电动伸缩门 (Retractable Gate at School Entrance)
============================================================================
项目已收官（M0–M59 ✅）。按「无未完成里程碑时自行增加改进项」新增 M60：
校门仪式带（匾文 M14 → 校旗 M37 → 门卫室 M52 → 校训碑 M54 → 花池 M55 →
校徽 M59）之外，南向校门虽有 M11 立柱+横梁+匾文「框架」，但两柱之间 x∈[-6.3,6.3]
仍是敞开的、没有实体门——不像能开关的校门。本里程碑在两柱之间补一座电动
伸缩门（一排竖向金属栅条 + 上下横杆，覆盖闭合段，保留右侧伸缩开口）+ 右柱内侧
电机箱，让"进门"动作有可见的边界。

选址（M11 之后铁律，禁止硬编码）：
  - 真实洞口左右沿从 M11_GatePillar-1 / M11_GatePillar1 世界 AABB 动态读取
    （实测左柱右沿 x=-6.3、右柱左沿 x=+6.3、柱中线 y≈-47.4、柱顶 z=6.0）。
  - 做楼体/校门 AABB 碰撞自检（z 真正与门体 [0,1.5] 重叠才算）：立柱/横梁/
    匾文都高于门体，不会误判；若闭合段内确有低位实体则向右收窄（兜底）。

设计（原型级、静态金属门、零破坏其它物体）：
  - 伸缩栅条（一排竖向金属圆杆 + 上/中/下横杆，合并为单 mesh，覆盖闭合段
    x∈[-6.0, 2.8]，保留 x∈[2.8, 6.0] 为伸缩开口）。
  - 电机箱（右柱内侧基座，石质箱）。
  - M11 已有立柱/横梁/匾文保留不动（本门只填空缺的「扇」）。

避坑（沿用 PLAN.md + M59 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 primitive + bmesh 直建，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M60_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector

PREFIX = "M60_"

# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs), max(c.x for c in cs),
            min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs)]


def clear_old():
    n = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
    for me in list(bpy.data.meshes):
        if me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def new_mat(name, base, rough, metal=0.0, emit=0.0, emit_col=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.get("Material Output")
        if out:
            m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = base + (1.0,)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit > 0.0 and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (emit_col or base) + (1.0,)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


# ---------------------------------------------------------------- 选址
left_p = bpy.data.objects.get("M11_GatePillar-1")
right_p = bpy.data.objects.get("M11_GatePillar1")
if left_p is not None and right_p is not None:
    bl = aabb(left_p)
    br = aabb(right_p)
    xL = bl[1]                 # 左柱右沿 ≈ -6.3
    xR = br[0]                 # 右柱左沿 ≈ 6.3
    yWall = (bl[2] + bl[3]) / 2.0   # 柱中线 ≈ -47.4
    pillar_top = max(bl[5], br[5])
else:
    # 兜底硬编码（极少触发）
    xL, xR, yWall, pillar_top = -6.3, 6.3, -47.4, 6.0

OPEN_W = xR - xL              # 洞口宽 ≈ 12.6m
GATE_Y = yWall

CHECK_PREFIXES = ("Bldg_", "M11_Gate", "M11_Wall", "M59_", "M54_", "M55_",
                  "M52_", "M14_", "M43_", "M58_", "M48_", "M49_",
                  "M44_", "M50_", "M46_", "M47_", "M42_", "M40_", "M39_",
                  "M41_", "M38_")
# 注：M51_（绿篱/花箱）是沿墙合并单 mesh，其 AABB 跨过校门洞但几何刻意跳过
#     洞口，不会与门体相交，故不参与碰撞自检（避免合并 AABB 误判）。


def overlaps_box(x0, x1, y0, y1, z0=0.0, z1=1.6):
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if not o.name.startswith(CHECK_PREFIXES):
            continue
        b = aabb(o)
        if b is None:
            continue
        # z 范围必须真正与门体(z∈[0,1.5])重叠；立柱/横梁/匾文(z>1.6)不算
        if b[5] < z0 or b[4] > z1:
            continue
        if x0 < b[1] and x1 > b[0] and y0 < b[3] and y1 > b[2]:
            return o.name
    return None


# 闭合段：覆盖洞口左大半，右侧留伸缩开口
closed_x0 = xL + 0.3
closed_x1 = xL + OPEN_W * 0.72
collide = overlaps_box(closed_x0, closed_x1, GATE_Y - 0.7, GATE_Y + 0.7, 0.0, 1.6)
shrink = 0
while collide and (closed_x1 - closed_x0) > 4.0:
    closed_x1 -= 0.5
    shrink += 1
    collide = overlaps_box(closed_x0, closed_x1, GATE_Y - 0.7, GATE_Y + 0.7, 0.0, 1.6)

placement = {"xL": round(xL, 2), "xR": round(xR, 2), "yWall": round(yWall, 2),
             "pillarTop": round(pillar_top, 2), "closed_x0": round(closed_x0, 2),
             "closed_x1": round(closed_x1, 2), "shrink": shrink, "collide": collide}

# ---------------------------------------------------------------- 清旧 + 材质
# ⚠ 必须在创建材质【之前】clear_old()：否则刚建的 M60_ 材质会被清掉（M18 同坑）。
n_removed = clear_old()
stone = new_mat(PREFIX + "Stone", (0.46, 0.45, 0.43), 0.85, 0.0)        # 电机箱 混凝土
metal = new_mat(PREFIX + "Metal", (0.62, 0.64, 0.66), 0.38, 1.0)         # 栅条 不锈钢

# ---------------------------------------------------------------- 主构建
# 1) 伸缩栅条（+ 上/中/下横杆），合并为单 mesh
bm = bmesh.new()
bar_r = 0.04
bar_h = 1.5
bar_z = bar_h / 2.0
n_bars = 0
x = closed_x0
while x <= closed_x1 + 1e-6:
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=8,
                                radius1=bar_r, radius2=bar_r, depth=bar_h)
    for v in ret["verts"]:
        v.co.x += x
        v.co.y += GATE_Y
        v.co.z += bar_z
    n_bars += 1
    x += 0.42
# 横杆：上(z=1.42)/中(z=0.75)/下(z=0.10)
gate_w = closed_x1 - closed_x0
gate_cx = (closed_x0 + closed_x1) / 2.0
for rz, rh, rd in ((1.42, 0.12, 0.10), (0.75, 0.08, 0.08), (0.10, 0.10, 0.10)):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    for v in ret["verts"]:
        v.co.x = v.co.x * gate_w + gate_cx
        v.co.y = v.co.y * rd + GATE_Y
        v.co.z = v.co.z * rh + rz
gate_me = bpy.data.meshes.new(PREFIX + "GateMesh")
bm.to_mesh(gate_me)
bm.free()
gate = bpy.data.objects.new(PREFIX + "Gate", gate_me)
gate.location = (0.0, 0.0, 0.0)
gate.data.materials.clear()
gate.data.materials.append(metal)
bpy.context.collection.objects.link(gate)

# 2) 电机箱（右柱内侧基座，清晰不挡门体）
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(xR - 0.6, GATE_Y, 0.9))
mb = bpy.context.active_object
mb.name = PREFIX + "Motor"
mb.scale = (1.0, 0.6, 1.0)
mb.data.materials.clear()
mb.data.materials.append(stone)

# 3) 验证相机（校门外南向，看入门框+伸缩门）
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is None:
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    bpy.context.collection.objects.link(cam)
cam.data.lens = 35.0
cam.location = (0.0, yWall - 16.0, 4.5)
look = Vector((0.0, yWall, 1.5))
cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染设定
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    try:
        sc.cycles.compute_device_type = "OPTIX"
    except Exception:
        pass
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0
except Exception:
    pass

n_m60 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M60",
    "ok": True,
    "n_removed_old": n_removed,
    "placement": placement,
    "n_bars": n_bars,
    "n_m60_objects": n_m60,
    "n_total_objects": len(bpy.data.objects),
}
print("M60_RESULT=" + repr(result))
