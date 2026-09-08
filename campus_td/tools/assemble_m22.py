# assemble_m22.py — 把 M22 漫游 PNG 序列合成为 MP4（imageio-ffmpeg 自带 ffmpeg）
import imageio.v2 as imageio
import os, glob

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
FRAMES_DIR = BASE + r"/campus_td/previews/m22_frames"
OUT = BASE + r"/campus_td/previews/m22_flythrough.mp4"
FPS = 30

files = sorted(glob.glob(os.path.join(FRAMES_DIR, "m22_*.png")))
if not files:
    raise SystemExit("未找到 PNG 序列：%s" % FRAMES_DIR)
writer = imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
for f in files:
    writer.append_data(imageio.imread(f))
writer.close()
print("frames=%d out=%s size=%d" % (len(files), OUT, os.path.getsize(OUT)))
