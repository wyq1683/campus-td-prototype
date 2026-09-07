# assemble_m09.py — 把 M9 漫游 PNG 序列合成为 MP4（用 imageio-ffmpeg 自带的 ffmpeg，无需系统 ffmpeg）
# 运行：python assemble_m09.py
import imageio.v2 as imageio
import os, glob

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
FRAMES_DIR = BASE + r"/campus_td/previews/m09_frames"
OUT = BASE + r"/campus_td/previews/m09_walkthrough.mp4"
FPS = 30

files = sorted(glob.glob(os.path.join(FRAMES_DIR, "m09_*.png")))
if not files:
    raise SystemExit("未找到 PNG 序列：%s" % FRAMES_DIR)
writer = imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
for i, f in enumerate(files):
    writer.append_data(imageio.imread(f))
writer.close()
# 清理重复的 frame_*.png（与 m09_*.png 内容相同，由某个 frame 写入器产出；占盘 ~190MB）
removed = 0
for f in glob.glob(os.path.join(FRAMES_DIR, "frame_*.png")):
    try:
        os.remove(f); removed += 1
    except OSError:
        pass
print("frames=%d out=%s size=%d removed_stray=%d" % (len(files), OUT, os.path.getsize(OUT), removed))
