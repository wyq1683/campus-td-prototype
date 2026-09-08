# stats_m31.py — 对 M31 正午硬光预览图做像素统计（沿用 M28/M29 校准口径，0-255 sRGB）
# 输出：meanRGB / 过曝%(>248) / 死黑%(<8) / nonblack% / max，便于判断曝光是否过亮/过暗。
import sys
from PIL import Image
import numpy as np

PATHS = [
    (r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m31_noon_harsh_hero.png", "hero"),
    (r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td/previews/m31_noon_harsh_aerial.png", "aerial"),
]

for p, name in PATHS:
    try:
        im = Image.open(p).convert("RGB")
        a = np.asarray(im, dtype=np.float64)
        n = a.shape[0] * a.shape[1]
        mean = a.reshape(-1, 3).mean(axis=0)
        over = np.mean((a[:, :, 0] > 248) & (a[:, :, 1] > 248) & (a[:, :, 2] > 248)) * 100
        # 死黑：L<8
        lum = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
        dark = np.mean(lum < 8) * 100
        nonblack = np.mean(lum > 2) * 100
        mx = int(a.reshape(-1, 3).max())
        print(f"{name}: meanRGB({mean[0]:.1f},{mean[1]:.1f},{mean[2]:.1f}) over%={over:.2f} dark%={dark:.2f} nonblack%={nonblack:.2f} max={mx}")
    except Exception as e:
        print(f"{name}: ERROR {e}")
