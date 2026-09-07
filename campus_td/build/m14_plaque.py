# m14_plaque.py — M14 校门匾文（补齐 M5B 遗留项）
#
# 背景：M5B 做完「校门青铜嵌板 + 石框」，但**匾文一直空着** —— 当时环境缺 CJK 字体。
#   2026-09-07 复核：宿主机有 NotoSerifSC-VF / msyh / Deng / SimsunExtG，可以做。
#   M11 总平重排把校门重建在 y=-48（M11_GatePlaque），匾面朝南(-y)，本脚本挂到它上面。
#
# 设计：
#   - 匾 = 深色底板 (M11_GatePlaque) + 金色立体字 + 四周石框。传统匾额走「黑底金字」。
#   - 字体按优先级回退：思源宋体（匾额最合适）→ 雅黑 → 等线 → 宋体扩展。
#     VF（variable font）在某些 Blender 版本会加载失败，故必须做回退链，不能只赌一个。
#   - 文字本地 +Z 是正面，绕 X 轴 +90° 后 +Z → -Y，正好朝南且字序沿 X、字顶朝 +Z；
#     extrude 沿本地 +Z，旋转后即沿 -Y 凸出 —— 一步到位，不用再手动偏移。
#
# 幂等：只删 M14_* 前缀；不改动 M11 的匾板本体。
# 运行：exec(compile(open(r"...campus_td/build/m14_plaque.py").read(), "m14", "exec"))

import bpy
import math
import mathutils

PREFIX = "M14_"

# ---- 可调参数 ----
SCHOOL_NAME = "晨光中学"      # 校名（中性，可改；4 字在 6.0m 匾上排布最舒服）
# 注意：GOLD 的**绝对亮度**比金属度更决定"金不金"。实测 metal 0.60->0.40 对色相几乎
# 无效（R/B 1.45->1.47），根因是字 L~185 已进 AgX 高光压缩区，那里颜色被强制拉向白。
# 压低 base 亮度把字拉回线性区（L~130）才能保住饱和度 —— 想更金就往下压，别去调 metal。
GOLD = (0.62, 0.44, 0.13)
# 匾底：M11 给的是青铜嵌板，但**金属在阳光下反光强，把黑底金字的对比吃掉了**
# （实测：匾底 p50=116 vs 字 p99=159，仅 1.35:1，字"有"但不跳）。
# 传统匾额本来就是深底金字，故 M14 给匾板单独换一块深色哑光底。
BOARD = (0.055, 0.050, 0.045)
STONE = (0.46, 0.45, 0.42)
# 2026-09-07 字体实测（tools/_font_probe.py，size=1.0 / "晨光中学" 4 字）：
#   simhei     w=3.82 h=0.92  OK   黑体，最饱满最醒目 —— 匾额首选
#   Dengb      w=3.23 h=0.78  OK   等线 Bold
#   msyhbd     w=3.01 h=0.75  OK   雅黑 Bold
#   simsun     w=3.91 h=0.92  OK   宋体 Regular（细，兜底）
#   simsunb    w=1.91 h=0.68  BAD  Windows 上它其实是 SimSun-ExtB，缺常用汉字
#   Deng       w=0.0  h=0.0   BAD  等线 Regular 在这台机 glyph 解析为空
#   *SC-VF     w=1.36 h=0.32  BAD  可变字体在 Blender 里被缩到 0.32 倍且取最细实例
# 教训：**不能只看「文件在不在」就写进候选链**，必须量实际字形尺寸。
# 所以 pick_font() 里带尺寸自检，不合格自动换下一个 —— 换机器也不会静默出空匾。
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",       # 黑体（首选）
    r"C:\Windows\Fonts\Dengb.ttf",        # 等线 Bold
    r"C:\Windows\Fonts\msyhbd.ttc",       # 雅黑 Bold
    r"C:\Windows\Fonts\simsun.ttc",       # 宋体（兜底）
]
FONT_H_MIN = 0.55      # 单位字高下限：低于它就是 VF 缩放异常 / 空字形
FONT_W_MIN = 0.55      # 单位字宽下限（每字）：低于它就是缺字 / 回退字体

# ---- 匾文排布：按「目标字高」反算 size，再按匾宽回缩，换校名不用手动调 ----
TEXT_H = 0.82          # 目标字高（m），匾高 1.2m 时占 68%
WIDTH_FILL = 0.78      # 文字总宽最多占匾宽的比例


