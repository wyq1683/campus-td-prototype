# m17_props.py — M17 教学家具与食堂道具细化
# 回溯：M11 总平重排后教学楼室内(Int_Teach_*)仅余地板/黑板/隔墙，M3 的 18 套课桌椅已丢失；
#       食堂(M8_Canteen_*)已有 4 桌+8 长椅+取餐台+4 吊灯。
# 本脚本：
#   · 教学楼：回填课桌椅阵列(2  bank + 中央过道) + 教师讲台区(讲桌+讲台+投影幕+挂钟) + 角落书架
#   · 食堂：轻量点缀(菜单板/垃圾桶×2/绿植×2/餐具回收台)
# 所有坐标从**已探针的真实 AABB** 推算（不硬编码旧址），墙体内面=地板上界外推 0.4~0.6m。
# 材质全部复用既有 PBR_*；少量自定义纯色材质自建(仅本脚本用)。
# PREFIX = "M17_"（幂等：clear_old 只删 M17_ 前缀，绝不碰其他物体）。

import bpy, bmesh, mathutils

PREFIX = "M17_"
FLOOR_Z = 0.14  # Int_Teach_Floor / M8_Canteen_Floor 顶面 z

# ---------- 幂等清理 ----------
def clear_old():
    old = [o for o in bpy.data.objects if o.name.startswith(PREFIX)]
    for o in old:
        nm = o.name
        bpy.data.objects.remove(o, do_unlink=True)
    return len(old)

# ---------- 材质 ----------
def get_mat(name):
    return bpy.data.materials.get(name)

