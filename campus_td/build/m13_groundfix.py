# m13_groundfix.py — M13 地面层补光标定（能量扫描）
#
# 背景：M12 的对照实验查出，被当作"已调好基准"的地面层 1F 自身 p50=40.5，
#   低于室内合理带下限 55（-26%）。但地面层是阅览室，6 个深色书架会拉低中位数，
#   所以不能断定是"照明不足"还是"家具吸光" —— 需要扫描才知道提 energy 有没有用。
#
# 做法：复用 M12 的**同一机位**（同建筑、同进深、同镜头），只改 M8_Library 的
#   energy，渲 240(现状) / 340 / 460 三张，用亮度分位数曲线选值。
#   只改 energy 不加灯 → Cycles CPU 成本不变（MEMORY：加灯成本陡增，改强度不涨）。
#
# 幂等：扫完把 energy 复位到扫描前的值，不留副作用。
# 运行：... + "\nresult = sweep([240.0, 340.0, 460.0])"

import bpy

M12_SRC = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m12_uppercheck.py"
OUTDIR = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
LAMP = "M8_Library"
SAMPLES = 64          # 扫描用，比 M12 的 96 低一档换速度（只看相对趋势）

# 载入 M12 的机位算法，保证与 M12 数据严格同机位可比
_g = globals()
exec(compile(open(M12_SRC, encoding="utf-8").read(), "m12", "exec"), _g)
place_cam = _g["place_cam"]


def render_at(energy, tag=None):
    """tag 给定时用于文件名（环境光扫描用 W###，补光扫描用 E###），避免两类图混淆。"""
    lt = bpy.data.lights.get(LAMP)
    if lt is None:
        return {"ok": False, "why": "missing light %s" % LAMP}
    lt.energy = energy

    got = place_cam("ground")
    if got is None:
        return {"ok": False, "why": "no building"}
    cam, info = got

    sc = bpy.context.scene
    hidden = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            hidden.append((o, o.hide_render))
            o.hide_render = True

    sc.camera = cam
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "CPU"
    except Exception:
        pass
    sc.cycles.samples = SAMPLES
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.resolution_percentage = 100
    path = "%s/m13_ground_%s.png" % (OUTDIR, ("E%03d" % int(round(energy))) if tag is None else tag)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

    for o, was in hidden:
        o.hide_render = was
    return {"ok": True, "energy": energy, "file": path,
            "cam": [round(v, 2) for v in cam.location]}


def _world_bg():
    w = bpy.context.scene.world
    if w is None or not w.use_nodes:
        return None
    for n in w.node_tree.nodes:
        if n.type == "BACKGROUND":
            return n
    return None


def sweep_world(levels=(1.0, 1.6, 2.2)):
    """扫 World 环境光强度。

    为什么换方向：补光扫描显示 energy 240→460（+92%）只把 p50 从 40.5 抬到 43.7（+8%），
    p99 恒定 —— 天花板 AREA 灯照不到书架/墙的垂直面（cosine），提强度无效。
    环境光从各个方向进来，能照亮垂直面，且**不增加 Cycles 采样成本**（还是同一个背景）。
    代价是影响全场景，所以要同时盯 p99 / 过曝率，别把室外打曝。
    """
    bg = _world_bg()
    if bg is None:
        return {"ok": False, "why": "no world background node"}
    orig = bg.inputs["Strength"].default_value
    lt = bpy.data.lights.get(LAMP)
    if lt is not None:
        lt.energy = 240.0          # 补光回到现状值，只变环境光
    out = []
    for s in levels:
        bg.inputs["Strength"].default_value = s
        r = render_at(240.0, tag="W%03d" % int(round(s * 100)))   # 文件名 m13_ground_W160.png
        r["world_strength"] = s
        out.append(r)
    bg.inputs["Strength"].default_value = orig
    return {"m13w": True, "restored_world": orig, "shots": out}


def sweep(levels=(240.0, 340.0, 460.0)):
    lt = bpy.data.lights.get(LAMP)
    if lt is None:
        return {"ok": False, "why": "missing light %s" % LAMP}
    orig = lt.energy
    out = []
    for e in levels:
        out.append(render_at(e))
    lt.energy = orig          # 复位：扫描本身不留副作用，落地由 m08b_light.py 负责
    return {"m13": True, "lamp": LAMP, "restored_energy": orig, "shots": out}
