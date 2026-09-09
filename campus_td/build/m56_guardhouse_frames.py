# -*- coding: utf-8 -*-
"""
M56 · 校门卫室窗框与门框细化 (Gate Guardhouse Window/Door Frame Detail)
==========================================================================
项目已收官（M0–M55 ✅）。按「无未完成里程碑时自行增加改进项」新增 M56：
M55 的"下一步"建议首项 = 校门卫室窗框细化。M52 的门卫室窗/门只有平板玻璃 + 木门，
没有窗框/门套，显得"贴"在墙上。本里程碑给窗与门各加一套混凝土框（窗框四边 + 窗台 +
竖向窗棂；门套两侧门垛 + 门楣 + 门槛），让它像真的嵌进墙里，提升校门仪式带的完成度。

坐标（M11 之后铁律，禁止硬编码）：
  - 全部从场景里当前 M52_Window / M52_Door 对象的世界 AABB 动态读取，
    不依赖 M52 脚本里的常量。M52 物体若不存在则优雅跳过（不报错）。

设计（原型级，无 Boolean、无 mode_set，全 box 面板拼装，铁律安全）：
  - 窗框：4 条边条（左/右/上/下）+ 下方窗台（略宽略厚）+ 1 道竖向窗棂（十字格 realism）。
    颜色比墙体略深（M56_Frame 暖灰），与 M52 浅灰混凝土形成层次。
  - 门套：2 侧门垛（jamb）+ 门楣横梁（lintel）+ 门槛（threshold），同 M56_Frame。
  - 仅新建 M56_ 前缀物体，零破坏其它物体；幂等：先清旧 M56_ 再建。

避坑（沿用 PLAN.md + M43..M55 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M56_，绝不 select_all+delete。
  - Blender 5.2 Principled 输入名 Base Color / Metallic / Roughness（材质全程序化）。
"""
import bpy
import bmesh
from mathutils import Vector, Matrix

PREFIX = "M56_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"


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


def get_mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            bsdf.inputs["Metallic"].default_value = metal
            bsdf.inputs["Roughness"].default_value = rough
            # 加一点表面变化，避免纯色假面
            try:
                tex = m.node_tree.nodes.new("ShaderNodeTexNoise")
                tex.inputs["Scale"].default_value = 24.0
                tex.inputs["Detail"].default_value = 6.0
                ramp = m.node_tree.nodes.new("ShaderNodeValToRGB")
                ramp.color_ramp.elements[0].position = 0.42
                ramp.color_ramp.elements[1].position = 0.58
                m.node_tree.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
                mix = m.node_tree.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                m.node_tree.links.new(ramp.outputs["Color"], mix.inputs["B"])
                m.node_tree.links.new(bsdf.inputs["Base Color"], mix.inputs["Result"])
                mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
                mix.inputs["Factor"].default_value = 0.25
            except Exception:
                pass
    return m


