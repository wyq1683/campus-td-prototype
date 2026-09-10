# probe_m67_cam.py — check actual M67_Cam and geometry at (-2,-13)
import bpy, mathutils

cam = bpy.data.objects.get("M67_Cam")
if cam:
    print("M67_Cam loc=", tuple(cam.location))
    print("M67_Cam rot=", tuple(cam.rotation_euler))
    print("M67_Cam lens=", cam.data.lens if cam.data else None)
else:
    print("M67_Cam MISSING")

# What's at (-2,-13,8) downward?
dg = bpy.context.evaluated_depsgraph_get()
d = mathutils.Vector((0,0,-1))
for start_z in [8, 6, 4, 2]:
    res = bpy.context.scene.ray_cast(dg, mathutils.Vector((-2.0,-13.0,start_z)), d, distance=start_z+1)
    print("ray from z=%d:" % start_z, "hit=%s loc=%s obj=%s" % (res[0], tuple(res[1]) if res[0] else None, res[4].name if res[0] and res[4] else None))

# list objects near (-2,-13) in xy
print("NEAR (-2,-13):")
for o in bpy.data.objects:
    if o.bound_box is None: continue
    try:
        corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        xs=[c.x for c in corners]; ys=[c.y for c in corners]; zs=[c.z for c in corners]
        if min(xs)<= -2 <= max(xs) and min(ys)<= -13 <= max(ys) and max(zs)>0.5:
            print(o.name, "x(%.1f,%.1f) y(%.1f,%.1f) zmax=%.2f" % (min(xs),max(xs),min(ys),max(ys),max(zs)))
    except Exception:
        pass
result = {"ok": True}
