# stats_m36.py — M36 序列帧像素统计核验（防过曝 / 确认闪光阶梯单调性）
# 判据（沿 M29/M34 已收敛经验）：峰帧 meanLum ~150 且 over% < 6；暗帧 meanLum < 15；
#   且 pre < charge < peak、glow/flick 位于中段、resid 回落 → 时间线亮度阶梯成立。
import os
from PIL import Image

base = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
names = ["pre", "charge", "peak", "glow", "flick", "decay", "resid"]
files = ["m36_forked_seq_%s.png" % t for t in names] + ["m36_forked_seq_aerial_peak.png"]

lums = {}
for name in files:
    p = os.path.join(base, name)
    if not os.path.exists(p):
        print(name, "MISSING")
        continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    px = im.load()
    sr = sg = sb = 0
    over = dark = bright = 0
    slum = 0.0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            sr += r; sg += g; sb += b
            mx = max(r, g, b)
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            slum += lum
            if mx > 248: over += 1
            if lum < 8: dark += 1
            if mx > 200: bright += 1
    step = (h // 2) * (w // 2)
    ml = slum / step
    lums[name] = ml
    print(f"{name}: {w}x{h} meanLum={ml:.1f} meanRGB=({sr/step:.1f},{sg/step:.1f},{sb/step:.1f}) "
          f"over%={100*over/step:.2f} dark%={100*dark/step:.2f} bright%={100*bright/step:.2f}")

seq = [lums.get("m36_forked_seq_%s.png" % t) for t in names]
if all(v is not None for v in seq):
    print("LUM_LADDER=" + " -> ".join("%s:%.1f" % (t, v) for t, v in zip(names, seq)))
    peak = seq[2]
    print("PEAK_IS_MAX=", peak == max(seq), " PRE_IS_MIN=", seq[0] == min(seq))
