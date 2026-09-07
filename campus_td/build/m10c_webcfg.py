# m10c_webcfg.py — 生成 WebGL2 原型用的前端配置
#
# 单一数据源：读取 m10_balance.py --export 产出的 m10_config.json，
# 补入从 Blender 探针取到的建筑轮廓，输出 campus_td/web/config.js。
# 前端只读 config.js，不手抄任何数字。
#
# 用法：python campus_td/build/m10c_webcfg.py

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "build", "m10_config.json")
OUT = os.path.join(BASE, "web", "config.js")

# 建筑轮廓：2026-09-07 对 Blender 场景实测（Bldg_*_Roof 包围盒 + 层高 3.9m）
#   世界坐标沿用 Blender 的 (x, y)，前端里 y 映射为 shader 的 z（Y 轴朝上）。
#   2026-09-07b M11 总平重排后更新：场地由 46m 扩到 96m，7 栋楼重排到 U 形路径之外，
#   Teach/Lab 不再超界，故取消此前的「按场地裁剪」。
#   高度沿用 floors x 3.9 的层高值（不含 0.4m 屋面板），与塔防数值口径一致。
BUILDINGS = [
    # name,     x0,    x1,    y0,    y1,   height, note
    ("Admin",   -45.0, -31.0,  26.0,  36.0, 15.6, ""),
    ("Dorm",    -45.5, -30.5,  -9.0,   1.0, 23.4, ""),
    ("Gym",      24.5,  39.5,  -0.5,  12.5, 11.7, ""),
    ("Canteen",  28.5,  43.5, -15.5,  -4.5,  7.8, ""),
    ("Library", -46.0, -30.0,   6.0,  18.0, 15.6, ""),
    ("Teach",   -32.5,  32.5, -37.5, -20.5, 15.6, ""),
    ("Lab",     -24.5,  24.5,  23.5,  38.5, 19.5, ""),
]

# 场地半边长（M11 后为 96 x 96m）
SITE_HALF = 48.0


def main():
    with open(SRC, encoding="utf-8") as f:
        cfg = json.load(f)

    cfg["buildings"] = [
        {"name": n, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "h": h, "note": note}
        for n, x0, x1, y0, y1, h, note in BUILDINGS
    ]
    cfg["level"]["site_half"] = SITE_HALF
    cfg["_meta"]["generated_by"] = "campus_td/build/m10c_webcfg.py"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 自动生成，勿手改。来源：campus_td/build/m10_config.json + Blender 建筑探针\n")
        f.write("// 重新生成：python campus_td/build/m10c_webcfg.py\n")
        f.write("const CFG = ")
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    print("[m10c] %s -> %s" % (SRC, OUT))
    print("[m10c] buildings=%d waves=%d towers=%d slots=%d"
          % (len(cfg["buildings"]), len(cfg["waves"]),
             len(cfg["towers"]["fixed"]), len(cfg["towers"]["slots"])))
    return OUT


if __name__ == "__main__":
    main()
