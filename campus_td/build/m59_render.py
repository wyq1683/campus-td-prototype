# -*- coding: utf-8 -*-
"""
M59 · 渲染（仅出图，不建物体）
复用 M59_Cam 圆雕特写 + M19C_HeroDay 校园语境，白昼 Cycles GPU OptiX。
特写加临时 POINT 补光，渲染后清理零孤儿。
"""
import bpy
import os
from mathutils import Vector

PREFIX = "M59_"
PREVIEW_DIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
os.makedirs(PREVIEW_DIR, exist_ok=True)

sc = bpy.context.scene
rendered = []
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    try:
        sc.cycles.compute_device_type = "OPTIX"
    except Exception:
        pass
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.0

    hero = bpy.data.objects.get("M19C_HeroDay")
    cam = bpy.data.objects.get(PREFIX + "Cam")
    if cam is not None:
        cam.data.lens = 35.0
        bpy.context.view_layer.update()

    # 1) 校园语境（英雄机位）
    if hero is not None:
        sc.camera = hero
        sc.render.filepath = PREVIEW_DIR + "/m59_gate_emblem_hero.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)

    # 2) 圆雕特写（临时补光，结束清理）
    if cam is not None:
        sc.camera = cam
        fill = bpy.data.lights.new(PREFIX + "FillLight", "POINT")
        fill.energy = 120.0
        fill.color = (1.0, 0.96, 0.88)
        fill_obj = bpy.data.objects.new(PREFIX + "Fill", fill)
        fill_obj.location = cam.location + Vector((0.0, 0.0, 0.5))
        bpy.context.scene.collection.objects.link(fill_obj)
        bpy.context.view_layer.update()
        sc.render.filepath = PREVIEW_DIR + "/m59_gate_emblem_closeup.png"
        bpy.ops.render.render(write_still=True)
        rendered.append(sc.render.filepath)
        bpy.data.objects.remove(fill_obj, do_unlink=True)
        bpy.data.lights.remove(fill)
        if hero is not None:
            sc.camera = hero
except Exception as e:
    rendered.append("RENDER_WARN:" + str(e))

n_m59 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
print("M59_RENDER=" + repr({"rendered": rendered, "n_m59_objects": n_m59}))
