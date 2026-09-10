# probe_m58.py — scene probe to design M58 (campus driveway blue edge lines)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import bpy
from mathutils import Vector

def aabb(o):
    cs=[o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs),max(c.x for c in cs),min(c.y for c in cs),max(c.y for c in cs),min(c.z for c in cs),max(c.z for c in cs)]

# 关键字过滤
keys = ("Road","Path","Lane","Drive","TD_","M5_","Site_","Ground","Plaza","M11_Wall","M11_Gate","M38_Pitch","Bldg_","M50_","M54_")
summ = {k:[] for k in keys}
names_all=[o.name for o in bpy.data.objects]
for o in bpy.data.objects:
    for k in keys:
        if k in o.name:
            b=aabb(o)
            summ[k].append((o.name, round(b[0],1),round(b[1],1),round(b[2],1),round(b[3],1),round(b[4],1),round(b[5],1)))
            break

# 学校中心 & 围墙
walls=[aabb(o) for o in bpy.data.objects if o.name.startswith("M11_Wall")]
if walls:
    xmin=min(b[0] for b in walls); xmax=max(b[1] for b in walls)
    ymin=min(b[2] for b in walls); ymax=max(b[3] for b in walls)
else:
    xmin,xmax,ymin,ymax=-48,48,-48,48

# TD 路径点（TD_Path 折线）
td=[o for o in bpy.data.objects if o.name.startswith("TD_")]
result={
  "n_objects": len(bpy.data.objects),
  "campus":[round(xmin,1),round(xmax,1),round(ymin,1),round(ymax,1)],
  "gate": None,
  "by_key": {k:v for k,v in summ.items() if v},
  "td_count": len(td),
  "td_names": [o.name for o in td][:40],
}
gp=bpy.data.objects.get("M11_GatePlaque")
if gp: result["gate"]=[round(gp.location.x,1),round(gp.location.y,1),round(gp.location.z,1)]
print("PROBE58="+repr(result))
'''

resp = send_execute(CODE, strict_json=False, timeout=120.0)
print("STATUS:", resp.get("status"))
print("STDERR:", (resp.get("stderr") or "")[:2000])
print("OUT:", (resp.get("stdout") or "")[:4000])
