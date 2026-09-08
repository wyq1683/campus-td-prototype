# m07b_qa.py — V3.1 粒子特效 QA（Blender 侧：只负责构建 + 渲染，像素差分交给外部 runner）
# 做法：同一机位同一帧，渲染 ① 基线（隐藏所有 V3_ 发射器 + 暂停 v3_update 处理器）
#      ② 带粒子（恢复 muzzle，hit 由处理器按目标显隐）；回传两张 PNG 路径供外部像素差分。
#      选 frame=5：此时 Tower_1 射程内有敌人（出生点近塔基）→ 同时验证枪口+命中火花。
import bpy, os, mathutils

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PRE = os.path.join(ROOT, "previews")
PREFIX = "V3_"
QA_FRAME = 5
W, H = 640, 360


def _ensure_built():
    import importlib.util, sys
    if bpy.data.objects.get("V3_Muzzle_Tower_1") is not None:
        return
    def _load(modname, path):
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        return mod
    m07b = _load("m07b_vfx_mod", ROOT + "/build/m07b_vfx.py")
    m07b.build_vfx()


def _setup_camera():
    sc = bpy.context.scene
    cam = bpy.data.objects.get(PREFIX + "QA_Cam")
    if cam is None:
        bpy.ops.object.camera_add(location=(-30.0, -20.0, 7.0))
        cam = bpy.context.active_object
        cam.name = PREFIX + "QA_Cam"
    cam.location = (-30.0, -20.0, 7.0)
    cam.data.lens = 40.0
    cam.data.clip_end = 200.0
    trg = mathutils.Vector((-22.0, -13.0, 3.2))
    direction = trg - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    return cam


def _render(path):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "GPU"
    except Exception:
        pass
    sc.cycles.samples = 64
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    sc.frame_set(QA_FRAME)
    bpy.ops.render.render(write_still=True)


def _pop_v3_handler():
    h = None
    for hh in list(bpy.app.handlers.frame_change_pre):
        if getattr(hh, "__name__", "") == "v3_update":
            h = hh
            bpy.app.handlers.frame_change_pre.remove(hh)
    return h


def _push_v3_handler(h):
    if h is not None:
        bpy.app.handlers.frame_change_pre.append(h)


def qa_vfx():
    _ensure_built()
    _setup_camera()
    base_path = os.path.join(PRE, "m07b_qa_base.png")
    out_path = os.path.join(PRE, "m07b_qa.png")

    # ① 基线：隐藏 muzzle+hit 发射器，并暂停 v3_update（避免它把 hit 显隐回来）
    h = _pop_v3_handler()
    for o in bpy.data.objects:
        if o.name.startswith(PREFIX + "Muzzle_") or o.name.startswith(PREFIX + "Hit_"):
            o.hide_render = True
    _render(base_path)

    # ② 带粒子：恢复 muzzle（常驻），hit 由处理器按目标显隐
    _push_v3_handler(h)
    for o in bpy.data.objects:
        if o.name.startswith(PREFIX + "Muzzle_"):
            o.hide_render = False
    bpy.context.scene.frame_set(QA_FRAME)  # 触发 v3_update 定位 hit
    _render(out_path)

    g = globals()
    g["result"] = {
        "qa_frame": QA_FRAME,
        "base_png": base_path,
        "with_png": out_path,
        "objects": len(bpy.data.objects),
        "note": "粒子增量像素由外部 runner 用 PIL 差分判定",
    }
    return g["result"]


if __name__ == "__main__":
    qa_vfx()
