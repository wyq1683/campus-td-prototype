# m12_analyze.py — 上层补光量化判读
#
# 判据：同一栋 Library、同一房间进深、同一支镜头，只差楼层。
#   地面层 1F（M8 补光 240/300，M8B 已调好）= 基准
#   上层   3F（M8D 补光 200）= 待测
# 比的是**亮度分布形态**，不是绝对构图（两层家具密度不同，绝对值本来就有差）。
#
# 用法：python campus_td/build/m12_analyze.py [upper.png] [ground.png]

import os
import sys
import statistics

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow：pip install Pillow")
    raise SystemExit(1)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(BASE, "previews")
F_UPPER = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PREV, "m12_upper_F2.png")
F_GROUND = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PREV, "m12_ground_1F.png")

# 判读阈值（室内成片的经验带）
BAND_P50 = (55.0, 150.0)     # 中位亮度合理带
MAX_BLOWN = 0.03             # 过曝（>248）占比上限
MAX_CRUSH = 0.06             # 死黑（<8）占比上限
TOL = 0.25                   # 与基准层相差 25% 以内算一致


def lum_stats(path):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    vals = []
    step = 2
    for y in range(0, H, step):
        for x in range(0, W, step):
            r, g, b = px[x, y]
            vals.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    vals.sort()
    n = len(vals)

    def q(p):
        return vals[min(n - 1, int(p * n))]

    return {
        "file": os.path.basename(path),
        "size": (W, H),
        "n": n,
        "mean": round(statistics.mean(vals), 1),
        "p10": round(q(0.10), 1),
        "p50": round(q(0.50), 1),
        "p75": round(q(0.75), 1),
        "p90": round(q(0.90), 1),
        "p99": round(q(0.99), 1),
        "blown": round(sum(1 for v in vals if v > 248) / n, 4),   # 过曝
        "crush": round(sum(1 for v in vals if v < 8) / n, 4),     # 死黑
    }


