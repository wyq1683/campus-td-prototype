# _m15_probe.py — 一次性探针：摸清 M8C 斜板楼梯在场景里的实际状态
# 为什么：M11 总平重排把 7 栋楼整体挪过，M8C 脚本里的 center 常量是**旧坐标**，
#        不能拿来定位。必须读场景里对象的**当前** location，按 M12 机位自适应的同一思路。
# 运行：exec(compile(open(r"...\campus_td\tools\_m15_probe.py").read(), "p", "exec"))

import bpy
import re

PAT = re.compile(r"^M8C_(\w+)_Stair_(\d+)$")


def probe():
    out = []
    for o in bpy.data.objects:
        m = PAT.match(o.name)
        if m is None:
            continue
        out.append({
            "name": o.name,
            "bldg": m.group(1),
            "floor": int(m.group(2)),
            "loc": [round(v, 3) for v in o.location],
            "dim": [round(v, 3) for v in o.dimensions],
            "rot": [round(v, 4) for v in o.rotation_euler],
            "mods": [md.type for md in o.modifiers],
        })
    out.sort(key=lambda d: (d["bldg"], d["floor"]))
    return out


stairs = probe()
# 每栋楼的外壳 AABB（用来算楼梯井可用进深）
shells = {}
for b in ("Admin", "Dorm", "Canteen", "Library"):
    xs, ys = [], []
    for o in bpy.data.objects:
        if o.name.startswith("Bldg_%s" % b) or o.name.startswith("M8C_%s" % b):
            bb = o.bound_box
            for c in bb:
                xs.append(o.matrix_world @ __import__("mathutils").Vector(c))
    if xs:
        shells[b] = {
            "y_min": round(min(v.y for v in xs), 2),
            "y_max": round(max(v.y for v in xs), 2),
        }

result = {
    "m15": True,
    "n_stairs": len(stairs),
    "stairs": stairs,
    "shells": shells,
    "per_building": {b: sum(1 for s in stairs if s["bldg"] == b) for b in ("Admin", "Dorm", "Canteen", "Library")},
    "objects": len(bpy.data.objects),
}
print("M15 PROBE:", result)
