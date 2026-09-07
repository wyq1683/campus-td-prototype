# _m15_verify_probe.py — diagnose whether M11 verify all_ok=False in render_m15
# was caused by stale misplaced M08C components persisting in the live scene.
import bpy, mathutils
exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m11_masterplan.py").read(), "m11", "exec"))

def bbox2(objs):
    mn = [1e9, 1e9]; mx = [-1e9, -1e9]
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            mn[0] = min(mn[0], w[0]); mx[0] = max(mx[0], w[0])
            mn[1] = min(mn[1], w[1]); mx[1] = max(mx[1], w[1])
    return mn[0], mn[1], mx[0], mx[1]

# expected shell footprint per MASTERPLAN target center ± half-extent guesses
EXPECT = {
    "Teach":   (-32.5, -37.5, 32.5, -20.5),
    "Lab":     (-24.5, 23.5, 24.5, 38.5),
    "Admin":   (-45.0, 26.0, -31.0, 36.0),
    "Library": (-46.0, 6.0, -30.0, 18.0),
    "Dorm":    (-45.5, -9.0, -30.5, 1.0),
    "Gym":     (24.5, -0.5, 39.5, 12.5),
    "Canteen": (28.5, -15.5, 43.5, -4.5),
}

diag = {}
for b in ORDER:
    objs = [o for o in bpy.data.objects if owner(o.name) == b]
    ex = EXPECT[b]
    outliers = []
    for o in objs:
        x0, y0, x1, y1 = bbox2([o])
        # flag any object that pokes clearly outside the expected shell footprint
        outside = (x0 < ex[0] - 0.5 or x1 > ex[2] + 0.5 or
                   y0 < ex[1] - 0.5 or y1 > ex[3] + 0.5)
        if outside:
            outliers.append({"name": o.name, "type": o.type,
                             "box": [round(x0,2), round(y0,2), round(x1,2), round(y1,2)],
                             "loc": [round(o.location.x,2), round(o.location.y,2), round(o.location.z,2)]})
    diag[b] = {"n": len(objs), "n_out": len(outliers), "outliers": outliers}

vf = verify()
result = {
    "verify_all_ok": vf["all_ok"],
    "verify_clash": vf["clash"],
    "verify_boxes": vf["boxes"],
    "per_building_outliers": diag,
    "total_outlier_objs": sum(d["n_out"] for d in diag.values()),
    "n_step_objects": sum(1 for o in bpy.data.objects if o.name.endswith("_Steps")),
    "objects": len(bpy.data.objects),
}
print("PROBE result:", result)
