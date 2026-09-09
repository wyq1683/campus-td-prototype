# assemble_m37.py — 把 M37 的 16 张迎风飘动序列帧合成无缝循环 MP4（imageio-ffmpeg，回退 ffmpeg）
import os, subprocess, shutil

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
OUT_DIR = os.path.join(BASE, "previews")
FPS = 12
NLOOP = 16
OUT = os.path.join(OUT_DIR, "m37_flag_loop.mp4")

# 取 ffmpeg 可执行文件
FF = None
try:
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FF = shutil.which("ffmpeg")
if not FF:
    raise SystemExit("no ffmpeg available")

seq = [os.path.join(OUT_DIR, "m37_flag_loop_%03d.png" % k) for k in range(NLOOP)]
for p in seq:
    if not os.path.exists(p):
        raise SystemExit("missing frame: " + p)

list_path = os.path.join(OUT_DIR, "_m37_concat.txt")
with open(list_path, "w") as fh:
    for f in seq:
        fh.write("file '%s'\n" % f.replace("/", "\\"))

cmd = [
    FF, "-y", "-f", "concat", "-safe", "0", "-i", list_path,
    "-r", str(FPS),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
    OUT,
]
r = subprocess.run(cmd, capture_output=True, text=True)
os.remove(list_path)
if r.returncode != 0:
    raise SystemExit("ffmpeg failed:\n" + r.stderr[-2000:])
print("WROTE", OUT, os.path.getsize(OUT), "bytes,", NLOOP, "frames @", FPS, "fps")
