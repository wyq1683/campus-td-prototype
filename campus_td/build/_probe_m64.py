import bpy, mathutils, json

def AABB(o):
    corners = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    xs=[c.x for c in corners]; ys=[c.y for c in corners]; zs=[c.z for c in corners]
    return (min(xs),min(ys),min(zs),max(xs),max(ys),max(zs))

# blocker prefixes (real structures); exclude campus-wide merged rings + TD markers (false huge AABB)
EXCLUDE_PREFIXES = ("M50_","M51_","M7_","Tower_","Enemy_","M10B_","TD_","Site_","M19C_")
objs = bpy.data.objects
blockers=[]
for o in objs:
    n=o.name
    if n.startswith(EXCLUDE_PREFIXES): continue
    if o.name in ("Camera","M11_CamAerial"): continue
    bb=AABB(o)
    # ignore tiny/flat decorative? keep all; but skip pure-camera helper
    if o.type=='CAMERA': continue
    blockers.append((n,bb))

# interior bounds from M11_Wall* AABB union (perimeter)
wall=[(n,b) for n,b in blockers if n.startswith("M11_Wall")]
if wall:
    minx=min(b[0] for _,b in wall); maxx=max(b[3] for _,b in wall)
    miny=min(b[1] for _,b in wall); maxy=max(b[4] for _,b in wall)
else:
    minx,maxx,miny,maxy=-48,48,-48,48

# shrink margin inside wall
mx0,mx1,my0,my1 = minx+2, maxx-2, miny+2, maxy-2

step=1.0
def occupied(x,y):
    for n,(a,b,c,d,e,f) in blockers:
        if a-0.5<=x<=d+0.5 and c-0.5<=y<=e+0.5:
            return n
    return None

# grid over interior
grid={}
for gx in range(int(mx0),int(mx1)+1):
    for gy in range(int(my0),int(my1)+1):
        grid[(gx,gy)] = occupied(gx,gy) is None

# find largest clear axis-aligned rectangle (greedy expand) - sample candidates
best=None
xs=sorted(set(g[0] for g in grid)); ys=sorted(set(g[1] for g in grid))
# limit candidates
cand=[(x,y) for x in range(int(mx0),int(mx1)+1,3) for y in range(int(my0),int(my1)+1,3) if grid.get((x,y))]
def rect_ok(x0,y0,x1,y1):
    for x in range(x0,x1+1):
        for y in range(y0,y1+1):
            if not grid.get((x,y),False): return False
    return True
top=[]
for (cx,cy) in cand:
    # expand right and up
    x1=cx
    while grid.get((x1+1,cy),False): x1+=1
    y1=cy
    while grid.get((cx,y1+1),False): y1+=1
    area=(x1-cx+1)*(y1-cy+1)
    if area>=15*15:
        top.append((area,cx,cy,x1,y1))
top.sort(reverse=True)
top=top[:8]

# key structure AABBs for reference
key=[]
for n,b in blockers:
    if any(n.startswith(p) for p in ("Bldg_","M11_Wall","M38_","M46_","M11_FlagPole","M37_Flag","M62_","M63_","M41_")):
        key.append((n,[round(v,1) for v in b]))

result = {
    "wall_interior": [round(v,1) for v in (mx0,my0,mx1,my1)],
    "n_blockers": len(blockers),
    "top_clear_rects": [[round(a,1)]+list(b) for a,b in [ (t[0],t[1:]) for t in top]],
    "key_aabb": key,
    "n_total_objects": len(objs),
}
print("RESULT_JSON_START")
print(json.dumps(result))
print("RESULT_JSON_END")
