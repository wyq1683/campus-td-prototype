import bpy
from mathutils import Vector

def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs), max(c.x for c in cs),
            min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs)]

plaza_info = []
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.type == "MESH" and ("Plaza" in o.name or "Floor" in o.name or (o.name.startswith("M11_") and ("Plaza" in o.name or "Road" in o.name))):
        b = aabb(o)
        plaza_info.append({"name": o.name, "z": [round(b[4], 4), round(b[5], 4)], "y": [round(b[2], 2), round(b[3], 2)]})

m59_info = []
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.name.startswith("M59_"):
        b = aabb(o)
        m59_info.append({"name": o.name, "z": [round(b[4], 4), round(b[5], 4)], "xy": [round((b[0]+b[1])/2, 2), round((b[2]+b[3])/2, 2)]})

result = {"plaza": plaza_info, "m59": m59_info}
print(result)
