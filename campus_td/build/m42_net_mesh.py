# -*- coding: utf-8 -*-
"""
M42 · 球门真网眼（Procedural Goal Net Mesh）
==========================================
延续 M38（室外运动场）→ M39（球门/角旗/记分牌）→ M40（半透球网面板）→ M41（看台/替补席）。

为什么做这个（而不是 backlog 里的「围栏/广告牌」）：
  选址探针 tools/probe_m42.py 实测——球场东西端线外 (x≈CX±19) 正好压着塔防玩法区
  （M7_Core / M7_Exit / M7_Beacon_Tower_1..4 / Enemy_* 路径 / M10D 血条），
  南北边线外 |y|≈9.2 压着 M10B 建塔位（SLOT_A/B/C/D_Pad+PadRing）与 M41 替补席腿。
  → 加围栏会侵占并遮挡玩法元素，判定为不可做；改推进 backlog 另一项「球网程序化网眼」。

做什么：
  M40 的球网是 4 块 Alpha 0.22 的实心半透面板（远看是一层白雾，没有网眼）。
  本里程碑用**真几何**重建球网：每个网面由「水平绳 + 垂直绳」细方条组成规则网格
  （网眼 18cm / 绳截面 2.6cm），每个网面的所有绳合并进**单一 mesh**（8 个物体，约 312 根绳）。
  同时把 M40 的 8 块半透面板设为不渲染/不可见（**可逆隐藏，不删除**），避免与新网共面产生白雾/z-fighting。

坐标全部**从场景当前几何读取**（PLAN.md 铁律：M11 之后禁止硬编码建筑坐标）：
  - 球门线 x / 半宽 y / 高度 z ← M39_Goal{W,E}_PostA/PostB/Bar 的世界 AABB
  - 网进深外端 x_far        ← M40_Net{W,E}_Back 的世界 AABB

避坑（沿用 PLAN.md 清单 + 历次经验）：
  - 顶层执行：MCP 用 exec(compile(open().read())) 跑，__name__ != "__main__"，逻辑不能包在 main()（M38 踩过）。
  - 不调 bpy.ops.*.mode_set（MCP exec 内 poll fail）；全部用 bmesh 直建。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError）。
  - 幂等 + 前缀隔离：只清 M42_ 前缀，绝不 select_all+delete。
  - **scale 烘进顶点**：绳条用 bmesh.ops.create_cube(matrix=...) 直接生成世界尺寸，物体 scale 保持 1，
    规避 M10D「obj.data 换网格丢 scale」类问题。
  - fallback 颜色用 list + [1.0]（M38 踩过 tuple+list 报错）。
"""
import bpy
import bmesh
import mathutils
from mathutils import Vector, Matrix

PREFIX = "M42_"

MESH_PITCH = 0.18      # 网眼间距（m），真实足球网 ~10~12cm，此处取 18cm 保证远景可读为“网”而非灰墙
CORD = 0.026           # 绳截面边长（m）
INSET = 0.02           # 相对 M40 面板向内让开，避免共面

# ---------------------------------------------------------------- 工具
def aabb(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [c.x for c in cs]; ys = [c.y for c in cs]; zs = [c.z for c in cs]
    return [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]


def clear_old():
    n = 0
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            nm = o.name
            bpy.data.objects.remove(o, do_unlink=True)
            n += 1
    for me in list(bpy.data.meshes):
        if me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)
    for ca in list(bpy.data.cameras):
        if ca.name.startswith(PREFIX):
            bpy.data.cameras.remove(ca)
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX):
            bpy.data.materials.remove(m)
    return n


def get_cord_mat():
    name = PREFIX + "NetCord"
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = [0.90, 0.93, 0.96] + [1.0]
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.55
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0
            # 极微弱自发光：球门网绳在高对比阴影中仍能读出网格，而不像灯泡自发光
            if "Emission Color" in bsdf.inputs and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = [0.90, 0.93, 0.96, 1.0]
                bsdf.inputs["Emission Strength"].default_value = 0.7
    return m


def frange_incl(a, b, step):
    """从 a 到 b（含端点）均匀取点，保证端点落在绳上（网的边缘要有绳）。"""
    span = b - a
    if span <= 1e-6:
        return [a]
    n = max(1, int(round(span / step)))
    return [a + span * i / n for i in range(n + 1)]


class BarBuilder:
    """把若干根方条绳合并进单一 mesh。"""
    def __init__(self):
        self.bm = bmesh.new()
        self.count = 0

    def bar(self, center, size):
        M = Matrix.Translation(Vector(center)) @ Matrix.Diagonal(
            Vector((size[0], size[1], size[2], 1.0)))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self.count += 1

    def finish(self, name, mat):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        o = bpy.data.objects.new(name, me)
        o.data.materials.append(mat)
        bpy.context.scene.collection.objects.link(o)
        return o


# ---------------------------------------------------------------- 网面生成
def net_plane_x(name, x, y0, y1, z0, z1, mat):
    """垂直背网：固定 x，y/z 平面上的网格。"""
    b = BarBuilder()
    for y in frange_incl(y0, y1, MESH_PITCH):          # 竖绳（沿 z）
        b.bar((x, y, (z0 + z1) / 2.0), (CORD, CORD, z1 - z0))
    for z in frange_incl(z0, z1, MESH_PITCH):          # 横绳（沿 y）
        b.bar((x, (y0 + y1) / 2.0, z), (CORD, y1 - y0, CORD))
    return b.finish(name, mat), b.count


