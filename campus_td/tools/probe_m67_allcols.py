# probe_m67_allcols.py — for each M67 speed bump, cast vertical column & report blockers
import bpy, mathutils
dg = bpy.context.evaluated_depsgraph_get()
d = mathutils.Vector((0.0, 0.0, -1.0))

def world_aabb(o):
    if o.bound_box is None:
        return None
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
    return (min(xs), min(ys), max(xs), max(ys), max(zs))

bumps = [o for o in bpy.data.objects if o.name.startswith("M67_BumpBase_")]
for b in bumps:
    a = world_aabb(b)
    cx = (a[0]+a[2])/2.0
    cy = (a[1]+a[3])/2.0
    topz = a[4]
    print("=== BUMP", b.name, "center=(%.1f,%.1f) topz=%.3f" % (cx, cy, topz))
    z = 8.0
    hits = []
    for _ in range(20):
        res = bpy.context.scene.ray_cast(dg, mathutils.Vector((cx, cy, z)), d, distance=z+1)
        if not res[0]:
            break
        loc = res[1]; obj = res[4]
        hits.append((round(loc.z,3), obj.name if obj else "?"))
        nz = loc.z - 0.05
        if nz < -1: break
        z = nz
    # report only non-trivial blockers above the bump
    blockers = [h for h in hits if h[0] > topz + 0.02 and not (h[1].startswith("M10D_") or h[1].startswith("M10C_") or h[1].startswith("Enemy_"))]
    print("  column:", hits)
    print("  PERSISTENT_BLOCKERS:", blockers)
result = {"ok": True}
