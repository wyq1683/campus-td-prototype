# probe_site.py — 探 roads / ground / world 节点状态，供 M5 场地细化
import bpy, mathutils

roads = []
for o in bpy.data.objects:
    if o.name.startswith("Road"):
        pts = [o.matrix_world @ mathutils.Vector(v) for v in o.bound_box]
        xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
        roads.append({"name": o.name, "x": [round(min(xs), 1), round(max(xs), 1)],
                     "y": [round(min(ys), 1), round(max(ys), 1)], "z": [round(min(zs), 1), round(max(zs), 1)]})

ground = bpy.data.objects.get("Ground")
g = None
if ground:
    pts = [ground.matrix_world @ mathutils.Vector(v) for v in ground.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    g = {"x": [round(min(xs), 1), round(max(xs), 1)], "y": [round(min(ys), 1), round(max(ys), 1)]}

world = bpy.data.worlds.get("World") or (bpy.data.worlds[0] if bpy.data.worlds else None)
wnodes = [n.name for n in world.node_tree.nodes] if world and world.node_tree else None
has_env = None
if world and world.node_tree:
    has_env = any(n.type in ("TEX_ENVIRONMENT", "TEX_SKY") for n in world.node_tree.nodes)

result = {"roads": roads, "ground": g, "world_nodes": wnodes, "world_has_env_or_sky": has_env}
print("PROBE_SITE:", result)
