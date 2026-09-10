# -*- coding: utf-8 -*-
"""M62 构建执行器：经 blmcp_client 直连 9876 socket 跑 m62_gazebo.py（仅建模，不渲染）。"""
import sys
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

BUILD = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m62_gazebo.py"
CODE = r'exec(compile(open(r"%s").read(), "m62", "exec"))' % BUILD

if __name__ == "__main__":
    resp = send_execute(CODE, strict_json=False, timeout=300)
    print(resp)
