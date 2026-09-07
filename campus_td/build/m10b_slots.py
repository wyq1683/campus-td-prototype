# m10b_slots.py — M10B：把 M10 设计文档里的 4 个「玩家建塔位」落到 Blender 场景
#
# 数据来源：campus_td/build/m10_config.json（由 m10_balance.py --export 生成）
#   SLOT_A (-3,-13) 覆盖 6-32   → 补南盲区
#   SLOT_B (-3, 13) 覆盖 70-93  → 补北盲区
#   SLOT_C (16,  0) 覆盖 38-64  → 东腿杀区
#   SLOT_D (-11,13) 覆盖 78-102 → 基地前最后防线
#
# 重要：设计坐标在**路径中心线**上（1D 弧长模型），但塔不能立在敌人走的路中间。
# 因此统一沿路径法向偏移 4.5m 到 U 形内侧（庭院）。经核算，半径 13m 的圆与
# 路径直线求交，每端仅损失约 0.8m 覆盖（如 SLOT_A：6-32m → 6.8-31.2m），
# 与仿真模型一致，可直接使用。
#
# 幂等：PREFIX = "M10B_"，只清同前缀旧物体再重建。
# 用法：exec(compile(open(r".../m10b_slots.py").read(), "m10b", "exec"))
#       build_slots()

import bpy
import math

PREFIX = "M10B_"
RANGE_R = 13.0
OFFSET = 4.5          # 法向偏移量（内侧）
DASH_N = 16           # 虚线环段数
PAD_R = 2.2           # 建造台半径
PAD_H = 0.14

# 名称 → (路径上的设计坐标, 法向偏移方向, 覆盖弧长, 说明)
SLOTS = [
    ("SLOT_A", (-3.0, -13.0), (0.0, +1.0), (6.0, 32.0),  "补南盲区"),
    ("SLOT_B", (-3.0, 13.0),  (0.0, -1.0), (70.0, 93.0), "补北盲区"),
    ("SLOT_C", (16.0, 0.0),   (-1.0, 0.0), (38.0, 64.0), "东腿杀区"),
    ("SLOT_D", (-11.0, 13.0), (0.0, -1.0), (78.0, 102.0), "基地前最后防线"),
]

# 「可建造空地」配色：青绿 = 空位可建
C_PAD = (0.16, 0.85, 0.68, 1.0)
C_DASH = (0.20, 0.95, 0.78, 1.0)
C_MARK = (0.35, 1.00, 0.85, 1.0)


# ===========================================================================
def clear_old():
    """只删 M10B_ 前缀的旧物体。先取 name 再 remove，避免 ReferenceError。"""
    removed = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
            del nm
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return removed


def _mat(name, rgba, emission=1.2, alpha=1.0):
    """自发光材质（Principled BSDF 按 type 找，兼容不同 Blender 版本）。"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)

    if alpha < 1.0:
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.location = (80, 0)
        trans = nt.nodes.new("ShaderNodeBsdfTransparent")
        trans.location = (-120, -120)
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (-120, 120)
        nt.links.new(trans.outputs["BSDF"], mix.inputs[1])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[2])
        mix.inputs["Fac"].default_value = 1.0 - alpha
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    else:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bsdf.inputs["Base Color"].default_value = rgba
    try:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    except Exception:
        pass
    if alpha < 1.0:
        try:
            bsdf.inputs["Alpha"].default_value = alpha
        except Exception:
            pass
    mat.blend_method = "BLEND" if alpha < 1.0 else "OPAQUE"
    return mat


def _add(obj, mat=None):
    """只挂材质。注意：bpy.ops.mesh.primitive_*_add 已自动把对象链接到活动集合，
    再调 collection.objects.link 会报"已在集合里"。"""
    obj.data.materials.append(mat)
    return obj


def build_slots():
    clear_old()
    made = []

    mat_pad = _mat(PREFIX + "Pad", C_PAD, emission=0.9, alpha=0.55)
    mat_dash = _mat(PREFIX + "Dash", C_DASH, emission=1.6, alpha=0.85)
    mat_mark = _mat(PREFIX + "Marker", C_MARK, emission=2.4)

    for sname, (px, py), (nx, ny), cover, desc in SLOTS:
        tx, ty = px + nx * OFFSET, py + ny * OFFSET   # 偏移后的塔位

        # ---- 1. 建造台（矮圆柱）----
        bpy.ops.mesh.primitive_cylinder_add(
            radius=PAD_R, depth=PAD_H, vertices=32, location=(tx, ty, PAD_H / 2.0))
        pad = bpy.context.active_object
        pad.name = PREFIX + sname + "_Pad"
        _add(pad, mat_pad)
        pad["m10b_slot"] = sname
        pad["m10b_cover"] = list(cover)
        pad["m10b_desc"] = desc
        made.append(pad.name)

        # ---- 2. 台面内圈实线（提示可建范围）----
        bpy.ops.mesh.primitive_torus_add(
            major_radius=PAD_R - 0.15, minor_radius=0.07,
            major_segments=40, minor_segments=8,
            location=(tx, ty, PAD_H + 0.02))
        ring = bpy.context.active_object
        ring.name = PREFIX + sname + "_PadRing"
        _add(ring, mat_dash)
        made.append(ring.name)

        # ---- 3. 射程虚线环（半径 13m，16 段）----
        # 每段 box 长轴沿切线：rotation.z = θ + π/2
        for i in range(DASH_N):
            th = 2.0 * math.pi * i / DASH_N
            dx, dy = RANGE_R * math.cos(th), RANGE_R * math.sin(th)
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(tx + dx, ty + dy, 0.10))
            d = bpy.context.active_object
            d.name = "%s%s_Dash%02d" % (PREFIX, sname, i)
            d.scale = (2.0, 0.22, 0.10)
            d.rotation_euler = (0.0, 0.0, th + math.pi / 2.0)
            _add(d, mat_dash)
            made.append(d.name)

        # ---- 4. 悬浮标记（八面体，提示"此处可建"）----
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.55, radius2=0.0, depth=1.1, vertices=4,
            location=(tx, ty, 3.0))
        mk = bpy.context.active_object
        mk.name = PREFIX + sname + "_Marker"
        mk.rotation_euler = (math.pi, 0.0, math.pi / 4.0)   # 尖朝下
        _add(mk, mat_mark)
        made.append(mk.name)

        print("[m10b] %-7s 设计位(%.1f,%.1f) → 实际(%.1f,%.1f) 覆盖 %.0f-%.0fm  %s"
              % (sname, px, py, tx, ty, cover[0], cover[1], desc))

    print("[m10b] 新建对象 %d 个，场景合计 %d" % (len(made), len(bpy.data.objects)))
    return dict(total_new=len(made), scene=len(bpy.data.objects))
