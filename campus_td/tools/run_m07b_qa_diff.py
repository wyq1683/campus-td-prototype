import sys
import json
import os
import math

# Add path for blmcp_client
sys.path.insert(0, r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/tools")
from blmcp_client import send_execute

# QA code string
CODE = '''exec(compile(open(r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/build/m07b_qa.py").read(), "m07bqa", "exec"))
result = qa_vfx()'''

# Execute QA via MCP
resp = send_execute(CODE, strict_json=False, timeout=300.0)

# Write raw response to console
print(json.dumps(resp, ensure_ascii=False, indent=2))

# If execution OK and contains result
if "status" in resp and resp["status"] == "ok" and "result" in resp:
    res = resp["result"]
    base_path = res["base_png"]
    with_path = res["with_png"]
    try:
        from PIL import Image
        base_img = Image.open(base_path).convert("L")
        with_img = Image.open(with_path).convert("L")
        # Ensure same size
        if base_img.size != with_img.size:
            raise ValueError("Image sizes differ: {} vs {}".format(base_img.size, with_img.size))
        # Convert to list of pixel values
        base_pixels = list(base_img.getdata())
        with_pixels = list(with_img.getdata())
        diff_pixels = [abs(b - w) for b, w in zip(base_pixels, with_pixels)]
        avg_diff = sum(diff_pixels)/len(diff_pixels) if diff_pixels else 0
        max_diff = max(diff_pixels) if diff_pixels else 0
        # Basic stats
        diff_stats = {
            "avg_diff": avg_diff,
            "max_diff": max_diff,
            "diff_pixels_count": len(diff_pixels),
            "pixel_change_ratio": (len([d for d in diff_pixels if d>0])/len(diff_pixels)) if diff_pixels else 0
        }
        print("\nPixel diff stats:", json.dumps(diff_stats, ensure_ascii=False, indent=2))
    except Exception as e:
        print("\nDiff computation error:", str(e))
else:
    print("\nQA execution failed or no result.")
