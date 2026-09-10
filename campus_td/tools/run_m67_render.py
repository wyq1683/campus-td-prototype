import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute

CODE = r'''
exec(compile(open(r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\build\m67_render.py").read(), "m67r", "exec"))
'''
res = send_execute(CODE, strict_json=False, timeout=540)
print(res)
