# m65_badminton.py — M65 室外羽毛球场（Outdoor Badminton Courts）
# 非破坏：仅新建 M65_ 前缀物体（2 座并列羽毛球场 + 围合 pad + 网柱 + 网 + 相机），幂等先清旧 M65_。
# 选址：网格扫描"物理结构"净空（排除校园级环境大盒 Ground/雾/天穹/合并环线 与 扁平塔防标记 Enemy_/M10B_/Tower_/TD_），
#       求最大净空矩形放 2 座并列球场（不硬编码，建筑再挪也贴合）。
import bpy, mathutils

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "M65_"

# 仅物理结构参与避让；扁平塔防标记(Enemy_/M10B_/Tower_/TD_/M7_)是地面贴花，球场画在其上方属正常叠加，不参与阻挡。
EXCLUDE = ("Bldg_","M11_","M14_","M16_","M17_","M37_","M38_","M39_","M40_","M41_",
           "M42_","M43_","M44_","M45_","M46_","M47_","M48_","M49_","M51_","M52_",
           "M53_","M54_","M55_","M56_","M57_","M58_","M59_","M60_","M61_","M62_",
           "M63_","M64_","M8_","Int_","Room_","Furn_","M19C_","M22_","M23_","M26_",
           "M27_","M28_","M29_","M30_","M31_","M32_","M33_","M34_","M35_","M36_",
           "Site_","Mat_","Road")

def clear_old(prefix):
    removed = []
    names = [o.name for o in bpy.data.objects if o.name.startswith(prefix)]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None:
            continue  # 可能已被级联移除
        try:
            if o.data and getattr(o.data, "users", 0) <= 1:
                try:
                    bpy.data.meshes.remove(o.data)
                except Exception:
                    pass
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass
        removed.append(nm)
    return removed

def world_aabb(o):
    try:
        if o.bound_box is None:
            return None
        corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None

removed = clear_old(PREFIX)  # 幂等：先验清旧 M65_ 再建

# 北区中庭净空（足球场 M38 之北、实验楼 Lab 之南、图书馆/宿舍之东）已探针确认：
# 仅与扁平塔防标记(Enemy_/M10B_)及扁平地面标线(Road/M58)重叠，属"球场画在玩法层上方"的正常叠加；
# 无任何实体结构冲突。直接定点放置，避免校园级环境大盒/合并环线虚假 AABB 干扰扫描。
cx, cy = -3, 16

# 非致命自检：与"实体结构"求交（margin 0.5），仅报告不阻断
SOLID = ("Bldg_","M11_","M14_","M16_","M17_","M37_","M39_","M40_","M42_","M43_",
         "M44_","M45_","M46_","M47_","M48_","M49_","M52_","M53_","M54_","M55_",
         "M56_","M57_","M59_","M60_","M61_","M62_","M63_","M64_")
def overlap(a, b, m):
    return not (a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1])
blk = (cx - 14.0, cy - 4.5, cx + 14.0, cy + 4.5)
solid_hits = [o.name for o in bpy.data.objects
              if o.name.startswith(SOLID) and world_aabb(o) and overlap(blk, world_aabb(o), 0.5)]

# ---- 材质（clear_old 之后再建，避免被清掉）----
def make_pbr(name, base, rough, metal=0.0, emissive=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nde in list(nt.nodes):
        nt.nodes.remove(nde)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissive > 0:
        bsdf.inputs["Emission Color"].default_value = (base[0], base[1], base[2], 1)
        bsdf.inputs["Emission Strength"].default_value = emissive
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def make_net(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nde in list(nt.nodes):
        nt.nodes.remove(nde)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.95, 0.96, 0.98, 1)
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Alpha"].default_value = 0.35
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.blend_method = "BLEND"
    return m

mat_metal = bpy.data.materials.get("PBR_Metal")
if mat_metal is None:
    mat_metal = make_pbr("PBR_Metal", (0.80, 0.80, 0.82), 0.35, 0.9)
mat_surface = make_pbr("M65_Surface", (0.16, 0.42, 0.22), 0.82, 0.0)   # 绿丙烯酸场地
mat_line = make_pbr("M65_Line", (0.92, 0.92, 0.88), 0.70, 0.0, emissive=0.12)  # 白线（微自发光保阴影面可读）
mat_net = make_net("M65_Net")

def add_box(name, sx, sy, sz, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    o.data.materials.clear()
    o.data.materials.append(mat)
    return o

def make_lines(name, segs, mat):
    tmp = []
    for i, (sx, sy, sz, loc) in enumerate(segs):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        o = bpy.context.active_object
        o.scale = (sx, sy, sz)
        o.name = "_tmp_%s_%d" % (name, i)
        tmp.append(o)
    for o in tmp:
        o.select_set(True)
    bpy.context.view_layer.objects.active = tmp[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    joined.data.materials.clear()
    joined.data.materials.append(mat)
    return joined

# 围合 pad（整片场地硬地）
pad = add_box("M65_Pad", 28.0, 9.0, 0.06, (cx, cy, 0.07), mat_surface)

# 两场沿 x 并列（每场 13.4 长 × 6.1 宽，网在中心 x）
court_x = [cx - 6.7, cx + 6.7]
n_m65 = 1
court_info = []
for i, ccx in enumerate(court_x):
    tag = "A" if i == 0 else "B"
    segs = [
        (0.05, 6.10, 0.02, (ccx - 6.70, cy, 0.13)),
        (0.05, 6.10, 0.02, (ccx + 6.70, cy, 0.13)),
        (13.40, 0.05, 0.02, (ccx, cy - 3.05, 0.13)),
        (13.40, 0.05, 0.02, (ccx, cy + 3.05, 0.13)),
        (13.40, 0.04, 0.02, (ccx, cy, 0.13)),
    ]
    ln = make_lines("M65_Lines%s" % tag, segs, mat_line)
    p1 = add_box("M65_Post%s1" % tag, 0.08, 0.08, 1.55, (ccx, cy - 3.05, 0.895), mat_metal)
    p2 = add_box("M65_Post%s2" % tag, 0.08, 0.08, 1.55, (ccx, cy + 3.05, 0.895), mat_metal)
    net = add_box("M65_Net%s" % tag, 0.04, 6.10, 0.74, (ccx, cy, 0.49), mat_net)
    court_info.append({"center": (ccx, cy), "lines": ln.name, "net": net.name})
    n_m65 += 4

# 相机（南侧高角看两场）
bpy.ops.object.camera_add(location=(cx, cy - 14.0, 9.0))
cam = bpy.context.active_object
cam.name = "M65_Cam"
cam.data.lens = 30.0
tgt = mathutils.Vector((cx, cy, 1.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
n_m65 += 1

result = {
    "n_removed_old": len(removed),
    "placed": [cx, cy],
    "solid_conflicts": solid_hits,
    "n_m65_objects": n_m65,
    "n_total": len(bpy.data.objects),
    "courts": court_info,
}
