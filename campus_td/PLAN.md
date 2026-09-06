# 项目计划 · 高中校园塔防原型（Cinematic Enterable High School TD Prototype）

> 本文件是项目唯一权威计划书。自动任务每次运行都会读取它来决定下一步。
> 上下文可能被压缩，但本文件常驻磁盘，是抗压缩的"项目大脑"。
> 最后更新：2026-09-06

---

## 1. 项目背景（Background）

用户（Yuqi，初中生，正在做校园塔防游戏原型）希望用 **Blender + Blender MCP 链路**构建一个**真实可进入、电影级质感**的**高中学校**3D 原型。

来源：此前已完成「校园塔防模拟器 v1」——通过 mcporter→blmcp→Blender addon（端口 9876）链路，用 bpy 脚本在 Blender 5.2 内建立了草地+U 形路径+6 栋教学楼+4 座发光防御塔+7 个敌人+俯视相机，并成功 Cycles 渲染出图（见 `../render_campus_td.png`）。

本次升级目标：从"示意性塔防地图"升级为"**完整高中校园、所有建筑可进入、电影级真实材质与光照**"的原型，塔防玩法层（塔/敌人/路径）作为叠加系统保留并 refinement。

---

## 2. 愿景与目标（Vision & Goals）

**愿景**：一个能在 Blender 视口里自由行走（Walk Navigation）、每个房间都有正确尺度与材质、光影接近实拍电影感的高中校园。它同时是塔防游戏的一关地图。

**目标（SMART）**
- G1 全校园可行走：每栋主建筑 exterior + interior 都建模，室内有地板/墙/门/窗/楼梯，能用 Walk Navigation 走进去。
- G2 电影级材质：全场景 PBR，程序化节点材质库（草地/沥青/砖墙/混凝土/玻璃/木地板/金属/瓷砖），含使用痕迹（磨损/脏污）。
- G3 电影级光照：HDRI 天光 + 阳光 + 室内补光，EEVEE Next 光线追踪/探针 或 Cycles GPU 终帧；AgX 色调映射 + Bloom（Compositor）辉光。
- G4 塔防层：防御塔布局合理、敌人沿曲线路径、出生点/波次占位可视。
- G5 可交付预览：每个里程碑出一张渲染预览图，存 `previews/`。

---

## 3. 范围界定（Scope）

**In scope（原型级）**
- 场地：地形、校门、主干道、步行道、围墙、操场（跑道+球场）、绿化。
- 建筑（均可进入）：教学楼（主）、实验楼、图书馆、食堂、宿舍楼、体育馆、行政楼。
- 室内：走廊、楼梯、典型教室（含课桌椅、黑板）、食堂大厅、图书馆阅览区等代表性空间。
- 塔防层：防御塔（已有 4 座，优化布局）、敌人路径（改 Bezier 曲线）、出生点、波次标记。
- 材质/光照/后期：见 G2/G3。

**Out of scope（本期不做）**
- 真实游戏逻辑/AI（导出到 Godot/Unity 时再做，仅留原型与标记）。
- 人物角色绑定动画、剧情。
- 真实贴图下载（优先程序化节点，避免国内 CDN 慢；HDRI 如需再单独处理）。

---

## 4. 技术栈与工具链（Tech Stack）

| 层 | 选择 | 说明 |
|---|---|---|
| Blender | 5.2.1 LTS（`D:\建模\blender\blender.exe`） | 活动实例；注意 C 盘另有 msi 实例 |
| MCP 链路 | mcporter → blmcp → addon `blender_mcp_addon` @9876 | 见 `../.workbuddy/memory/MEMORY.md` 启动代码 |
| 建筑生成 | **Archimesh**（官方内置 Extensions 插件） | rooms/doors/windows/stairs + Auto Hole + Cycles 材质 |
| 材质 | 程序化 Shader Nodes（Brick/Noise/Voronoi/Musgrave/ColorRamp/Bump/Displacement） | 不依赖外部贴图 |
| 执行方式 | `execute_blender_code(code='exec(compile(open(r"...campus_td/build/X.py").read(),"X","exec"))')` | 大段 bpy 写文件再 exec，避 shell 转义 |
| 渲染 | EEVEE Next（实时/预览）或 Cycles GPU OptiX（终帧） | Bloom 走 Compositor Glare |
| 预览 | `render_viewport_to_path` → 读返回 filepath → cp 到 `previews/` | 该工具忽略传参路径 |

