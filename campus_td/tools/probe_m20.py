import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute
code = r'''
import bpy, os
sc = bpy.context.scene
cp = bpy.context.preferences.addons['cycles'].preferences
cp.compute_device_type = 'OPTIX'
cp.get_devices()
devs = [(d.name, d.type, d.use) for d in cp.devices]
sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.denoiser = "OPTIX"
sc.cycles.use_denoising = True
sc.view_settings.view_transform = "AgX"
sc.cycles.samples = 64
sc.render.resolution_x = 800
sc.render.resolution_y = 450
sc.render.image_settings.file_format = 'PNG'
out = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m20_probe.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
result = {"ok": os.path.exists(out), "size": os.path.getsize(out) if os.path.exists(out) else None, "devs": devs, "device": sc.cycles.device}
'''
resp = send_execute(code, strict_json=False, timeout=180.0)
print(resp)
