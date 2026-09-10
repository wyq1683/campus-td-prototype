import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute
CODE = r'''
import bpy
names = [o.name for o in bpy.data.objects if o.name.startswith("M46_")]
print("M46_NAMES", names)
'''
print(send_execute(CODE, strict_json=False, timeout=120))
