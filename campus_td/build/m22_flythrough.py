# m22_flythrough.py — 里程碑 M22：影院级漫游视频（Cycles GPU OptiX，多机位平滑运镜）
# 非破坏：不删除/重建任何场景物体，仅新建一个临时相机 M22_Cam（前缀 M22_，幂等）用于出图。
# 思路：复用 M21 已验证的 6 个命名机位（hero_day / aerial_dusk / gate / crenellations / classroom / stairs），
#   在它们之间做平滑运镜 —— 位置 lerp + 朝向 slerp（shortest-arc）+ 焦距 lerp，
#   逐帧渲染 PNG 序列，由 tools/assemble_m22.py 外部合成为 MP4。
# 相较 M9（EEVEE、沿旧坐标飞行、M11 重排后已失效）：本视频基于当前布局的已验证机位，且用 OptiX 终帧质量。
import bpy, mathutils, importlib.util, os, time, math

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
M06 = BASE + r"/build/m06_lighting.py"
OUT_DIR = BASE + r"/previews/m22_frames"
OUT = BASE + r"/previews"

# 巡游顺序（沿已验证机位串联成一条电影感路径）
TOUR = ["M19C_HeroDay", "M11_CamAerial", "M14_Cam", "M16_Cam", "M17_Cam", "M15_Cam"]

FRAMES_PER_SEG = 16        # 每段过渡帧数 → 5 段 × 16 + 1 = 81 帧
FPS = 30
W, H = 1280, 720
SAMPLES = 160
PREFIX = "M22_"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def quat_slerp(a, b, t):
    """shortest-arc 四元数 slerp（手动实现，避免依赖各版 API 差异）。"""
    ax, ay, az, aw = a.x, a.y, a.z, a.w
    bx, by, bz, bw = b.x, b.y, b.z, b.w
    dot = ax * bx + ay * by + az * bz + aw * bw
    if dot < 0.0:                      # 保证最短弧
        bx, by, bz, bw = -bx, -by, -bz, -bw
        dot = -dot
    if dot > 0.9995:
        q = mathutils.Quaternion((aw + t * (bw - aw), ax + t * (bx - ax),
                                  ay + t * (by - ay), az + t * (bz - az)))
        q.normalize()
        return q
    theta0 = math.acos(max(-1.0, min(1.0, dot)))
    theta = theta0 * t
    s0 = math.sin(theta0)
    s1 = math.cos(theta) - dot * math.sin(theta) / s0
    s2 = math.sin(theta) / s0
    return mathutils.Quaternion((s1 * aw + s2 * bw, s1 * ax + s2 * bx,
                                s1 * ay + s2 * by, s1 * az + s2 * bz))


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def hide_previews():
    h = []
    for o in bpy.data.objects:
        if o.name.startswith("Mat_Preview_"):
            h.append((o, o.hide_render))
            o.hide_render = True
    return h


def show(h):
    for o, was in h:
        o.hide_render = was


def main():
    sc = bpy.context.scene

    # ---- 1) Cycles GPU (OptiX) ----
    cpref = bpy.context.preferences.addons['cycles'].preferences
    cpref.compute_device_type = 'OPTIX'
    cpref.get_devices()
    for d in cpref.devices:
        if d.type in ('OPTIX', 'CUDA'):
            d.use = True

    sc.render.engine = "CYCLES"
    sc.view_settings.view_transform = 'AgX'

    m06 = load(M06, "m06l")
    m06.build_lighting('day')           # 全片统一白昼光照，保证过渡连贯

    # ---- 2) 读取巡游机位的世界变换 ----
    wps = []
    for nm in TOUR:
        cam = bpy.data.objects.get(nm)
        if cam is None:
            continue
        loc, quat, _scl = cam.matrix_world.decompose()
        wps.append({"name": nm, "loc": loc, "quat": quat, "lens": cam.data.lens})
    if len(wps) < 2:
        result = {"error": "too few cameras", "found": [w["name"] for w in wps]}
        return result

    # ---- 3) 建/清 M22_Cam ----
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    for c in [c for c in bpy.data.cameras if c.name.startswith(PREFIX)]:
        bpy.data.cameras.remove(c)

    cam_data = bpy.data.cameras.new(PREFIX + "Cam")
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 400.0
    cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_mode = 'QUATERNION'

    # ---- 4) 渲染配置 ----
    sc.cycles.device = 'GPU'
    sc.cycles.denoiser = 'OPTIX'
    sc.cycles.use_denoising = True
    sc.cycles.samples = SAMPLES
    sc.cycles.max_bounces = 12
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = 'AgX'
    sc.render.resolution_x = W
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'

    os.makedirs(OUT_DIR, exist_ok=True)
    hidden = hide_previews()

    segs = len(wps) - 1
    total_frames = segs * FRAMES_PER_SEG + 1
    t0 = time.time()
    rendered = 0
    frame_times = []
    for f in range(total_frames):
        pos = f / FRAMES_PER_SEG
        seg = min(int(pos), segs - 1)
        t = pos - seg
        te = smoothstep(t)
        a, b = wps[seg], wps[seg + 1]
        loc = a["loc"].lerp(b["loc"], te)
        quat = quat_slerp(a["quat"], b["quat"], te)
        lens = a["lens"] + (b["lens"] - a["lens"]) * te
        cam.location = loc
        cam.rotation_quaternion = quat
        cam.data.lens = lens
        fp = os.path.join(OUT_DIR, "m22_%04d.png" % f)
        sc.render.filepath = fp
        tf = time.time()
        bpy.ops.render.render(write_still=True)
        frame_times.append(round(time.time() - tf, 2))
        rendered += 1

    show(hidden)
    total = round(time.time() - t0, 1)

    result = {
        "milestone": "M22",
        "device": sc.cycles.device,
        "compute_device_type": cpref.compute_device_type,
        "denoiser": sc.cycles.denoiser,
        "samples": sc.cycles.samples,
        "resolution": [W, H],
        "fps": FPS,
        "tour": [w["name"] for w in wps],
        "total_frames": total_frames,
        "rendered": rendered,
        "frames_dir": OUT_DIR,
        "avg_frame_s": round(sum(frame_times) / max(1, len(frame_times)), 2),
        "max_frame_s": max(frame_times) if frame_times else None,
        "total_s": total,
        "n_obj": len(bpy.data.objects),
        "mp4": BASE + r"/previews/m22_flythrough.mp4",
    }
    g = globals()
    g["result"] = result
    return result


if __name__ == "__main__" or True:
    main()