---

## 5. 质量基准（Cinematic Quality Bar）

**材质（PBR）**
- albedo 落在物理合理区间：深木 0.1–0.2 / 混凝土 0.3–0.4 / 浅石 0.5–0.6；禁止纯黑纯白。
- metallic 二值（0 或 1），过渡处除外。
- 必须加表面变化：Noise/Voronoi/Musgrave 驱动 color & roughness 变化；ColorRamp 控制范围。
- Normal/Bump 出微观起伏；(Cycles) 用 Displacement 出真实几何起伏（近景）。
- 加使用痕迹：边缘磨损（edge wear）、角落积灰、渗水渍。

**光照 / 渲染**
- EEVEE Next：开 Raytracing（替代旧 SSR）、Ambient Occlusion、Shadows cube/cascade ≥2048、Irradiance Volume + Reflection Cubemap 探针烘焙 GI。
- 或 Cycles GPU（OptiX）+ Denoising，终帧 512 samples，光钳制防 firefly。
- Color Management：AgX（或 Filmic）色调映射，曝光微调。
- Bloom：Compositor → Glare 节点 → Bloom 模式（EEVEE Next 渲染设置里已无 Bloom）。
- 天光：World shader 用 Environment Texture(HDRI) + Light Path `Is Camera Ray` 混合，让天空在镜头里亮、对场景照明贡献小。

**构图**
- 终帧 1920×1080 或 3840×2160；俯视/人视双视角各出图。

---

## 6. 场景架构与命名规范（Naming Convention）

**关键原则：每个里程碑的物体用统一前缀，构建脚本只删同名前缀旧物体再重建 → 幂等、互不破坏。**

| 前缀 | 内容 | 里程碑 |
|---|---|---|
| `Site_` | 地形/道路/围墙/操场/绿化 | M0/M5 |
| `Bldg_` | 建筑外壳（含 `_roof`） | M2/M4 |
| `Room_` / `Int_` | 室内（地板/墙/门/窗/楼梯/家具） | M3/M4 |
| `Mat_` | 材质预览球（可选） | M1 |
| `Tower_` | 防御塔（base/ring/glow） | M0/M8 |
| `Enemy_` | 敌人单位 | M0/M8 |
| `TD_` | 塔防路径/出生点/波次标记 | M8 |
| `Light_`/`Probe_` | 灯光/探针 | M6 |

构建脚本放 `campus_td/build/`，命名 `mNN_xxx.py`（如 `m01_materials.py`）。

---

## 7. 里程碑路线图（Milestones）

- **M0 基础与管线**（✅ 已完成 v1）：场地平面、U 形路径、6 栋示意教学楼、4 塔、7 敌人、俯视相机、Cycles 出图。
- **M1 程序化材质库**：建节点组材质库（草/沥青/砖/混凝土/玻璃/木/金属/瓷砖），应用至现有网格；写 `build/m01_materials.py`。
- **M2 建筑外壳（Archimesh）**：教学楼 + 实验楼 exterior，门窗开洞，真实尺度。
- **M3 室内可进入**：上述 2 栋做走廊/楼梯/典型教室；用 Walk Navigation 验证可进入；写 `build/m03_interior_*.py`。
- **M4 其余建筑**：图书馆/食堂/宿舍/体育馆/行政楼 exterior+代表性 interior。
- **M5 场地细化**：真实沥青路、围墙、操场跑道球场、树木绿化、校门、标识。
- **M6 光照与 HDRI**：World HDRI + 阳光 + 室内灯 + 探针烘焙。
- **M7 电影级后期**：AgX + Compositor Bloom + 终帧渲染预览。
- **M8 塔防层 refinement**：Tower 布局平衡、Enemy 沿 Bezier 曲线、出生点/波次标记。
- **M9 导航/导出**：Walk Navigation 参数固化；Godot/Unity 导出说明（可选）。

