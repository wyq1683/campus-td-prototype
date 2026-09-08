# assemble_m36.py — 把 M36 的 7 张英雄序列帧合成可循环 MP4（imageio-ffmpeg）
# 时序设计：暗场久停 → 先导一瞬 → 主回击单帧爆闪 → 余辉渐落 → 二次放电 → 衰减 → 残光久停
# 实现：concat demuxer 里重复列出同一帧来"拉长停留"，配 -r 8（M32 实测 -fps_filter 在 ffmpeg 7.1 不存在）
import os, subprocess, imageio_ffmpeg

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
OUT_DIR = os.path.join(BASE, "previews")
# (tag, 停留帧数)
HOLDS = [("pre", 4), ("charge", 1), ("peak", 1), ("glow", 2), ("flick", 1), ("decay", 2), ("resid", 4)]
FPS = 8
OUT = os.path.join(OUT_DIR, "m36_forked_seq_loop.mp4")

ff = imageio_ffmpeg.get_ffmpeg_exe()

seq = []
for tag, hold in HOLDS:
    p = os.path.join(OUT_DIR, "m36_forked_seq_%s.png" % tag)
    if not os.path.exists(p):
        raise SystemExit("missing frame: " + p)
    seq += [p] * hold

list_path = os.path.join(OUT_DIR, "_m36_concat.txt")
with open(list_path, "w") as fh:
    for f in seq:
        fh.write("file '%s'\n" % f.replace("/", "\\"))

cmd = [
    ff, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
    "-r", str(FPS),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
    OUT,
]
r = subprocess.run(cmd, capture_output=True, text=True)
os.remove(list_path)
if r.returncode != 0:
    raise SystemExit("ffmpeg failed:\n" + r.stderr[-2000:])
print("WROTE", OUT, os.path.getsize(OUT), "bytes,", len(seq), "frames @", FPS, "fps")
