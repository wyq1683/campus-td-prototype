# assemble_m32.py — 把 6 张英雄序列帧合成可循环 MP4（imageio-ffmpeg）
import os, imageio_ffmpeg

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
OUT_DIR = os.path.join(BASE, "previews")
ORDER = ["pre", "charge", "peak", "glow", "flick", "resid"]
FPS = 4  # 每帧 ~0.25s，循环播放有节奏感
OUT = os.path.join(OUT_DIR, "m32_lightning_loop.mp4")

ff = imageio_ffmpeg.get_ffmpeg_exe()
files = [os.path.join(OUT_DIR, "m32_lightning_%s.png" % t) for t in ORDER]
for f in files:
    if not os.path.exists(f):
        raise SystemExit("missing frame: " + f)

# 用 ffmpeg concat（循环列表自身即可循环，这里直接串成一段，播放器 loop 即可）
list_path = os.path.join(OUT_DIR, "_m32_concat.txt")
with open(list_path, "w") as fh:
    for f in files:
        fh.write("file '%s'\n" % f.replace("/", "\\"))

cmd = [
    ff, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
    "-r", str(FPS),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
    OUT,
]
import subprocess
r = subprocess.run(cmd, capture_output=True, text=True)
os.remove(list_path)
if r.returncode != 0:
    raise SystemExit("ffmpeg failed:\n" + r.stderr[-2000:])
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
