# m01b_scanned_materials.py  — M1b CC0 扫描贴图材质库
# 来源：Poly Haven (CC0) 经 tools/fetch_ph_textures.py 拉到 assets/textures/<slug>/
# 设计：
#   - 幂等：清掉旧的 Mat_CC0_* 与预览球再重建。
#   - 用 Box 投影 + Generated 坐标（三平面式），不依赖网格 UV，密度由 Mapping 缩放控制。
#   - 每材质按 manifest 的 roles 连 Principled BSDF：diff(sRGB)->BaseColor,
#     nor(Non-Color)->NormalMap, arm 拆 R/G/B -> AO/Rough/Metallic；另有 rough/ao/metal 单独图则覆盖；
#     disp(Non-Color)->Bump 串接法线；AO 通过 Mix(MULTIPLY) 压到 BaseColor（5.2 的 BSDF 无 AO 输入）。
#   - 应用目标与 m01_materials.MAT_BY_TARGET 对齐（glass/enemy/glow 保留程序化）。
# 插件：Node Wrangler 已启用，可在 UI 对任意 CC0 文件夹用 "Add Principled Setup" 交互式重建；
#       本脚本用确定性构建器保证 headless 幂等重建（项目铁律：重建脚本不得依赖脆弱的上下文相关算子）。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m01b_scanned_materials.py").read(),"m01b","exec"))')

import bpy, json, os

# 本构建脚本随项目固定路径运行（经 MCP exec 时无 __file__），直接写死 ROOT。
ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
TEX = os.path.join(ROOT, "assets", "textures")
MANIFEST = os.path.join(TEX, "manifest.json")
PREFIX = "Mat_CC0_"

DISPLAY = {"grass": "Grass", "asphalt": "Asphalt", "brick": "Brick",
           "concrete": "Concrete", "tile": "Tile", "metal": "Metal", "wood": "Wood"}
# Box 投影重复密度（Generated 0..1 乘以该值 = 跨包围盒重复次数）
TILING = {"grass": 30.0, "asphalt": 12.0, "brick": 10.0, "concrete": 8.0,
          "tile": 16.0, "metal": 6.0, "wood": 4.0}

# V1.1: 目标分辨率（默认升 2K；该 res 缺失时回退 1K）。可用环境变量 M1B_RES 覆盖为 "4k" 等。
RES = os.environ.get("M1B_RES", "2k")


def pick_roles(entry):
    """从 manifest 条目中挑选当前 RES 的 roles 字典；该 res 缺失则回退 1K。"""
    res = entry.get("res", {})
    chosen = res.get(RES) or res.get("1k")
    return chosen["roles"] if chosen else {}


_IMAGES = {}


def load_img(abspath):
    if abspath in _IMAGES:
        return _IMAGES[abspath]
    img = bpy.data.images.load(abspath)
    img.colorspace_settings.name = "sRGB"  # 默认；按角色改
    _IMAGES[abspath] = img
    return img


def clear_old():
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX + "Preview_"):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data:
                try:
                    bpy.data.meshes.remove(data)
                except Exception:
                    pass


def img_node(nt, abspath, colorspace, label, x, y, vec):
    it = nt.nodes.new("ShaderNodeTexImage")
    it.location = (x, y)
    it.image = load_img(abspath)
    it.image.colorspace_settings.name = colorspace
    it.projection = "BOX"
    it.projection_blend = 0.2
    it.extension = "REPEAT"
    it.label = label
    nt.links.new(vec, it.inputs["Vector"])
    return it


