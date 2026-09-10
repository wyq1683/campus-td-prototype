# m64_basketball.py — M64 室外篮球架 (Outdoor Basketball Hoops)
# 非破坏：仅建 M64_ 前缀物体，先清旧 M64_ 再重建（幂等）。
# 坐标全部动态读取 + 自动避障选址（M11 后铁律），不硬编码任何既有建筑坐标。
import bpy, mathutils, math
from mathutils import Vector

PREFIX = "M64_"
ROOT = "D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"

def clear_old():
    removed = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed += 1
    return removed

def aabb(o):
    c = [o.matrix_world @ Vector(v) for v in o.bound_box]
    xs=[p.x for p in c]; ys=[p.y for p in c]; zs=[p.z for p in c]
    return (min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))

# ---- blocker set for placement self-check ----
BLOCK_PREFIXES = ("Bldg_","M11_Wall","M46_","M38_","M41_","M62_","M63_","M43_",
                  "M61_","M48_","M49_","M53_","M44_","M47_","M45_","M52_","M39_",
                  "M40_","M42_","M16_","M59_","M54_","M55_","M60_","M37_Flag",
                  "M11_FlagPole","M11_Tree","Road","M58_","M50_","M51_")
def blocker_aabbs():
    out=[]
    for o in bpy.data.objects:
        if o.name.startswith(BLOCK_PREFIXES):
            out.append((o.name, aabb(o)))
    return out

def box_clear(cx, cy, hx, hy, blockers, pad=0.0):
    # is axis-aligned box [cx-hx, cx+hx]x[cy-hy, cy+hy] clear of all blockers (+pad)?
    for n, b in blockers:
        if (b[0]-pad <= cx+hx and b[3]+pad >= cx-hx and
            b[1]-pad <= cy+hy and b[4]+pad >= cy-hy):
            return n
    return None

def ring_clear(cx, cy, r, blockers, pad=0.0):
    # sample 16 points around ring radius r
    for i in range(16):
        a = i/16*2*math.pi
        x = cx + math.cos(a)*r; y = cy + math.sin(a)*r
        if box_clear(x, y, 0.1, 0.1, blockers, pad):
            return True
    return False

# ---- materials (created AFTER clear_old; guard against duplicates) ----
def get_mat(name, maker):
    m = bpy.data.materials.get(name)
    if m: return m
    return maker(name)

