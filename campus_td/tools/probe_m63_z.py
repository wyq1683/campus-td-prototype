import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute

CODE = r'''
import bpy, json
from mathutils import Vector
def aabb(o):
    cs=[o.matrix_world@Vector(c) for c in o.bound_box]
    return [min(c.x for c in cs),max(c.x for c in cs),min(c.y for c in cs),max(c.y for c in cs),min(c.z for c in cs),max(c.z for c in cs)]
out=[]
for o in bpy.data.objects:
    if o.name.startswith("M63_"):
        b=aabb(o)
        out.append([o.name, round(b[4],3), round(b[5],3), round(b[0],2), round(b[3],2), round(b[2],2), round(b[3]-b[2],2)])
out.sort(key=lambda t:t[1])
print("M63Z="+json.dumps(out))
'''
res = send_execute(CODE, strict_json=False, timeout=120)
print(res)
