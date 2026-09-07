# 导出说明 · 高中校园塔防原型 → Godot / Unity

> 里程碑 **M9 Godot/Unity 导出说明**（backlog 收尾项）。
> 本文件把 Blender 5.2 场景 `campus_td.blend` 导出为游戏引擎可直接消费的资产包，并讲清本项目特有的坑。
> 最后更新：2026-09-07

---

## 1. 为什么导出 / 目标格式

原型期用 Blender 建"可进入、电影级"的校园 + 塔防叠加层。要变成真正的可玩关卡，需要把几何体、命名、尺度带进游戏引擎（Godot 4 / Unity），再在引擎里接管游戏逻辑、碰撞、光照与后期。

**交换格式选 glTF 2.0 的 `.glb` 二进制包**（不是 FBX、不是 Collada）：

- Blender 5.2 内置 `io_scene_gltf2` 插件默认启用，`File → Export → glTF 2.0` 直接出。
- Godot 4 有**原生内置 glTF 导入器**；Unity 用官方 **glTFast**（`com.unity.cloud`）或 Khronos `UnityGLTF` 导入器，都能吃 `.glb`。
- Collada / Better Collada 在 Godot 社区已明确弃用（坑多、动画/材质易丢）；FBX 对骨骼网格更宽容，但本原型无骨骼，不需要。

---

## 2. 一键导出（已就绪，非破坏）

本仓库已带可执行交付（不删/不改场景，只写文件）：

```bash
# 在 campus_td/ 下，经 Direct TCP Socket 直连 Blender MCP @9876（超时 540s）
python tools/run_m19b_export.py
```

- 脚本：`campus_td/build/m19b_export.py`
- 产物：`campus_td/exports/campus_td.glb`
- 实测（2026-09-07）：1098 个对象 / 1065 个网格 / **9.55 MB**，导出耗时约 2 秒。

导出参数（脚本内已固定，见 `m19b_export.py`）：

| 参数 | 值 | 作用 |
|---|---|---|
| `export_format` | `GLB` | 单文件二进制，引擎通用 |
| `use_selection` | `False` | 导出整关（含全部建筑/塔/敌人/路径） |
| `export_apply` | `True` | **烘掉修改器**——M15 Array 真实踏步若不烘，只导出 1 级斜板；其余布尔门洞已在建造时 apply，无残留 |
| `export_yup` | `True` | glTF 规范 Y-up，自动 Z-up→Y-up，引擎无需手动转正 |
| `export_materials` | `EXPORT` | 导出 Principled PBR（注意：程序化节点会塌成平涂，见 §5） |
| `export_cameras` / `export_lights` | `True` | 带漫游/特写机位 + `KHR_lights_punctual` 基线光 |
| `export_tangents` / `export_normals` / `export_texcoords` | `True` | 保留法线/切线/UV，便于日后 bake 贴图 |
| `export_extras` | `True` | 保留自定义属性 |

> 导出器会打印 `WARNING: ... Could not calculate tangents`——这是因为部分物体是非三角化网格（盒子/柱体等），**仅影响未来 bake 法线贴图的质量，对当前平涂 PBR 导出无碍**，可忽略。

---

## 3. 在 Godot 4 导入

1. 把 `campus_td.glb` 拖进项目 `res://`（如 `res://assets/`）。
2. 双击 `.glb` → 点「打开（Advanced Import Settings 旁的打开）」→ 另存为 `.tscn` 继承场景（之后改模型就重导出 `.glb` 再「重新导入」，不要直接改 `.glb`）。
3. 在 `.tscn` 里按节点名工作：
   - `Bldg_*` 建筑外壳、`M11_*` 场地、`M8_*` 室内、`M15_*` 楼梯、`M16_*` 垛口、`M17_*` 家具 —— 环境几何。
   - `Tower_*` 防御塔、`Enemy_*` 敌人、`TD_*` 路径/波次标记、`M10B_*` 建塔位 —— **玩法语义节点**，引擎按名实例化塔/敌人/路径/波次（本原型塔防数值见 `build/m10_config.json` 与 `web/`）。
