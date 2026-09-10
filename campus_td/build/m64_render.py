# m64_render.py — M64 渲染（仅渲染，不建物体）
# 复用已验证相机：M64_Cam(特写) / M19C_HeroDay(英雄) / M11_CamAerial(鸟瞰)
# Cycles GPU OptiX / AgX / 白昼
import bpy, os

ROOT = "D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
PREV = os.path.join(ROOT, "campus_td", "previews")
os.makedirs(PREV, exist_ok=True)

sc = bpy.context.scene
# ---- ensure day lighting (reuse m06 if present) ----
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("m06", os.path.join(ROOT, "campus_td", "build", "m06_lighting.py"))
    m06 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m06)
    m06.build_lighting('day')
except Exception as e:
    print("lighting reuse skipped:", e)

# ---- render settings ----
sc.render.engine = 'CYCLES'
try:
    sc.cycles.device = 'GPU'
    sc.cycles.compute_device_type = 'OPTIX'
    sc.cycles.denoiser = 'OPTIX'
except Exception:
    pass
sc.cycles.samples = 256
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.view_settings.view_transform = 'AgX'
sc.view_settings.exposure = 0.0

def render_cam(cam_name, out_name, exposure=0.0):
    cam = bpy.data.objects.get(cam_name)
    if cam is None:
        return f"MISSING:{cam_name}"
    sc.camera = cam
    sc.view_settings.exposure = exposure
    out = os.path.join(PREV, out_name)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return out

results = []
# Top-down court closeup is well-lit (sun overhead); no exposure bump needed
results.append(("closeup", render_cam("M64_Cam", "m64_basketball_closeup.png", exposure=0.0)))
results.append(("hero",    render_cam("M19C_HeroDay", "m64_basketball_hero.png")))
results.append(("aerial",  render_cam("M11_CamAerial", "m64_basketball_aerial.png")))

# restore active camera to hero day (don't leave M64_Cam active)
hero = bpy.data.objects.get("M19C_HeroDay")
if hero: sc.camera = hero

result = {"renders": results, "active_cam_restored": "M19C_HeroDay" if hero else None}
print("RESULT_JSON_START")
import json
print(json.dumps(result))
print("RESULT_JSON_END")
