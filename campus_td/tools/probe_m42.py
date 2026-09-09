# probe_m42.py — M42 选址探针：检查球场四周拟建广告牌/端线围网处是否已有物体
import bpy
from mathutils import Vector

CX, CY = -3.0, 0.0

def aabb(o):
    try:
        cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    except Exception:
        return None
    xs = [c.x for c in cs]; ys = [c.y for c in cs]; zs = [c.z for c in cs]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def overlaps(a, box):
    if a is None: return False
    x0,x1,y0,y1,z0,z1 = a
    bx0,bx1,by0,by1,bz0,bz1 = box
    return not (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1 or z1 < bz0 or z0 > bz1)

# 拟建区域
zones = {
    # 端线高围网（西/东）
    "fence_W": (CX-20.0, CX-18.0, CY-13.0, CY+13.0, 0.2, 7.0),
    "fence_E": (CX+18.0, CX+20.0, CY-13.0, CY+13.0, 0.2, 7.0),
    # 边线广告牌（南/北）位于看台前缘之前
    "boards_N": (CX-17.0, CX+17.0, CY+8.9, CY+9.5, 0.05, 1.2),
    "boards_S": (CX-17.0, CX+17.0, CY-9.5, CY-8.9, 0.05, 1.2),
}

hits = {k: [] for k in zones}
for o in bpy.data.objects:
    if o.type not in ("MESH",): continue
    nm = o.name
    a = aabb(o)
    for k, box in zones.items():
        if overlaps(a, box):
            hits[k].append(nm)

def brief(lst, n=14):
    return sorted(lst)[:n]

# 关键参考物 AABB
refs = {}
for nm in ("M11_PlazaCourt", "M38_Pitch", "M38_Track", "M39_Scoreboard_Panel",
           "M41_Bleacher_N_4", "M41_Bleacher_S_4", "Ground"):
    o = bpy.data.objects.get(nm)
    if o:
        a = aabb(o)
        refs[nm] = [round(v,2) for v in a] if a else None

# 找 M39 记分牌相关名字
sb = sorted([o.name for o in bpy.data.objects if o.name.startswith("M39_") and "Score" in o.name])

result = {
    "n_total": len(bpy.data.objects),
    "hits_counts": {k: len(v) for k, v in hits.items()},
    "hits_fence_W": brief(hits["fence_W"]),
    "hits_fence_E": brief(hits["fence_E"]),
    "hits_boards_N": brief(hits["boards_N"]),
    "hits_boards_S": brief(hits["boards_S"]),
    "refs": refs,
    "scoreboard_objs": sb,
    "has_PBR_Metal": "PBR_Metal" in bpy.data.materials,
    "has_PBR_Concrete": "PBR_Concrete" in bpy.data.materials,
    "cam_now": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
    "m42_existing": len([o for o in bpy.data.objects if o.name.startswith("M42_")]),
}
print("PROBE_M42", result)
