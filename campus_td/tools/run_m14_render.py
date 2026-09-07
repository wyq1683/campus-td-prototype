# run_m14_render.py — render the M14 school-gate plaque (full clean rebuild: M06+M11+M14)
# Avoids mcporter's short call timeout; uses the proven Direct TCP socket with a long timeout.
import sys, json
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute, RENDER_M14_CODE

resp = send_execute(RENDER_M14_CODE, strict_json=False, timeout=1500.0)
print(json.dumps(resp, ensure_ascii=False, indent=2))
