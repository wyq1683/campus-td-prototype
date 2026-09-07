# m05_site.py — M5 场地细化 + 环境光
# (a) World 改 Nishita Sky Texture -> 真实天光/环境反射（离线免 HDRI）
# (b) 场地物件：前庭院铺装 / 校门牌坊(双柱+额) / 旗杆 / 围墙(四周, 南向留门) / 花坛×4 / 树阵×10
# 幂等：删除所有 M5_ 前缀对象后重建；保留 M0-M4 的 Ground/Road/Bldg/Tower/Enemy。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m05_site.py").read(),"m05","exec"))')

import bpy
import mathutils

PREFIX = "M5_"
G = 23.0  # 地面半边长（ground x/y ∈ [-23,23]）


def get_mat(name, color=(0.8, 0.8, 0.8)):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    if m.use_nodes:
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    else:
        m.diffuse_color = color
    return m


def clear_all():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name  # 先存名，remove 后 StructRNA 即失效
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def add_cyl(name, r, h, loc, seg=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=seg, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def set_mat(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


# ---------- (a) 环境光：solid sky-blue Background（Sky Texture 渲出来偏灰，solid 保证可见蓝天） ----------
def setup_sky_world():
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    # 清掉除 World Output 外的节点
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    # 下午晴天天蓝（地平线偏白 + 顶部偏蓝），M6 再换 HDRI 写真
    bg.inputs["Color"].default_value = (0.58, 0.78, 0.92, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return True


# ---------- (b) 场地物件 ----------
def build_site():
    brick = get_mat("PBR_Brick")
    concrete = get_mat("PBR_Concrete")
    wood = get_mat("PBR_Wood")
    metal = get_mat("PBR_Metal")
    leaf = get_mat("PBR_Leaf", (0.18, 0.42, 0.16))
    soil = get_mat("PBR_Soil", (0.22, 0.15, 0.10))
    red = get_mat("M5_FlagRed", (0.72, 0.12, 0.10))
    built = []

    # 1) 前庭院铺装（薄板，z=0.05，盖住前区 y[-21,-10]）
    plaza = add_box(PREFIX + "Plaza", (38.0, 11.0, 0.1), (0.0, -15.5, 0.05))
    set_mat(plaza, brick)
    built.append("Plaza")

    # 2) 校门牌坊：双柱(x=±6, h=5) + 额枋(混凝土, 跨 x[-7,7], z=5) + 匾(深色)
    for sx in (-1, 1):
        p = add_box(PREFIX + "GatePillar%d" % sx, (1.2, 1.2, 5.0), (sx * 6.0, -21.0, 2.5))
        set_mat(p, brick)
    lintel = add_box(PREFIX + "GateLintel", (14.4, 1.4, 1.2), (0.0, -21.0, 5.4))
    set_mat(lintel, concrete)
    plaque = add_box(PREFIX + "GatePlaque", (5.0, 0.1, 1.0), (0.0, -21.0, 5.4))
    set_mat(plaque, get_mat("PBR_Concrete_Dark", (0.18, 0.18, 0.20)))
    built.append("Gate")

    # 3) 旗杆：金属杆(h=10) + 红旗下垂
    pole = add_cyl(PREFIX + "FlagPole", 0.18, 10.0, (0.0, -18.5, 5.0), seg=12)
    set_mat(pole, metal)
    flag = add_box(PREFIX + "Flag", (3.0, 0.1, 1.8), (1.6, -18.5, 9.2))
    set_mat(flag, red)
    built.append("Flag")

    # 4) 围墙：四周，南向(y=-23)留 x[-7,7] 门洞
    wall_h, wall_t = 2.4, 0.3
    # 后墙 y=+23
    add_box(PREFIX + "WallBack", (2 * G, wall_t, wall_h), (0.0, 23.0, wall_h / 2.0))
    # 左墙 x=-23
    add_box(PREFIX + "WallLeft", (wall_t, 2 * G, wall_h), (-23.0, 0.0, wall_h / 2.0))
    # 右墙 x=+23
    add_box(PREFIX + "WallRight", (wall_t, 2 * G, wall_h), (23.0, 0.0, wall_h / 2.0))
    # 前墙分两段（门洞 x[-7,7]）
    add_box(PREFIX + "WallFrontL", (16.0, wall_t, wall_h), (-15.0, -23.0, wall_h / 2.0))
    add_box(PREFIX + "WallFrontR", (16.0, wall_t, wall_h), (15.0, -23.0, wall_h / 2.0))
    # 给所有墙混凝土材质
    for o in bpy.data.objects:
        if o.name.startswith(PREFIX + "Wall"):
            set_mat(o, concrete)
    built.append("Wall")

    # 5) 花坛 ×4（砖身 + 土面）
    beds = [(-12.0, -12.0), (12.0, -12.0), (-12.0, -9.0), (12.0, -9.0)]
    for i, (bx, by) in enumerate(beds):
        body = add_box(PREFIX + "Bed%d" % i, (3.0, 1.2, 0.6), (bx, by, 0.35))
        set_mat(body, brick)
        top = add_box(PREFIX + "BedSoil%d" % i, (2.8, 1.0, 0.12), (bx, by, 0.68))
        set_mat(top, soil)
    built.append("Beds x%d" % len(beds))

    # 6) 树阵 ×10（木干 + 绿冠）
    trees = [(-20.0, -12.0), (20.0, -12.0), (-20.0, 6.0), (20.0, 6.0),
             (-18.0, 16.0), (18.0, 16.0), (-14.0, -20.0), (14.0, -20.0),
             (0.0, -20.5), (-8.0, 18.5)]
    for i, (tx, ty) in enumerate(trees):
        trunk = add_cyl(PREFIX + "TreeTrunk%d" % i, 0.3, 4.0, (tx, ty, 2.0), seg=8)
        set_mat(trunk, wood)
        canopy = add_box(PREFIX + "TreeCanopy%d" % i, (4.5, 4.5, 4.0), (tx, ty, 5.6))
        set_mat(canopy, leaf)
    built.append("Trees x%d" % len(trees))

    return built


def main():
    removed = clear_all()
    sky_ok = setup_sky_world()
    built = build_site()
    result = {"m5": True, "removed": len(removed), "sky": sky_ok, "built": built,
              "engine": bpy.context.scene.render.engine}
    print("M5 result:", result)
    return result


result = main()
