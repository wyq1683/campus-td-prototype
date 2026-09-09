# m41_bleachers.py — 里程碑 M41 · 室外运动场看台与替补席 (OptiX)
# 非破坏：仅新建 M41_ 前缀物体；幂等：先清旧 M41_ 再建。
# 坐标沿用 M38/M39/M40 中央广场球场：中心 (CX,CY)=(-3,0)，半宽15/半深8.5。
import bpy, bmesh, math
from mathutils import Vector

PREFIX = "M41_"
CX, CY = -3.0, 0.0          # 球场中心（与 M38/M39/M40 一致）
FIELD_HALF_W, FIELD_HALF_D = 15.0, 8.5   # 球场半宽/半深

def clear_old(prefix):
    removed = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            nm = o.name
            if o.data and o.data.users <= 1:
                try: o.data.user_clear()
                except Exception: pass
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
    return removed

def get_mat(name, fallback_rgb):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.get("Principled_BSDF")
    if not bsdf:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bsdf = n; break
    if bsdf and "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = fallback_rgb + (1.0,)
    return m

def add_box(name, size, loc, mat, rot=(0,0,0)):
    x,y,z = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.scale = (x, y, z)
    obj.location = Vector(loc)
    obj.rotation_euler = rot
    if mat: obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj

# ---- 材质（优先复用已有 PBR，否则自建灰色混凝土/木/金属）----
mat_concrete = get_mat("PBR_Concrete", (0.62,0.62,0.60)) if "PBR_Concrete" in bpy.data.materials else get_mat(PREFIX+"Concrete", (0.62,0.62,0.60))
mat_wood     = get_mat("PBR_Wood", (0.42,0.28,0.16)) if "PBR_Wood" in bpy.data.materials else get_mat(PREFIX+"Wood", (0.42,0.28,0.16))
mat_metal    = get_mat("PBR_Metal", (0.30,0.32,0.34)) if "PBR_Metal" in bpy.data.materials else get_mat(PREFIX+"Metal", (0.30,0.32,0.34))
mat_roof     = get_mat(PREFIX+"Roof", (0.18,0.20,0.22))
mat_seat     = get_mat(PREFIX+"Seat", (0.20,0.45,0.55))

n_removed = clear_old(PREFIX)
built = []

# ---- 两侧阶梯看台（北 y+、南 y-）----
SIDES = [1.0, -1.0]          # 北/南
N_ROWS = 5
ROW0_Y = 9.5                  # 第一排前缘距球场中心(沿 y)
STEP_D = 0.72                 # 每排进深
ROW_H  = 0.6                  # 每排抬高
STAND_LEN = 32.0              # 看台沿 x 长度
for s in SIDES:
    for i in range(N_ROWS):
        fr = ROW0_Y + i*STEP_D          # 前缘 |y|
        front_y = s*fr
        cy = front_y + s*(STEP_D/2.0)   # 盒中心 y
        H = ROW_H*(i+1)
        cz = H/2.0
        # 实心阶梯块：从地面到踏面，逐渐更高更靠外 → 看台剖面
        o = add_box(f"{PREFIX}Bleacher_{ 'N' if s>0 else 'S' }_{i}",
                    (STAND_LEN, STEP_D, H),
                    (CX, cy, cz), mat_concrete)
        built.append(o.name)

# ---- 替补席（每队 1 座，置于中场两侧边线外 y=±9.0，x=CX）----
def add_bench(tag, side):
    bx = CX
    by = side*9.0
    # 座面
    add_box(f"{PREFIX}Bench_{tag}_Seat", (3.2,0.5,0.10), (bx, by, 0.45), mat_seat)
    # 靠背
    add_box(f"{PREFIX}Bench_{tag}_Back", (3.2,0.10,0.55), (bx, by - side*0.22, 0.72), mat_seat)
    # 两条腿
    for dx in (-1.45, 1.45):
        add_box(f"{PREFIX}Bench_{tag}_Leg_{ 'L' if dx<0 else 'R' }", (0.10,0.10,0.45), (bx+dx, by, 0.225), mat_wood)
    # 顶棚（2 柱 + 1 板）
    for dx in (-1.45, 1.45):
        add_box(f"{PREFIX}Bench_{tag}_Post_{ 'L' if dx<0 else 'R' }", (0.10,0.10,1.9), (bx+dx, by, 0.95), mat_metal)
    add_box(f"{PREFIX}Bench_{tag}_Roof", (3.6,1.3,0.08), (bx, by - side*0.1, 1.95), mat_roof)
    built.append(f"{PREFIX}Bench_{tag}")

add_bench("Home", 1.0)
add_bench("Away", -1.0)

# ---- 预览相机：复用已验证 M39_Cam（不新建，避免污染计数）----
cam = bpy.data.objects.get("M39_Cam")
if cam:
    bpy.context.scene.camera = cam
else:
    # 兜底：自建一份与 M39_Cam 同参数的相机
    cb = bpy.data.cameras.new(PREFIX+"Cam")
    cbo = bpy.data.objects.new(PREFIX+"Cam", cb)
    cbo.location = (10,26,15); cb.lens = 35
    bpy.context.scene.collection.objects.link(cbo)
    bpy.context.scene.camera = cbo

n_total = len(bpy.data.objects)
result = {
    "n_bleacher_boxes": N_ROWS*2,
    "n_benches": 2,
    "n_m41_objects": len(built),
    "n_total_objects": n_total,
    "n_removed_old": n_removed,
    "cam": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
}
print("M41_RESULT", result)
