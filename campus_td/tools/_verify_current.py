# _verify_current.py — read-only ground-truth probe for the M11-era indoor coordinate fix.
# Does NOT import m11_masterplan (its module-level main() would rebuild the site).
import bpy
import mathutils

KNOWN = ["Teach", "Lab", "Admin", "Library", "Dorm", "Gym", "Canteen"]
# Indoor / light / halo objects that must sit inside their building footprint.
INDOOR_PREFIXES = ("M8_", "M8D_", "M8E_", "M8_Halo_", "M6_Halo_M8_", "Furn_", "Int_")
MISPLACE_TH = 30.0  # meters from building center -> suspected leftover at pre-M11 coords


def bldg_center(bname):
    xs, ys = [], []
    for o in bpy.data.objects:
        if not o.name.startswith("Bldg_%s" % bname):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector((c[0], c[1], c[2], 1.0))
            xs.append(w.x)
            ys.append(w.y)
    if not xs:
        return None
    return ((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5)


def bcode(name):
    for k in KNOWN:
        if k in name:
            return k
    return None


centers = {k: bldg_center(k) for k in KNOWN}
scene_objs = len(bpy.data.objects)

per_b = {k: 0 for k in KNOWN}
outliers = []
for o in bpy.data.objects:
    if not o.name.startswith(INDOOR_PREFIXES):
        continue
    bc = bcode(o.name)
    cx = o.matrix_world.translation.x
    cy = o.matrix_world.translation.y
    if bc is None or centers[bc] is None:
        outliers.append((o.name, "no-center"))
        continue
    d = ((cx - centers[bc][0]) ** 2 + (cy - centers[bc][1]) ** 2) ** 0.5
    if d > MISPLACE_TH:
        outliers.append((o.name, round(d, 1)))
    else:
        per_b[bc] += 1

# Count m08-style key markers
m8_halo = sum(1 for o in bpy.data.objects if o.name.startswith("M8_Halo_"))
m6_halo_m8 = sum(1 for o in bpy.data.objects if o.name.startswith("M6_Halo_M8_"))

result = {
    "scene_objs": scene_objs,
    "centers": {k: (round(v[0], 2), round(v[1], 2)) if v else None for k, v in centers.items()},
    "indoor_per_building": per_b,
    "total_indoor_checked": sum(per_b.values()),
    "outlier_objs": len(outliers),
    "outlier_sample": outliers[:20],
    "m8_halo_shells": m8_halo,
    "m6_halo_m8_shells": m6_halo_m8,
}
print("VERIFY_CURRENT:", result)
