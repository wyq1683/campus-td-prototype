# m03_interior.py — M3 室内可进入（教学楼 Bldg_Teach 地面层，手动 box + Boolean）
# 幂等：按前缀 Int_Teach_ / Stair_Teach_ / Furn_Teach_ / Light_Int_Teach_ 清旧再重建。
# 不依赖 Archimesh（本环境无此扩展，M2 已确认）；沿用 M2 手动构建法，headless 链路最稳。
# 内容：可行走室内地板、隔墙(带门洞)、黑板、课桌阵列、楼梯(层间连通演示)、临时室内补光(预览用,M6 做 HDRI)。
# 运行（每小时构建自动化，Direct TCP Socket @9876）：
#   exec(compile(open(r"...campus_td/build/m03_interior.py").read(),"m03","exec"))

import bpy

# ---- 教学楼几何（与 m02_archimesh.py 对齐）----
BX, BY = -18.0, 14.0          # 平面中心
FX, FY = 64.0, 16.0           # x 宽, y 进深
FLOOR_H = 3.9
WALL_T = 0.4
# 外墙内表面（室内净空）
IX0, IX1 = BX - FX/2 + WALL_T, BX + FX/2 - WALL_T   # -49.8 .. 13.8
IY0, IY1 = BY - FY/2 + WALL_T, BY + FY/2 - WALL_T   # 6.2 .. 21.8
INNER_W = IX1 - IX0
INNER_D = IY1 - IY0

PREFIXES = ["Int_Teach_", "Stair_Teach_", "Furn_Teach_", "Light_Int_Teach_"]


def get_mat(name, ensure_nodes=True):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    return m


def set_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


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
        print("bool warn:", label, e)
    bpy.data.objects.remove(cutter, do_unlink=True)


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in PREFIXES):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    # 同时清掉上一轮可能残留的临时 cutter（命名 Cut_Int_）
    for o in list(bpy.data.objects):
        if o.name.startswith("Cut_Int_"):
            bpy.data.objects.remove(o, do_unlink=True)
    return removed


def build():
    removed = clear_old()

    mat_brick = get_mat("PBR_Brick")
    mat_conc = get_mat("PBR_Concrete")
    mat_wood = get_mat("PBR_Wood")
    mat_tile = get_mat("PBR_Tile")
    # 黑板：深色低粗糙
    mat_board = get_mat("Int_Board")
    if mat_board.use_nodes:
        nt = mat_board.node_tree
        bs = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bs is None:
            bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bs.inputs["Base Color"].default_value = (0.04, 0.07, 0.06, 1)
        bs.inputs["Roughness"].default_value = 0.35

    built = {}

    # 1) 室内地板（可行走；抬离地面 0.02 防 z-fighting）
    floor = add_box("Int_Teach_Floor", (INNER_W, INNER_D, 0.12),
                    (BX, BY, 0.08))
    set_mat(floor, mat_tile)
    built["floor"] = (round(INNER_W, 1), round(INNER_D, 1))

    # 2) 隔墙（平行 Y，x=-8）分教室侧(X< -8)与走廊侧(X> -8)，带门洞
    part = add_box("Int_Teach_Part", (0.3, INNER_D, FLOOR_H - 0.1),
                   (-8.0, BY, (FLOOR_H - 0.1) / 2 + 0.02))
    set_mat(part, mat_brick)
    # 门洞：靠 y=10 处，X 向穿透墙厚
    cut_hole(part, (0.5, 1.6, 2.4), (-8.0, 10.0, 1.2), "Int_Teach_door")
    built["partition"] = True

    # 3) 黑板（贴在 -Y 内墙，教室侧）
    board = add_box("Int_Teach_Board", (4.0, 0.1, 1.4), (-30.0, IY0 + 0.2, 1.9))
    set_mat(board, mat_board)
    built["board"] = True

    # 4) 课桌 + 椅阵列（教室侧 X:-46..-14, Y:8/11）
    desks = 0
    chairs = 0
    cols = list(range(-46, -13, 4))      # -46..-14
    rows = [8.0, 11.0]
    for cx in cols:
        for cy in rows:
            d = add_box("Furn_Teach_Desk_%d_%d" % (cx, int(cy)),
                        (1.2, 0.6, 0.75), (cx, cy, 0.375 + 0.02))
            set_mat(d, mat_wood)
            desks += 1
            ch = add_box("Furn_Teach_Chair_%d_%d" % (cx, int(cy)),
                         (0.5, 0.5, 0.45), (cx, cy - 0.7, 0.225 + 0.02))
            set_mat(ch, mat_wood)
            chairs += 1
    built["desks"] = desks
    built["chairs"] = chairs

    # 5) 楼梯（层间连通演示）：沿 +Y 上行，位于 +X 端 x=12
    steps = 0
    nstep = 9
    for i in range(nstep):
        zc = 0.02 + (i + 0.5) * (FLOOR_H / nstep)
        sy = 8.0 + i * (INNER_D / nstep)
        s = add_box("Stair_Teach_S%d" % i, (2.0, INNER_D / nstep + 0.1, FLOOR_H / nstep),
                    (12.0, sy, zc))
        set_mat(s, mat_conc)
        steps += 1
    built["stairs"] = steps

    # 6) 临时室内补光（预览用，M6 做正式 HDRI/探针）
    light = bpy.data.lights.get("Int_Teach_Fill")
    if light is None:
        light = bpy.data.lights.new("Int_Teach_Fill", type="AREA")
    light.energy = 120.0
    light.size = 6.0
    lamp = bpy.data.objects.get("Light_Int_Teach_Fill")
    if lamp is None:
        lamp = bpy.data.objects.new("Light_Int_Teach_Fill", light)
        bpy.context.collection.objects.link(lamp)
    lamp.location = (BX, BY, FLOOR_H - 0.3)
    lamp.data.energy = 120.0
    built["fill_light"] = True

    return removed, built


def main():
    removed, built = build()
    result = {
        "m3": True,
        "removed_old": len(removed),
        "built": built,
        "engine": bpy.context.scene.render.engine,
        "total_objects": len(bpy.data.objects),
    }
    print("M3 result:", result)
    return result


result = main()
