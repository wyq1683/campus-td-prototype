import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blmcp_client import send_execute

ROOT = os.path.dirname(os.path.abspath(__file__))
probe_path = os.path.join(ROOT, "probe_plaza_height.py").replace("\\", "/")

CODE = f'''
import bpy
exec(compile(open("{probe_path}").read(), "probe_plaza_height.py", "exec"))
'''

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=120.0)
    print("STATUS:", resp.get("status"))
    print("STDERR:", (resp.get("stderr") or "")[:2000])
    print("RESULT:", resp.get("result"))
