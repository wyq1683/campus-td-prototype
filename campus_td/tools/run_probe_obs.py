import sys
sys.path.insert(0, r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools")
from blmcp_client import send_execute
CODE = r'''
exec(compile(open(r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\tools\probe_m67_obs.py").read(), "probe", "exec"))
'''
print(send_execute(CODE, strict_json=False, timeout=120))
