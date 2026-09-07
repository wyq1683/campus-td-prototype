# m04_fix_materials.py — 修复 PBR_Brick / PBR_Concrete 缺少 Vector 输入导致渲染发灰
# 幂等：反复跑都能稳定接通 Generated→Mapping→Texture( Vector )并提亮砖色。
import bpy


def patch_brick():
    m = bpy.data.materials.get("PBR_Brick")
    if m is None or not m.use_nodes:
        return False
    nt = m.node_tree
    brick = next((n for n in nt.nodes if n.type == "TEX_BRICK"), None)
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if brick is None or bsdf is None:
        return False
    # 加 Texture Coordinate + Mapping（如已有则复用）
    tex = next((n for n in nt.nodes if n.type == "TEX_COORD"), None)
    if tex is None:
        tex = nt.nodes.new("ShaderNodeTexCoord")
        tex.location = (brick.location.x - 500, brick.location.y)
    mapping = next((n for n in nt.nodes if n.type == "MAPPING"), None)
    if mapping is None:
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.location = (brick.location.x - 280, brick.location.y)
    mapping.inputs["Scale"].default_value = (10.0, 10.0, 10.0)
    # 接线：Generated → Mapping.Vector → BrickTexture.Vector
    def link(a, b, fs, ts):
        if not any(l.from_node == a and l.to_node == b and l.from_socket.name == fs and l.to_socket.name == ts for l in nt.links):
            nt.links.new(a.outputs[fs], b.inputs[ts])
    link(tex, mapping, "Generated", "Vector")
    link(mapping, brick, "Vector", "Vector")
    # 砖色提亮（暖红）+ 加大尺度让花纹可见
    brick.inputs["Color1"].default_value = (0.58, 0.24, 0.18, 1.0)
    brick.inputs["Color2"].default_value = (0.68, 0.30, 0.22, 1.0)
    brick.inputs["Mortar"].default_value = (0.30, 0.28, 0.26, 1.0)
    brick.inputs["Scale"].default_value = 8.0
    brick.inputs["Mortar Size"].default_value = 0.02
    bsdf.inputs["Roughness"].default_value = 0.75
    return True


def patch_concrete():
    m = bpy.data.materials.get("PBR_Concrete")
    if m is None or not m.use_nodes:
        return False
    nt = m.node_tree
    noise = next((n for n in nt.nodes if n.type == "TEX_NOISE"), None)
    if noise is None:
        return False
    tex = next((n for n in nt.nodes if n.type == "TEX_COORD"), None)
    if tex is None:
        tex = nt.nodes.new("ShaderNodeTexCoord")
        tex.location = (noise.location.x - 400, noise.location.y)
    if not any(l.from_node == tex and l.to_node == noise and l.from_socket.name == "Generated" for l in nt.links):
        nt.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.52, 0.52, 0.52, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
    return True


result = {"brick": patch_brick(), "concrete": patch_concrete()}
print("FIX:", result)