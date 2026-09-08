# run_m26.py — Direct TCP Socket 执行 m26_golden_hour.py（绕开 mcporter 默认超时）
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

BUILD = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m26_golden_hour.py"
CODE = 'exec(compile(open(r"%s").read(), "m26", "exec"))' % BUILD

resp = send_execute(CODE, strict_json=False, timeout=900.0)
print(resp)
