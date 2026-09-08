# m07b_vfx.py — V3.1 粒子特效层（叠加系统，不破坏 M0–M19 / M1b / M7）
# 职责：
#   1) 枪口闪光 (Muzzle Flash)：四角塔顶各 1 个发射器，常驻短命粒子喷泉 = "蓄能武器辉光"。
#   2) 命中火花 (Hit Sparks)：每塔 1 个发射器，frame_change 时 relocate 到本塔锁定的敌人身上，
#      无目标则隐藏 → 呈现"被击中→迸发火花"。复用 M7 射程判定。
#   3) 粒子参数严格按 V3.1 交付标准：≤800 粒/次、生命周期 ≤0.4s（按场景 fps 换算帧数）。
#   4) 材质走 5.2 节点 API：emissive + ADD 混合，AgX 下仍能"点亮"。
# 幂等：PREFIX=V3_ 清理；instance 模板球置于屏外 (9999,9999,9999) 不参与画面。
# 运行：execute_blender_code(code='exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m07b_vfx.py").read(),"m07b","exec"))\nbuild_vfx()')

import bpy
import mathutils

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "V3_"
BEAM_TOP_Z = 4.2          # 与 M7 光束起点一致
RANGE_R = 13.0            # 与 M7 一致
N_ENEMY = 7
TOWER_TYPES = {
    "Tower_1": ("RAPID", (0.30, 0.85, 1.00)),
    "Tower_2": ("AOE",   (1.00, 0.55, 0.15)),
    "Tower_3": ("SLOW",  (0.65, 0.35, 1.00)),
    "Tower_4": ("BASIC", (1.00, 0.90, 0.55)),
}
# 喷口色（枪口偏冷白、命中偏暖橙），保证火花辨识度
FLASH_COLOR = (0.75, 0.92, 1.00)
SPARK_COLOR = (1.00, 0.62, 0.22)


def _fps(scene):
    return max(1.0, scene.render.fps / max(scene.render.fps_base, 1e-3))


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
# 材质工具（5.2 节点 API）
# ---------------------------------------------------------------------------
def emissive_mat(name, color, strength=3.0, additive=False):
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
    if additive:
        try:
            mat.blend_method = "ADD"
        except Exception:
            pass
        mat.use_backface_culling = False
    return mat


def make_instance_template(name, radius, mat):
    """屏外小实例球，作为粒子 OBJECT 渲染的模板（不进入画面）。"""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius,
                                          location=(9999.0, 9999.0, 9999.0))
    ico = bpy.context.active_object
    ico.name = PREFIX + name
    ico.data.materials.append(mat)
    ico.hide_viewport = True
    ico.hide_render = False  # 模板在屏外，渲染也不可见；实例由粒子系统生成
    return ico


# ---------------------------------------------------------------------------
# 粒子系统
# ---------------------------------------------------------------------------
def add_particles(obj, name, ico, *, count, life_frames, normal_factor,
                  gravity, brownian, color_strength, size=0.06):
    mod = obj.modifiers.new(PREFIX + "PS_" + name, "PARTICLE_SYSTEM")
    ps = obj.particle_systems[-1]
    s = ps.settings
    s.count = count
    s.frame_start = 1.0
    s.frame_end = float(bpy.context.scene.frame_end)
    s.lifetime = float(life_frames)
    s.lifetime_random = 0.6
    s.emit_from = "VOLUME"
    s.physics_type = "NEWTON"
    s.normal_factor = normal_factor
    s.factor_random = 1.0
    s.particle_size = size
    s.size_random = 0.7
    s.brownian_factor = brownian
    s.drag_factor = 0.0
    s.effector_weights.gravity = gravity
    s.render_type = "OBJECT"
    s.instance_object = ico
    # 隐藏发射器本体网格，仅显示粒子（5.2 已移除 use_emit，发射由 frame_start/end 控制）
    obj.show_instancer_for_viewport = False
    obj.show_instancer_for_render = False
    return ps


def make_emitter(name, loc, ico, *, count, life_frames, normal_factor,
                 gravity, brownian, color_strength, size=0.06):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=loc)
    em = bpy.context.active_object
    em.name = PREFIX + name
    # 发射器本体需有网格但不可见；挂一个透明占位材质避免杂色
    hold = emissive_mat("Hold_" + name, (0, 0, 0), 0.0)
    em.data.materials.append(hold)
    add_particles(em, name, ico, count=count, life_frames=life_frames,
                  normal_factor=normal_factor, gravity=gravity, brownian=brownian,
                  color_strength=color_strength, size=size)
    return em


# ---------------------------------------------------------------------------
# frame_change 处理器：hit 发射器跟随锁定敌人
# ---------------------------------------------------------------------------
def _nearest_enemy(tw):
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
    return best


def v3_update(scene):
    for name in TOWER_TYPES:
        tw = bpy.data.objects.get(name)
        hit = bpy.data.objects.get(PREFIX + "Hit_" + name)
        if tw is None or hit is None:
            continue
        tgt = _nearest_enemy(tw)
        if tgt is None:
            hit.hide_viewport = True
            hit.hide_render = True
            continue
        hit.hide_viewport = False
        hit.hide_render = False
        hit.location = (tgt.location.x, tgt.location.y, tgt.location.z + 0.4)


def register_handler():
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "v3_update":
            bpy.app.handlers.frame_change_pre.remove(h)
    bpy.app.handlers.frame_change_pre.append(v3_update)


# ---------------------------------------------------------------------------
# 主构建
# ---------------------------------------------------------------------------
def build_vfx():
    sc = bpy.context.scene
    cleared = clear_all()
    # 确保 M7 塔防层存在（塔 + 敌人 + 路径）
    if bpy.data.objects.get("Tower_1") is None:
        exec(compile(open(ROOT + "/build/m07_towerdefense.py").read(), "m07", "exec"))
        build_towerdefense()
    life = max(2, round(0.4 * _fps(sc)))

    flash_ico = make_instance_template("Ico_Flash", 0.07,
                                        emissive_mat("Flash", FLASH_COLOR, 4.0, additive=True))
    spark_ico = make_instance_template("Ico_Spark", 0.05,
                                        emissive_mat("Spark", SPARK_COLOR, 3.0, additive=True))

    muzzles, hits = [], []
    for name, (ttype, color) in TOWER_TYPES.items():
        tw = bpy.data.objects.get(name)
        if tw is None:
            continue
        bx, by, bz = tw.location
        mz = (bx, by, bz + BEAM_TOP_Z)
        m = make_emitter("Muzzle_" + name, mz, flash_ico,
                         count=150, life_frames=life, normal_factor=2.6,
                         gravity=0.0, brownian=0.05, color_strength=4.0, size=0.07)
        muzzles.append(m.name)
        # 命中发射器：初始置于塔顶并隐藏，frame_change 时跟随敌人
        h = make_emitter("Hit_" + name, mz, spark_ico,
                         count=300, life_frames=life, normal_factor=1.1,
                         gravity=1.0, brownian=0.22, color_strength=3.0, size=0.05)
        h.hide_viewport = True
        h.hide_render = True
        hits.append(h.name)

    register_handler()
    sc.frame_set(int(sc.frame_current))
    g = globals()
    g["result"] = {
        "built": True,
        "cleared": cleared,
        "muzzle_emitters": muzzles,
        "hit_emitters": hits,
        "instance_templates": [flash_ico.name, spark_ico.name],
        "life_frames": life,
        "fps": _fps(sc),
        "objects": len(bpy.data.objects),
    }
    return g["result"]


if __name__ == "__main__":
    build_vfx()
