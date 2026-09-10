# probe_m67_obs.py — list AABBs of obstacles + road segments to pick clear bump offsets
import bpy, mathutils

def world_aabb(o):
    if o.bound_box is None:
        return None
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
    return (min(xs), min(ys), max(xs), max(ys), max(zs))

print("=== OBSTACLES (towers/bleachers near road midpoints) ===")
for nm in ["M7_Ring_Tower_2", "M41_Bleacher_S_4", "M41_Bleacher_N_4"]:
    o = bpy.data.objects.get(nm)
    if o:
        a = world_aabb(o)
        print(nm, "AABB=(%.1f,%.1f)-(%.1f,%.1f) zmax=%.2f" % (a[0],a[1],a[2],a[3],a[4]))
    else:
        print(nm, "MISSING")

print("=== ROADS ===")
for o in bpy.data.objects:
    if o.name.startswith("Road") and world_aabb(o):
        a = world_aabb(o)
        print(o.name, "AABB=(%.1f,%.1f)-(%.1f,%.1f) zmax=%.3f" % (a[0],a[1],a[2],a[3],a[4]))

# All M41 bleachers AABB (to know extent along roads)
print("=== ALL M41 BLEACHERS ===")
for o in bpy.data.objects:
    if o.name.startswith("M41_Bleacher"):
        a = world_aabb(o)
        if a:
            print(o.name, "(%.1f,%.1f)-(%.1f,%.1f)" % (a[0],a[1],a[2],a[3]))

# All M7 towers AABB
print("=== ALL M7 TOWERS ===")
for o in bpy.data.objects:
    if o.name.startswith("M7_") and "Tower" in o.name:
        a = world_aabb(o)
        if a:
            print(o.name, "(%.1f,%.1f)-(%.1f,%.1f) zmax=%.2f" % (a[0],a[1],a[2],a[3],a[4]))

result = {"ok": True}