def make_flat_mat(name, rgb, rough=0.7, metallic=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    # 按类型找 Principled（Blender 5.x 节点名可能本地化，必须用 type 查找）
    bsdf = None
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            bsdf = n
            break
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.get("Material Output")
        if out is not None:
            m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    return m

MAT_WOOD   = get_mat("PBR_Wood")
MAT_TILE   = get_mat("PBR_Tile")
MAT_METAL  = get_mat("PBR_Metal")
MAT_CONC   = get_mat("PBR_Concrete")
MAT_CONCD  = get_mat("PBR_Concrete_Dark")
MAT_LEAF   = get_mat("PBR_Leaf")
MAT_BRICK  = get_mat("PBR_Brick")
MAT_SCREEN = make_flat_mat(PREFIX + "ScreenMat", (0.92, 0.93, 0.95), rough=0.5)
MAT_CLOCK  = make_flat_mat(PREFIX + "ClockMat", (0.96, 0.96, 0.96), rough=0.4)
MAT_BOOK   = make_flat_mat(PREFIX + "BookMat",  (0.45, 0.13, 0.13), rough=0.8)
MAT_POT    = get_mat("PBR_Concrete_Dark") or make_flat_mat(PREFIX + "PotMat", (0.55, 0.32, 0.22), rough=0.9)

# ---------- bmesh 立方体辅助 ----------
def _add_box(bm, sx, sy, sz, cx, cy, cz):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    for v in ret["verts"]:
        v.co.x = v.co.x * sx + cx
        v.co.y = v.co.y * sy + cy
        v.co.z = v.co.z * sz + cz

def make_mesh(name, boxes, mat):
    """boxes: list of (sx,sy,sz,cx,cy,cz). 合并为单个网格对象。"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for (sx, sy, sz, cx, cy, cz) in boxes:
        _add_box(bm, sx, sy, sz, cx, cy, cz)
    bm.to_mesh(mesh)
    bm.free()
    if mat is not None:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj

# ---------- 课桌 / 课椅 ----------
def make_desk(name, cx, cy, mat=MAT_WOOD):
    """桌面 + 4 腿，合并为 1 个网格。桌面高 0.74。"""
    top_z = FLOOR_Z + 0.74
    boxes = [
        (0.90, 0.50, 0.05, cx, cy, top_z),           # 桌面
        (0.05, 0.05, 0.74, cx - 0.40, cy - 0.20, FLOOR_Z + 0.37),
        (0.05, 0.05, 0.74, cx + 0.40, cy - 0.20, FLOOR_Z + 0.37),
        (0.05, 0.05, 0.74, cx - 0.40, cy + 0.20, FLOOR_Z + 0.37),
        (0.05, 0.05, 0.74, cx + 0.40, cy + 0.20, FLOOR_Z + 0.37),
    ]
    return make_mesh(name, boxes, mat)

def make_chair(name, cx, cy, mat=MAT_WOOD):
    """座面 + 靠背 + 4 腿，合并为 1 个网格。椅在课桌 +Y 侧（学生面朝 -Y 黑板）。"""
    seat_z = FLOOR_Z + 0.45
    boxes = [
        (0.42, 0.42, 0.05, cx, cy, seat_z),                       # 座面
        (0.42, 0.05, 0.45, cx, cy + 0.18, seat_z + 0.225),        # 靠背(+Y)
        (0.04, 0.04, 0.45, cx - 0.17, cy - 0.17, FLOOR_Z + 0.225),
        (0.04, 0.04, 0.45, cx + 0.17, cy - 0.17, FLOOR_Z + 0.225),
        (0.04, 0.04, 0.45, cx - 0.17, cy + 0.17, FLOOR_Z + 0.225),
        (0.04, 0.04, 0.45, cx + 0.17, cy + 0.17, FLOOR_Z + 0.225),
    ]
    return make_mesh(name, boxes, mat)

# ===== 1. 教学楼课桌椅阵列 =====
# 室内可用区：x[-31,31] y[-36,-22]（墙内面外推 0.6）。黑板在 -Y 墙(y≈-36.4)。学生面朝 -Y。
# 中央过道 x=0 宽 2.4；每bank 9 列(step 2.4)，4 排(沿 y)。
removed = clear_old()
n_desk = n_chair = 0
row_ys = [-34.5, -31.5, -28.5, -25.5]
aisle = 1.2
for r, ry in enumerate(row_ys):
    for side in (-1, 1):
        for i in range(9):
            x = side * (aisle + i * 2.4)
            d = make_desk("%sTeach_Desk_%d_%d_%d" % (PREFIX, r, 0 if side < 0 else 1, i), x, ry, MAT_WOOD)
            c = make_chair("%sTeach_Chair_%d_%d_%d" % (PREFIX, r, 0 if side < 0 else 1, i), x, ry + 0.55, MAT_WOOD)
            n_desk += 1; n_chair += 1

# ===== 2. 教师讲台区（黑板正前，-Y 墙内侧）=====
# 讲桌（比学生桌宽）+ 教师椅 + 讲台地台 + 投影幕(挂 -Y 墙, 黑板上方) + 挂钟(挂 +Y 后墙)
# 宽讲桌 1.6×0.7
make_mesh("%sTeacherDesk" % PREFIX,
          [(1.60, 0.70, 0.06, -12.0, -35.0, FLOOR_Z + 0.74),
           (0.06, 0.06, 0.74, -12.0 - 0.72, -35.0 - 0.30, FLOOR_Z + 0.37),
           (0.06, 0.06, 0.74, -12.0 + 0.72, -35.0 - 0.30, FLOOR_Z + 0.37),
           (0.06, 0.06, 0.74, -12.0 - 0.72, -35.0 + 0.30, FLOOR_Z + 0.37),
           (0.06, 0.06, 0.74, -12.0 + 0.72, -35.0 + 0.30, FLOOR_Z + 0.37)], MAT_WOOD)
make_chair("%sTeacherChair" % PREFIX, -12.0, -34.3, MAT_WOOD)

# 讲台地台（low dais）中心 (0,-35.0)
make_mesh("%sPodium" % PREFIX, [(3.0, 1.2, 0.20, 0.0, -35.0, FLOOR_Z + 0.10)], MAT_TILE)

# 投影幕：挂 -Y 墙(y=-36.8 内面)，黑板(x[-14,-10],z[1.2,2.6])上方。薄板朝 +Y。
make_mesh("%sScreen" % PREFIX, [(2.4, 0.06, 1.3, -12.0, -36.5, 3.2)], MAT_SCREEN)

# 挂钟：挂 +Y 后墙(y=-21.2 内面)，朝 -Y。薄盘(在 Y 方向薄)。
make_mesh("%sClock" % PREFIX, [(0.6, 0.10, 0.6, -20.0, -21.55, 2.4)], MAT_CLOCK)

# ===== 3. 角落书架（WX-1 & WY1 拐角，x≈-31, y≈-22）=====
bx, by = -30.3, -22.6
sh = 2.0
make_mesh("%sBookshelf" % PREFIX,
          [(1.2, 0.40, sh, bx, by, FLOOR_Z + sh / 2),       # 柜体
           (1.1, 0.05, 0.04, bx, by, FLOOR_Z + 0.5),        # 层板1
           (1.1, 0.05, 0.04, bx, by, FLOOR_Z + 1.0),        # 层板2
           (1.1, 0.05, 0.04, bx, by, FLOOR_Z + 1.5)], MAT_WOOD)
# 几本示意书（彩色薄板，朝 +X 露出书脊）
for k in range(6):
    make_mesh("%sBook_%d" % (PREFIX, k),
              [(0.06, 0.30, 0.22, bx + 0.45, by - 0.10 + k * 0.0, FLOOR_Z + 0.30 + (k % 3) * 0.5)], MAT_BOOK)

# ===== 4. 食堂点缀 =====
# 食堂地板 x[29.4,42.6] y[-14.6,-5.4]，墙内面 WY-1(y=-14.8)/WY1(y=-5.2)/WX-1(x=29.2)/WX1(x=42.8)
# 4.1 菜单板：挂南墙(WY-1)朝 +Y
make_mesh("%sMenu" % PREFIX, [(2.0, 0.08, 1.2, 36.0, -14.55, 2.0)], MAT_BRICK)
# 4.2 垃圾桶 ×2（圆柱，靠近墙角）
for (px, py, tag) in [(31.0, -13.6, "A"), (42.2, -6.4, "B")]:
    mesh = bpy.data.meshes.new("%sBin_%s" % (PREFIX, tag))
    bm = bmesh.new()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=16,
                                radius1=0.25, radius2=0.20, depth=0.7)
    for v in ret["verts"]:
        v.co.z += FLOOR_Z + 0.35
    bm.to_mesh(mesh); bm.free()
    mesh.materials.append(MAT_METAL)
    obj = bpy.data.objects.new("%sBin_%s" % (PREFIX, tag), mesh)
    obj.location = (px, py, 0.0)
    bpy.context.scene.collection.objects.link(obj)
# 4.3 绿植 ×2（陶盆 + 叶球）
for (px, py, tag) in [(31.6, -6.2, "A"), (42.2, -13.4, "B")]:
    make_mesh("%sPlantPot_%s" % (PREFIX, tag), [(0.32, 0.32, 0.40, px, py, FLOOR_Z + 0.20)], MAT_POT)
    mesh = bpy.data.meshes.new("%sPlantLeaf_%s" % (PREFIX, tag))
    bm = bmesh.new()
    ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
    for v in ret["verts"]:
        v.co.z += FLOOR_Z + 0.40 + 0.45
        v.co.x += px; v.co.y += py
    bm.to_mesh(mesh); bm.free()
    # icosphere 顶点在局部原点，需要整体平移——上面已加 px,py；但 create_icosphere 在原点，
    # 先平移到 (px,py, z) 再原地缩放。修正：逐顶点加中心。
    mesh.materials.append(MAT_LEAF)
    obj = bpy.data.objects.new("%sPlantLeaf_%s" % (PREFIX, tag), mesh)
    bpy.context.scene.collection.objects.link(obj)
# 4.4 餐具回收台（靠东墙 WX1）
make_mesh("%sTrayStation" % PREFIX, [(1.2, 0.6, 0.9, 41.8, -10.0, FLOOR_Z + 0.45)], MAT_CONC)

# ===== 5. 渲染相机 M17_Cam（教室英雄机位：后墙附近俯看课桌椅阵列与黑板）=====
cam = bpy.data.cameras.new("M17_Cam")
cam.lens = 28.0
cam_obj = bpy.data.objects.new("M17_Cam", cam)
cam_obj.location = (0.0, -23.0, 4.5)
target = mathutils.Vector((0.0, -34.0, 1.0))
cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.collection.objects.link(cam_obj)

result = {
    "removed_old": removed,
    "desks": n_desk,
    "chairs": n_chair,
    "objects_now": len(bpy.data.objects),
    "cam": "M17_Cam",
}
