# -*- coding: utf-8 -*-
"""M63 渲染 + 几何自检（build/render 分离）。"""
import bpy
from mathutils import Vector

sc = bpy.context.scene
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

OUT = r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\previews"
PREFIX = "M63_"

# ---- closeup（站亭特写：小物体易落阴影，+0.8 提亮保证可读）----
sc.view_settings.exposure = 0.8
cam = bpy.data.objects.get(PREFIX + "Cam")
if cam is not None:
    sc.camera = cam
sc.render.filepath = OUT + r"\m63_sorting_closeup.png"
bpy.ops.render.render(write_still=True)

# ---- hero（复用校园英雄机位，标准曝光 0.0）----
sc.view_settings.exposure = 0.0
hero = bpy.data.objects.get("M19C_HeroDay")
if hero is not None:
    sc.camera = hero
sc.render.filepath = OUT + r"\m63_sorting_hero.png"
bpy.ops.render.render(write_still=True)

# ---- 几何自检：M63 是否与任一 Bldg_ AABB 相交 ----
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs), max(c.x for c in cs),
            min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs)]

m63 = [aabb(o) for o in bpy.data.objects if o.name.startswith(PREFIX)]
bldg = [aabb(o) for o in bpy.data.objects if o.name.startswith("Bldg_")]
# M63 union
if m63:
    ux0 = min(b[0] for b in m63); ux1 = max(b[1] for b in m63)
    uy0 = min(b[2] for b in m63); uy1 = max(b[3] for b in m63)
    uz0 = min(b[4] for b in m63); uz1 = max(b[5] for b in m63)
else:
    ux0 = ux1 = uy0 = uy1 = uz0 = uz1 = 0.0
hit = []
for b in bldg:
    if ux0 < b[1] and ux1 > b[0] and uy0 < b[3] and uy1 > b[2] and uz0 < b[5] and uz1 > b[4]:
        hit.append(b[0:2])
result = {
    "render": "ok",
    "m63_union": [round(ux0,2), round(ux1,2), round(uy0,2), round(uy1,2), round(uz0,2), round(uz1,2)],
    "bldg_intersections": len(hit),
}
print("M63_RENDER=" + repr(result))
