# run_m21_stairs.py — 补渲 M21 画廊缺失的 stairs 帧（M15_Cam），Direct TCP 900s
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import bpy, mathutils, importlib.util, os, time
BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT = BASE + r"/previews"
spec = importlib.util.spec_from_file_location("m06l", M06)
m06 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m06)
cpref = bpy.context.preferences.addons['cycles'].preferences
cpref.compute_device_type='OPTIX'; cpref.get_devices()
for d in cpref.devices:
    if d.type in ('OPTIX','CUDA'): d.use=True
sc = bpy.context.scene
sc.render.engine="CYCLES"; sc.cycles.device='GPU'; sc.view_settings.view_transform='AgX'
def hide_previews():
    h=[]
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            h.append((o,o.hide_render)); o.hide_render=True
    return h
def show(h):
    for o,w in h: o.hide_render=w
cam = bpy.data.objects.get("M15_Cam")
if cam is None:
    result={"status":"skip_no_cam"}
else:
    m06.build_lighting("day")
    sc.camera = cam
    h = hide_previews()
    sc.cycles.device='GPU'; sc.cycles.denoiser='OPTIX'; sc.cycles.use_denoising=True
    sc.cycles.samples=512; sc.cycles.max_bounces=12
    sc.cycles.caustics_reflective=False; sc.cycles.caustics_refractive=False
    sc.view_settings.view_transform='AgX'
    sc.render.resolution_x=2560; sc.render.resolution_y=1440; sc.render.resolution_percentage=100
    out = os.path.join(OUT,"m21_gallery_stairs.png")
    sc.render.filepath = out
    t0=time.time(); bpy.ops.render.render(write_still=True); dt=round(time.time()-t0,1)
    show(h)
    result={"status":"ok","shot":"stairs","camera":"M15_Cam","out":out,
            "size":os.path.getsize(out) if os.path.exists(out) else None,"time_s":dt}
'''
resp = send_execute(CODE, strict_json=False, timeout=900.0)
print(resp)
