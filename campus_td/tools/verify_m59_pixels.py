"""M59 final pixel verification: hero + closeup.
Reports meanRGB, dark%(<8), over%(>248), blue%(b>r+25 & b>g+15), gold%(r>180 & g>120 & b<120).
"""
from PIL import Image
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = {
    "hero": os.path.join(HERE, "previews", "m59_gate_emblem_hero.png"),
    "closeup": os.path.join(HERE, "previews", "m59_gate_emblem_closeup.png"),
}


def stats(path):
    im = Image.open(path).convert("RGB")
    px = list(im.getdata())
    n = len(px)
    rs = gs = bs = 0
    dark = over = blue = gold = 0
    for r, g, b in px:
        rs += r; gs += g; bs += b
        if (r + g + b) / 3.0 < 8:
            dark += 1
        if r > 248 and g > 248 and b > 248:
            over += 1
        if b > r + 25 and b > g + 15:
            blue += 1
        if r > 180 and g > 120 and b < 120:
            gold += 1
    return {
        "meanR": round(rs / n, 1),
        "meanG": round(gs / n, 1),
        "meanB": round(bs / n, 1),
        "dark%": round(100.0 * dark / n, 2),
        "over%": round(100.0 * over / n, 2),
        "blue%": round(100.0 * blue / n, 2),
        "gold%": round(100.0 * gold / n, 2),
    }


for k, f in files.items():
    if os.path.exists(f):
        print(f"[{k}] {os.path.basename(f)} -> {stats(f)}")
    else:
        print(f"[{k}] MISSING {f}")
