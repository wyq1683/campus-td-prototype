# m10d_enemies.py — M10D 敌人差异化建模（叠加在 M0/M7 塔防层之上，不破坏其它物体）
#
# 目标：把当前 7 个同色锥体敌人 (Enemy_1..Enemy_7) 重建成 5 种可辨识外形 +
#       每个敌人头顶悬浮可朝向相机的血条 (HP bar)。5 种类型取自 m10_config.json：
#         Swarm 蜂群(小刺球) / Rusher 突进(拉长八面体) / Elite 精英(六棱甲柱)
#         Tank  重坦(臃肿球) / Boss  首领(大球+尖刺冠)
# 设计判断：
#   - 保留 Enemy_1..Enemy_7 的名字（M7 的 frame_change 处理器按名字移动它们，
#     改名会让塔防动画失效）。只替换网格 + 加子物体（血条/尖刺），父物体名字不变。
#   - 血条、尖刺、M10D 专属材质全部用 M10D_ 前缀 → 幂等：clear_all 只删 M10D_ 再重建。
#   - 渲染用 in-script Cycles（headless 最稳，同 M3/M8/M9）。渲染前临时摘掉 M7 的
#     frame_change 处理器，把 7 个敌人摆成"展示纵队"出图，渲染后再挂回处理器并复位到路径。
# 运行：execute_blender_code(code='exec(compile(open(r"...campus_td/build/m10d_enemies.py").read(),"m10d","exec"))')

import bpy
import math
import mathutils

PREFIX = "M10D_"

# 7 个敌人槽位 -> 5 种类型（覆盖全部 5 种，并演示同型多实例）
# (type, color_rgb, metallic, rough, bar_z, hp_frac_for_preview)
# 配色对齐 web/index.html 的 enemyCol()，保证 Blender 场景与 WebGL 原型同一套视觉语言。
ENEMY_ROSTER = [
    ("Swarm", (0.58, 0.78, 0.48), 0.0, 0.55, 1.0, 0.90),
    ("Rusher", (0.96, 0.86, 0.32), 0.1, 0.40, 1.3, 0.70),
    ("Elite", (0.36, 0.76, 1.00), 0.55, 0.35, 1.4, 0.50),
    ("Tank", (0.96, 0.36, 0.30), 0.30, 0.55, 1.4, 0.35),
    ("Elite", (0.36, 0.76, 1.00), 0.55, 0.35, 1.4, 0.60),
    ("Rusher", (0.96, 0.86, 0.32), 0.1, 0.40, 1.3, 0.80),
    ("Boss", (1.00, 0.36, 0.76), 0.20, 0.30, 2.4, 1.00),
]
N = 7

PREVIEW_PATH = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m10d_enemies.png"


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
    for m in [m for m in bpy.data.materials if m.name.startswith(PREFIX)]:
        bpy.data.materials.remove(m)
    return removed


# ---------------------------------------------------------------------------
# 材质工具（按 PLAN 避坑 #3：Principled 按 type 找）
# ---------------------------------------------------------------------------
def _principled(mat):
    for nd in mat.node_tree.nodes:
        if nd.type == "BSDF_PRINCIPLED":
            return nd
    return mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")


