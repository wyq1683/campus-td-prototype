# run_m10d.py — Direct TCP wrapper for M10D build+render with long timeout
# (mcporter's default 60s call timeout is too short for Cycles renders)
import json
import sys

sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

M10D_PATH = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m10d_enemies.py"
code = r'exec(compile(open(r"%s").read(), "m10d", "exec"))' % M10D_PATH

resp = send_execute(code, strict_json=False, timeout=600.0)
print(json.dumps(resp, ensure_ascii=False, indent=2))
