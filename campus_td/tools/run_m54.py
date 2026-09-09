# tools/run_m54.py — execute M54 build+render via direct Blender MCP socket (proven path)
import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

CODE = ('exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/'
        r'campus_td/build/m54_motto_stele.py").read(), "m54", "exec"))')

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=540.0)
    print(resp)
