# m67_speed_bumps.py — M67 校园主干道减速带（Campus Driveway Speed Bumps）
# 非破坏：仅新建 M67_ 前缀物体（橡胶减速带 + 黄色顶面 + 相机），幂等先清旧 M67_。
# 沿现有 Road/Road.001/Road.002 路面长边中段铺设；与 M50 自行车道、M58 蓝色边线互补。
import bpy, mathutils, os, math

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "M67_"

def clear_old(prefix):
    removed = []
    names = [o.name for o in bpy.data.objects if o.name.startswith(prefix)]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None:
            continue
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
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        return (min(xs), min(ys), max(xs), max(ys), max(zs))
    except Exception:
        return None

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

def add_box(name, sx, sy, sz, loc, mat, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    o.rotation_euler = rot
    o.data.materials.clear()
    o.data.materials.append(mat)
    return o

# 实体足迹（楼体/塔）：仅纳入 z_max>1.0m 的高大遮挡物，排除 M11_PlazaCourt/M7_Path 等
# 全园扁平地坪（高度≈0）假阳性；刻意排除 M25/M50/M51/M58 等 campus-wide 虚假大盒。
def solid_footprints():
    pre = ("Bldg_", "M7_", "M11_")
    fps = []
    for o in bpy.data.objects:
        if not any(o.name.startswith(p) for p in pre):
            continue
        if o.bound_box is None:
            continue
        a = world_aabb(o)
        if a is None:
            continue
        dx = a[2] - a[0]; dy = a[3] - a[1]
        if dx > 70 or dy > 70:       # 跳过 campus-wide 合并大盒
            continue
        if (a[4] - min(c[2] for c in [o.matrix_world @ mathutils.Vector(v) for v in o.bound_box])) < 1.0:
            continue                  # 扁平地坪不遮挡
        fps.append((o.name, a[0], a[1], a[2], a[3], a[4]))
    return fps

def hump_blocked(x, y, fps):
    for nm, minx, miny, maxx, maxy, maxz in fps:
        if minx - 0.5 <= x <= maxx + 0.5 and miny - 0.5 <= y <= maxy + 0.5:
            return nm
    return None

removed = clear_old(PREFIX)

mat_base = make_pbr("M67_BumpBase", (0.06, 0.06, 0.06), 0.92, 0.0)       # 黑色橡胶底
# 黄色顶面：低自发光（0.6）——刚好在白昼阳光下读作醒目黄，又不至于被 AgX
# 高光压缩冲淡成白绿；漫反射颜色也保持高饱和。
mat_top  = make_pbr("M67_BumpTop",  (0.95, 0.72, 0.02), 0.55, 0.0, emissive=0.6)  # 黄色防滑顶

roads = [o for o in bpy.data.objects if o.name.startswith("Road") and world_aabb(o)]
humps = []
for idx, rd in enumerate(roads):
    a = world_aabb(rd)
    minx, miny, maxx, maxy, maxz = a
    dx = maxx - minx
    dy = maxy - miny
    cx = (minx+maxx)/2.0
    cy = (miny+maxy)/2.0
    road_z = maxz
    if dx >= dy:
        # 路段沿 x
        width = dy
        length = dx
        angle = 0.0
        road_dir = mathutils.Vector((1.0, 0.0, 0.0))
    else:
        # 路段沿 y
        width = dx
        length = dy
        angle = math.pi/2.0
        road_dir = mathutils.Vector((0.0, 1.0, 0.0))
    if width < 1.0 or length < 2.0:
        continue
    # 每段路在中点铺一条减速带
    hlen = 1.60
    hwid = max(width - 0.20, 1.50)
    hbase_z = road_z + 0.06
    htop_z  = road_z + 0.13
    add_box("M67_BumpBase_%d" % idx, hlen/2.0, hwid/2.0, 0.06/2.0,
            (cx, cy, hbase_z), mat_base, rot=(0.0, 0.0, angle))
    add_box("M67_BumpTop_%d" % idx, hlen*0.85/2.0, hwid*0.80/2.0, 0.06/2.0,
            (cx, cy, htop_z), mat_top, rot=(0.0, 0.0, angle))
    humps.append({"idx": idx, "center": (cx, cy, road_z), "dir": (road_dir.x, road_dir.y), "width": width})

# 兜底：若没找到 Road 则在西段补一条
if not humps:
    add_box("M67_BumpBase_0", 1.6/2.0, 3.0/2.0, 0.06/2.0, (-31.0, -14.0, 0.13), mat_base, rot=(0,0,0))
    add_box("M67_BumpTop_0", 1.36/2.0, 2.4/2.0, 0.06/2.0, (-31.0, -14.0, 0.19), mat_top, rot=(0,0,0))
    humps.append({"idx": 0, "center": (-31.0, -14.0, 0.12), "dir": (1.0, 0.0), "width": 3.0})

# ---- 选址相机：俯视 z=8，选南段减速带（-2,-13）作为 hero 主体 --------------
# 教训（M67 调试）：低 3/4 在密集校园里极易把相机塞进自行车棚/看台之间；
# 俯视则构图稳定，只需在渲染时临时隐藏头顶 clutter（看台/敌人/血条/M7_Path 路径），
# 非破坏地让减速带在沥青路面上完整可见。这里只建相机，隐藏由 m67_render.py 负责。
best = min(humps, key=lambda h: h["center"][1])   # 南段（y 最小）
hx, hy, hz = best["center"]
cam_loc = mathutils.Vector((hx, hy, 5.0))
bpy.ops.object.camera_add(location=tuple(cam_loc))
cam = bpy.context.active_object
cam.name = "M67_Cam"
cam.data.lens = 35.0
tgt = mathutils.Vector((hx, hy, hz + 0.05))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()

n_m67 = 1 + len(humps) * 2
result = {
    "n_removed_old": len(removed),
    "n_humps": len(humps),
    "humps": humps,
    "best_center": best["center"],
    "best_blocked_by": best.get("blocked_by"),
    "n_m67_objects": n_m67,
    "n_total": len(bpy.data.objects),
}