def net_plane_y(name, y, x0, x1, z0, z1, mat):
    """侧网：固定 y，x/z 平面上的网格。"""
    b = BarBuilder()
    for x in frange_incl(x0, x1, MESH_PITCH):
        b.bar((x, y, (z0 + z1) / 2.0), (CORD, CORD, z1 - z0))
    for z in frange_incl(z0, z1, MESH_PITCH):
        b.bar(((x0 + x1) / 2.0, y, z), (x1 - x0, CORD, CORD))
    return b.finish(name, mat), b.count


def net_plane_z(name, z, x0, x1, y0, y1, mat):
    """顶网：固定 z，x/y 平面上的网格。"""
    b = BarBuilder()
    for x in frange_incl(x0, x1, MESH_PITCH):
        b.bar((x, (y0 + y1) / 2.0, z), (CORD, y1 - y0, CORD))
    for y in frange_incl(y0, y1, MESH_PITCH):
        b.bar(((x0 + x1) / 2.0, y, z), (x1 - x0, CORD, CORD))
    return b.finish(name, mat), b.count


# ---------------------------------------------------------------- 主流程
n_removed = clear_old()
cord_mat = get_cord_mat()

built = []
cords = 0
geom_log = {}

for tag in ("W", "E"):
    pa = bpy.data.objects.get("M39_Goal%s_PostA" % tag)
    pb = bpy.data.objects.get("M39_Goal%s_PostB" % tag)
    bar = bpy.data.objects.get("M39_Goal%s_Bar" % tag)
    back = bpy.data.objects.get("M40_Net%s_Back" % tag)
    if not (pa and pb and bar and back):
        geom_log[tag] = "MISSING_SOURCE"
        continue

    A, B, C, D = aabb(pa), aabb(pb), aabb(bar), aabb(back)
    x_line = (C[0] + C[1]) / 2.0                     # 球门线 x（横梁中心）
    y_hi = max(A[3], B[3]); y_lo = min(A[2], B[2])   # 立柱外沿 y
    w = (y_hi - y_lo) / 2.0 - CORD                   # 网半宽（略内收，贴柱内侧）
    z_top = C[5] - 0.06                              # 网顶 ≈ 横梁下沿
    z_bot = min(A[4], B[4])                          # 网底（与柱底齐，埋进草皮）
    x_far = (D[0] + D[1]) / 2.0                      # 网外端 x（沿用 M40 进深）
    # 让开 M40 面板：网面整体向球场方向内收 INSET
    sgn = 1.0 if x_far > x_line else -1.0
    x_far_in = x_far - sgn * INSET
    x0, x1 = (min(x_line, x_far_in), max(x_line, x_far_in))

    o, c = net_plane_x("%sNet%s_Back" % (PREFIX, tag), x_far_in, -w, w, z_bot, z_top, cord_mat)
    built.append(o.name); cords += c
    o, c = net_plane_z("%sNet%s_Top" % (PREFIX, tag), z_top, x0, x1, -w, w, cord_mat)
    built.append(o.name); cords += c
    for s in (1.0, -1.0):
        o, c = net_plane_y("%sNet%s_Side%d" % (PREFIX, tag, int(s)), s * w, x0, x1, z_bot, z_top, cord_mat)
        built.append(o.name); cords += c

    geom_log[tag] = {
        "x_line": round(x_line, 3), "x_far_in": round(x_far_in, 3),
        "half_w": round(w, 3), "z_bot": round(z_bot, 3), "z_top": round(z_top, 3),
        "depth": round(abs(x_far_in - x_line), 3),
    }

# ---- 可逆隐藏 M40 半透面板（不删除；恢复只需把 hide_render/hide_viewport 置 False）----
hidden = []
for o in bpy.data.objects:
    if o.name.startswith("M40_Net"):
        o.hide_render = True
        o.hide_viewport = True
        hidden.append(o.name)

# ---- 近景相机：贴近西球门展示网眼（M42_ 前缀，幂等可清）----
# 近景机位：西球门右后方，避开 M11_Tree21(y≈4) 树冠，背景为天空/球场草地
# 第五次实拍收敛位置 (-20.0, -6.0, 3.0) 可完整框住背网+顶网+侧网
cam_data = bpy.data.cameras.new(PREFIX + "CamNet")
cam = bpy.data.objects.new(PREFIX + "CamNet", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = Vector((-20.0, -6.0, 3.0))
tgt = Vector((-18.0, 0.0, 1.0))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 40.0
bpy.context.scene.camera = cam

# ---- 渲染设定（确定性；与 M38..M41 一致）----
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.samples = 256
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.view_settings.view_transform = "AgX"
except Exception as e:
    geom_log["render_cfg_warn"] = str(e)

n_m42 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M42",
    "n_removed_old": n_removed,
    "n_net_surfaces": len(built),
    "n_cords_total": cords,
    "surfaces": built,
    "geom": geom_log,
    "m40_panels_hidden": hidden,
    "mesh_pitch": MESH_PITCH,
    "cord": CORD,
    "n_m42_objects": n_m42,
    "n_total_objects": len(bpy.data.objects),
    "cam": bpy.context.scene.camera.name,
}
print("M42_RESULT=" + repr(result))
