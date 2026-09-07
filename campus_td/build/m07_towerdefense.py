# m07_towerdefense.py — M7 塔防层 refinement（叠加系统，不破坏 M0–M6 场景）
# 职责：
#   1) 敌人路径：把 7 个 Enemy 的初始落位连成一条 U 形路线（Catmull-Rom 平滑，弧长匀速），
#      并建一条可见的发光导览管 (M7_Path) 还原同一曲线，保证"看得到 = 走得到"。
#   2) 敌人动画：frame_change_pre 处理器沿路径推进 7 个敌人（相位错开成纵队），循环。
#   3) 塔射程可视化：四角塔各加半透明全息穹顶 (M7_Range_*) + 地面范围环 (M7_Ring_*)，
#      半径 RANGE_R，Fresnel 边缘辉光，不投影、不挡视线。
#   4) 塔类型：四角塔映射 连发/范围/减速/基础 四种，用差异色信标 (M7_Beacon_*) + 穹顶/环着色表达。
#   5) 关卡语义：出生点 (M7_Spawn, 路径西端红环) + 玩家基地核心 (M7_Exit/M7_Core, 北端绿环)。
# 设计判断：塔防是叠加层，不改动 M6 统一金色辉光；用"类型色 = 信标/穹顶/环"传达玩法，
#           HUD(金钱/血量) 属屏幕空间，留给游戏引擎(M8/M9 视频化)叠加，本里程碑只建 3D 语义。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m07_towerdefense.py").read(),"m07","exec"))\nbuild_towerdefense()')

import bpy
import mathutils

PREFIX = "M7_"

# ---- 路径航点（与 7 敌人初始落位完全一致），z=0.8 贴路面 ----
WP = [
    (-22.0, -13.0),   # 0 出生点 / 南道西端 (近 Tower_1)
    ( -4.0, -13.0),   # 1 Enemy_3 落位 (南道中段)
    ( 16.0, -13.0),   # 2 东南角
    ( 16.0,   2.0),   # 3 Enemy_5 落位 (东道中段)
    ( 16.0,  13.0),   # 4 东北角
    (  0.0,  13.0),   # 5 Enemy_7 落位 (北道中段)
    (-22.0,  13.0),   # 6 终点 / 北道西端 (近 Tower_4 = 玩家基地)
]
Z = 0.8
N_ENEMY = 7
ANIM_FRAMES = 250.0

# ---- 塔类型映射：角塔 -> (类型标签, 类型色) ----
TOWER_TYPES = {
    "Tower_1": ("RAPID", (0.30, 0.85, 1.00)),   # 西南 连发 青
    "Tower_2": ("AOE",   (1.00, 0.55, 0.15)),   # 东南 范围 橙
    "Tower_3": ("SLOW",  (0.65, 0.35, 1.00)),   # 东北 减速 紫
    "Tower_4": ("BASIC", (1.00, 0.90, 0.55)),   # 西北 基础 金 (守基地)
}
RANGE_R = 13.0


# ---------------------------------------------------------------------------
# 幂等清理
# ---------------------------------------------------------------------------
def clear_all():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    for cu in [c for c in bpy.data.curves if c.name.startswith(PREFIX)]:
        bpy.data.curves.remove(cu)
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    return removed