---

## 8. 避坑清单（Pitfalls — 来自调研与实测）

1. **Bloom 在 EEVEE Next（4.2+/5.x）已从渲染设置移除** → 改用 Compositor 的 Glare 节点（Bloom 模式）。
2. **MCP exec 里别调 `bpy.ops.object.mode_set`**：清空场景后无活动对象会 poll fail；删完默认就是 OBJECT 模式。
3. **Principled 节点按 `type=='BSDF_PRINCIPLED'` 找**，名字 `get('Principled BSDF')` 在 5.x 可能返回 None。
4. **锥体 `primitive_cone_add` 用 `radius1`/`radius2`**，cylinder 才用 `radius`。
5. **`render_viewport_to_path` 忽略 output_path**，读返回的 `result.filepath` 才是真路径。
6. **Walk Navigation 只碰水平面、垂直墙穿模**：室内必须铺地板面才能"走进去"；台阶低于视点高度自动上、高于穿；斜坡 ≤88° 可爬、89° 穿。
7. **Archimesh 是官方内置**（Extensions 启用），用 Auto Hole 给门窗开洞；生成的墙是 modifier 驱动、可后期编辑。
8. **材质必须加变化**：纯色显假；Noise/Voronoi/Musgrave + ColorRamp 控制 + Normal/Bump；近景用 Displacement。
9. **HDRI 用 Light Path Is Camera Ray 混合**：天空亮、照明贡献小，避免室内过曝。
10. **EEVEE Next 用 Raytracing 替代 SSR**；GI 靠 Irradiance Volume + Reflection Cubemap 烘焙。
11. **多行 if 在 Python Console 缩进累积导致整段跳过** → `exec("""...""")` 三引号包裹。
12. **两个 Blender 5.2 实例**：C 盘 msi + D 盘 blender.exe；插件/脚本务必对准活动实例（D 盘），共享 addons 在 `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\`。

来源：uhiyama-lab 渲染指南、Blender-Artworks Rendering.md、reelmind EEVEE 摄影级、startingframe 程序化石材、strayspark 材质管线、oldetinkerer 程序化混凝土、blender.tekriss 程序化砖、imeshh EEVEE Next 室内、suzhar Walk Navigation、blender/blender-addons Archimesh。

---

## 9. 文件与资产结构

```
campus_td/
  PLAN.md            # 本计划书（权威）
  PROGRESS.md        # 进度日志（自动任务每次追加）
  RESEARCH.md        # 教程/避坑收集（自动任务追加）
  build/             # 里程碑构建脚本 mNN_xxx.py（幂等、前缀隔离）
  previews/          # 各里程碑渲染预览 PNG
```
根目录 `render_campus_td.png` / `build_campus_td.py` = M0 v1。

---

## 10. 自动任务协作约定（Automation Contract）

- 每日构建任务：读 PLAN.md 找下一个未完成里程碑 → 写/复用 `build/mNN_*.py` → 经 MCP 执行 → 渲染预览 cp 到 `previews/` → 追加 PROGRESS.md。
- Blender 离线时：跳过构建，改为研究该里程碑技术、追加 RESEARCH.md，并标记"等待 Blender 在线"。
- 每周研究任务：为未来 1–2 个里程碑搜集 GitHub/Web 教程与避坑，追加 RESEARCH.md（带日期+来源链接）。
- **自动化数量纪律（用户明确）**：保持最少自动化。当前 = 1 个每日构建（顺序走完 M1–M9）+ 1 个每周研究，**不按里程碑各建一个**。若未来自动化数量逼近上限，**先在执行会话里把任务做实，再补建自动化**（执行优先于自动化定义）。每日构建任务本身即"每天定期完成任务 + 实时更新进度"的载体。
- 所有写操作保持**幂等 + 前缀隔离**，绝不 `select_all+delete` 全场景（除非该里程碑明确要重建整块）。
- 进度日志格式：
  ```
  ## YYYY-MM-DD HH:MM [里程碑 Mx] 状态：完成/部分/跳过
  - 做了：…
  - 遇到：…
  - 下一步：…
  - 预览：previews/mNN_xxx.png
  ```
