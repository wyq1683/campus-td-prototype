# probe_layout.py — 探测 Bldg_* 关键建筑的世界包围盒（前缀匹配）
import bpy, mathutils

watch = ("Bldg_Teach", "Bldg_Lab", "Bldg_C", "Bldg_D", "Bldg_E", "Bldg_F")
res = []
for o in bpy.data.objects:
    base = o.name.split("_")[0] + "_" + o.name.split("_")[1] if o.name.count("_") >= 1 else o.name
    if not any(o.name.startswith(w) for w in watch):
        continue
    pts = [o.matrix_world @ mathutils.Vector(v) for v in o.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    res.append({
        "name": o.name,
        "x": [round(min(xs), 1), round(max(xs), 1)],
        "y": [round(min(ys), 1), round(max(ys), 1)],
        "z": [round(min(zs), 1), round(max(zs), 1)],
    })
result = {"bldg_objs": res}
print("PROBE:", result)