def get_mat(name, color, metal=0.0, rough=0.5, emit=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        if emit > 0.0 and "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit
    return m


def set_mat(o, mat):
    if o.data.materials:
        o.data.materials[0] = mat
    else:
        o.data.materials.append(mat)


def clear_old():
    removed = []
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            removed.append(nm)
    return removed


def pick_font(text):
    """逐个候选字体加载 -> 建临时 text 量尺寸 -> 取第一个字形正常的。
    返回 (font, h_unit, w_unit, tried)。h_unit/w_unit 是 size=1.0 时的字高/总宽。"""
    tried = []
    n = max(1, len(text))
    for p in FONT_CANDIDATES:
        try:
            f = bpy.data.fonts.load(p)
        except Exception as e:
            tried.append({"file": p.split("\\")[-1], "ok": False, "err": str(e)[:60]})
            continue
        # 临时探针（放远处，量完立刻删）
        bpy.ops.object.text_add(location=(0.0, 0.0, -9999.0))
        o = bpy.context.active_object
        o.data.body = text
        o.data.font = f
        o.data.size = 1.0
        o.data.align_x = "CENTER"
        bpy.context.view_layer.update()
        h_unit, w_unit = o.dimensions.y, o.dimensions.x
        bpy.data.objects.remove(o, do_unlink=True)
        ok = (h_unit >= FONT_H_MIN) and (w_unit >= n * FONT_W_MIN)
        tried.append({"file": p.split("\\")[-1], "ok": True, "font": f.name,
                      "h": round(h_unit, 3), "w": round(w_unit, 3), "pass": bool(ok)})
        if ok:
            return f, h_unit, w_unit, tried
    return None, 0.0, 0.0, tried


def find_plaque():
    for nm in (PREFIX + "", "M11_GatePlaque", "M5B_PlaquePanel", "M5_GatePlaque"):
        o = bpy.data.objects.get(nm)
        if o is not None:
            return o
    return None


def add_box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    return o


def build():
    removed = clear_old()
    plaque = find_plaque()
    if plaque is None:
        return {"ok": False, "why": "no plaque object"}

    pc = plaque.location
    pd = plaque.dimensions
    # 匾中心与前脸（匾面朝 -y）
    cx, cy, cz = pc.x, pc.y, pc.z
    face_y = cy - pd.y * 0.5
    w, h = pd.x, pd.z

    font, h_unit, w_unit, tried = pick_font(SCHOOL_NAME)
    if font is None:
        return {"ok": False, "why": "no usable CJK font (all failed glyph check)", "tried": tried}
    # 按目标字高反算 size，再按匾宽回缩（换校名字数不用手调）
    size = TEXT_H / h_unit
    est_w = w_unit * size
    if est_w > w * WIDTH_FILL:
        size *= (w * WIDTH_FILL) / est_w

    # ---- 0) 匾面换深色哑光底（只改这个对象的材质槽，不动 M11 的共享材质定义）----
    set_mat(plaque, get_mat("M14_PlaqueBoard", BOARD, metal=0.0, rough=0.72))

    # ---- 1) 金色立体字 ----
    bpy.ops.object.text_add(location=(cx, face_y, cz))
    txt = bpy.context.active_object
    txt.name = PREFIX + "Text"
    td = txt.data
    td.body = SCHOOL_NAME
    td.font = font
    td.align_x = "CENTER"
    td.align_y = "CENTER"
    td.size = size               # 由 TEXT_H / 匾宽反算得出，非硬编码
    td.extrude = 0.05              # 沿本地 +Z 挤出 -> 旋转后沿 -Y 凸出（朝南）
    td.bevel_depth = 0.008
    td.bevel_resolution = 2
    # 文字本地 +Z 为正面：绕 X 轴 +90° 后 +Z -> -Y（朝南），字顶 +Y -> +Z（朝上）
    txt.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    # metal 别拉满：金属只反射环境，而室外环境是蓝天 -> B 通道被拉高，金字发白
    # （实测 metal=0.60/rough=0.30 时亮像素 R/B 只有 1.45，纯金应约 2.9）。
    # 降到 0.40 让漫反射金主导，同时略抬 rough 避免高光过曝。
    set_mat(txt, get_mat("M14_PlaqueGold", GOLD, metal=0.35, rough=0.40))

    # ---- 2) 四周石框（4 条，稍凸出匾面，压住字的外沿）----
    frame_t = 0.16
    frame_d = 0.10
    fy = face_y - 0.02
    stone = get_mat("M14_PlaqueStone", STONE, metal=0.0, rough=0.75)
    half_w = w * 0.5 + frame_t * 0.5
    half_h = h * 0.5 + frame_t * 0.5
    specs = [
        ("FrameTop", (w + frame_t * 2.0, frame_d, frame_t), (cx, fy, cz + half_h)),
        ("FrameBot", (w + frame_t * 2.0, frame_d, frame_t), (cx, fy, cz - half_h)),
        ("FrameL", (frame_t, frame_d, h), (cx - half_w, fy, cz)),
        ("FrameR", (frame_t, frame_d, h), (cx + half_w, fy, cz)),
    ]
    for nm, size, loc in specs:
        o = add_box(PREFIX + nm, size, loc)
        set_mat(o, stone)

    bpy.context.view_layer.update()
    return {"ok": True, "plaque": plaque.name,
            "plaque_center": [round(v, 3) for v in (cx, cy, cz)],
            "plaque_size": [round(v, 3) for v in (w, pd.y, h)],
            "text": {"name": txt.name, "body": td.body, "size": td.size,
                     "extrude": td.extrude,
                     "dim": [round(v, 3) for v in txt.dimensions],
                     "loc": [round(v, 3) for v in txt.location],
                     "rot": [round(v, 3) for v in txt.rotation_euler]},
            "font": {"used": font.name, "tried": tried},
            "removed": len(removed)}


def build_cam():
    """正面看校门匾：机位在围墙外 y=-62，与匾同高 z=cz，70mm。"""
    plaque = find_plaque()
    cz = plaque.location.z if plaque else 6.6
    cam = bpy.data.objects.get(PREFIX + "Cam")
    if cam is None:
        bpy.ops.object.camera_add(location=(0.0, -62.0, cz))
        cam = bpy.context.active_object
        cam.name = PREFIX + "Cam"
    cam.location = (0.0, -62.0, cz)
    cam.data.lens = 70.0
    target = mathutils.Vector((0.0, -48.0, cz))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return [round(v, 2) for v in cam.location]


def main():
    b = build()
    cam = build_cam() if b.get("ok") else None
    b["cam"] = cam
    b["m14"] = True
    b["objects"] = len(bpy.data.objects)
    result = b
    print("M14 result:", result)
    return result


result = main()
