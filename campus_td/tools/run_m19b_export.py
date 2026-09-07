# run_m19b_export.py — 经 Direct TCP Socket 直连 Blender MCP @9876 执行 m19b_export.py
# 用项目已验证的 send_execute（超时 540s，绕开 mcporter 60s 客户端超时无法覆盖大场景导出）。
import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

SCRIPT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m19b_export.py"
code = 'exec(compile(open(r"%s").read(), "m19b_export", "exec"))' % SCRIPT

resp = send_execute(code, strict_json=False, timeout=540.0)
print(resp)
