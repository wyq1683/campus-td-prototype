# probe_m67_stack.py — enumerate vertical stack above hero target (-2,-13)
import bpy, mathutils
dg = bpy.context.evaluated_depsgraph_get()
ox, oy = -2.0, -13.0
hits = []
z = 8.0
d = mathutils.Vector((0.0, 0.0, -1.0))
for _ in range(20):
    res = bpy.context.scene.ray_cast(dg, mathutils.Vector((ox, oy, z)), d, distance=z + 1)
    if not res[0]:
        break
    loc = res[1]
    obj = res[4]            # Object
    pidx = res[3]           # polygon index
    mtl_name = "?"
    if obj is not None and obj.data is not None and hasattr(obj.data, "polygons") and pidx >= 0:
        try:
            mi = obj.data.polygons[pidx].material_index
            mats = obj.data.materials
            if mi < len(mats):
                mtl_name = mats[mi].name if mats[mi] else "?"
        except Exception as e:
            mtl_name = "err:%s" % e
    hits.append((round(loc.z, 3), obj.name if obj else "?", mtl_name))
    nz = loc.z - 0.05
    if nz < -1:
        break
    z = nz
print("STACK_ABOVE", ox, oy)
for h in hits:
    print(h)

# Also: count materials among M67 / nearby to see if green source exists
print("M67_OBJS", [o.name for o in bpy.data.objects if o.name.startswith("M67_")])
# cam check
cam = bpy.data.objects.get("M67_Cam")
if cam:
    print("CAM_LOC", tuple(cam.location), "ROT", tuple(cam.rotation_euler))
# list any object whose AABB contains (ox,oy)
print("CONTAINERS:")
for o in bpy.data.objects:
    if o.bound_box is None:
        continue
    try:
        corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        if min(xs)-0.3 <= ox <= max(xs)+0.3 and min(ys)-0.3 <= oy <= max(ys)+0.3:
            if max(zs) > 0.3:
                print(o.name, "zmax=%.2f" % max(zs), "mats=", [m.name if m else None for m in o.data.materials] if o.data and hasattr(o.data,'materials') else "?")
    except Exception:
        pass
result = {"hits": hits}
