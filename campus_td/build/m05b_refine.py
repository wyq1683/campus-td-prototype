# m05b_refine.py — M5 场地细节精修（可选精修 backlog 第 1 项）
# 目标：① 树冠 box -> icosphere 有机树丛；② 围墙压顶(coping)；③ 校门匾做青铜嵌板精修。
# 幂等：删除所有 M5B_ 前缀对象后重建；对既有 M5_ 对象做"修饰"
#       （删旧 box 树冠 / 在墙上加压顶 / 在匾前加嵌板）。
# 运行：blmcp_client.py m05_refine
# 注意：5.2 新动画系统与本脚本无关；材质沿用 m01/m05 的 PBR_* 命名。

import bpy
import mathutils

PREFIX = "M5B_"


# ---------- helpers ----------
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


def get_metal_mat(name, color=(0.45, 0.32, 0.12), rough=0.45):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    if m.use_nodes:
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            try:
                bsdf.inputs["Metallic"].default_value = 1.0
                bsdf.inputs["Roughness"].default_value = rough
            except Exception:
                pass
    return m


def set_mat(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(o.name)
    return removed


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


# 确定性伪随机（避免 random 跨运行差异，保证幂等可复现）
def jitter(seed, k):
    v = ((seed * 9301 + k * 49297 + 233280) % 233280) / 233280.0
    return v


def refine_trees():
    leaf = get_mat("PBR_Leaf", (0.18, 0.42, 0.16))
    trees = [(-20.0, -12.0), (20.0, -12.0), (-20.0, 6.0), (20.0, 6.0),
             (-18.0, 16.0), (18.0, 16.0), (-14.0, -20.0), (14.0, -20.0),
             (0.0, -20.5), (-8.0, 18.5)]
    made = []
    for i, (tx, ty) in enumerate(trees):
        # 删旧 box 树冠（m05 的 M5_TreeCanopy%d）
        old = bpy.data.objects.get("M5_TreeCanopy%d" % i)
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        # 主干保留 M5_TreeTrunk%d；新建有机树丛（主球 + 2 卫星球）
        r0 = 2.5 + 0.5 * jitter(i, 1)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r0, location=(tx, ty, 5.6))
        main = bpy.context.active_object
        main.name = PREFIX + "TreeFoliage%d_0" % i
        set_mat(main, leaf)
        for k in (1, 2):
            ox = (jitter(i, k) - 0.5) * 2.0
            oy = (jitter(i, k + 10) - 0.5) * 2.0
            oz = (jitter(i, k + 20) - 0.3) * 1.2
            rk = 1.6 + 0.6 * jitter(i, k + 30)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rk,
                                                  location=(tx + ox, ty + oy, 5.6 + oz))
            sat = bpy.context.active_object
            sat.name = PREFIX + "TreeFoliage%d_%d" % (i, k)
            set_mat(sat, leaf)
        made.append(i)
    return made


def refine_walls():
    concrete = get_mat("PBR_Concrete")
    coping_h = 0.35
    wall_names = ["M5_WallBack", "M5_WallLeft", "M5_WallRight", "M5_WallFrontL", "M5_WallFrontR"]
    made = []
    for wn in wall_names:
        w = bpy.data.objects.get(wn)
        if w is None:
            continue
        top = w.location.z + w.dimensions.z / 2.0
        cx, cy = w.location.x, w.location.y
        dx, dy = w.dimensions.x, w.dimensions.y
        # 压顶：比墙略宽 0.25，置于墙顶，收口更"完成"
        cap = add_box(PREFIX + "Coping_%s" % wn, (dx + 0.25, dy + 0.25, coping_h),
                      (cx, cy, top + coping_h / 2.0))
        set_mat(cap, concrete)
        made.append(wn)
    return made


def refine_gate():
    # 在 M5_GatePlaque 前（门枋前脸 y<-20.3）加青铜嵌板 + 深色石框。
    # 注：原 M5_GatePlaque 实际嵌在门枋体积内（y=-21 在门枋 y[-21.7,-20.3] 区间），
    #     不可见；此处新建嵌板置于门枋前脸之外，确保可见。匾文(校名)待 CJK 字体就位后深化。
    plaque = bpy.data.objects.get("M5_GatePlaque")
    made = []
    if plaque is None:
        return made
    bronze = get_metal_mat("M5B_Bronze", (0.45, 0.32, 0.12), 0.45)
    # 嵌板：略小于匾，前移避开门枋前脸(y=-20.3)
    panel = add_box(PREFIX + "PlaquePanel", (4.4, 0.12, 0.85), (0.0, -20.18, 5.4))
    set_mat(panel, bronze)
    # 外框：深色石框，包住嵌板
    frame = get_mat("PBR_Concrete_Dark", (0.18, 0.18, 0.20))
    f = add_box(PREFIX + "PlaqueFrame", (5.2, 0.16, 1.05), (0.0, -20.26, 5.4))
    set_mat(f, frame)
    made = ["M5B_PlaquePanel", "M5B_PlaqueFrame"]
    return made


def main():
    removed = clear_old()
    trees = refine_trees()
    walls = refine_walls()
    gate = refine_gate()
    result = {"m5b": True, "removed_old": len(removed), "trees": len(trees),
              "walls_coped": len(walls), "gate": gate, "objects": len(bpy.data.objects)}
    print("M5B result:", result)
    return result


result = main()
