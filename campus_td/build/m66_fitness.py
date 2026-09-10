# m66_fitness.py — M66 室外健身器材区（Outdoor Fitness / Calisthenics Area）
# 非破坏：仅新建 M66_ 前缀物体（橡胶地垫 + 双杠 + 单杠 + 肋木 + 指示牌 + 相机），幂等先清旧 M66_。
# 选址：网格探针确认校内唯一净空 = 东北草坪 (x≈33, y≈19)，临近 M62 凉亭花园；
#       脚本内嵌 placement 搜索（候选点 + SOLID 碰撞自检，margin 0.5），建筑再挪也贴合。
import bpy, mathutils, os

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "M66_"

# 仅物理结构参与避让（与 M65 同款集合）
SOLID = ("Bldg_","M11_","M14_","M16_","M17_","M37_","M38_","M39_","M40_","M41_",
         "M42_","M43_","M44_","M45_","M46_","M47_","M48_","M49_","M51_","M52_",
         "M53_","M54_","M55_","M56_","M57_","M58_","M59_","M60_","M61_","M62_",
         "M63_","M64_","M65_","M8_","Int_","Room_","Furn_","M19C_","M22_","M23_","M26_",
         "M27_","M28_","M29_","M30_","M31_","M32_","M33_","M34_","M35_","M36_",
         "Site_","Mat_","Road","M25_")

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
        xs = [c.x for c in corners]; ys = [c.y for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None

removed = clear_old(PREFIX)  # 幂等：先验清旧 M66_ 再建

def overlap(a, b, m):
    return not (a[2]+m < b[0] or b[2]+m < a[0] or a[3]+m < b[1] or b[3]+m < a[1])

def solid_hits(blk, margin):
    return [o.name for o in bpy.data.objects
            if o.name.startswith(SOLID) and world_aabb(o) and overlap(blk, world_aabb(o), margin)]

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

mat_metal = bpy.data.materials.get("PBR_Metal")
if mat_metal is None:
    mat_metal = make_pbr("PBR_Metal", (0.80, 0.80, 0.82), 0.35, 0.9)
# 深绿橡胶安全垫（复用校园运动场色调，但更深哑光）
mat_mat = make_pbr("M66_Mat", (0.09, 0.26, 0.15), 0.95, 0.0)
# 指示牌底板（深金属灰）
mat_sign = make_pbr("M66_SignBoard", (0.18, 0.20, 0.22), 0.6, 0.7)

def add_box(name, sx, sy, sz, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    o.data.materials.clear()
    o.data.materials.append(mat)
    return o

# ---- 选址搜索：优先探针确认的东北净空 ----
candidates = [(33.0,19.0),(36.0,20.0),(32.0,20.0),(36.0,40.0),(30.0,18.0),(24.0,-16.0)]
chosen = None
for (cxx,cyy) in candidates:
    if not solid_hits((cxx-5.5, cyy-3.5, cxx+5.5, cyy+3.5), 0.5):
        chosen = (cxx,cyy); break
if chosen is None:
    chosen = (33.0,19.0)   # 兜底
cx, cy = chosen
mat_blk = (cx-5.0, cy-3.0, cx+5.0, cy+3.0)
conflicts = solid_hits(mat_blk, 0.5)

# ---- 橡胶安全地垫 ----
add_box("M66_Mat", 10.0, 6.0, 0.06, (cx, cy, 0.04), mat_mat)
n_m66 = 1

# ---- 双杠（Parallel Bars）：2 横杠(沿 x) + 4 腿 ----
for lx in (cx-1.6, cx+1.6):
    for ly in (cy-0.4, cy+0.4):
        add_box("M66_PBarLeg_%d%d" % (1 if lx<cx else 2, 1 if ly<cy else 2), 0.07, 0.07, 1.10, (lx, ly, 0.55), mat_metal)
        n_m66 += 1
add_box("M66_PBarA", 3.4, 0.07, 0.07, (cx, cy-0.4, 1.10), mat_metal)
add_box("M66_PBarB", 3.4, 0.07, 0.07, (cx, cy+0.4, 1.10), mat_metal)
n_m66 += 2

# ---- 单杠（Horizontal Bar）：2 柱 + 1 横杠(沿 y) ----
add_box("M66_HBarPostL", 0.09, 0.09, 2.40, (cx+3.4, cy-1.0, 1.20), mat_metal)
add_box("M66_HBarPostR", 0.09, 0.09, 2.40, (cx+3.4, cy+1.0, 1.20), mat_metal)
add_box("M66_HBar", 0.07, 2.0, 0.07, (cx+3.4, cy, 2.20), mat_metal)
n_m66 += 3

# ---- 肋木（Stall Bars / 攀爬梯）：2 柱 + 5 横档 ----
add_box("M66_LadderPostL", 0.08, 0.08, 2.20, (cx-3.4, cy-0.4, 1.10), mat_metal)
add_box("M66_LadderPostR", 0.08, 0.08, 2.20, (cx-3.4, cy+0.4, 1.10), mat_metal)
n_m66 += 2
for i in range(5):
    z = 0.40 + i*0.40
    add_box("M66_LadderRung%d" % i, 0.06, 0.80, 0.06, (cx-3.4, cy, z), mat_metal)
    n_m66 += 1

# ---- 指示牌「健身区」（CJK，复用 M14 验证字体管线）----
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/simhei.ttf",
    r"C:/Windows/Fonts/Dengb.ttf",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simsun.ttc",
]
def pick_font():
    for f in FONT_CANDIDATES:
        if not os.path.exists(f):
            continue
        try:
            bpy.ops.object.text_add()
            t = bpy.context.active_object
            t.data.font = bpy.data.fonts.load(f)
            t.data.body = "健身区"
            t.data.size = 1.0
            bpy.context.view_layer.update()
            w = t.dimensions.x; h = t.dimensions.y
            bpy.data.objects.remove(t, do_unlink=True)
            if h >= 0.55 and w >= 0.55 * 1.5:
                return f
        except Exception:
            try:
                bpy.data.objects.remove(t, do_unlink=True)
            except Exception:
                pass
    return r"C:/Windows/Fonts/simhei.ttf"

font = pick_font()
add_box("M66_SignBoard", 2.4, 0.10, 1.05, (cx, cy-3.1, 1.32), mat_sign)
bpy.ops.object.text_add()
st = bpy.context.active_object
st.name = "M66_SignText"
st.data.font = bpy.data.fonts.load(font)
st.data.body = "健身区"
st.data.size = 0.55
st.data.materials.clear()
st.data.materials.append(make_pbr("M66_SignText", (0.95,0.95,0.90), 0.6, 0.0, emissive=0.35))
st.location = (cx, cy-3.1, 1.85)
st.rotation_euler = (1.5708, 0.0, 0.0)   # 本地 +Z 正面 → 朝 -Y（南），面向相机
n_m66 += 2

# ---- 相机（南侧 3/4 视角，看入器材区；指示牌朝南正对相机）----
bpy.ops.object.camera_add(location=(cx+5.0, cy-15.0, 7.0))
cam = bpy.context.active_object
cam.name = "M66_Cam"
cam.data.lens = 35.0
tgt = mathutils.Vector((cx, cy, 1.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
n_m66 += 1

result = {
    "n_removed_old": len(removed),
    "placed": [cx, cy],
    "conflicts": conflicts,
    "n_m66_objects": n_m66,
    "n_total": len(bpy.data.objects),
}
