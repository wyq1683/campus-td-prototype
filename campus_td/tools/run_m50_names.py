import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute
CODE = r'''
import bpy
print("M50_", [o.name for o in bpy.data.objects if o.name.startswith("M50_")])
print("M58_", [o.name for o in bpy.data.objects if o.name.startswith("M58_")])
'''
print(send_execute(CODE, strict_json=False, timeout=120))
