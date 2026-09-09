# probe_m42b.py — 读 M39 球门 / M40 球网当前世界 AABB，供 M42 真网眼对齐
import bpy
from mathutils import Vector

def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return [round(min(xs),3), round(max(xs),3), round(min(ys),3), round(max(ys),3), round(min(zs),3), round(max(zs),3)]

m39 = {o.name: aabb(o) for o in bpy.data.objects if o.name.startswith("M39_")}
m40 = {o.name: aabb(o) for o in bpy.data.objects if o.name.startswith("M40_")}

# 西/东球门整体 AABB（按名字含 W / E 归组）
def group_aabb(names):
    if not names: return None
    xs0=[];xs1=[];ys0=[];ys1=[];zs0=[];zs1=[]
    for n in names:
        a = m39[n]
        xs0.append(a[0]); xs1.append(a[1]); ys0.append(a[2]); ys1.append(a[3]); zs0.append(a[4]); zs1.append(a[5])
    return [round(min(xs0),3), round(max(xs1),3), round(min(ys0),3), round(max(ys1),3), round(min(zs0),3), round(max(zs1),3)]

goalW = [n for n in m39 if "Goal" in n and ("W" in n.split("Goal")[-1] or n.endswith("W") or "_W" in n)]
goalE = [n for n in m39 if "Goal" in n and ("E" in n.split("Goal")[-1] or n.endswith("E") or "_E" in n)]

result = {
    "m39_names": sorted(m39.keys()),
    "m40_names": sorted(m40.keys()),
    "m39_aabb": m39,
    "m40_aabb": m40,
    "goalW_guess": sorted(goalW), "goalW_aabb": group_aabb(goalW),
    "goalE_guess": sorted(goalE), "goalE_aabb": group_aabb(goalE),
}
print("PROBE_M42B_OK")
