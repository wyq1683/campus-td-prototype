import bpy
out = {}
for b in ("Admin", "Dorm", "Gym", "Canteen", "Library"):
    ws = [o for o in bpy.data.objects if o.name.startswith("Bldg_%s_W" % b)]
    info = []
    for o in ws:
        info.append({
            "name": o.name,
            "loc": [round(v, 2) for v in o.location],
            "dim": [round(v, 2) for v in o.dimensions],
        })
    out[b] = info
result = out
print("WALLS:", result)
