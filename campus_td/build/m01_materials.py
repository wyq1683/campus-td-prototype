# m01_materials.py  — M1 程序化 PBR 材质库
# 幂等：清掉旧的 PBR_*/Mat_*/Mat_Glow/Mat_Enemy 材质与预览球，再重建。
# 应用至 v1 网格：Ground->草, Road->沥青, Bldg(非roof)->砖, *_roof->混凝土,
#                Tower base/ring->金属, Tower glow->自发光, Enemy->红。
# 另建 8 个预览球 Mat_Preview_* 用于 QA。
# 来源约定：PLAN.md §5 质量基准（albedo 区间 / 变化 / Bump / 使用痕迹）。
# 运行方式（每日自动化）：
#   execute_blender_code(code='exec(compile(open(r"...campus_td/build/m01_materials.py").read(),"m01","exec"))')

import bpy

# ---------- 材质集合 ----------
PBR_SET = ["PBR_Grass", "PBR_Asphalt", "PBR_Brick", "PBR_Concrete",
           "PBR_Glass", "PBR_Wood", "PBR_Metal", "PBR_Tile"]
EXTRA = ["Mat_Glow", "Mat_Enemy"]
ALL_MATS = PBR_SET + EXTRA


# ---------- 工具 ----------
def clear_old():
    # 删预览球（物体 + 网格数据）
    for o in list(bpy.data.objects):
        if o.name.startswith("Mat_Preview_"):
            if o.data and o.data.name not in ("Cube", "Plane", "Sphere"):
                try:
                    bpy.data.meshes.remove(o.data)
                except Exception:
                    pass
            bpy.data.objects.remove(o, do_unlink=True)
    # 删旧材质
    for m in list(bpy.data.materials):
        if m.name in ALL_MATS:
            bpy.data.materials.remove(m)


def new_mat(name, blend="OPAQUE"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.blend_method = blend
    return m


def bsdf_of(mat):
    nt = mat.node_tree
    bs = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bs is None:
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    # 清掉默认 link，避免重复连接
    for inp in bs.inputs:
        for ln in list(inp.links):
            nt.links.remove(ln)
    return nt, bs


def vary_color(nt, bs, col_dark, col_light, scale=8.0, detail=6.0):
    """Noise -> ColorRamp -> Base Color（物理合理双色区间）。"""
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = (-700, 250)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 250)
    ramp.color_ramp.elements[0].color = col_dark
    ramp.color_ramp.elements[1].color = col_light
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    return n


def vary_rough(nt, bs, base=0.7, amp=0.2, scale=12.0):
    """Noise -> *amp -> +base -> Roughness（避免纯色死板）。"""
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = (-700, -100)
    n.inputs["Scale"].default_value = scale
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    m1.location = (-450, -100)
    m1.inputs[1].default_value = amp
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "ADD"
    m2.location = (-200, -100)
    m2.inputs[1].default_value = base
    nt.links.new(n.outputs["Fac"], m1.inputs[0])
    nt.links.new(m1.outputs[0], m2.inputs[0])
    nt.links.new(m2.outputs[0], bs.inputs["Roughness"])
    return n


def bump(nt, bs, strength=0.3, scale=20.0, dist=0.02):
    """Noise -> Bump -> Normal（微观起伏）。"""
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.location = (-400, -450)
    n.inputs["Scale"].default_value = scale
    b = nt.nodes.new("ShaderNodeBump")
    b.location = (-150, -450)
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    nt.links.new(n.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bs.inputs["Normal"])
    return b


# ---------- 各材质构建 ----------
def build_grass(m):
    nt, bs = bsdf_of(m)
    vary_color(nt, bs, (0.05, 0.16, 0.04, 1), (0.13, 0.33, 0.08, 1), scale=45, detail=9)
    vary_rough(nt, bs, base=0.88, amp=0.10, scale=35)
    bump(nt, bs, strength=0.5, scale=70, dist=0.04)


def build_asphalt(m):
    nt, bs = bsdf_of(m)
    vary_color(nt, bs, (0.03, 0.03, 0.035, 1), (0.11, 0.11, 0.12, 1), scale=28, detail=9)
    vary_rough(nt, bs, base=0.78, amp=0.16, scale=45)
    bump(nt, bs, strength=0.18, scale=14, dist=0.015)
    # 裂缝感：Voronoi 轻微抬升 roughness
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.location = (-700, -300)
    v.inputs["Scale"].default_value = 6.0
    mv = nt.nodes.new("ShaderNodeMath")
    mv.operation = "MULTIPLY"
    mv.location = (-450, -300)
    mv.inputs[1].default_value = 0.08
    av = nt.nodes.new("ShaderNodeMath")
    av.operation = "ADD"
    av.location = (-220, -300)
    av.inputs[1].default_value = 0.85
    nt.links.new(v.outputs["Fac"], mv.inputs[0])
    nt.links.new(mv.outputs[0], av.inputs[0])
    nt.links.new(av.outputs[0], bs.inputs["Roughness"])


def build_brick(m):
    nt, bs = bsdf_of(m)
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.location = (-450, 250)
    brick.inputs["Color1"].default_value = (0.30, 0.12, 0.10, 1)
    brick.inputs["Color2"].default_value = (0.37, 0.16, 0.13, 1)
    brick.inputs["Mortar"].default_value = (0.22, 0.22, 0.22, 1)
    brick.inputs["Scale"].default_value = 5.0
    brick.inputs["Mortar Size"].default_value = 0.03
    nt.links.new(brick.outputs["Color"], bs.inputs["Base Color"])
    vary_rough(nt, bs, base=0.82, amp=0.10, scale=18)
    bump(nt, bs, strength=0.16, scale=9, dist=0.012)


