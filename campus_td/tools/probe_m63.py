import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute

PROBE = r'''
import bpy, json
from mathutils import Vector
def aabb(o):
    if o.type!='MESH' or o.data is None or len(o.data.vertices)==0: return None
    cs=[o.matrix_world @ v.co for v in o.data.vertices]
    xs=[p.x for p in cs]; ys=[p.y for p in cs]; zs=[p.z for p in cs]
    return (min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))
objs=list(bpy.data.objects)
cx0,cy0,cx1,cy1=1e9,1e9,-1e9,-1e9
for o in objs:
    if o.name.startswith('M11_Wall'):
        b=aabb(o)
        if b:
            cx0=min(cx0,b[0]);cy0=min(cy0,b[1]);cx1=max(cx1,b[3]);cy1=max(cy1,b[4])
blockers=[]
FLAT=('M38_','M11_Gate','M59_','M54_','M55_','M60_','Road','M58_','M62_','M49_','M53_')
SKIP=('M7_','Tower_','Enemy_','M10B_','M50_','M51_')
for o in objs:
    if o.type!='MESH' or o.data is None: continue
    b=aabb(o)
    if not b: continue
    nm=o.name
    if nm.startswith(SKIP): continue
    if nm.startswith('Bldg_'):
        blockers.append((b,'bldg',nm)); continue
    zext=b[5]-b[2]
    if nm.startswith(FLAT): blockers.append((b,'flat',nm))
    elif zext>=1.2 and b[5]<3.5: blockers.append((b,'tall',nm))
def clear(x,y,w=5,d=3):
    rx0,rx1=x-w/2,x+w/2; ry0,ry1=y-d/2,y+d/2
    for (b,kind,nm) in blockers:
        if rx1>b[0] and rx0<b[3] and ry1>b[1] and ry0<b[4]:
            if kind=='bldg': return False
            if kind=='tall' and b[5]>0.4: return False
            if kind=='flat' and b[2]<0.5: return False
    return True
cands=[]
xs=list(range(int(cx0)+9,int(cx1)-9+1,4))
ys=list(range(int(cy0)+9,int(cy1)-9+1,4))
for gx in xs:
    for gy in ys:
        if not clear(gx,gy,5,3): continue
        dg=((gx-36)**2+(gy-30)**2)**0.5
        df=((gx-0)**2+(gy+45)**2)**0.5
        if dg<11 or df<9: continue
        dc=((gx)**2+(gy)**2)**0.5
        if dc<12 or dc>42: continue
        cands.append([gx,gy,round(dc,1),round(dg,1)])
cands.sort(key=lambda t:(t[2]))
out={'campus':[cx0,cy0,cx1,cy1],'n_clear':len(cands),'cands':cands[:25]}
print('PROBE_RESULT='+json.dumps(out))
'''
res = send_execute(PROBE, strict_json=False, timeout=120)
print(res)
