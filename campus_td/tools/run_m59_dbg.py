# run_m59_dbg.py — run M59 build wrapped in try/except to surface the real traceback
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

CODE = r'''
import traceback, bpy
n_before = sum(1 for o in bpy.data.objects if o.name.startswith("M59_"))
try:
    exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m59_gate_emblem.py").read(), "m59", "exec"))
    result = {"built": True, "n_before": n_before}
except Exception:
    result = {"built": False, "n_before": n_before, "traceback": traceback.format_exc()[-3000:]}
'''

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=300.0)
    print("STATUS:", resp.get("status"))
    print("STDERR:", (resp.get("stderr") or "")[:2000])
    print("RESULT:", resp.get("result"))
