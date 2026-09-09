# -*- coding: utf-8 -*-
"""
M45 · 恢复白昼基线（Restore Day Baseline）
删除 M45_NightWorld、恢复单一 'World'、曝光 0、相机 M19C_HeroDay。
保证场景回到 M45 几何建好后的白昼稳定态，不污染后续自动化里程碑。
"""
import bpy

PREFIX = "M45_"

sc = bpy.context.scene
day_world = bpy.data.worlds.get("World")
if day_world is not None:
    sc.world = day_world
# 删除临时夜空（若存在且非白昼基线）
nw = bpy.data.worlds.get(PREFIX + "NightWorld")
if nw is not None and nw != day_world:
    bpy.data.worlds.remove(nw, do_unlink=True)

try:
    sc.view_settings.exposure = 0.0
except Exception:
    pass

cam = bpy.data.objects.get("M19C_HeroDay")
if cam is not None:
    sc.camera = cam

print("M45_RESTORED=" + repr({
    "world": sc.world.name if sc.world else None,
    "exposure": sc.view_settings.exposure,
    "camera": sc.camera.name if sc.camera else None,
    "n_worlds": len(bpy.data.worlds),
}))
