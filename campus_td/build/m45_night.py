# -*- coding: utf-8 -*-
"""
M45 · 夜间展示态（Night Preview State）
把场景切到暗调夜空，露出 M45 泛光灯塔的球场照明效果，供 render_viewport_to_path 出夜战预览。
结束由 m45_restore.py 恢复白昼基线（单一 'World'、曝光 0、相机 M19C_HeroDay），避免污染后续里程碑。
"""
import bpy
from mathutils import Vector

PREFIX = "M45_"

# 新建暗调夜空（独立 World，不碰白昼基线）
wname = PREFIX + "NightWorld"
nw = bpy.data.worlds.get(wname)
if nw is None:
    nw = bpy.data.worlds.new(wname)
nw.use_nodes = True
nt = nw.node_tree
# 清空默认节点
for nd in list(nt.nodes):
    nt.nodes.remove(nd)
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = [0.012, 0.022, 0.050, 1.0]   # 暗蓝夜空
bg.inputs["Strength"].default_value = 1.0
out = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

sc = bpy.context.scene
sc.world = nw
try:
    sc.view_settings.exposure = -0.35
except Exception as e:
    pass

cam = bpy.data.objects.get("M39_Cam") or bpy.data.objects.get("M19C_HeroDay")
if cam is not None:
    sc.camera = cam

n_m45 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
print("M45_NIGHT_STATE=" + repr({
    "world": nw.name,
    "exposure": sc.view_settings.exposure,
    "camera": sc.camera.name if sc.camera else None,
    "n_m45_objects": n_m45,
}))