4. **碰撞**：glTF 不含碰撞体。给需要行走/阻挡的网格加 `StaticBody3D` + `CollisionShape3D`（用 `MeshInstance3D` 的 convex/trimesh 或简化 Box）。重点：`Ground`/`Int_*_Floor`/`M8_*_Floor` 地板（可行走）、`Bldg_*`/`M11_Wall*` 外墙（阻挡）。`M15_*` 楼梯建议用若干 Box 碰撞近似踏步，避免穿模。
5. **材质**：本关导出的材质是平涂 PBR（见 §5）。Godot 4 对 `.glb` 用 Material Override 覆盖即可；要做电影级观感，按 §5 在 Blender 里 bake 后再导入。
6. **光照/后期**：`KHR_lights_punctual` 只给基线方向/点光，AgX 色调映射**不转移**。在 Godot 里用 `WorldEnvironment`（雾/天空）+ `DirectionalLight` + `CameraAttributes`（色调映射）重设电影感。

> Godot 4 提示：用 `.glb` 而非 Embedded glTF——早期版本 Embedded 不生成 mipmap、且 draw call 性能较差。

---

## 4. 在 Unity 导入

1. 安装 glTF 导入器：**glTFast**（Package Manager → `+` → `com.unity.cloud` 的 glTFast）或 Khronos `UnityGLTF`。
2. 把 `campus_td.glb` 放进 `Assets/`（如 `Assets/CampusTD/`），Unity 自动生成 prefab。
3. **坐标/尺度**：glTF 是 Y-up、1 unit = 1 m；Blender 场景单位也是米（scale 1.0），所以导入后建筑高度、塔防射程（13 m）等与 Blender 完全一致，**无需缩放**。若模型"躺平"，是导入器少了 Y-up 处理——glTFast 默认正确，确认导入设置勾选了 Y-up。
4. **碰撞**：给 `Ground`/地板/外墙加 `MeshCollider`（convex 用于外墙）或 `BoxCollider`；楼梯用阶梯 Box。
5. **材质**：导入为 `Lit`(URP/HDRP) 或 Standard PBR，平涂底色；电影级观感按 §5 bake。
6. **光照/色调映射**：Unity 不读 AgX。用 URP/HDRP 的 `Volume`（Exposure/Tonemapping=ACES/Neutral）+ `DirectionalLight` + `Lighting` 天光重设。
7. 若启用 Draco/Meshopt 压缩（本脚本未开），需导入器带对应解码器。

---

## 5. ⚠ 本项目最关键的坑（务必先看）

### 5.1 程序化节点材质**不导出** → 必须 bake

本场景所有 PBR 材质都是 **Blender 程序化节点图**（Noise / Voronoi / Brick / ColorRamp 驱动颜色与粗糙度），**没有任何图片贴图**。

glTF 2.0 只有一种 PBR 模型（metallic-roughness），导出器**只读取 `Principled BSDF` 的标准输入**（Base Color / Roughness / Metallic / Normal / AO / Emissive）。任何挂在 `Principled` 之前的 Noise/Voronoi/Brick/节点组，导出时会被算成**平涂平均色**——砖纹、混凝土噪点、渗水渍、木纹全部消失，模型变成"刷了平均色的素模"。

**结果**：直接导出的 `.glb` 几何/命名/尺度都对，但观感是平涂版，不是 Blender 里看到的电影级。

**要电影级观感，导出前在 Blender 里 bake**（Cycles 下）：
1. 给每个程序化材质新建目标图片节点（Diffuse 2048²、Roughness、Normal 各一张）。
2. `Cycles` 渲染引擎 → `Bake`：Diffuse（只留 Color）/ Roughness / Normal（Tangent 空间）。
3. 把烘焙图接到 `Principled BSDF` 对应槽，**删除程序化节点**（避免导出歧义）。
4. 再跑 `m19b_export.py`。

> 注意颜色空间：法线图必须 Non-Color，否则会被 gamma 校正两次产生瑕疵。

### 5.2 动画**不导出**

