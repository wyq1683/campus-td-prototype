# -*- coding: utf-8 -*-
"""M61 渲染执行器：经 blmcp_client 直连 9876 socket 跑 m61_render.py（仅渲染）。"""
import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

RENDER = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m61_render.py"
CODE = r'exec(compile(open(r"%s").read(), "m61r", "exec"))' % RENDER

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=540)
    print(resp)
