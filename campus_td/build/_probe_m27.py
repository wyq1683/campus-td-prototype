import bpy, json
roofs = [o.name for o in bpy.data.objects if o.type == "MESH" and o.name.lower().endswith("_roof")]
site = [o.name for o in bpy.data.objects if o.name.startswith("Site_")]
ground = [o.name for o in bpy.data.objects if "ground" in o.name.lower()]
bldg = [o.name for o in bpy.data.objects if o.name.startswith("Bldg_")][:30]
print("PROBE_ROOFS=" + json.dumps(roofs))
print("PROBE_SITE=" + json.dumps(site))
print("PROBE_GROUND=" + json.dumps(ground))
print("PROBE_BLDG_COUNT=" + str(sum(1 for o in bpy.data.objects if o.name.startswith("Bldg_"))))
result = {"roofs": roofs, "site": site, "ground": ground}