- **M7 敌人运动**由 `frame_change_pre` 处理程序（按帧算 Catmull-Rom 弧长）驱动，**不是** Blender Action / 关键帧 → glTF 导出器看不到动画轨，**不会成动画**。游戏里敌人沿路径移动要在引擎用 `web/config.js` / `build/m10_config.json` 的路径数据重做。
- **M9 漫游相机**是真正的 keyframed Action（位置 BEZIER + 旋转 slerp）→ 若勾选 `Export → Animation` 且包含相机，可导出为相机动画轨（Godot/Unity 用作过场）。
- 结论：导出的是"静态关卡几何 + 命名标记"，**塔防玩法（敌人/塔/波次/锁定）全部在引擎侧实现**，本仓库 `web/`（WebGL2 原型）与 `build/m10_balance.py`（平衡模拟）是数值真源。

### 5.3 塔防语义靠**节点名**保留

glTF 节点名 = Blender 对象名。下列前缀随 `.glb` 一起导出，引擎按名解析即可挂载玩法：

| 前缀 | 含义 | 引擎用途 |
|---|---|---|
| `Tower_*` | 4 座防御塔（base/ring/glow） | 塔实例 + 射程 |
| `Enemy_*` | 7 个敌人单位 | 敌人实例 |
| `TD_*` | 路径/出生点/波次标记 | 路径曲线/波次数据 |
| `M10B_*` | 4 个建塔位（36 个对象） | 可建造点 |
| `Bldg_*` / `M11_*` / `M8_*` / `M15_*` / `M16_*` / `M17_*` | 环境几何 | 静态关卡 |

### 5.4 尺度与坐标轴（本项目已对齐，零额外处理）

- Blender 场景单位 = 米，`unit scale = 1.0`；Godot/Unity 均 1 unit = 1 m → **零缩放误差**。
- 导出器 `export_yup=True` 自动把 Blender Z-up 转成 glTF Y-up，引擎里模型"正立"，无需手动旋转。

### 5.5 辅助体可隐藏（生产导出更干净）

整关导出会带上 `M6_SkyDome`（300 m 自发光天穹球）、`M6_Halo_*`（辉光壳）、`Mat_Preview_*`（10 个材质预览球）——它们对游戏无益且膨胀文件。生产导出前在 Blender 里 `hide_render` 或移出选中集再导出即可（本脚本默认导出整关，保留"整关"语义）。

---

## 6. 推荐生产级工作流

1. **Bake 材质**：对 10 种 PBR 程序化材质各 bake Diffuse/Roughness/Normal → 图片材质（§5.1）。
2. **分组导出**（可选）：环境（Bldg_/M11_/M8_/M15_/M16_/M17_）与玩法标记（Tower_/Enemy_/TD_/M10B_）可分两个 `.glb`，或隐藏 M6_/Mat_ 辅助体后导一个干净包。
3. **引擎接管**：Godot/Unity 导入 → 加碰撞 → 按节点名挂塔防逻辑（用 `build/m10_config.json`）→ 重设光照/色调映射/后期。
4. **迭代**：Blender 改动后重导 `.glb` → 引擎「重新导入」，不手动改导入后的场景。

---

## 7. 来源（调研依据）

- Blender 官方 glTF 2.0 导出器文档：https://docs.blender.org/manual/en/latest/addons/io_scene_gltf2.html
- Godot 4 导入 glTF 讨论（弃用 Collada、用 .glb）：https://godotengine.org/qa/43625/blender-to-godot-asset-workflow-hell
- Godot 4 材质/glb 工作流：https://godotengine.org/qa/125697/godot-4-how-to-edit-materials-on-a-3d-imported-model
- Blender 5.x glTF 导出器变更（Draco 默认、KHR_materials_variants、lightmap UV；**程序化节点不导出**）：https://bitsoulhosting.com/marketplace/blog/blender-5-gltf-export-what-breaks-unity-godot-ue5
- Blender 5.2 glTF/GLB 导出选项（Apply Modifiers / Y-up 自动 / KHR_lights_punctual / 切线）：https://blenderdeluxe.com/en/3d-design/exporting-blender-52-models-to-the-web-with-gltfglb-1104
- 实时引擎导出管线（bake 流程、GLB 打包、颜色空间）：https://www.varsitytutors.com/practice/subjects/blender/lessons/export-textures-and-package-assets-for-sharing-intro
- 实时引擎贴图烘焙 SOP：https://wiki.mh8.fr/doku.php?id=3d:export-runtime
