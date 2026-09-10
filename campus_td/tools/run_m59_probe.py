# run_m59_probe.py — read-only scene probe for M59 placement design
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import bpy, mathutils
def aabb(o):
    bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs=[v.z for v in bb]
    return (round(min(xs),2),round(max(xs),2),round(min(ys),2),round(max(ys),2),round(min(zs),2),round(max(zs),2))
roads=[o for o in bpy.data.objects if o.name.startswith("Road")]
road_info=[(o.name, aabb(o)) for o in roads]
gate=bpy.data.objects.get("M11_GatePlaque")
gate_info=aabb(gate) if gate else None
stele=bpy.data.objects.get("M54_Stele")
stele_info=aabb(stele) if stele else None
m55=[o.name for o in bpy.data.objects if o.name.startswith("M55_")]
flag=bpy.data.objects.get("M11_FlagPole")
flag_info=aabb(flag) if flag else None
result={"roads":road_info,"gate":gate_info,"stele":stele_info,"m55_count":len(m55),"flag":flag_info,"objs":len(bpy.data.objects)}
'''

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=120.0)
    print("STATUS:", resp.get("status"))
    print("STDERR:", (resp.get("stderr") or "")[:2000])
    print("RESULT:", resp.get("result"))
