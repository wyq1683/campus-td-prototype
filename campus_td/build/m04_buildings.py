# m04_buildings.py — M4 其余建筑外壳（行政楼/宿舍楼/食堂/体育馆/图书馆 exterior）
# 复用 M2 建筑语言：四周边墙 box + Boolean 切 ribbon 窗与门洞；砖墙 + 混凝土屋顶；层高 3.9m。
# 幂等：删除旧 v1 示意楼 Bldg_C/D/E/F 与已建 M4 楼（前缀）后重建。
# 布局：全部置于前区广场 y[-23,5]，避让后方 Bldg_Teach/Lab（y>5.5），互不重叠。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m04_buildings.py").read(),"m04","exec"))')

import bpy

FLOOR_H = 3.9
WALL_T = 0.4

# M4 建筑定义：(name, 中文, (宽x, 进深y), 层数, 窗高, 窗台高, 门宽, 门高, (中心x, 中心y), single_band)
# single_band=True: 仅首层切一道贯通大玻璃带（体育馆等高大厅用），层数仍决定总高。
BUILDINGS = [
    ("Bldg_Admin",    "行政楼", (13.0, 9.0),  4, 2.2, 0.9, 4.0, 3.2, (-16.5, -15.0), False),
    ("Bldg_Dorm",     "宿舍楼", (14.0, 9.0),  6, 2.2, 0.9, 4.0, 3.2, (  0.0, -15.0), False),
    ("Bldg_Gym",      "体育馆", (14.0, 12.0), 3, 8.0, 0.9, 6.0, 4.5, ( 15.0, -15.0), True),
    ("Bldg_Canteen",  "食堂",   (14.0, 10.0), 2, 2.4, 0.9, 5.0, 3.4, (-16.0,  -3.0), False),
    ("Bldg_Library",  "图书馆", (15.0, 11.0), 4, 2.6, 0.9, 6.0, 4.0, (  2.0,  -3.0), False),
]

PREFIXES = ["Bldg_Admin", "Bldg_Dorm", "Bldg_Gym", "Bldg_Canteen", "Bldg_Library",
            "Bldg_C", "Bldg_D", "Bldg_E", "Bldg_F"]  # 清掉 v1 示意楼


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    return m


def clear_all():
    removed = []
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in PREFIXES):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def add_box(name, size, location):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def cut_hole(wall, hole_size, hole_center, label):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=hole_center)
    cutter = bpy.context.active_object
    cutter.name = "Cut_" + label
    cutter.scale = (hole_size[0], hole_size[1], hole_size[2])
    cutter.hide_render = True
    cutter.hide_viewport = True
    mod = wall.modifiers.new("Bool_" + label, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    try:
        bpy.context.view_layer.objects.active = wall
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as e:
        print("bool apply warn:", label, e)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build_shell(name, loc, fp, floors, win_h, sill, door_w, door_h, brick, glass, concrete, single_band=False):
    fx, fy = fp
    h = floors * FLOOR_H
    bx, by = loc[0], loc[1]
    cy = h / 2.0
    walls = []
    for sx in (1, -1):
        w = add_box(name + "_WX" + str(sx), (WALL_T, fy, h), (bx + sx * fx / 2.0, by, cy))
        walls.append(("X", sx, w))
    for sy in (1, -1):
        w = add_box(name + "_WY" + str(sy), (fx, WALL_T, h), (bx, by + sy * fy / 2.0, cy))
        walls.append(("Y", sy, w))
    # 每层 ribbon 窗（single_band 时仅首层一道贯通大玻璃带）
    floor_idx = [0] if single_band else range(floors)
    for f in floor_idx:
        yc = sill + win_h / 2.0 + f * FLOOR_H
        for tag, sx, w in walls:
            if tag == "X":
                cut_hole(w, (WALL_T + 0.2, fy * 0.8, win_h), (bx + sx * fx / 2.0, by, yc), name + "_winX%d" % f)
        for tag, sy, w in walls:
            if tag == "Y":
                cut_hole(w, (fx * 0.8, WALL_T + 0.2, win_h), (bx, by + sy * fy / 2.0, yc), name + "_winY%d" % f)
    # 入口门：前墙 +Y 中央（1 层）
    for tag, sy, w in walls:
        if tag == "Y" and sy == 1:
            cut_hole(w, (door_w, WALL_T + 0.2, door_h), (bx, by + fy / 2.0, door_h / 2.0), name + "_door")
    # 屋顶板
    roof = add_box(name + "_Roof", (fx + 1.0, fy + 1.0, 0.4), (bx, by, h + 0.2))
    for _, _, w in walls:
        if w.data.materials:
            w.data.materials[0] = brick
        else:
            w.data.materials.append(brick)
    if roof.data.materials:
        roof.data.materials[0] = concrete
    else:
        roof.data.materials.append(concrete)
    return {"name": name, "floors": floors, "size": (fx, fy, round(h, 2))}


def main():
    removed = clear_all()
    mat_brick = get_mat("PBR_Brick")
    mat_glass = get_mat("PBR_Glass")
    mat_concrete = get_mat("PBR_Concrete")
    built = []
    for spec in BUILDINGS:
        name, label, fp, floors, win_h, sill, door_w, door_h, loc, single_band = spec
        r = build_shell(name, loc, fp, floors, win_h, sill, door_w, door_h, mat_brick, mat_glass, mat_concrete, single_band)
        built.append({"label": label, **r})
        print("built", label, r)
    result = {"m4": True, "removed": len(removed), "built": built, "engine": bpy.context.scene.render.engine}
    print("M4 result:", result)
    return result


result = main()
