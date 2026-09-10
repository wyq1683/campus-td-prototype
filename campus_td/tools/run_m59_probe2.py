# run_m59_probe2.py — list AABBs of gate/stele/garden objects to find real open ground
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import bpy, mathutils
def aabb(o):
    try:
        bb=[o.matrix_world@mathutils.Vector(c) for c in o.bound_box]
    except Exception:
        return None
    if not bb: return None
    xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs=[v.z for v in bb]
    return (round(min(xs),2),round(max(xs),2),round(min(ys),2),round(max(ys),2),round(min(zs),2),round(max(zs),2))
out={}
for pfx in ("M11_Gate","M54","M55","M37"):
    out[pfx]=[(o.name, aabb(o)) for o in bpy.data.objects if o.name.startswith(pfx)]
result={"items":out}
'''

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=120.0)
    print("STATUS:", resp.get("status"))
    print("STDERR:", (resp.get("stderr") or "")[:2000])
    r = resp.get("result") or {}
    for pfx, items in r.get("items", {}).items():
        print("==", pfx, "==")
        for name, b in items:
            print("  ", name, b)
