# verify_m67.py — analyze hero/aerial pixel stats for M67 speed bump visibility
import sys
try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image

def stats(path, label):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    n = 0; sl = 0.0; over = 0; dark = 0
    yellow = 0; yx = 0; yy = 0
    # sample grid for speed
    step = 4
    for y in range(0, H, step):
        for x in range(0, W, step):
            r, g, b = px[x, y]
            n += 1
            lum = 0.299*r + 0.587*g + 0.114*b
            sl += lum
            if lum > 248: over += 1
            if lum < 8: dark += 1
            # saturated yellow: r,g high, b low
            if r > 150 and g > 110 and b < 110 and (r - b) > 60 and (g - b) > 40:
                yellow += 1
                yx += x; yy += y
    meanLum = sl / n
    print("[%s] size=%dx%d meanLum=%.1f over=%.2f%% dark=%.2f%% yellow=%.2f%%" % (
        label, W, H, meanLum, 100.0*over/n, 100.0*dark/n, 100.0*yellow/n))
    if yellow > 0:
        print("   yellow centroid=(%.0f,%.0f) count=%d" % (yx/yellow, yy/yellow, yellow))
    # central region (middle 40%) yellow fraction
    cx0, cx1 = int(W*0.3), int(W*0.7); cy0, cy1 = int(H*0.3), int(H*0.7)
    ny = 0; ncy = 0
    for y in range(cy0, cy1, step):
        for x in range(cx0, cx1, step):
            r, g, b = px[x, y]; ny += 1
            if r > 150 and g > 110 and b < 110 and (r - b) > 60 and (g - b) > 40:
                ncy += 1
    print("   center-region yellow=%.2f%%" % (100.0*ncy/ny))
    # sample exact center pixel
    rc, gc, bc = px[W//2, H//2]
    print("   center pixel RGB=(%d,%d,%d)" % (rc, gc, bc))

stats(r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\previews\m67_speed_bumps_hero.png", "HERO")
stats(r"D:\AI\WorkBuddy\Workspace\2026-09-05-23-46-59\campus_td\previews\m67_speed_bumps_aerial.png", "AERIAL")