def build_concrete(m):
    nt, bs = bsdf_of(m)
    vary_color(nt, bs, (0.20, 0.21, 0.22, 1), (0.34, 0.35, 0.37, 1), scale=16, detail=8)
    vary_rough(nt, bs, base=0.80, amp=0.12, scale=26)
    bump(nt, bs, strength = 0.12, scale = 12, dist = 0.01)
    # 渗水渍：Musgrave 压暗 albedo 边角
    mg = nt.nodes.new("ShaderNodeTexMusgrave")
    mg.location = (-700, 420)
    mg.inputs["Scale"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-450, 420)
    ramp.color_ramp.elements[0].color = (0.12, 0.12, 0.13, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.31, 0.33, 1)
    nt.links.new(mg.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])


def build_glass(m):
    nt, bs = bsdf_of(m)
    bs.inputs["Base Color"].default_value = (0.85, 0.92, 0.93, 1)
    bs.inputs["Roughness"].default_value = 0.05
    bs.inputs["IOR"].default_value = 1.5
    bs.inputs["Transmission"].default_value = 1.0


def build_wood(m):
    nt, bs = bsdf_of(m)
    vary_color(nt, bs, (0.10, 0.06, 0.03, 1), (0.22, 0.13, 0.06, 1), scale=6.0, detail=4.0)
    vary_rough(nt, bs, base=0.52, amp = 0.16, scale = 10)
    bump(nt, bs, strength = 0.10, scale = 8, dist = 0.01)


def build_metal(m):
    nt, bs = bsdf_of(m)
    bs.inputs["Base Color"].default_value = (0.55, 0.57, 0.60, 1)
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Roughness"].default_value = 0.35
    vary_rough(nt, bs, base=0.30, amp=0.22, scale=30)
    # 金属不铺 Bump，保持平滑反射


def build_tile(m):
    nt, bs = bsdf_of(m)
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.location = (-450, 250)
    brick.inputs["Color1"].default_value = (0.52, 0.54, 0.55, 1)
    brick.inputs["Color2"].default_value = (0.60, 0.62, 0.63, 1)
    brick.inputs["Mortar"].default_value = (0.30, 0.28, 0.26, 1)
    brick.inputs["Scale"].default_value = 22.0  # 小瓷砖
    brick.inputs["Mortar Size"].default_value = 0.015
    nt.links.new(brick.outputs["Color"], bs.inputs["Base Color"])
    vary_rough(nt, bs, base=0.28, amp=0.10, scale=40)
    bump(nt, bs, strength=0.10, scale=30, dist=0.008)


def build_glow(m):
    nt, bs = bsdf_of(m)
    bs.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1)
    bs.inputs["Emission Color"].default_value = (0.25, 0.85, 1.0, 1)
    bs.inputs["Emission Strength"].default_value = 6.0


def build_enemy(m):
    nt, bs = bsdf_of(m)
    bs.inputs["Base Color"].default_value = (0.72, 0.10, 0.10, 1)
    bs.inputs["Roughness"].default_value = 0.5
    bs.inputs["Metallic"].default_value = 0.1


BUILDERS = {
    "PBR_Grass": build_grass, "PBR_Asphalt": build_asphalt, "PBR_Brick": build_brick,
    "PBR_Concrete": build_concrete, "PBR_Glass": build_glass, "PBR_Wood": build_wood,
    "PBR_Metal": build_metal, "PBR_Tile": build_tile, "Mat_Glow": build_glow,
    "Mat_Enemy": build_enemy,
}

MAT_BY_TARGET = {
    "grass": "PBR_Grass", "asphalt": "PBR_Asphalt", "brick": "PBR_Brick",
    "concrete": "PBR_Concrete", "glass": "PBR_Glass", "wood": "PBR_Wood",
    "metal": "PBR_Metal", "tile": "PBR_Tile", "glow": "Mat_Glow", "enemy": "Mat_Enemy",
}


# ---------- 应用 ----------
def apply_mat(obj, mat):
    if obj.type != "MESH" or mat is None:
        return False
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    return True


def apply_to_scene(mats):
    counts = {}
    for o in bpy.data.objects:
        name = o.name.lower()
        target = None
        if name == "ground":
            target = "grass"
        elif "road" in name:
            target = "asphalt"
        elif name.endswith("_roof") or name == "roof":
            target = "concrete"
        elif "tower" in name and "glow" in name:
            target = "glow"
        elif "tower" in name:
            target = "metal"
        elif "enemy" in name:
            target = "enemy"
        elif "bldg" in name:
            target = "brick"
        if target:
            m = mats.get(MAT_BY_TARGET[target])
            if apply_mat(o, m):
                counts[target] = counts.get(target, 0) + 1
    return counts


def make_previews(mats):
    n = len(ALL_MATS)
    for i, key in enumerate(ALL_MATS):
        m = mats.get(key)
        if not m:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=1.2, location=(60.0 + i * 3.0, 0.0, 1.4))
        sph = bpy.context.active_object
        sph.name = "Mat_Preview_" + key
        sph.data.materials.append(m)


# ---------- 主流程 ----------
def main():
    clear_old()
    mats = {}
    for key in ALL_MATS:
        m = new_mat(key, blend="BLEND" if key == "PBR_Glass" else "OPAQUE")
        BUILDERS[key](m)
        mats[key] = m
    counts = apply_to_scene(mats)
    make_previews(mats)
    result = {
        "m1": True,
        "materials": ALL_MATS,
        "applied": counts,
        "preview_spheres": [k for k in ALL_MATS],
        "engine": bpy.context.scene.render.engine,
    }
    print("M1 result:", result)
    return result


result = main()
