# m02_archimesh.py — M2 建筑外壳（教学楼 + 实验楼 exterior，门窗开洞，真实尺度）
# 幂等：删除旧 Bldg_A / Bldg_B（及同名新名），重建 Bldg_Teach / Bldg_Lab。
# 构建方式：手动可靠构建（四周边墙 box + Boolean 切门窗洞），不依赖 Archimesh op 的视口上下文，
#          仅顺手 enable archimesh 供 M3 室内使用（失败不影响本里程碑）。
# 尺度：层高 FLOOR_H（教室净高需求）；教学楼 4F / 实验楼 5F；窗台 0.9m、窗高 2.2m、入口门 3.2m。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m02_archimesh.py").read(),"m02","exec"))')

import bpy

# 旧 v1 示意楼 -> 新真实外壳映射
OLD_NEW = {
    "Bldg_A": {"new": "Bldg_Teach", "floors": 4, "label": "教学楼"},
    "Bldg_B": {"new": "Bldg_Lab",   "floors": 5, "label": "实验楼"},
}
FLOOR_H = 3.9          # 层高 m
WALL_T = 0.4           # 墙厚 m
WIN_H = 2.2            # 窗高 m
SILL = 0.9             # 窗台高 m
DEFAULT_FP = {"Bldg_A": (64.0, 16.0), "Bldg_B": (48.0, 14.0)}   # (x 宽, y 进深)
DEFAULT_LOC = {"Bldg_Teach": (-18.0, 14.0), "Bldg_Lab": (18.0, 14.0)}  # (x, y) 平面中心


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    return m


PREFIXES = ["Bldg_Teach", "Bldg_Lab", "Bldg_A", "Bldg_B"]

def clear_all():
    """幂等清理：按前缀删除所有旧 v1 楼(Bldg_A/B)与已建新楼(Bldg_Teach/Lab)
    及其墙/屋顶/洞口残留，避免上一轮失败留下的孤儿墙体重复叠加导致 z-fighting。"""
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
    """在 wall 上 Boolean 切矩形洞（cutter 盒，切完即删）。"""
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


def build_shell(name, loc, fp, floors, brick, glass, concrete):
    fx, fy = fp                                   # x 宽, y 进深
    h = floors * FLOOR_H
    bx, by = loc[0], loc[1]
    cy = h / 2.0
    walls = []
    # 四面边墙
    for sx in (1, -1):
        w = add_box(name + "_WX" + str(sx), (WALL_T, fy, h), (bx + sx * fx / 2.0, by, cy))
        walls.append(("X", sx, w))
    for sy in (1, -1):
        w = add_box(name + "_WY" + str(sy), (fx, WALL_T, h), (bx, by + sy * fy / 2.0, cy))
        walls.append(("Y", sy, w))
    # 每层 ribbon 窗（沿墙宽 0.8，留边）
    for f in range(floors):
        yc = SILL + WIN_H / 2.0 + f * FLOOR_H
        for tag, sx, w in walls:
            if tag == "X":
                # X 端墙沿 Y 向延伸 fy，窗宽取 fy*0.8；洞沿墙厚(X) pierce
                cut_hole(w, (WALL_T + 0.2, fy * 0.8, WIN_H), (bx + sx * fx / 2.0, by, yc), name + "_winX%d" % f)
        for tag, sy, w in walls:
            if tag == "Y":
                # Y 侧墙沿 X 向延伸 fx，窗宽取 fx*0.8；洞沿墙厚(Y) pierce
                cut_hole(w, (fx * 0.8, WALL_T + 0.2, WIN_H), (bx, by + sy * fy / 2.0, yc), name + "_winY%d" % f)
    # 入口门：前墙 +Y 中央（1 层）
    for tag, sy, w in walls:
        if tag == "Y" and sy == 1:
            cut_hole(w, (4.0, WALL_T + 0.2, 3.2), (bx, by + fy / 2.0, 1.6), name + "_door")
    # 屋顶板
    roof = add_box(name + "_Roof", (fx + 1.0, fy + 1.0, 0.4), (bx, by, h + 0.2))
    # 材质
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
    # 顺手启用 archimesh 供 M3；失败忽略（当前环境未装 archimesh）
    try:
        bpy.ops.preferences.addon_enable(module="archimesh")
        print("archimesh enabled")
    except Exception as e:
        print("archimesh enable skipped:", e)
    mat_brick = get_mat("PBR_Brick")
    mat_glass = get_mat("PBR_Glass")
    mat_concrete = get_mat("PBR_Concrete")
    built = []
    for old, spec in OLD_NEW.items():
        new = spec["new"]
        loc = list(DEFAULT_LOC[new])
        fp = DEFAULT_FP[old]
        floors = spec["floors"]
        r = build_shell(new, loc, fp, floors, mat_brick, mat_glass, mat_concrete)
        built.append(r)
    result = {"m2": True, "removed": len(removed), "built": built, "engine": bpy.context.scene.render.engine}
    print("M2 result:", result)
    return result


result = main()
