# encode_m09.py — 将 M9 漫游 PNG 序列编码为 MP4（使用 imageio-ffmpeg 自带的静态 ffmpeg）
import imageio_ffmpeg, subprocess, os, shutil

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
frames_dir = BASE + r"/campus_td/previews/m09_frames"
out_mp4 = BASE + r"/campus_td/previews/m09_walkthrough.mp4"
out_still = BASE + r"/campus_td/previews/m09_preview.png"   # 末帧 = 图书馆阅览室室内

ff = imageio_ffmpeg.get_ffmpeg_exe()
print("FFMPEG:", ff)

# 1) 编码 MP4：30fps, H264, yuv420p(广泛兼容), crf 18 高质量
cmd = [ff, "-y", "-framerate", "30", "-i", os.path.join(frames_dir, "frame_%04d.png"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
       "-movflags", "+faststart", out_mp4]
r = subprocess.run(cmd, capture_output=True, text=True)
print("ENCODE_RC=", r.returncode)
if r.returncode != 0:
    print("STDERR:", r.stderr[-3000:])

# 2) 末帧作为静态预览图（证明可进入 + 电影感整合）
src = os.path.join(frames_dir, "frame_0120.png")
if os.path.exists(src):
    shutil.copy(src, out_still)
    print("STILL_COPIED:", out_still)

if os.path.exists(out_mp4):
    print("MP4_SIZE_MB=%.1f" % (os.path.getsize(out_mp4) / 1e6))