def build(target, slug, roles):
    mat = bpy.data.materials.new(PREFIX + DISPLAY[target])
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.location = (400, 0)
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])

    # 坐标：Generated -> Mapping(Scale) -> 共享 vec
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-1500, 0)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (-1300, 0)
    s = TILING[target]
    mp.inputs["Scale"].default_value = (s, s, s)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    vec = mp.outputs["Vector"]

    path = lambda role: os.path.join(ROOT, roles[role])

    # ARM 打包（R=AO, G=Rough, B=Metal），优先于单独图解析
    arm_ao = arm_rough = arm_metal = None
    if "arm" in roles:
        arm = img_node(nt, path("arm"), "Non-Color", "ARM", -1000, -450, vec)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.mode = "RGB"
        sep.location = (-700, -450)
        nt.links.new(arm.outputs["Color"], sep.inputs["Color"])
        arm_ao, arm_rough, arm_metal = sep.outputs["Red"], sep.outputs["Green"], sep.outputs["Blue"]

    # 基础色 + AO（5.2 BSDF 无 AO 输入 -> 用 Mix(MULTIPLY) 压到 BaseColor）
    base_src = None
    if "diff" in roles:
        col = img_node(nt, path("diff"), "sRGB", "Albedo", -1000, 300, vec)
        base_src = col.outputs["Color"]
        ao_src = None
        if "ao" in roles:
            ao_img = img_node(nt, path("ao"), "Non-Color", "AO", -700, -650, vec)
            ao_src = ao_img.outputs["Color"]
        elif arm_ao:
            ao_src = arm_ao
        if ao_src is not None:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.location = (100, -100)
            nt.links.new(base_src, mix.inputs["A"])
            nt.links.new(ao_src, mix.inputs["B"])
            base_src = mix.outputs["Result"]
        nt.links.new(base_src, bs.inputs["Base Color"])

    # 法线（+ 位移做 Bump 串接）
    normal_in = None
    if "nor" in roles:
        nor = img_node(nt, path("nor"), "Non-Color", "Normal", -1000, 50, vec)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (100, 250)
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
        normal_in = nm.outputs["Normal"]
    if "disp" in roles:
        disp = img_node(nt, path("disp"), "Non-Color", "Disp", -1000, -200, vec)
        bump = nt.nodes.new("ShaderNodeBump")
        bump.location = (100, 450)
        bump.inputs["Strength"].default_value = 0.3
        nt.links.new(disp.outputs["Color"], bump.inputs["Height"])
        if normal_in:
            nt.links.new(normal_in, bump.inputs["Normal"])
        normal_in = bump.outputs["Normal"]
    if normal_in:
        nt.links.new(normal_in, bs.inputs["Normal"])

    # 粗糙度
    if "rough" in roles:
        r = img_node(nt, path("rough"), "Non-Color", "Rough", -700, -850, vec)
        nt.links.new(r.outputs["Color"], bs.inputs["Roughness"])
    elif arm_rough:
        nt.links.new(arm_rough, bs.inputs["Roughness"])

    # 金属度
    if "metal" in roles:
        mt = img_node(nt, path("metal"), "Non-Color", "Metal", -700, -1050, vec)
        nt.links.new(mt.outputs["Color"], bs.inputs["Metallic"])
    elif arm_metal:
        nt.links.new(arm_metal, bs.inputs["Metallic"])

    return mat


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
            target = None
        elif "tower" in name:
            target = "metal"
        elif "enemy" in name:
            target = None
        elif "bldg" in name:
            target = "brick"
        elif "_floor" in name:
            # 体育馆/食堂地面用瓷砖，其余室内地面用木地板
            target = "tile" if ("gym" in name or "canteen" in name
                                or "bath" in name or "toilet" in name) else "wood"
        elif any(k in name for k in ("desk", "chair", "shelf", "bookshelf", "bleacher")):
            target = "wood"
        if target:
            m = mats.get(PREFIX + DISPLAY[target])
            if apply_mat(o, m):
                counts[target] = counts.get(target, 0) + 1
    return counts


def make_previews(mats):
    for i, t in enumerate(DISPLAY):
        kname = PREFIX + DISPLAY[t]
        m = mats.get(kname)
        if not m:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(60.0 + i * 3.0, 4.0, 1.4))
        sph = bpy.context.active_object
        sph.name = PREFIX + "Preview_" + DISPLAY[t]
        sph.data.materials.append(m)


def main():
    manifest = json.load(open(MANIFEST))
    clear_old()
    mats = {}
    for target in DISPLAY:
        if target in manifest:
            roles = pick_roles(manifest[target])
            if roles:
                mats[PREFIX + DISPLAY[target]] = build(target, manifest[target]["slug"], roles)
    counts = apply_to_scene(mats)
    make_previews(mats)
    result = {
        "m1b": True,
        "materials": list(mats.keys()),
        "slugs": {t: manifest[t]["slug"] for t in manifest},
        "applied": counts,
        "preview_spheres": [PREFIX + "Preview_" + DISPLAY[t] for t in DISPLAY],
        "images_loaded": len(_IMAGES),
    }
    print("M1b result:", result)
    return result


result = main()
