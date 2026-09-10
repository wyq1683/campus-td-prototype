# run_m59_cam_probe.py — check M59_Cam actual location in scene
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import bpy, mathutils
cam = bpy.data.objects.get("M59_Cam")
if cam:
    result={"name":cam.name,"loc":list(cam.location),"rot":list(cam.rotation_euler),"lens":cam.data.lens}
else:
    result={"error":"M59_Cam not found"}
'''

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=60.0)
    print("RESULT:", resp.get("result"))
