# -*- coding: utf-8 -*-
"""
M69 · 升旗台 (Flag-Raising Platform · OptiX)
============================================================================
项目已收官（M0–M68 ✅）。按「无未完成里程碑时自行增加改进项」新增 M69。

背景：M62–M68 连续多轮的「下一步」首推都是「升旗台」，但长期被 M46 自行车棚
选址 bug 阻塞——M46 自行车棚的包围盒（x∈[-6.2,6.2] y∈[-16.05,1.8]）压住了
校园主旗杆 M11_FlagPole(-3,0)。 relocation M46 属破坏性变更（待人工决定），
本自动化不擅自改动。

本里程碑采取非破坏、零冲突的解法：在主旗杆被占用的前提下，于探针确认的【校园
北侧净空 assembly ground (0,28)】新建一座**独立完整的升旗台**——抬升台基 +
三级踏步 + 中央讲台 + 自带旗杆与校旗，作为校园第二集会/升旗广场。既补齐了
"升旗台"这一标志性设施，又不触碰任何已有物体（M11 之后铁律：坐标从探针读、
不硬编码、只清 M69_ 前缀）。

坐标（M11 之后铁律）：
  - 中心 C=(0,28,0) 由探针网格扫描确认为 SOLID 结构净空（BLOCKER_COUNT 1288
    中无任一与该 8×6m 台基重叠）。
  - 构建前再做一次轻量碰撞自检：若 C 处与 Bldg_*/M11_* 等实体结构重叠则跳过，
    避免任何潜在穿模。

设计（原型级、实体结构）：
  - 台基：8×6m 方台，高 0.6m，暖灰花岗岩（复用 PBR_Concrete，缺失则新建 M69_Stone）。
  - 踏步：南向（-y，面向校园中心）三级 0.2m 踏步，与台基同材质合并。
  - 讲台：台基中央 2.8×2.1×0.3m 略深色讲台。
  - 旗杆：台基中央 φ0.12 / 高 12m 金属杆（复用 PBR_Metal，缺失则新建 M69_Metal）
    + 顶端金色球冠。
  - 校旗：杆顶 +X 侧 2.4×1.5m 藏青校旗（M69_Flag，弱自发光保可读）。
  - 相机：M69_Cam 自南侧（校园中心方向）3/4 低角看入台基。

避坑（沿用 PLAN.md + M56–M68 经验）：
  - 顶层执行：MCP 用 exec(compile(open().read()))，逻辑不包 main()。
  - 不调 mode_set；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 删旧物体先取 nm=o.name 再 remove（防 StructRNA ReferenceError，pitfall #16）。
  - 幂等 + 前缀隔离：只清 M69_，绝不 select_all+delete。
  - 5.2 Principled 输入名 Base Color / Roughness / Metallic / Emission Strength。
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix

ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"
PREFIX = "M69_"

# ---- 选址（探针确认净空；此处再做防御性自检）----
CX, CY = 0.0, 28.0
PW, PD = 8.0, 6.0          # 台基 footprint (x, y)
PLAT_H = 0.6
STEP_H = 0.2
STEP_DEPTH = 0.9
N_STEPS = 3
POLE_H = 12.0
POLE_R = 0.12
FLAG_W, FLAG_H = 2.4, 1.5

# ---------------------------------------------------------------- 工具
def world_aabb(o):
    try:
        if o.bound_box is None:
            return None
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
    except Exception:
        return None


def clear_old(prefix):
    removed = []
    names = [o.name for o in bpy.data.objects if o.name.startswith(prefix)]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None:
            continue
        nm2 = o.name
        try:
            if o.data and getattr(o.data, "users", 0) <= 1:
                try:
                    bpy.data.meshes.remove(o.data)
                except Exception:
                    pass
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass
        removed.append(nm2)
    # 清孤儿 mesh / curve
    for m in list(bpy.data.meshes):
        if m.users == 0:
            try:
                bpy.data.meshes.remove(m)
            except Exception:
                pass
    return removed


def box_into(bm, sx, sy, sz, cx, cy, cz, mat_idx):
    """向 bm 追加一个居中于 (cx,cy,cz)、尺寸 (sx,sy,sz) 的 box。"""
    prim = bmesh.new()
    bmesh.ops.create_cube(prim, size=1.0)
    M = Matrix((
        (sx, 0.0, 0.0, cx),
        (0.0, sy, 0.0, cy),
        (0.0, 0.0, sz, cz),
        (0.0, 0.0, 0.0, 1.0),
    ))
    prim.transform(M)
    vmap = {}
    for v in prim.verts:
        vmap[v] = bm.verts.new(v.co)
    for f in prim.faces:
        nf = bm.faces.new([vmap[e] for e in f.verts])
        nf.material_index = mat_idx
    prim.free()


def make_pbr(name, base, rough, metal=0.0, emissive=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nde in list(nt.nodes):
        nt.nodes.remove(nde)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissive > 0:
        bsdf.inputs["Emission Color"].default_value = (base[0], base[1], base[2], 1)
        bsdf.inputs["Emission Strength"].default_value = emissive
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- 防御性碰撞自检
def collision_check():
    pad = (CX - PW / 2 - 0.4, CY - PD / 2 - N_STEPS * STEP_DEPTH - 0.4, -0.5,
           CX + PW / 2 + 0.4, CY + PD / 2 + 0.4, POLE_H + 1.0)
    block_prefix = ("Bldg_", "M11_", "M37_", "M43_", "M44_", "M45_", "M46_", "M47_",
                    "M48_", "M49_", "M52_", "M53_", "M54_", "M55_", "M56_", "M57_",
                    "M58_", "M59_", "M60_", "M61_", "M62_", "M63_", "M64_", "M65_",
                    "M66_", "M67_", "M68_", "M38_", "M39_", "M40_", "M41_", "M42_",
                    "M16_", "M17_", "M15_", "M8_", "Int_", "Furn_")
    hits = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if not any(o.name.startswith(p) for p in block_prefix):
            continue
        a = world_aabb(o)
        if a is None:
            continue
        if (a[3] - a[0]) > 70 or (a[4] - a[1]) > 70 or (a[5] - a[2]) > 70:
            continue
        # overlap test
        if not (a[3] < pad[0] or a[0] > pad[3] or a[4] < pad[1] or a[1] > pad[4] or a[5] < pad[2] or a[2] > pad[5]):
            hits.append(o.name)
    return hits


# ---------------------------------------------------------------- 主构建
_blockers = collision_check()
if _blockers:
    result = {"milestone": "M69", "ok": False, "reason": "site conflict at (0,28)",
              "conflicts": _blockers[:10], "n_total": len(bpy.data.objects)}
    print("M69_RESULT=" + repr(result))
    raise SystemExit(0)

removed = clear_old(PREFIX)

# 材质（优先复用既有 PBR，缺失则自建，保持零依赖）
stone = bpy.data.materials.get("PBR_Concrete") or make_pbr(PREFIX + "Stone", (0.52, 0.52, 0.50), 0.82)
podium_mat = make_pbr(PREFIX + "Podium", (0.40, 0.40, 0.38), 0.78)
metal = bpy.data.materials.get("PBR_Metal") or make_pbr(PREFIX + "Metal", (0.62, 0.63, 0.65), 0.30, metal=0.7)
finial_mat = make_pbr(PREFIX + "Finial", (0.85, 0.70, 0.30), 0.25, metal=0.7)
flag_mat = make_pbr(PREFIX + "Flag", (0.09, 0.15, 0.40), 0.75, emissive=0.10)

# --- 台基 + 踏步 + 讲台（stone / podium 合并为几个 mesh 物体）---
bm_deck = bmesh.new()
# 台基
box_into(bm_deck, PW, PD, PLAT_H, CX, CY, PLAT_H / 2.0, 0)
# 三级踏步（南侧 -y 面，逐级上升）
for i in range(N_STEPS):
    h = STEP_H * (i + 1)
    front = CY - PD / 2 - (i + 1) * STEP_DEPTH
    back = CY - PD / 2 - i * STEP_DEPTH
    cyc = (front + back) / 2.0
    box_into(bm_deck, PW, (back - front), h, CX, cyc, h / 2.0, 0)
me_deck = bpy.data.meshes.new(PREFIX + "Deck")
bm_deck.to_mesh(me_deck)
bm_deck.free()
o_deck = bpy.data.objects.new(PREFIX + "Deck", me_deck)
o_deck.data.materials.append(stone)
bpy.context.scene.collection.objects.link(o_deck)

# 讲台（台基中央）
bm_pod = bmesh.new()
box_into(bm_pod, 2.8, 2.1, 0.3, CX, CY, PLAT_H + 0.15, 0)
me_pod = bpy.data.meshes.new(PREFIX + "Podium")
bm_pod.to_mesh(me_pod)
bm_pod.free()
o_pod = bpy.data.objects.new(PREFIX + "Podium", me_pod)
o_pod.data.materials.append(podium_mat)
bpy.context.scene.collection.objects.link(o_pod)

# --- 旗杆 + 金顶（metal / finial）---
bm_pole = bmesh.new()
# 杆：真实圆柱（bmesh create_cone，radius1==radius2 即圆柱，16 段），
# 免 box 方截面的生硬感；不调 mode_set、不碰场景，纯 bmesh 直建。
prim = bmesh.new()
bmesh.ops.create_cone(prim, cap_ends=True, cap_tris=False, segments=16,
                      radius1=POLE_R, radius2=POLE_R, depth=POLE_H)
M = Matrix.Translation((CX, CY, PLAT_H + POLE_H / 2.0))
prim.transform(M)
vmap = {}
for v in prim.verts:
    vmap[v] = bm_pole.verts.new(v.co)
for f in prim.faces:
    bm_pole.faces.new([vmap[e] for e in f.verts])
prim.free()
# 注：金顶球冠由下方独立 M69_Finial（金色材质）提供，此处不再并入 bm_pole，
# 避免与 o_fin 在杆顶形成双面重合（metal 内嵌球与 gold 球 z-fighting）的冗余。
me_pole = bpy.data.meshes.new(PREFIX + "Pole")
bm_pole.to_mesh(me_pole)
bm_pole.free()
o_pole = bpy.data.objects.new(PREFIX + "Pole", me_pole)
o_pole.data.materials.append(metal)
bpy.context.scene.collection.objects.link(o_pole)
# 另加一个金顶 mesh（独立材质）
bm_fin = bmesh.new()
bmesh.ops.create_icosphere(bm_fin, radius=0.20, subdivisions=2)
M = Matrix.Translation((CX, CY, PLAT_H + POLE_H))
bm_fin.transform(M)
me_fin = bpy.data.meshes.new(PREFIX + "Finial")
bm_fin.to_mesh(me_fin)
bm_fin.free()
o_fin = bpy.data.objects.new(PREFIX + "Finial", me_fin)
o_fin.data.materials.append(finial_mat)
bpy.context.scene.collection.objects.link(o_fin)

# --- 校旗（杆顶 +X 侧，薄 box）---
bm_flag = bmesh.new()
box_into(bm_flag, FLAG_W, 0.04, FLAG_H, CX + POLE_R + FLAG_W / 2.0, CY,
         PLAT_H + POLE_H - FLAG_H / 2.0 - 0.3, 0)
me_flag = bpy.data.meshes.new(PREFIX + "Flag")
bm_flag.to_mesh(me_flag)
bm_flag.free()
o_flag = bpy.data.objects.new(PREFIX + "Flag", me_flag)
o_flag.data.materials.append(flag_mat)
bpy.context.scene.collection.objects.link(o_flag)

# ---------------------------------------------------------------- 选址相机
# 自南侧（校园中心方向，-y）看入台基，3/4 低角，框住台基+旗杆+校旗。
# 用纯 data API 建相机（不调 bpy.ops.object.camera_add），免 operator 对
# 上下文/活动对象的依赖，headless MCP exec 更稳（M69 从未实跑，先消除唯一
# 一个 operator 调用）。「若 Camera 不存在则创建」自然满足：M69_Cam 被
# clear_old 清掉后此处重建。
cam_loc = Vector((CX + 4.0, CY - 16.0, 4.5))
cam_data = bpy.data.cameras.new(PREFIX + "Cam")
cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = cam_loc
cam.data.lens = 35.0
tgt = Vector((CX, CY, 2.2))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

n_m69 = sum(1 for o in bpy.data.objects if o.name.startswith(PREFIX))
result = {
    "milestone": "M69",
    "ok": True,
    "site": (CX, CY),
    "n_removed_old": len(removed),
    "n_m69_objects": n_m69,
    "n_total_objects": len(bpy.data.objects),
    "deck_size": (PW, PD, PLAT_H),
    "steps": N_STEPS,
    "pole_height": POLE_H,
    "flag_size": (FLAG_W, FLAG_H),
}
print("M69_RESULT=" + repr(result))
