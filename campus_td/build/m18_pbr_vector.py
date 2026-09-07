# m18_pbr_vector.py — M18 里程碑：PBR 材质 Vector 全局修复（防复发）
# 幂等 in-place 补丁：不删/不重建任何材质，只给每个程序化纹理节点接通
#   Generated 坐标（砖类 PBR_Brick 经 Mapping(Scale 10)，与 M4 已验证密度一致；
#   其余 Noise/Voronoi/Tile 用纯 Generated，避免 Mapping 放大导致过密）。
# 解决 PLAN 避坑 #8 + M4 实测：未连 Vector 时 Brick 默认采样落在 mortar 整面发灰。
# 覆盖 M4 只修过 PBR_Brick/PBR_Concrete 的缺口：PBR_Tile 及 Grass/Asphalt/Wood 的
#   Noise 纹理此前同样缺 Vector（虽 Noise 默认即 Generated，显式连通 = 防复发）。
import bpy

TARGETS = ["PBR_Grass", "PBR_Asphalt", "PBR_Brick", "PBR_Concrete",
           "PBR_Glass", "PBR_Wood", "PBR_Metal", "PBR_Tile",
           "Mat_Glow", "Mat_Enemy"]

# 需要 Vector 的纹理节点类型
TEX_TYPES = {"TEX_NOISE", "TEX_VORONOI", "TEX_BRICK", "TEX_MUSGRAVE",
             "TEX_WAVE", "TEX_CHECKER", "TEX_WHITE_NOISE"}

# 仅 PBR_Brick 使用 Mapping(Scale 10)（M4 已验证大砖密度）；PBR_Tile 用节点自身 Scale(22)。
BRICK_MAPPING = {"PBR_Brick": True, "PBR_Tile": False}


def ensure_coords(nt):
    """每个材质树建一个 TexCoord(Generated)；砖类再接 Mapping(Scale 10)。
    返回 (gen_socket, brick_vec_socket)。幂等：复用已有节点。"""
    tc = next((n for n in nt.nodes if n.type == "TEX_COORD"), None)
    if tc is None:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tc.location = (-1200, 0)
    gen = tc.outputs["Generated"]
    mp = next((n for n in nt.nodes if n.type == "MAPPING"), None)
    if mp is None:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.location = (-1000, 0)
        mp.inputs["Scale"].default_value = (10.0, 10.0, 10.0)
        nt.links.new(gen, mp.inputs["Vector"])
    return gen, mp.outputs["Vector"]


def patch_material(m, use_brick_mapping=True):
    if not m.use_nodes:
        return 0
    nt = m.node_tree
    gen, brick_vec = ensure_coords(nt)
    added = 0
    for n in nt.nodes:
        if n.type not in TEX_TYPES:
            continue
        if "Vector" not in n.inputs:
            continue
        if n.inputs["Vector"].is_linked:
            continue
        vec = brick_vec if (n.type == "TEX_BRICK" and use_brick_mapping) else gen
        nt.links.new(vec, n.inputs["Vector"])
        added += 1
    return added


def main():
    summary = {}
    total_added = 0
    for name in TARGETS:
        m = bpy.data.materials.get(name)
        if m is None:
            summary[name] = {"present": False}
            continue
        added = patch_material(m, BRICK_MAPPING.get(name, False))
        total_added += added
        nt = m.node_tree
        tex_nodes = [n for n in nt.nodes if n.type in TEX_TYPES]
        linked = sum(1 for n in tex_nodes
                     if "Vector" in n.inputs and n.inputs["Vector"].is_linked)
        summary[name] = {"present": True, "tex_nodes": len(tex_nodes),
                         "vector_linked": linked, "added_now": added}
    result = {"m18": True, "total_added": total_added, "materials": summary}
    print("M18 result:", result)
    return result


result = main()
