# run_m59_render.py — Direct TCP runner for M59 render only
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m59_render.py").read(), "m59r", "exec"))'

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=540.0)
    print("STATUS:", resp.get("status"))
    print("STDOUT:", (resp.get("stdout") or "")[:4000])
    print("STDERR:", (resp.get("stderr") or "")[:4000])
    print("RESULT:", resp.get("result"))
