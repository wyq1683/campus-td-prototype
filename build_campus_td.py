import bpy
import math
import mathutils

# ---------- 1. 清空旧物体（保留 World） ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ---------- 2. 世界背景（天空蓝） ----------
world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.62, 0.74, 0.92, 1.0)
    bg.inputs['Strength'].default_value = 1.0

# ---------- 3. 程序化材质 ----------
def make_mat(name, color, rough=0.85, metallic=0.0, emissive=None, emit_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metallic
    if emissive is not None:
        bsdf.inputs['Emission Color'].default_value = (*emissive, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emit_strength
    return mat

grass      = make_mat('grass',      (0.30, 0.62, 0.26))
road       = make_mat('road',       (0.22, 0.22, 0.25))
brick      = make_mat('brick',      (0.74, 0.43, 0.34))
roof       = make_mat('roof',       (0.42, 0.44, 0.50))
tower_base = make_mat('tower_base', (0.30, 0.32, 0.38), metallic=0.35, rough=0.4)
tower_ring = make_mat('tower_ring', (0.10, 0.55, 0.85), metallic=0.6,  rough=0.3)
tower_glow = make_mat('tower_glow', (0.0, 0.0, 0.0), emissive=(0.15, 0.95, 1.0), emit_strength=3.5)
enemy_mat  = make_mat('enemy',      (0.88, 0.20, 0.20), rough=0.5)

# ---------- 4. 地形（草地） ----------
bpy.ops.mesh.primitive_plane_add(size=46, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = 'Ground'
ground.data.materials.append(grass)

# ---------- 5. U 形敌人路径 ----------
ROAD_W = 3.2
def add_road(cx, cy, sx, sy):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, 0.06))
    o = bpy.context.active_object
    o.name = 'Road'
    o.scale = (sx, sy, 0.12)
    o.data.materials.append(road)

add_road(-2.0, -13.0, 40.0, ROAD_W)   # 下横段  x:-22..18  y=-13
add_road( 16.0,  0.0, ROAD_W, 28.0)   # 右竖段  x=16  y:-14..14
add_road(-2.0, 13.0, 40.0, ROAD_W)    # 上横段  x:-22..18  y=13

# ---------- 6. 教学楼群（砖墙+屋顶） ----------
def add_building(x, y, w, d, h, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h/2))
    o = bpy.context.active_object
    o.name = name
    o.scale = (w, d, h)
    o.data.materials.append(brick)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h + 0.3))
    r = bpy.context.active_object
    r.name = name + '_roof'
    r.scale = (w * 1.06, d * 1.06, 0.6)
    r.data.materials.append(roof)

# 下场区 (y 约 -18)
add_building(-15, -18, 6, 5, 7, 'Bldg_A')
add_building(-5,  -18, 5, 5, 9, 'Bldg_B')
add_building( 5,  -18, 6, 5, 6, 'Bldg_C')
# 上场区 (y 约 18)
add_building(-15, 18, 6, 5, 8, 'Bldg_D')
add_building(-5,  18, 5, 5, 6, 'Bldg_E')
add_building( 5,  18, 6, 5, 10, 'Bldg_F')

# ---------- 7. 发光防御塔（圆柱+光环+发光顶） ----------
def add_tower(x, y, name):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.95, depth=3.0, location=(x, y, 1.5))
    base = bpy.context.active_object
    base.name = name
    base.data.materials.append(tower_base)

    bpy.ops.mesh.primitive_torus_add(location=(x, y, 3.2), major_radius=1.05, minor_radius=0.26)
    ring = bpy.context.active_object
    ring.name = name + '_ring'           # 默认即平躺光环（孔轴=Z）
    ring.data.materials.append(tower_ring)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(x, y, 4.1))
    top = bpy.context.active_object
    top.name = name + '_glow'
    top.data.materials.append(tower_glow)

add_tower(-22, -13, 'Tower_1')
add_tower( 16, -13, 'Tower_2')
add_tower( 16, 13, 'Tower_3')
add_tower(-22, 13, 'Tower_4')

# ---------- 8. 敌人单位（沿路径排布） ----------
def add_enemy(x, y, name):
    bpy.ops.mesh.primitive_cone_add(radius1=0.6, radius2=0.05, depth=1.4, location=(x, y, 0.8))
    e = bpy.context.active_object
    e.name = name
    e.data.materials.append(enemy_mat)

add_enemy(-20, -13, 'Enemy_1')
add_enemy(-12, -13, 'Enemy_2')
add_enemy(-4,  -13, 'Enemy_3')
add_enemy( 16, -7,  'Enemy_4')
add_enemy( 16,  2,  'Enemy_5')
add_enemy( 8,   13, 'Enemy_6')
add_enemy( 0,   13, 'Enemy_7')

# ---------- 9. 灯光 ----------
bpy.ops.object.light_add(type='SUN', location=(12, -10, 26))
sun = bpy.context.active_object
sun.name = 'Sun'
sun.data.energy = 2.6
sun.rotation_euler = (math.radians(55), 0, math.radians(30))

bpy.ops.object.light_add(type='POINT', location=(0, 0, 14))
pt = bpy.context.active_object
pt.name = 'Fill'
pt.data.energy = 220

# ---------- 10. 俯视相机（look-at 原点） ----------
cam = bpy.data.objects.get('Camera')
if cam is None:
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
cam.name = 'Camera'
cam.location = (0, -32, 30)
target = mathutils.Vector((0, 0, 2))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 35
bpy.context.scene.camera = cam

# ---------- 11. 渲染设置 ----------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.device = 'CPU'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100

result = {
    "built": True,
    "objects": len(bpy.data.objects),
    "engine": scene.render.engine,
}