def pbr_mat(name, color, metallic=0.0, rough=0.5, emit=0.0):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emit > 0.0:
        bsdf.inputs["Emission Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def emissive_mat(name, color, strength=1.5):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


# ---------------------------------------------------------------------------
# 网格替换：保留 Enemy_i 名字，只换 mesh
# ---------------------------------------------------------------------------
def replace_mesh(obj, builder):
    """builder() 通过 bpy.ops.mesh.primitive_*_add 创建一个新物体并留作 active_object。"""
    old_mesh = obj.data
    builder()
    new_obj = bpy.context.active_object
    # 关键：builder 给临时物体设的非 1 scale（Rusher 拉长 / Tank 压扁）不会随 .data 一起
    # 迁移 —— 只取 data 会让两者退化成普通球。必须先把 scale 烘进顶点再交给目标对象。
    sc = new_obj.scale
    if abs(sc.x - 1.0) > 1e-6 or abs(sc.y - 1.0) > 1e-6 or abs(sc.z - 1.0) > 1e-6:
        for v in new_obj.data.vertices:
            v.co.x *= sc.x
            v.co.y *= sc.y
            v.co.z *= sc.z
        new_obj.data.update()
    obj.data = new_obj.data
    bpy.data.objects.remove(new_obj, do_unlink=True)
    if old_mesh is not None and old_mesh.users == 0:
        try:
            bpy.data.meshes.remove(old_mesh)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 5 种外形构造器（primitive add 操作，避坑 #4：cone 用 radius1/radius2）
# ---------------------------------------------------------------------------
def build_swarm():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.45)


def build_rusher():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=0, radius=0.5)
    bpy.context.active_object.scale = (0.5, 1.0, 0.5)


def build_elite():
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.55, depth=1.0)


def build_tank():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8)
    bpy.context.active_object.scale = (1.15, 1.15, 0.9)


def build_boss():
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.15)


BUILDERS = {
    "Swarm": build_swarm,
    "Rusher": build_rusher,
    "Elite": build_elite,
    "Tank": build_tank,
    "Boss": build_boss,
}


# ---------------------------------------------------------------------------
# 血条（父到 Enemy_i，TRACK_TO 相机始终朝向镜头）
# ---------------------------------------------------------------------------
def make_hp_bar(enemy, cam, bar_z, frac):
    W = 1.4
    bg = bpy.data.objects.new(PREFIX + "HPbg_" + enemy.name, bpy.data.meshes.new(PREFIX + "HPbg_" + enemy.name))
    bg_mesh = bg.data
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    tmp = bpy.context.active_object
    bg.data = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    bg.scale = (W, 0.06, 0.20)
    bg.location = (0.0, 0.0, bar_z)
    bpy.context.scene.collection.objects.link(bg)
    bg.parent = enemy
    # 血条 location 是"相对敌人"的局部偏移 -> 必须显式把 parent_inverse 钉成单位阵，
    # 否则 Blender 会为了保留原世界坐标把血条留在世界原点，而不是浮在敌人头顶。
    bg.matrix_parent_inverse = mathutils.Matrix()
    assign_mat(bg, emissive_mat("HPbg", (0.04, 0.04, 0.04), 0.6))

    fill = bpy.data.objects.new(PREFIX + "HPfill_" + enemy.name, bpy.data.meshes.new(PREFIX + "HPfill_" + enemy.name))
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    tmp = bpy.context.active_object
    fill.data = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    col = (0.25, 0.95, 0.35) if frac > 0.5 else ((0.98, 0.80, 0.20) if frac > 0.3 else (0.95, 0.30, 0.25))
    fill.scale = (W * frac, 0.07, 0.22)
    fill.location = (-(W / 2.0) * (1.0 - frac), 0.0, bar_z)
    bpy.context.scene.collection.objects.link(fill)
    fill.parent = enemy
    fill.matrix_parent_inverse = mathutils.Matrix()   # 同 bg：局部偏移，不保留世界坐标
    assign_mat(fill, emissive_mat("HPfill", col, 1.8))

    for bar in (bg, fill):
        con = bar.constraints.new("TRACK_TO")
        con.target = cam
        con.track_axis = "TRACK_Z"
        con.up_axis = "UP_Y"
    return bg.name, fill.name


