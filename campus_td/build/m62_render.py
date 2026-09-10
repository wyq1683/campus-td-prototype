# -*- coding: utf-8 -*-
"""
M62 · 渲染（仅渲染，build/render 分离，沿用 M56–M61 教训）
用 M62_Cam（凉亭特写）出 closeup，再用已验证白昼英雄机位 M19C_HeroDay 出校园语境图。
"""
import bpy
import os

sc = bpy.context.scene
PREVIEW = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"

sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
    sc.cycles.compute_device_type = "OPTIX"
except Exception:
    pass
sc.cycles.samples = 256
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.view_settings.view_transform = "AgX"
sc.view_settings.exposure = 0.0

os.makedirs(PREVIEW, exist_ok=True)

# 1) closeup：凉亭特写
cam = bpy.data.objects.get("M62_Cam")
if cam is None:
    result = {"error": "M62_Cam not found"}
else:
    sc.camera = cam
    sc.render.filepath = PREVIEW + r"/m62_gazebo_closeup.png"
    bpy.ops.render.render(write_still=True)

# 2) hero：白昼校园语境图
hero = bpy.data.objects.get("M19C_HeroDay")
if hero is not None:
    sc.camera = hero
    sc.render.filepath = PREVIEW + r"/m62_gazebo_hero.png"
    bpy.ops.render.render(write_still=True)

result = {
    "rendered_closeup": PREVIEW + r"/m62_gazebo_closeup.png",
    "rendered_hero": PREVIEW + r"/m62_gazebo_hero.png",
    "engine": sc.render.engine,
    "objects": len(bpy.data.objects),
}
print("M62_RENDER=" + repr(result))
