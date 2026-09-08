import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

CODE = '''exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m07b_qa.py").read(), "m07bqa", "exec"))
result = qa_vfx()'''

resp = send_execute(CODE, strict_json=False, timeout=300.0)
import json
print(json.dumps(resp, ensure_ascii=False, indent=2))
