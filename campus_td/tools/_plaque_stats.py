# _plaque_stats.py — 校门匾文出图后量化校验（不靠肉眼）
#
# 为什么需要：模型读不了 PNG，「字有没有出来 / 金不金」必须转成数值断言。
#
# 判据 1（几何投影）：相机 (0,-62,6.6) 正对匾 (0,-48.35,6.6)，距离 13.59m，
#   70mm 镜头 / 36mm 传感器 / 1600px -> ppm = 1600 / (2*13.59*18/70) = 228.9 px/m。
#   匾 6.0x1.2m -> ROI 1373x275px，中心落在画面正中 (800,450)。
#   字 3.416x0.84m -> 782x192px；笔画约占字框 30~45% -> 亮像素占匾面积 12~20%。
#
# 判据 2（亮度双峰）：匾底深色青铜（暗） vs 金字（亮）。ROI 内取 Otsu 阈值二值化，
#   统计亮像素占比 + 非零列/行的跨度，与判据 1 对表。
#
# v2 修正：v1 用「R>90 且 R>1.5B」抓金色，结果抓到整幅画面里阳光下的暖色地面
#   （x 跨度 0..1598 = 满画面），判据失效 —— 必须先把统计**限定在匾的投影 ROI** 内。
#
# 运行：python _plaque_stats.py [png]

import sys
from PIL import Image

PPM = 1600.0 / (2.0 * (62.0 - 48.41) * 18.0 / 70.0)   # 228.9 px/m
CX, CY = 800.0, 450.0                                  # 匾中心投影（相机正对，居中）
PLAQUE_W, PLAQUE_H = 6.0, 1.2
TEXT_W, TEXT_H = 3.416, 0.84


def lum_hist(vals):
    vals = sorted(vals)
    n = len(vals)

    def q(p):
        return vals[min(n - 1, int(n * p))] if n else 0
    return {"n": n, "p10": q(0.10), "p50": q(0.50), "p75": q(0.75),
            "p90": q(0.90), "p99": q(0.99), "max": vals[-1] if n else 0}


def otsu(hist):
    """256 桶灰度直方图的 Otsu 阈值。"""
    total = sum(hist)
    if total == 0:
        return 128
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_b, w_b, best_t, best_v = 0.0, 0, 0, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        v = w_b * w_f * (m_b - m_f) ** 2
        if v > best_v:
            best_v, best_t = v, t
    return best_t


def stats(path):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    # 匾面 ROI（含石框）
    hw = PLAQUE_W * 0.5 * PPM
    hh = PLAQUE_H * 0.5 * PPM
    x0, x1 = int(CX - hw), int(CX + hw)
    y0, y1 = int(CY - hh), int(CY + hh)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)

    hist = [0] * 256
    lums = []
    cols = {}
    rows = {}
    gold = 0
    tot = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            L = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            hist[L] += 1
            lums.append(L)
            tot += 1
            if r > 90 and r > b * 1.5 and g > b:
                gold += 1

    t = otsu(hist)
    bright_cols, bright_rows = [], []
    nb = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            L = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            if L > t:
                nb += 1
                cols[x] = cols.get(x, 0) + 1
                rows[y] = rows.get(y, 0) + 1
    cxs = sorted(cols) if cols else []
    rys = sorted(rows) if rows else []
    out = {
        "size": [W, H], "ppm": round(PPM, 1),
        "roi": [x0, y0, x1, y1, x1 - x0, y1 - y0],
        "roi_lum": lum_hist(lums),
        "otsu_t": t,
        "bright_frac": round(nb / float(tot), 4) if tot else 0,
        "gold_frac_in_roi": round(gold / float(tot), 4) if tot else 0,
        "expect_text_px": [round(TEXT_W * PPM), round(TEXT_H * PPM)],
    }
    if cxs:
        out["bright_col_span"] = [cxs[0], cxs[-1], cxs[-1] - cxs[0]]
        # 剔除稀疏离群列（噪声/边框），取列计数 >= 峰值 10% 的范围
        pk = max(cols.values())
        dense = [x for x in cxs if cols[x] >= pk * 0.10]
        out["dense_col_span"] = [dense[0], dense[-1], dense[-1] - dense[0]] if dense else None
    if rys:
        out["bright_row_span"] = [rys[0], rys[-1], rys[-1] - rys[0]]
        pk = max(rows.values())
        dense = [y for y in rys if rows[y] >= pk * 0.10]
        out["dense_row_span"] = [dense[0], dense[-1], dense[-1] - dense[0]] if dense else None
    # ---- 字框内部 ROI：排除石框（STONE=0.46 亮度高，会把亮像素跨度撑大到含框）----
    iw = TEXT_W * 0.5 * PPM
    ih = TEXT_H * 0.5 * PPM
    ix0, ix1 = int(CX - iw), int(CX + iw)
    iy0, iy1 = int(CY - ih), int(CY + ih)
    ihist = [0] * 256
    ilums = []
    igold = 0
    for y in range(max(0, iy0), min(H, iy1)):
        for x in range(max(0, ix0), min(W, ix1)):
            r, g, b = px[x, y]
            L = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            ihist[L] += 1
            ilums.append(L)
            if r > 90 and r > b * 1.5 and g > b:
                igold += 1
    it = otsu(ihist)
    inb = sum(ihist[it + 1:])
    out["inner_roi"] = [ix0, iy0, ix1, iy1]
    out["inner_lum"] = lum_hist(ilums)
    out["inner_otsu_t"] = it
    out["inner_bright_frac"] = round(inb / float(len(ilums)), 4) if ilums else 0
    out["inner_gold_frac"] = round(igold / float(len(ilums)), 4) if ilums else 0
    # 字框内 p10≈底、p99≈字 -> 对比度（v2 实测 1.35:1 偏弱，v3 目标 >2.5:1）
    out["contrast"] = round((out["inner_lum"]["p99"] + 1.0) /
                            (out["inner_lum"]["p10"] + 1.0), 2)
    return out


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\previews\m14_plaque.png"
    s = stats(p)
    print("PLAQUE STATS:", s)
    ok = True
    if s["bright_frac"] < 0.04:
        print("WARN: 亮像素占比 %.3f%% 过低 —— 字可能没渲染出来或太暗" % (s["bright_frac"] * 100))
        ok = False
    print("字框内: 底 p10=%d / 字 p99=%d -> 对比度 %.2f:1"
          % (s["inner_lum"]["p10"], s["inner_lum"]["p99"], s["contrast"]))
    if s["contrast"] < 2.5:
        print("WARN: 对比度 < 2.5:1 —— 匾文不够醒目（目标 >= 2.5:1）")
        ok = False
    # 字宽改用 inner ROI 判：不再与石框混在一起（v2 曾虚报 137%）
    if s["inner_bright_frac"] < 0.15 or s["inner_bright_frac"] > 0.60:
        print("WARN: 字框内笔画占比 %.1f%% 不在 15~60%% 合理区间" % (s["inner_bright_frac"] * 100))
        ok = False
    else:
        print("字框内笔画占比 %.1f%% —— 落在合理区间，字确实渲染出来了"
              % (s["inner_bright_frac"] * 100))
    print("VERDICT:", "OK" if ok else "CHECK")
