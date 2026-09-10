import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute

CODE = r'''
import bpy, json
from mathutils import Vector
def aabb(o):
    if o.type!='MESH' or o.data is None or len(o.data.vertices)==0: return None
    cs=[o.matrix_world@Vector(c) for c in o.data.vertices]
    xs=[p.x for p in cs]; ys=[p.y for p in cs]; zs=[p.z for p in cs]
    return (min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
m38=[(o.name,o.type) for o in bpy.data.objects if o.name.startswith('M38')]
mwall=[(o.name,o.type) for o in bpy.data.objects if o.name.startswith('M11_Wall')]
print('M38_NAMES', json.dumps(m38))
print('M11WALL_N', len(mwall))
print('M11WALL_SAMPLE', json.dumps(mwall[:8]))
# bounding of pitch-ish: find M38 with largest xy footprint
big=None; best=-1
for o in bpy.data.objects:
    if o.name.startswith('M38'):
        b=aabb(o)
        if b:
            area=(b[3]-b[0])*(b[4]-b[1])
            if area>best: best=area; big=(o.name,b)
print('M38_BIGGEST', json.dumps(big))
# campus bounds from all M11_Wall
cx0,cy0,cx1,cy1=1e9,1e9,-1e9,-1e9
cnt=0
for o in bpy.data.objects:
    if o.name.startswith('M11_Wall') and not any(k in o.name for k in ('Coping','GatePlaque','FlagPole','Flag')):
        b=aabb(o)
        if b:
            cx0=min(cx0,b[0]);cy0=min(cy0,b[1]);cx1=max(cx1,b[3]);cy1=max(cy1,b[4]);cnt+=1
print('CAMPUS', cnt, json.dumps([cx0,cy0,cx1,cy1]))
'''
res = send_execute(CODE, strict_json=False, timeout=120)
print(res)
