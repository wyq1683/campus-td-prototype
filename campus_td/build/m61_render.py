# -*- coding: utf-8 -*-
"""
M61 · 渲染（仅渲染，build/render 分离，沿用 M56–M60 教训）
用 M61_Cam（首根立杆特写）出 closeup，再用已验证白昼英雄机位 M19C_HeroDay 出校园语境图。
"""
import bpy
import mathutils

sc = bpy.context.scene
PREVIEW = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"

# 渲染设定
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

import os
os.makedirs(PREVIEW, exist_ok=True)

# 1) closeup：首根立杆特写
cam = bpy.data.objects.get("M61_Cam")
if cam is None:
    result = {"error": "M61_Cam not found"}
else:
    sc.camera = cam
    sc.render.filepath = PREVIEW + r"/m61_cctv_closeup.png"
    bpy.ops.render.render(write_still=True)

# 2) hero：白昼校园语境图（监控立杆在周界成环）
hero = bpy.data.objects.get("M19C_HeroDay")
if hero is not None:
    sc.camera = hero
    sc.render.filepath = PREVIEW + r"/m61_cctv_hero.png"
    bpy.ops.render.render(write_still=True)

result = {
    "rendered_closeup": PREVIEW + r"/m61_cctv_closeup.png",
    "rendered_hero": PREVIEW + r"/m61_cctv_hero.png",
    "engine": sc.render.engine,
    "objects": len(bpy.data.objects),
}
print("M61_RENDER=" + repr(result))