def main():
    rows = {}
    for tag, p in (("upper", F_UPPER), ("ground", F_GROUND)):
        if not os.path.exists(p):
            print("[m12] 缺少 %s" % p)
            return
        rows[tag] = lum_stats(p)

    print("=" * 62)
    print("M12 上层补光量化判读  (Library：上层 3F vs 地面层 1F 基准)")
    print("=" * 62)
    hdr = ("指标", "上层 3F (E=200)", "地面 1F (基准)", "比值")
    print("%-10s %16s %16s %8s" % hdr)
    print("-" * 62)
    for k in ("mean", "p10", "p50", "p75", "p90", "p99"):
        u, g = rows["upper"][k], rows["ground"][k]
        r = (u / g) if g else float("nan")
        print("%-10s %16.1f %16.1f %8.2f" % (k, u, g, r))
    for k in ("blown", "crush"):
        u, g = rows["upper"][k], rows["ground"][k]
        r = (u / g) if g else float("nan")
        print("%-10s %15.2f%% %15.2f%% %8.2f" % (k, u * 100, g * 100, r))
    print("-" * 62)

    u, g = rows["upper"], rows["ground"]
    verdicts = []

    # 1) 绝对亮度带
    if BAND_P50[0] <= u["p50"] <= BAND_P50[1]:
        verdicts.append(("PASS", "中位亮度 %.1f 落在合理带 %s 内" % (u["p50"], BAND_P50)))
    elif u["p50"] < BAND_P50[0]:
        # M13 实测护栏：p50 低 ≠ 照明不足。Library 1F 画面被 6 个深色书架占满，
        #   实测补光 240→460（+92%）p50 只 40.5→43.7（+8%），天花板 AREA 灯照不到垂直面；
        #   环境光 0.45→1.0（+122%）也只 +17%。只要暗部没塌陷、高光正常，
        #   低 p50 应判为"内容偏暗"而非"照明故障"，别去动灯。
        if u["crush"] < 0.02 and u["p90"] > 100.0:
            verdicts.append(("PASS", "中位亮度 %.1f 低于合理带 %.0f，但死黑仅 %.2f%%、p90=%.0f 正常"
                             "→ 判定为**内容偏暗**（深色物体占画面），非照明故障，不建议提灯"
                             % (u["p50"], BAND_P50[0], u["crush"] * 100, u["p90"])))
        else:
            verdicts.append(("DARK", "中位亮度 %.1f 低于合理带下限 %.0f → 偏暗" % (u["p50"], BAND_P50[0])))
    else:
        verdicts.append(("BRIGHT", "中位亮度 %.1f 高于合理带上限 %.0f → 偏亮" % (u["p50"], BAND_P50[1])))

    # 2) 过曝 / 死黑
    if u["blown"] > MAX_BLOWN:
        verdicts.append(("BLOWN", "过曝像素 %.2f%% > %.1f%% → 高光溢出，应降 energy" % (u["blown"] * 100, MAX_BLOWN * 100)))
    if u["crush"] > MAX_CRUSH:
        verdicts.append(("CRUSH", "死黑像素 %.2f%% > %.1f%% → 暗部塌陷，应提 energy 或补环境光" % (u["crush"] * 100, MAX_CRUSH * 100)))

    # 3) 与基准层的一致性 —— 但**先自检基准层**：基准若自己不在合理带，
    #    相对判据只能当参考，不能当结论（地面层家具密度/颜色也与上层不同，p50 天然有差）。
    ratio = (u["p50"] / g["p50"]) if g["p50"] else 1.0
    base_ok = BAND_P50[0] <= g["p50"] <= BAND_P50[1]
    if not base_ok:
        verdicts.append(("WARN", "基准层 1F 自身 p50=%.1f 不在合理带 %s 内（%+0.f%%）"
                         "→ 相对判据仅作参考，以绝对判据为准"
                         % (g["p50"], BAND_P50, (g["p50"] / BAND_P50[0] - 1) * 100)))
        if g["crush"] > MAX_CRUSH or g["p99"] > 235.0:
            verdicts.append(("WARN", "基准层 1F 另有 死黑 %.2f%% / p99=%.0f → 高对比度"
                             "（窗光刺眼 + 室内欠曝），是后续优化项，不影响上层结论"
                             % (g["crush"] * 100, g["p99"])))
    if abs(ratio - 1.0) <= TOL:
        verdicts.append(("PASS", "与基准层相差 %.0f%%，在 ±%.0f%% 容差内 → 200 合适"
                         % ((ratio - 1) * 100, TOL * 100)))
    elif ratio > 1.0 + TOL:
        # 上层比基准亮：只有基准层**本身合格**时才建议下调，否则不动
        if base_ok:
            need = 200.0 / max(ratio, 0.05)
            verdicts.append(("BRIGHT", "比合格基准亮 %.0f%%（超出 ±%.0f%%）→ 建议 ~%d"
                             % ((ratio - 1) * 100, TOL * 100, round(need / 10) * 10)))
        else:
            verdicts.append(("PASS", "比基准层亮 %.0f%%，但基准层自身偏暗 → 判定 200 合适，不下调"
                             % ((ratio - 1) * 100)))
    else:
        need = 200.0 * (1.0 / max(ratio, 0.05))
        verdicts.append(("DARK", "比基准层暗 %.0f%%（超出 ±%.0f%%）→ 200 偏低，建议 ~%d"
                         % ((1 - ratio) * 100, TOL * 100, round(need / 10) * 10)))

    # 4) 终局：绝对判据全绿才算通过
    hard_fail = [v for v in verdicts if v[0] in ("DARK", "BRIGHT", "BLOWN", "CRUSH")]
    tag = "FAIL" if hard_fail else "PASS"
    verdicts.append((tag, "终局：上层补光 energy=200 %s" % ("需调整" if hard_fail else "判定合适，M8D 结案")))

    print("判读：")
    for tag, msg in verdicts:
        mark = {"PASS": "[OK]  ", "DARK": "[暗]  ", "BRIGHT": "[亮]  ", "WARN": "[注意]", "FAIL": "[FAIL]",
                "BLOWN": "[过曝]", "CRUSH": "[死黑]"}.get(tag, "[?]   ")
        print("  %s %s" % (mark, msg))
    print("=" * 62)
    return verdicts


if __name__ == "__main__":
    main()