# ---------------------------------------------------------------------------
# Boss 尖刺冠（子物体，随父移动）
# ---------------------------------------------------------------------------
def add_boss_spikes(enemy):
    names = []
    for k in range(6):
        a = math.radians(k * 60.0)
        # 在原点建好再改局部坐标：add 时给的 location 是世界坐标，parenting 后会被保留，
        # 导致尖刺留在世界原点而不是跟着 Boss 走。
        bpy.ops.mesh.primitive_cone_add(radius1=0.18, radius2=0.0, depth=0.6,
                                        location=(0.0, 0.0, 0.0))
        sp = bpy.context.active_object
        sp.name = PREFIX + "Spike_%s_%d" % (enemy.name, k)
        sp.location = (math.cos(a) * 0.6, math.sin(a) * 0.6, 1.25)
        sp.parent = enemy
        sp.matrix_parent_inverse = mathutils.Matrix()
        assign_mat(sp, emissive_mat("Spike", (0.85, 0.40, 1.00), 2.2))
        names.append(sp.name)
    return names


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def build_m10d():
    sc = bpy.context.scene
    cleared = clear_all()

    # 确保有相机（供 TRACK_TO 与渲染）
    cam = bpy.data.objects.get("M10D_Cam")
    if cam is None:
        bpy.ops.object.camera_add(location=(-2.0, -34.0, 14.0))
        cam = bpy.context.active_object
        cam.name = "M10D_Cam"
    # 相机更靠近、更低，24mm 广角，确保 7 个差异化敌人并排入画
    target = mathutils.Vector((0.0, -13.0, 0.8))
    cam.location = (0.0, -20.0, 8.0)
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    if cam.data:
        cam.data.lens = 24.0
    try:
        cam.constraints.clear()
    except Exception:
        pass

    made = []
    materials_used = []
    for i in range(1, N + 1):
        etype, color, metallic, rough, bar_z, frac = ENEMY_ROSTER[i - 1]
        e = bpy.data.objects.get("Enemy_%d" % i)
        if e is None:
            bpy.ops.mesh.primitive_cone_add(radius1=0.5, radius2=0.0, depth=1.0,
                                            location=(-18.0 + (i - 1) * 6.0, -13.0, 0.8))
            e = bpy.context.active_object
            e.name = "Enemy_%d" % i
        # 替换网格为对应外形
        replace_mesh(e, BUILDERS[etype])
        mat = pbr_mat("Mat_%s_%d" % (etype, i), color, metallic, rough,
                      emit=(0.6 if etype == "Boss" else 0.0))
        assign_mat(e, mat)
        materials_used.append(mat.name)
        # 血条
        make_hp_bar(e, cam, bar_z, frac)
        if etype == "Boss":
            add_boss_spikes(e)
        made.append((e.name, etype))

    # ---- 渲染：展示纵队（临时摘 handler，避免路径动画抢位）----
    handlers = bpy.app.handlers.frame_change_pre
    h = next((x for x in handlers if getattr(x, "__name__", "") == "update_enemies"), None)
    if h is not None:
        bpy.app.handlers.frame_change_pre.remove(h)

    # 摆成展示纵队：x 均匀铺开，y=-13（开阔南道地面），z=0.8
    for i in range(1, N + 1):
        e = bpy.data.objects.get("Enemy_%d" % i)
        if e is not None:
            # 收窄纵队间距，避免 35mm 远景把两端切出画面
            e.location = (-6.6 + (i - 1) * 2.2, -13.0, 0.8)
            e.rotation_euler = (0.0, 0.0, 0.0)

    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.filepath = PREVIEW_PATH
    bpy.ops.render.render(write_still=True)

    # 挂回 handler 并复位到路径当前帧
    if h is not None:
        bpy.app.handlers.frame_change_pre.append(h)
        try:
            h(sc)
        except Exception:
            pass

    g = globals()
    g["result"] = {
        "built": True,
        "milestone": "M10D",
        "enemies": made,
        "materials": materials_used,
        "cleared": cleared,
        "scene_objects": len(bpy.data.objects),
        "preview": PREVIEW_PATH,
    }
    print("M10D_RESULT " + str(g["result"]))
    return g["result"]


if __name__ == "__main__" or True:
    build_m10d()