def add_box(name, cx, cy, cz, sx, sy, sz, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Diagonal((sx, sy, sz, 1.0)))
    bm.transform(Matrix.Translation((cx, cy, cz)))
    me = bpy.data.meshes.new(PREFIX + name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(PREFIX + name, me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 主构建
n_removed = clear_old()
FRAME = get_mat(PREFIX + "Frame", (0.52, 0.52, 0.50), 0.0, 0.82)  # 略深暖灰窗/门套

win = bpy.data.objects.get("M52_Window")
door = bpy.data.objects.get("M52_Door")
parts = []

# ---- 窗框：四边 + 窗台 + 竖向窗棂 ----
if win is not None:
    w = aabb(win)
    wx0, wx1 = w[0], w[1]      # x 范围
    wy = w[3]                  # 前脸 y（max）
    wz0, wz1 = w[4], w[5]      # z 范围
    fw = 0.08                  # 边条 x 厚
    fd = 0.10                  # 边条 y 进深（向外凸）
    ft = 0.07                  # 上下边条 z 厚
    cyf = wy + fd / 2.0 - 0.02  # 框中心 y（略外凸于玻璃）
    cxw = (wx0 + wx1) / 2.0
    czw = (wz0 + wz1) / 2.0
    wh = wz1 - wz0
    # 左条
    add_box("WinFrameL", wx0 - fw / 2.0 - 0.01, cyf, czw, fw, fd, wh + 2 * ft, FRAME)
    # 右条
    add_box("WinFrameR", wx1 + fw / 2.0 + 0.01, cyf, czw, fw, fd, wh + 2 * ft, FRAME)
    # 上条
    add_box("WinFrameT", cxw, cyf, wz1 + ft / 2.0, (wx1 - wx0) + 2 * fw + 0.02, fd, ft, FRAME)
    # 下条（窗台，略宽略厚）
    add_box("WinSill", cxw, cyf, wz0 - 0.06, (wx1 - wx0) + 2 * fw + 0.10, fd + 0.04, 0.12, FRAME)
    # 竖向窗棂（十字格）
    add_box("WinMullV", cxw, cyf, czw, 0.04, fd, wh + 2 * ft, FRAME)
    # 横向窗棂
    add_box("WinMullH", cxw, cyf, czw, (wx1 - wx0) + 2 * fw, fd, 0.04, FRAME)
    parts.append("window_frame")

# ---- 门套：两侧门垛 + 门楣 + 门槛 ----
if door is not None:
    d = aabb(door)
    dx0, dx1 = d[0], d[1]
    dy = d[3]
    dz0, dz1 = d[4], d[5]
    fj = 0.09                  # 门垛 x 厚
    fd2 = 0.13                 # 门垛 y 进深
    cyd = dy + fd2 / 2.0 - 0.03
    cxdoor = (dx0 + dx1) / 2.0
    opw = (dx1 - dx0) + 2 * fj  # 门洞宽（含门垛）
    oph = dz1 - dz0            # 门洞高
    # 左门垛
    add_box("DoorJambL", dx0 - fj / 2.0, cyd, (dz0 + dz1) / 2.0, fj, fd2, oph + 0.10, FRAME)
    # 右门垛
    add_box("DoorJambR", dx1 + fj / 2.0, cyd, (dz0 + dz1) / 2.0, fj, fd2, oph + 0.10, FRAME)
    # 门楣横梁
    add_box("DoorLintel", cxdoor, cyd, dz1 + 0.06, opw, fd2, 0.12, FRAME)
    # 门槛
    add_box("DoorThresh", cxdoor, cyd, 0.06, opw, fd2 + 0.04, 0.12, FRAME)
    parts.append("door_frame")

# ---------------------------------------------------------------- 相机
cam = bpy.data.objects.get("M52_Cam")
hero = bpy.data.objects.get("M19C_HeroDay")
if cam is not None:
    cam.location = (cam.location.x, cam.location.y, 1.7)
    cam.data.lens = 35.0
    bpy.context.view_layer.update()

# ---------------------------------------------------------------- 渲染（Cycles GPU OptiX）
sc = bpy.context.scene
os.makedirs(PREVIEW_DIR, exist_ok=True)
rendered = []
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
    # 1) 校园语境（英雄机位）
    if hero is not None:
        sc.camera = hero
        sc.render.filepath = PREVIEW_DIR + "/m56_guardhouse_frames_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
    # 2) 门卫室特写（加临时补光，结束后清理零孤儿）
    if cam is not None:
        sc.camera = cam
        fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
        fill.energy = 120.0
        fill.color = (1.0, 0.96, 0.88)
        fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
        fill_obj.location = cam.location + Vector((0.0, 0.0, 0.5))
        bpy.context.scene.collection.objects.link(fill_obj)
        bpy.context.view_layer.update()
        sc.render.filepath = PREVIEW_DIR + "/m56_guardhouse_frames_closeup.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
        bpy.data.objects.remove(fill_obj, do_unlink=True)
        bpy.data.lights.remove(fill)
    if hero is not None:
        sc.camera = hero
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

# ---------------------------------------------------------------- 统计
n_m56 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M56",
    "ok": True,
    "n_removed_old": n_removed,
    "n_m56_objects": n_m56,
    "n_total_objects": len(bpy.data.objects),
    "window_present": win is not None,
    "door_present": door is not None,
    "parts_built": parts,
    "rendered": rendered,
}
print("M56_RESULT=" + repr(result))