# ---------------------------------------------------------------------------
# Catmull-Rom（弧长匀速采样）
# ---------------------------------------------------------------------------
def _cr(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * t +
                  (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
                  (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


def sample_path(u):
    """u in [0,1]，按弧长匀速返回 Vector3（z=Z）。"""
    n = len(WP)
    pts = [mathutils.Vector((WP[i][0], WP[i][1], Z)) for i in range(n)]
    seg = [(pts[i] - pts[i + 1]).length for i in range(n - 1)]
    total = sum(seg)
    d = max(0.0, min(1.0, u)) * total
    acc = 0.0
    for i in range(n - 1):
        if d <= acc + seg[i] or i == n - 2:
            local = (d - acc) / seg[i] if seg[i] > 0 else 0.0
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
            x = _cr(p0.x, p1.x, p2.x, p3.x, local)
            y = _cr(p0.y, p1.y, p2.y, p3.y, local)
            return mathutils.Vector((x, y, Z))
        acc += seg[i]
    return pts[-1]


# ---------------------------------------------------------------------------
# 敌人动画
# ---------------------------------------------------------------------------
def place_enemies_at_frame(f):
    for i in range(1, N_ENEMY + 1):
        e = bpy.data.objects.get("Enemy_%d" % i)
        if e is None:
            continue
        phase = (i - 1) / float(N_ENEMY)
        u = ((f / ANIM_FRAMES) + phase) % 1.0
        p = sample_path(u)
        e.location = (p.x, p.y, Z)


def update_enemies(scene):
    place_enemies_at_frame(scene.frame_current)
    update_beams(scene.frame_current)


BEAM_TOP_Z = 4.2


def update_beams(f):
    """把射程内最近的敌人用发光束连到塔顶；无目标则隐藏。"""
    for name in TOWER_TYPES:
        tw = bpy.data.objects.get(name)
        beam = bpy.data.objects.get(PREFIX + "Beam_" + name)
        if tw is None or beam is None:
            continue
        top = mathutils.Vector((tw.location.x, tw.location.y, BEAM_TOP_Z))
        best = None
        best_d = 1e9
        for i in range(1, N_ENEMY + 1):
            e = bpy.data.objects.get("Enemy_%d" % i)
            if e is None:
                continue
            d = (e.location - tw.location).length
            if d <= RANGE_R and d < best_d:
                best_d = d
                best = e
        if best is None:
            beam.hide_viewport = True
            beam.hide_render = True
            continue
        beam.hide_viewport = False
        beam.hide_render = False
        a = top
        b = best.location
        mid = (a + b) * 0.5
        beam.location = (mid.x, mid.y, mid.z)
        dirv = b - a
        L = dirv.length
        beam.scale = (1.0, 1.0, L)
        beam.rotation_euler = dirv.to_track_quat("Z", "Y").to_euler()


def register_handler():
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "update_enemies":
            bpy.app.handlers.frame_change_pre.remove(h)
    bpy.app.handlers.frame_change_pre.append(update_enemies)


# ---------------------------------------------------------------------------
# 材质工具
# ---------------------------------------------------------------------------
def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def emissive_mat(name, color, strength=2.0):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def holo_dome_mat(name, color):
    """Fresnel 边缘辉光壳：中心透视、边缘发光，干净的全息覆盖感。"""
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    try:
        mat.blend_method = "BLEND"
    except Exception:
        pass
    mat.use_backface_culling = False
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    fres = nt.nodes.new("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.25
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    em.inputs["Strength"].default_value = 0.7
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fres.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(trans.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# 可见路径管（与运动同一曲线）
# ---------------------------------------------------------------------------
def make_path_curve():
    SAMPLES = 64
    cu = bpy.data.curves.new(PREFIX + "Path", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(SAMPLES)
    for i in range(SAMPLES + 1):
        p = sample_path(i / float(SAMPLES))
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
    cu.bevel_depth = 0.16
    cu.bevel_resolution = 3
    obj = bpy.data.objects.new(PREFIX + "Path", cu)
    mat = emissive_mat("PathMat", (1.0, 0.85, 0.45), 2.2)
    cu.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    return obj.name


# ---------------------------------------------------------------------------
# 塔射程 + 类型信标
# ---------------------------------------------------------------------------
def make_tower_assets():
    made = []
    for name, (ttype, color) in TOWER_TYPES.items():
        tw = bpy.data.objects.get(name)
        if tw is None:
            continue
        bx, by, bz = tw.location

        # 射程穹顶
        bpy.ops.mesh.primitive_uv_sphere_add(radius=RANGE_R, location=(bx, by, bz))
        dome = bpy.context.active_object
        dome.name = PREFIX + "Range_" + name
        assign_mat(dome, holo_dome_mat("Dome_" + name, color))
        try:
            dome.visible_shadow = False
        except Exception:
            pass

        # 地面范围环
        bpy.ops.mesh.primitive_torus_add(major_radius=RANGE_R, minor_radius=0.16,
                                         location=(bx, by, 0.12))
        ring = bpy.context.active_object
        ring.name = PREFIX + "Ring_" + name
        assign_mat(ring, emissive_mat("Ring_" + name, color, 1.6))

        # 类型信标（塔顶上方锥标）
        bpy.ops.mesh.primitive_cone_add(radius1=0.5, radius2=0.0, depth=1.3,
                                        location=(bx, by, bz + 4.4))
        beacon = bpy.context.active_object
        beacon.name = PREFIX + "Beacon_" + name
        assign_mat(beacon, emissive_mat("Beacon_" + name, color, 2.4))
        # 锁定光束（初始隐藏；frame_change 时连到射程内最近敌人）
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=1.0,
                                            location=(bx, by, bz + 4.2))
        beam = bpy.context.active_object
        beam.name = PREFIX + "Beam_" + name
        bmat = emissive_mat("Beam_" + name, color, 3.0)
        try:
            bmat.blend_method = "ADD"
        except Exception:
            pass
        assign_mat(beam, bmat)
        beam.hide_viewport = True
        beam.hide_render = True
        try:
            beam.visible_shadow = False
        except Exception:
            pass
        made.append((name, ttype))
    return made


# ---------------------------------------------------------------------------
# 出生点 / 基地
# ---------------------------------------------------------------------------
def make_portals():
    # 出生点（路径西端，红环）
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.22,
                                     location=(WP[0][0], WP[0][1], 0.12))
    spawn = bpy.context.active_object
    spawn.name = PREFIX + "Spawn"
    assign_mat(spawn, emissive_mat("Spawn", (1.0, 0.28, 0.22), 2.2))

    # 玩家基地（路径北端，绿环 + 核心八面体）
    bpy.ops.mesh.primitive_torus_add(major_radius=1.6, minor_radius=0.22,
                                     location=(WP[-1][0], WP[-1][1], 0.12))
    exit_ = bpy.context.active_object
    exit_.name = PREFIX + "Exit"
    assign_mat(exit_, emissive_mat("Exit", (0.25, 1.0, 0.45), 2.2))

    bpy.ops.mesh.primitive_cone_add(radius1=0.9, radius2=0.0, depth=1.6,
                                    location=(WP[-1][0], WP[-1][1], 1.4))
    core = bpy.context.active_object
    core.name = PREFIX + "Core"
    assign_mat(core, emissive_mat("Core", (0.30, 1.0, 0.55), 2.6))
    return [spawn.name, exit_.name, core.name]


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def build_towerdefense():
    sc = bpy.context.scene
    cleared = clear_all()
    path = make_path_curve()
    towers = make_tower_assets()
    portals = make_portals()
    register_handler()
    sc.frame_start = 1
    sc.frame_end = int(ANIM_FRAMES)
    sc.frame_set(1)
    place_enemies_at_frame(1)
    g = globals()
    g["result"] = {
        "built": True,
        "path": path,
        "towers": towers,
        "beams": len(towers),
        "portals": portals,
        "range_radius": RANGE_R,
        "anim_frames": ANIM_FRAMES,
        "cleared": cleared,
        "objects": len(bpy.data.objects),
    }
    return g["result"]
