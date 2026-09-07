# run_m17.py — 发送 M17 渲染代码到 Blender MCP（540s 超时，绕开 cli 默认 120s）
import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

code = open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/_render_m17.py", encoding="utf-8").read()
resp = send_execute(code, strict_json=False, timeout=540.0)
print(__import__("json").dumps(resp, ensure_ascii=False, indent=2))
