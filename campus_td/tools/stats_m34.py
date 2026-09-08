import sys
from PIL import Image
import os

base = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews"
for name in ["m34_forked_lightning_hero.png", "m34_forked_lightning_aerial.png"]:
    p = os.path.join(base, name)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    px = im.load()
    n = w * h
    sr = sg = sb = 0
    over = 0      # max channel > 248
    dark = 0      # mean lum < 8
    bright = 0    # max channel > 200 (bolt highlight presence sanity)
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            sr += r; sg += g; sb += b
            mx = max(r, g, b); mn = min(r, g, b)
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            if mx > 248: over += 1
            if lum < 8: dark += 1
            if mx > 200: bright += 1
    step = (h//2) * (w//2)
    print(f"{name}: size={w}x{h} meanR={sr/step:.1f} meanG={sg/step:.1f} meanB={sb/step:.1f} "
          f"over%={100*over/step:.2f} dark%={100*dark/step:.2f} bright%={100*bright/step:.2f}")
