# run_m52.py — 直连 Blender MCP addon @9876，执行 M52 构建 + 双机位渲染 + 像素核验
import sys, json, os
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
BUILD = ROOT + r"/build/m52_gate_guardhouse.py"
PRE = ROOT + r"/previews"

code = open(BUILD, encoding="utf-8").read()
resp = send_execute(code, strict_json=False, timeout=540.0)
print("=== BUILD RESP ===")
print(json.dumps(resp, ensure_ascii=False)[:3000])

# 像素统计核验（PIL）
try:
    from PIL import Image
    def stats(path):
        if not os.path.exists(path):
            return {"path": path, "exists": False}
        im = Image.open(path).convert("RGB")
        px = im.getdata()
        n = len(px)
        rs = gs = bs = 0
        over = dark = 0
        for (r, g, b) in px:
            rs += r; gs += g; bs += b
            if r > 248 and g > 248 and b > 248: over += 1
            if r < 8 and g < 8 and b < 8: dark += 1
        return {
            "path": os.path.basename(path), "exists": True,
            "meanRGB": [round(rs/n, 1), round(gs/n, 1), round(bs/n, 1)],
            "over%": round(100.0*over/n, 2), "dark%": round(100.0*dark/n, 2),
        }
    print("=== PIXEL STATS ===")
    print(json.dumps({
        "closeup": stats(PRE + "/m52_guardhouse_closeup.png"),
        "hero": stats(PRE + "/m52_guardhouse_hero.png"),
    }, ensure_ascii=False))
except Exception as e:
    print("PIL_STATS_WARN:" + str(e))
