# m19b_export.py — 校园塔防原型 → glTF 2.0 (.glb) 一键导出
#
# 里程碑 M9「Godot/Unity 导出说明」的可执行交付物：把当前 Blender 场景导出为
# 游戏引擎可直接消费的 glTF 2.0 二进制包。脚本**非破坏**（只写文件，不删/不改场景）。
#
# 执行：tools/run_m19b_export.py （经 Direct TCP Socket 直连 Blender MCP @9876）
# 产物：campus_td/exports/campus_td.glb
#
# 设计要点（详见 EXPORT_GODOT_UNITY.md）：
#   - export_format=GLB ：单文件二进制，Godot/Unity 通用。
#   - export_apply=True ：烘掉修改器（M15 Array 真实踏步等），否则楼梯只导出 1 级斜板。
#   - export_yup=True   ：glTF 规范 Y-up，自动 Z-up→Y-up，引擎无需手动转正。
#   - 场景单位 = 米（scale 1.0）→ Godot/Unity 1 unit = 1m，零缩放误差。
#   - 程序化材质不导出（只 Principled 标准输入生效）→ 导出的 .glb 是"平涂底色"版，
#     保留几何/命名/尺度；要电影级观感需先在 Blender 里 bake 贴图（见导出说明文档）。

import bpy
import os
import json
from collections import Counter

BASE = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59"
EXPORT_DIR = os.path.join(BASE, "campus_td", "exports")
GLB_PATH = os.path.join(EXPORT_DIR, "campus_td.glb")

os.makedirs(EXPORT_DIR, exist_ok=True)

# 确保 glTF 2.0 插件可用（Blender 5.2 默认启用；保险起见尝试启用一次）
if not hasattr(bpy.ops.export_scene, "gltf"):
    try:
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    except Exception as e:
        print("addon_enable failed:", repr(e))

total = len(bpy.data.objects)
mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]

# 统计节点名前缀，便于引擎按名解析"玩法标记"（Tower_/Enemy_/TD_/M10B_ 等）
prefix_counter = Counter()
for o in bpy.data.objects:
    name = o.name
    if "_" in name:
        prefix_counter[name.split("_", 1)[0]] += 1
    else:
        prefix_counter["<noprefix>"] += 1

# 这些辅助体导出会膨胀文件且对游戏无益，统计但并非默认排除（保持"导出整关"语义）。
helper_prefixes = ("M6_SkyDome", "M6_Halo", "Mat_Preview")

export_kwargs = dict(
    filepath=GLB_PATH,
    export_format="GLB",
    use_selection=False,        # 导出整关
    export_apply=True,          # 烘修改器（Array 踏步 / 残余布尔）
    export_yup=True,            # Z-up -> Y-up 自动转换
    export_materials="EXPORT",  # 导出 Principled PBR（注意：程序化节点会塌成平涂）
    export_cameras=True,        # 含 M9/M14/M15/M16/M17 等漫游/特写机位
    export_lights=True,         # KHR_lights_punctual 基线光（AgX 不转移）
    export_extras=True,         # 保留自定义属性
    export_tangents=True,       # 法线贴图质量（bake 后需要）
    export_normals=True,
    export_texcoords=True,
)

ok = True
err = ""
try:
    bpy.ops.export_scene.gltf(**export_kwargs)
except Exception as e:
    ok = False
    err = repr(e)

size = os.path.getsize(GLB_PATH) if (ok and os.path.exists(GLB_PATH)) else 0

result = {
    "exported": ok,
    "path": GLB_PATH,
    "total_objects": total,
    "mesh_objects": len(mesh_objs),
    "file_bytes": size,
    "file_mb": round(size / 1048576.0, 2),
    "prefix_counts": dict(prefix_counter.most_common()),
    "helper_prefixes_present": [p for p in helper_prefixes if any(k.startswith(p) for k in prefix_counter)],
    "error": err,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