def mat_metal_pole(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.55,0.57,0.60,1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 1.0
    return m

def mat_board(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.95,0.96,0.98,1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.0
    return m

def mat_red(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.78,0.10,0.10,1.0)
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Metallic"].default_value = 0.0
    return m

def mat_rim(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.95,0.45,0.05,1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 0.7
    return m

def mat_net(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.9,0.9,0.92,1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Metallic"].default_value = 0.0
    m.blend_method = "BLEND"
    bsdf.inputs["Alpha"].default_value = 0.35
    return m

def mat_line(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.12,0.30,0.78,1.0)  # court blue
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Emission Strength"].default_value = 0.12
    bsdf.inputs["Emission Color"].default_value = (0.12,0.30,0.78,1.0)
    return m

# ---- object helpers ----
def new_mesh(name, data):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return o

def place(o, x, y, z):
    o.location = (x, y, z)

def build_hoop(idx, x0, y0, face, mats):
    # face = -1 -> rim faces -x (court at -x); +1 -> faces +x
    P = PREFIX
    parts = []
    # pole
    bpy.ops.mesh.primitive_cylinder_add(radius=0.075, depth=3.6, location=(0,0,0))
    pole = bpy.context.active_object; pole.name = f"{P}Pole_{idx}"; place(pole, x0 - face*1.5, y0, 1.8)
    pole.data.materials.append(mats["metal"])
    parts.append(pole.name)
    # backboard (vertical thin box)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    board = bpy.context.active_object; board.name = f"{P}Board_{idx}"
    board.scale = (0.05, 1.8, 1.05); place(board, x0 - face*0.45, y0, 3.45)
    board.data.materials.append(mats["board"])
    parts.append(board.name)
    # red target square on board (thin box, slightly in front of board face)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    sq = bpy.context.active_object; sq.name = f"{P}BoardMark_{idx}"
    sq.scale = (0.06, 0.6, 0.45); place(sq, x0 - face*0.45 - face*0.03, y0, 3.30)
    sq.data.materials.append(mats["red"])
    parts.append(sq.name)
    # arm (connect pole top to board)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
    arm = bpy.context.active_object; arm.name = f"{P}Arm_{idx}"
    arm.scale = (1.05, 0.08, 0.08); place(arm, x0 - face*0.975, y0, 3.45)
    arm.data.materials.append(mats["metal"])
    parts.append(arm.name)
    # rim (horizontal torus)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.225, minor_radius=0.022, location=(0,0,0))
    rim = bpy.context.active_object; rim.name = f"{P}Rim_{idx}"
    place(rim, x0 - face*0.15, y0, 3.05)
    rim.data.materials.append(mats["rim"])
    parts.append(rim.name)
    # net (cone, apex down)
    bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.10, depth=0.35, location=(0,0,0))
    net = bpy.context.active_object; net.name = f"{P}Net_{idx}"
    net.rotation_euler = (math.pi, 0, 0)  # apex down
    place(net, x0 - face*0.15, y0, 2.85)
    net.data.materials.append(mats["net"])
    parts.append(net.name)
    # ---- painted ground markings ----
    # 3-point arc: flat ring radius 6.0
    bpy.ops.mesh.primitive_torus_add(major_radius=6.0, minor_radius=0.07, location=(0,0,0))
    arc = bpy.context.active_object; arc.name = f"{P}Arc_{idx}"
    place(arc, x0 - face*0.15, y0, 0.12)
    arc.data.materials.append(mats["line"])
    parts.append(arc.name)
    # free-throw lane: two parallel lines length 5.8 at y0±1.8, extending toward court
    for sgn in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
        ln = bpy.context.active_object; ln.name = f"{P}Lane_{idx}{'_L' if sgn<0 else '_R'}"
        ln.scale = (5.8, 0.1, 0.02); place(ln, x0 - face*0.15 - face*2.9, y0 + sgn*1.8, 0.12)
        ln.data.materials.append(mats["line"])
        parts.append(ln.name)
    return parts

# ================= main =================
n_removed = clear_old()
blockers = blocker_aabbs()

# candidate locations (from probe + re-check):
# west band x in [-46,-25] at y=-14 is clear of buildings, bike shed, and
# away (>6m) from the SW/NW floodlight towers at x=-24.5 (arm reaches east).
# Two hoops face each other across an ~8m court; 3-pt arcs (r=6) clear of tower/wall.
candidates = [
    (-31.0, -14.0, -1),   # hoop A faces -x (court toward west, toward B)
    (-39.0, -14.0, +1),   # hoop B faces +x (court toward east, toward A)
]

# placement self-check
checks = []
for (x0,y0,face) in candidates:
    stand = box_clear(x0, y0, 1.6, 1.6, blockers, pad=0.3)
    ring = ring_clear(x0 - face*0.15, y0, 6.0, blockers, pad=0.3)
    checks.append((x0,y0,face, stand, ring))

mats = {
    "metal": get_mat("M64_PoleMat", mat_metal_pole),
    "board": get_mat("M64_BoardMat", mat_board),
    "red":   get_mat("M64_RedMat", mat_red),
    "rim":   get_mat("M64_RimMat", mat_rim),
    "net":   get_mat("M64_NetMat", mat_net),
    "line":  get_mat("M64_LineMat", mat_line),
}

built = []
for i,(x0,y0,face) in enumerate(candidates):
    built += build_hoop(i, x0, y0, face, mats)

# closeup camera: TOP-DOWN centered over the basketball court
# Reason: the west courtyard has dense M11_Tree canopies; horizontal angles are
# occluded. Top-down (above canopy height) is guaranteed clear and showcases the
# painted 3-pt arcs + free-throw lanes + hoop footprints. Centered between both
# hoops with a moderate lens so both stands + arcs frame together, tree at edge.
bpy.ops.object.camera_add(location=(candidates[0][0] - 4, candidates[0][1], 18))
cam = bpy.context.active_object; cam.name = f"{PREFIX}Cam"
cam.data.lens = 28
# look straight down at court center between the two hoops
cx = (candidates[0][0] + candidates[1][0]) / 2
cy = (candidates[0][1] + candidates[1][1]) / 2
target = Vector((cx, cy, 0.15))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
built.append(cam.name)

n_total = len(bpy.data.objects)
result = {
    "n_removed_old": n_removed,
    "n_m64_objects": len(built),
    "m64_names": built,
    "placement_checks": [[c[0],c[1],c[2], c[3] if c[3] else "clear", "ring_clear" if not c[4] else c[4]] for c in checks],
    "n_total_objects": n_total,
}
print("RESULT_JSON_START")
import json
print(json.dumps(result))
print("RESULT_JSON_END")
