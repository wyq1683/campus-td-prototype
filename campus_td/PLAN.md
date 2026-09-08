# 项目计划 · 高中校园塔防原型（Cinematic Enterable High School TD Prototype）

> 本文件是项目唯一权威计划书。自动任务每次运行都会读取它来决定下一步。
> 上下文可能被压缩，但本文件常驻磁盘，是抗压缩的"项目大脑"。
> 最后更新：2026-09-08 20:20（自动构建代理 · M36 分叉电弧多帧序列）

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
- **M1 程序化材质库**（✅）：建节点组材质库（草/沥青/砖/混凝土/玻璃/木/金属/瓷砖），应用至现有网格；写 `build/m01_materials.py`。
- **M2 建筑外壳（Archimesh）**（✅，改 box+Boolean）：教学楼 + 实验楼 exterior，门窗开洞，真实尺度。
- **M3 室内可进入**（✅）：上述 2 栋做走廊/楼梯/典型教室；用 Walk Navigation 验证可进入；写 `build/m03_interior.py`。
- **M4 其余建筑**（✅）：图书馆/食堂/宿舍/体育馆/行政楼 exterior；代表性 interior 推迟到 M8。
- **M5 场地细化**（✅）：真实沥青路、围墙、操场跑道球场、树木绿化、校门、标识。  
- **M5B 细节精修**（✅，可选 backlog 第 1 项）：树冠 box → icosphere 有机簇、围墙压顶 (coping)、校门青铜嵌板+石框（匾文待 CJK 字体后深化）。
- **M6 光照与 HDRI**（✅，离线化）：程序化渐变天穹 + SUN 主光 + AgX + 场景内 ADD 模拟 Bloom。
- **M7 塔防层 refinement**（✅）：U 形 Catmull-Rom 路径 + frame_change 动画 + 射程全息穹顶 + 类型信标 + 锁定光束 + 出生/基地。
- **M8 室内扩展**（✅）：5 栋代表房间(办公室/宿舍/球场/食堂/阅览室) + 程序化家具 + 每栋南立面切真实门洞。
- **M8B 室内补光精修**（✅，可选 backlog 第 2 项）：五间 AREA 补光 energy 160→240(普通)/300(体育馆) + 矩形灯尺寸按内净 0.7x 放大覆盖地面，消除暗角。
- **M8C 上层重复房间扩展**（✅，可选 backlog 第 3 项）：每上层铺楼板（留 1.45m 楼梯井槽）+ 上层简化家具 + 层间斜置楼梯体量，消灭"空壳楼"；Gym 通高球场不加楼板。scene 290→361（+71）。
- **M8D 上层房间补光**（✅，可选 backlog 第 4 项）：12 个上层各加一盏 AREA 灯（energy 200, 0.7x 内净, 该层地面+3.4m），配套 M8C 收尾；scene 361→373，灯光 9→21。
- **M8E 书架书条精修**（✅，可选 backlog 第 5 项）：删 6 块单色书板，换 72 本多色书条（6 书架 × 4 层 × 3 本，6 色确定性调色板，摆在书架前脸 -y 侧）；scene 373→439。
- **M9 导航/导出**（✅）：脚本化漫游相机（校门→广场→图书馆门洞→阅览室）+ EEVEE PNG 序列 + ffmpeg 编码 MP4；Godot/Unity 导出说明仍可选。
- **M10 玩法层数值**（✅）：纯 Python 平衡模拟器 `build/m10_balance.py`（不依赖 Blender，秒级迭代）+ 设计文档 `DESIGN.md` + 数值单一数据源 `build/m10_config.json`。核心结论：拐角塔覆盖 26m = 直腿塔 2 倍但两拐角已被固定塔占满；满配后覆盖达 100%，**减速是唯一全局杠杆** → SLOW 重做为覆盖区全体减速力场 + 乘算叠加。平衡带：熟练 16/20 通关、新手第 9 波崩。**（注：数值经步长收敛修正后重标定为 HP_SCALE 0.23，见 §6.1）**
- **M10B 建塔位落地**（✅）：`build/m10b_slots.py`（PREFIX=`M10B_`）把 4 个建塔位建进场景（法向内偏 4.5m 到庭院侧，避免塔立在路径上）；探针验证联合覆盖 100.0%；scene 439→515。
- **M10C WebGL2 可玩原型**（✅）：`web/index.html`（单文件）+ `web/config.js`（由 `build/m10c_webcfg.py` 生成）。GLSL 渲染关卡（SDF 追踪 + 建筑玻璃体 + 屏幕空间敌人光点），JS 跑同一套数值，含 HUD 与建造/升级交互。带 `?selftest=1` 无渲染自测，用于与 Python 仿真交叉验证。
- **M10D 敌人差异化建模**（✅，2026-09-07 复核并实跑通过）：5 种外形 + 血条。`build/m10d_enemies.py` 保留 `Enemy_1..7` 对象名（M7 逐帧按名写 location），只替换网格 + 挂子物体。
  ⚠️ **"幽灵里程碑"复核结论（修正此前判断）**：脚本一直存在，但本轮开工时场景里查不到 `M10D_*`（探针复核），说明**从未在当前 Blender 实例上跑成功过**。本轮实跑后修复两个真 bug 才生效：① `replace_mesh()` 只取 `.data`，builder 给临时物体设的 scale 会丢失 → Rusher 拉长 / Tank 压扁全部退化成球；改为先把 scale 烘进顶点。② 血条/尖刺用 `obj.parent = e` 后未把 `matrix_parent_inverse` 钉成单位阵 → 子物体被留在世界原点而非跟随敌人。另把配色对齐 `web/index.html` 的 `enemyCol()`。
  验证：7 个敌人体型分别为 Swarm 0.80 / Rusher 0.85(拉长) / Elite 六棱 / Tank 1.84×1.44(压扁) / Boss 2.3+6 尖刺；血条 `parent_inverse=Identity`、世界坐标 = 敌人+z 偏移；渲染后敌人已由 M7 handler 复原到 U 形路径。预览 `previews/m10d_enemies.png`。
- **M11 总平重排**（✅）：场地 46m→96m + 7 栋楼重排到 U 形路径走廊之外。`build/m11_masterplan.py`（PREFIX=`M11_`，幂等，delta 由外壳 AABB 中心算出故可重复运行）。修复两个硬伤：① Teach 65m / Lab 49m 超界且互穿；② 塔防 U 形路径穿过 5 栋楼 footprint。**路径/塔位/波次一个坐标不改** → M10 数值与 M10C 原型继续有效（浏览器自测仍 `lives=16 leaks=2`）。校验：无超界、无两两重叠、路径最小净距由 0.0m→7.5m。scene 515→584。预览 `previews/m11_masterplan.png`。
- ~~**修 Teach/Lab 超界**（⬜）~~：**已并入 M11 完成**（2026-09-07）。
- **M12 机位自适应 + 上层补光量化校验**（✅）：`build/m12_uppercheck.py` + `build/m12_analyze.py`。
  ① **修 M11 的连带问题**：M8/M8B/M8C/M8D/M8E 所有渲染相机都是按旧坐标硬编码的，场地重排后全部指向空地。M12 改为**从目标建筑当前 AABB 动态算机位**，建筑再挪也不失效。
  ② **把"目视确认上层补光"变成客观判据**：同一栋 Library、同一房间进深、同一支 20mm 镜头，只差楼层（上层 3F E=200 vs 地面 1F E=240 基准），比亮度分布分位数。
  **结论：上层 energy=200 合适** —— p50 73.7 落在室内合理带 (55,150)、过曝 0%、死黑 0%，M8D 结案。
  **附带发现（新 backlog）**："已调好"的地面层 1F 自身 p50=40.5（低于合理带 26%）且 p99=224 —— 窗光刺眼 + 室内欠曝的高对比度问题，M8B 当年是目视调的，没有量化依据。
  ⚠️ 对照实验的前提是**两张机位必须同一相对位置**：初版让地面层站门外拍，画面混进门框背光 → 15% 死黑，纯构图差异被误读成亮度差异。
- **M13 地面层补光标定**（✅，**结论是"不改"——负面结果，务必看这条再动手**）：`build/m13_groundfix.py` 做能量扫描。
  M12 曾把"地面层 1F p50=40.5 低于合理带"列为新 backlog，本轮扫描证明**不该改**：

  | 旋钮 | 变化 | p50 | 幅度 |
  |---|---|---|---|
  | 补光 `M8_Library` energy | 240 → 460（**+92%**） | 40.5 → 43.7 | **+8%**，p99 恒定 224.1 |
  | World 环境光 strength | 0.45 → 1.0（+122%） | 40.5 → 47.4 | +17% |
  | World 环境光 strength | 0.45 → 2.2（**+389%**） | 40.5 → 53.4 | +32%，p99 开始动（225.9） |

  根因：画面亮度由**窗光**主导；天花板 AREA 灯照不到书架/墙的**垂直面**（cosine 定律），提强度几乎无效。环境光效率更高，但要让 p50 够到 55 需要约 5 倍，且它**影响全场景**、会让室外发灰。
  **决定：维持 `M8_Library` energy=240、`World` strength=0.45 不变。** 现状过曝 0%、死黑 0.93%，p50 偏低的真实成因是阅览室 6 个深色书架占满画面 —— 是**内容偏暗**，不是照明故障。
  判读器 `m12_analyze.py` 已加护栏：`crush < 2% 且 p90 > 100` 时，p50 低于下限也判"内容偏暗，不建议提灯"。
- **M14 校门匾文**（✅）：`build/m14_plaque.py`（PREFIX=`M14_`）。补齐 M5B 遗留的匾文（当时缺 CJK 字体）。黑底金字 + 四周石框，校名 `SCHOOL_NAME = "晨光中学"`（顶部常量可改）。
  ⚠️ **字体不能只看"文件在不在"，必须量实际字形尺寸**（探针 `tools/_font_probe.py`，size=1.0 / "晨光中学" 4 字）：

  | 字体 | 4字宽 / 字高 | 判定 |
  |---|---|---|
  | **simhei.ttf** | 3.82 / 0.92 | ✅ 黑体，最饱满最醒目 → 采用 |
  | Dengb.ttf | 3.23 / 0.78 | ✅ 等线 Bold（次选） |
  | msyhbd.ttc | 3.01 / 0.75 | ✅ 雅黑 Bold（次选） |
  | simsun.ttc | 3.91 / 0.92 | ✅ 宋体（兜底） |
  | simsunb.ttf | 1.91 / 0.68 | ❌ Windows 上其实是 **SimSun-ExtB**，缺常用汉字 |
  | Deng.ttf | **0.0 / 0.0** | ❌ 等线 Regular 在本机 glyph 解析为空 |
  | NotoSerifSC-VF / NotoSansSC-VF | 1.36 / **0.32** | ❌ **可变字体在 Blender 里被缩到 0.32 倍**且取最细（ExtraLight/Thin）实例 |

  即**原候选链里首选的 VF 和兜底的 Deng 两个都是坏的**，不探针必然出空匾/细如发丝的匾。故 `pick_font()` 内建尺寸自检（单位字高 ≥0.55 且每字宽 ≥0.55），不合格自动换下一个字体——换机器也不会静默失败。
  排布不再硬编码 size：按 `TEXT_H=0.82m` 目标字高反算 `size`，若总宽超过匾宽 78% 再按宽度回缩 → **换校名（2 字 / 6 字）自动适配**。
  朝向沿用 M5B 结论：文字本地 +Z 为正面，绕 X 轴 +90° 后 +Z→-Y（朝南）、字顶→+Z，`extrude` 沿本地 +Z 即沿 -Y 凸出，一步到位。
  验证：字宽 3.42m（匾宽 6.0 的 57%）、字高 0.84m（匾高 1.2 的 70%）、位置 y=-48.41 贴匾前脸、rot=(1.571,0,0)。预览 `previews/m14_plaque.png`。
- **M15 楼梯真实踏步**（✅）：`build/m15_stairs.py`（PREFIX=`M15_`）。把 M8C 的**斜板楼梯**换成带 Array 修改器的真实踏步。
  原状：M8C 每段楼梯就是一块斜置 box（1.3m 宽 × 斜长 5.045 × 厚 0.18），坡度 **50.6°**（层高 3.9 / 水平投影 3.2），纯示意体量。
  新：层高 3.9m 按舒适公式 `2h+d≈0.63` 取 **h=0.177 / d=0.28 → 22 级、跑长 6.16m、坡度 32.3°**；每段 = 梯段底板(斜板) + **Array 踏步(count=22, 常量偏移 (0, 0.28, 0.177))** + 两侧斜扶手。
  **设计取舍**：楼梯井槽仅 1.45m 宽 → 只能放单跑 1.3m 宽，双跑（2×1.2+井）放不下；22 级略超"每段 ≤18 级"规范上限，但这是 1.45m 井宽 + 8~12m 进深下的唯一解，原型场景接受。
  ⚠ **两个约定（违反会静默错位）**：
  ① **坐标全部从场景里的旧楼梯对象读，不硬编码** —— M11 把 7 栋楼整体挪过，M8C 脚本里的 `center` 常量（如 Admin=(-16.5,-15)）早已失效，实测新位置 (-43.3, 31.005)。与 M12 机位自适应同一思路。
  ② **命名避开 `Stair_` / `Int_`** —— M11 的 `owner()` 见到含 `Stair_` 的名字会判给 Teach 并挪走它；本脚本改用 `Slope` / `Steps` / `Rail`，且 **M15 必须排在 M11 之后跑**（`M15_*` 不被 owner() 识别，M11 不会挪它们，跑反了就错位）。
  验证：12 段全部替换，Array count 全为 22，旧 `M8C_*_Stair_*` 清零，每段 `landing_ok`（最后一级顶面 == 上层楼面）与 `in_shell`（未捅出楼外）均为真。scene 592→629。预览 `previews/m15_stairs.png`。
- **M16 围墙垛口**（✅）：`build/m16_crenellations.py`（PREFIX=`M16_`，幂等）。在 M11 重建的 5 段 perimeter 围墙（`M11_WallBack`/`M11_WallFrontL`/`M11_WallFrontR`/`M11_WallLeft`/`M11_WallRight`，96m 场地、墙高 2.4m、厚 0.35m、顶有 `M11_Coping*` 压顶）之上，沿墙顶中线排布一列 **merlon 垛口**（交替方块 + 空隙，女儿墙/城垛质感）。坐标从 `M11_Wall*` 的 AABB 动态读取（不硬编码，墙再挪也贴合），merlon 高 0.55 / 沿墙宽 0.55 / 厚 0.47、中心间距 1.25m、坐于 coping 顶面（top = 墙与覆盖其上的 coping 的 max z）；复用 `PBR_Concrete`。共 **295 个**（Back/Left/Right 各 77、FrontL/FrontR 各 32）；校门洞 x∈[-8,8] 两端留 0.3m 余量防悬空。`M16_Cam` 由东南角（FrontR×Right 交汇 (48,-48)）动态推算、场外低角度看入，框进 corner merlon 转折 + coping + 远处校门牌坊。预览 `previews/m16_crenellations.png`。scene 629→925。
- **M17 教学家具与食堂道具细化**（✅）：`build/m17_props.py`（PREFIX=`M17_`，幂等）。回溯：M11 总平重排后 `Int_Teach_*` 仅余地板/黑板/隔墙，M3 的 18 套课桌椅已丢失 → **回填**教室：72 课桌 + 72 课椅（双 bank + 中央过道，沿 y 4 排 × 每侧 9 列），用 bmesh 把每套桌/椅合并为单网格（避免 144+ 子物体）；另加教师讲桌/椅、讲台地台、投影幕（-Y 墙黑板上方）、挂钟（+Y 后墙）、角落书架 + 6 本示意书。食堂（`M8_Canteen_*` 已有 4 桌 + 8 长椅 + 取餐台 + 4 吊灯）轻量点缀：菜单板（南墙）、垃圾桶×2、绿植×2、餐具回收台（东墙）。所有坐标从探针真实 AABB 推算（不硬编码旧址），几何校验教室/食堂区零越界。`M17_Cam`(0,-23,4.5,28mm) 教室英雄机位（后墙俯看课桌椅阵列与黑板）。预览 `previews/m17_props.png`。scene 925→1098。
- **M18 PBR 材质 Vector 全局修复（防复发）**（✅）：`build/m18_pbr_vector.py`（幂等 in-place，不删/不重建材质）。覆盖 M4 只修 `PBR_Brick`/`PBR_Concrete` 的缺口——给 `PBR_Grass`/`PBR_Asphalt`/`PBR_Wood` 的 Noise 与 `PBR_Tile` 的 Brick 显式接通 Generated 坐标（砖类走 `Mapping(Scale 10)` 匹配 M4 密度；其余用纯 Generated 防过密）。共 +19 个 Vector 链接，所有程序化纹理 100% 接通。同步把 Vector 修复**并入源文件 `m01_materials.py`**（`ensure_coords()` + 各 `build_*` 显式连线），未来重跑 m01 不再复发发灰。⚠ **实跑用 in-place 补丁而非重跑 m01**：m01 的 `clear_old` 会移除并重建全部 `PBR_*` 材质，M5/M11/M16 等物体按名引用这些材质→重建后旧槽悬空丢材质（破坏其他物体）。scene 1098（不变）。预览 `previews/m18_pbr_vector.png`。
- **M19 波次编辑器（Web）**（✅）：`web/sim.js`（与 `build/m10_balance.py` 逐行等价的平衡模拟引擎
- **M9 Godot/Unity 导出说明**（✅）：`EXPORT_GODOT_UNITY.md`（导出指南：glTF 2.0 选型、Godot 4 / Unity 导入步骤、本项目特有坑）+ `build/m19b_export.py`（一键 glTF 2.0 .glb 导出，非破坏）+ `tools/run_m19b_export.py`（Direct TCP Socket 540s）+ `exports/campus_td.glb`（实测 1098 obj / 1065 mesh / 9.55 MB）。格式选 glTF 2.0 .glb；Godot 4 原生 / Unity glTFast 导入；本项目关键坑：程序化节点材质不导出（需 bake 贴图才有电影级观感）、M7 动画不导出（frame_change 驱动非 Action）、塔防语义靠节点名 Tower_/Enemy_/TD_/M10B_ 保留、尺度 1u=1m 自动 Z→Y。：DT=0.05 / 护甲=每发伤害×(1-armor) / SLOW=覆盖区全体减速力场+乘算叠加 / ROI 棋盘感知 / 双策略 PLAN_GOOD·PLAN_NAIVE）+ `web/wave_editor.html`（浏览器编辑器：编辑 10 波构成与数值 → 实时验算熟练&新手两策略 → 导出 `m10_config.json`）。导出后 `python build/m10c_webcfg.py` 把数值推回 `web/config.js`，刷新 `index.html` 即可试玩。Node 交叉验证 `tools/test_wave_editor_sim.cjs` 与 Python 仿真逐波一致（熟练 16/20 漏 2、新手第 9 波崩）。
- **M14 校门匾文**（✅，补齐 M5B 遗留项）：`build/m14_plaque.py`（PREFIX=`M14_`，幂等）。M11 把校门重排到 y=-48（`M11_GatePlaque`，6.0×0.12×1.2m 深色底板，匾面朝 -y）。本脚本在匾面南向(-y)挂**金色立体校名「晨光中学」**（size 0.82 / extrude 0.05 / 绕 X+90° 朝南）+ 四周石框 + `M14_Cam` 特写机位（围墙外 y=-62，70mm，与匾同高）。字体用 `pick_font()` **带字形尺寸自检**（避可变字体 VF 被缩成空匾）；实测首选 **SimHei 黑体**（w=3.82 h=0.92 最饱满），兜底 等线B/雅黑B/宋体。`build_cam()` 由匾中心动态推算机位，建筑再挪也不失效。预览 `previews/m14_plaque.png`。
- **M10 玩法平衡模拟**（✅，纯 Python 验证）：`build/m10_balance.py` 数值仿真器（路径102m/固定塔覆盖76.5%/4建塔位/4塔型/5敌型/10波），双策略（熟练/新手）跑通并校验平衡带；当前数值过易（两策略零漏怪通关），待调参（降金币/升敌血/升漏怪代价/降SLOW上限）重跑。

- **M19c Cycles GPU OptiX 终帧**（✅）：`build/m19c_optix_final.py`（非破坏，仅配 GPU 出图）。RTX 5060 OptiX 设备启用（`cycles.device=GPU` / `compute_device_type=OPTIX` / `denoiser=OPTIX`）；白昼英雄 3/4 俯角 + 暮色鸟瞰双帧，2560×1440 / 512 samples / OptiX 降噪；英雄 28.5s、鸟瞰 12.4s（GPU 远快于 CPU 历史 3–7 分钟）。**M0–M19 全路线图 + 全部 backlog 至此 100% 完成，原型收官。**

- **M20 4K 超采样终帧**（⚠️ 受阻 / 硬件限制，非强制）：`build/m20_4k_final.py`（非破坏，仅 GPU 出图 + 质量阶梯）。目标把 M19c 的 2560×1440 升到真 4K。实测 **RTX 5060 8GB VRAM 无法承载 >2560×1440 的 OptiX 降噪全分辨率缓冲区**：3840×2160（降噪 / 无降噪 1024s）与 3200×1800（降噪）均写帧阶段 OOM 失败，仅 2560×1440（==M19c）可行。白昼英雄单帧 ~23 min、5.4MB。脚本已改为只跑 2560×1440 档以防空耗。**结论：真 4K 需 >8GB GPU，或改用分块渲染 / 序列帧 / 降纹理内存；原型已收官，M20 不阻塞后续。**

- **M21 镜头画廊（多机位 OptiX 终帧集）**（✅，2026-09-08）：`build/m21_gallery.py`（非破坏，仅 GPU 出图）+ `tools/run_m21.py`（Direct TCP 900s）。项目收官后新增的"完善"里程碑：把原型关键视角统一升到 Cycles GPU OptiX 终帧质量（2560×1440 / 512 samples / OptiX 降噪 / AgX），形成可对外展示的画廊。复用场景中已有命名相机（不新建/不破坏物体）：`M19C_HeroDay`(白昼英雄 3/4)、`M11_CamAerial`(暮色鸟瞰)、`M14_Cam`(校门匾文)、`M16_Cam`(围墙垛口)、`M17_Cam`(教室)、`M15_Cam`(真实踏步)。scene 1112（零破坏）。输出 `previews/m21_gallery_<shot>.png` 共 6 张。

- **M22 影院级漫游视频（OptiX 运镜）**（✅，2026-09-08）：`build/m22_flythrough.py`（非破坏，仅新建临时 `M22_Cam` 出图）+ `tools/run_m22.py`（Direct TCP 900s）+ `tools/assemble_m22.py`（imageio-ffmpeg 合成 MP4）。项目收官后新增的"完善"里程碑，把 M21 静态画廊升级成**动态漫游**：复用已验证的 6 个命名机位，在它们之间做平滑运镜（位置 lerp + 朝向 slerp shortest-arc + 焦距 lerp），逐帧渲染 PNG 序列后外部合成 MP4。相较 M9（EEVEE、沿 M11 前的旧坐标飞行、重排后已失效），本视频基于当前布局的已验证机位且用 OptiX 终帧质量。Cycles GPU OptiX / OptiX 降噪 / 160 samples / 1280×720 / 30fps / AgX / 白昼统一 `build_lighting('day')`。81 帧 / 2.7s / 8.29MB；scene 1112→1113（仅增 `M22_Cam`，零破坏）。输出 `previews/m22_flythrough.mp4` + 序列 `previews/m22_frames/m22_*.png`。

- **M23 360° 全景图（Equirectangular · OptiX 终帧）**（✅，2026-09-08）：`build/m23_panorama.py`（非破坏，仅新建临时 `M23_Pano` 相机，前缀 `M23_`）+ `tools/run_m23.py`（Direct TCP 900s）。项目收官后新增的"完善"里程碑——把已收官校园渲染成一张 2:1 等距矩形（Equirectangular）全景，可在 360° 查看器里沉浸式环视。落点算法取"不在任一 `Bldg_*` AABB 内、且距场地中心最近"的网格点 → 中庭 `(0,0,1.6)` 眼高，四周被楼体环抱（初版误用"距所有楼最远"选到边角 `(-44,-44)`，已重渲修正）。Cycles GPU OptiX / OptiX 降噪 / **512 samples** / 2560×1280 / AgX / 白昼统一 `build_lighting('day')`。2560×1280 总像素 3.27M < M20 实测 OOM 上限 3.69M（8GB VRAM），安全出图。**scene 1113→1114**（仅增 `M23_Pano` 相机，零破坏）。输出 `previews/m23_panorama.png`（4.19MB，等距矩形 2:1 经 PNG 头校验）。

- **M24 夜间塔防作战渲染（Night Defense · OptiX）**（✅，2026-09-08）：`build/m24_night.py`（非破坏，仅新建临时 `M24_` 前缀相机与点光；结束恢复光照）+ `tools/run_m24.py`（Direct TCP 900s）。项目收官后新增"完善/展示"里程碑——复刻已验证的 `M19C_HeroDay` 英雄机位，把白昼英雄 3/4 俯角重拍成**夜间作战**：压暗天光、冷蓝月光、提亮防御塔发光环与 `M6_Halo_*` 辉光壳、在 12 个 `Tower_*` 基座补冷色点光池。渲染 Cycles GPU OptiX / OptiX 降噪 / 256 samples / 2560×1440 / AgX。**scene 1114（零破坏，结束恢复 M24_ 临时对象并删除 `M24_NightWorld`）**。输出 `previews/m24_night_defense.png`（4.24MB）。

- **M25 大气体积雾（Atmospheric Volumetric Fog · OptiX）**（✅，2026-09-08）：`build/m25_atmosphere.py`（非破坏，仅新建 `M25_` 前缀雾盒+材质，持久化留存）+ `tools/run_m25.py`（Direct TCP 900s）。

- **M26 黄金时刻暖调渲染（Golden Hour · OptiX）**（✅，2026-09-08）：`build/m26_golden_hour.py`（非破坏，仅新建 `M26_` 临时世界/相机，结束恢复白昼基线）+ `tools/run_m26.py`（Direct TCP 900s）。收官后新增第 4 种时段氛围（继 day/dusk/night 之后）：低角度暖色阳光（M6_Sun 改 (78,58,22)、energy 4.5、color (1.0,0.52,0.22)）+ 暖橙→蜜桃→柔蓝→深蓝天穹渐变（`M26_GoldenWorld`，strength 0.55）+ AgX exposure 0.05；复用已验证 `M19C_HeroDay` 英雄机位与 `M11_CamAerial` 鸟瞰机位，双帧 2560×1440 / 256 samples / OptiX 降噪。与 **M25 持久化体积雾**叠加出暖色大气薄霭。hero 28.3s / aerial 14.5s；像素统计 hero mean(98.6,76.8,58.4) / aerial mean(153.6,126.5,97.1)（R>B 暖调显著、过曝 0%）；**scene 1115（仅增临时对象、结束恢复，零破坏）**。输出 `previews/m26_golden_hour_hero.png`（4.92MB）+ `previews/m26_golden_hour_aerial.png`（3.77MB）。项目收官后新增"完善/质感"里程碑——给 96m 校园罩一层低密度 `Principled Volume` 雾盒（density 0.012 / 冷色 (0.80,0.84,0.88) / anisotropy 0.30 / 全尺寸 90×90×14、z 跨 -1..13m），营造电影级大气景深：远处楼体在雾中淡出、近处保持锐利。避坑：体积材质必须只接 `Volume` 输出（不接 Surface 实心）；雾盒 `hide_viewport=True`（不污染 3D 视口）但 `hide_render=False`（渲染仍含）；密度压低以防 8GB VRAM OOM（M20 实测 >2560×1440 才 OOM，本档 1920×1080 安全）。复用已验证 `M19C_HeroDay` 英雄机位；Cycles GPU OptiX / OptiX 降噪 / 256 samples / 1920×1080 / AgX / 16.4s。**scene 1114→1115（仅 +1 雾盒，零破坏其他物体）**。输出 `previews/m25_atmosphere.png`（2.97MB，像素统计 mean(76.7,73.6,69.9)/黑 2.27%/过曝 0%）。若需更浓雾，仅改 `m25_atmosphere.py` 顶部 `Density` 重跑；雾盒对象 `M25_Fog` 在视口隐藏、渲染常驻。

- **M27 雪景冬季校园（Snowy Winter Campus · OptiX）**（✅，2026-09-08）：`build/m27_snow.py`（非破坏，仅新建 `M27_` 前缀临时世界/积雪/飘雪粒子；结束恢复白昼基线）+ `tools/run_m27.py`（Direct TCP 900s）。项目收官后新增第 5 种天气/季节氛围（继 day/dusk/night/golden 之后）：冷调明亮天光（`M27_SnowWorld` 白蓝渐变，strength 0.95）+ 冷白阳光（M6_Sun loc (52,-38,58)、energy 2.8、color (0.92,0.95,1.0)）+ AgX exposure 0.0。积雪层：动态读取 7 个 `Bldg_*_Roof` 世界 AABB 并放置 `M27_SnowCap_*` 屋顶雪盖；复制 `Ground` 地形生成 `M27_GroundSnow`（z +0.05）覆盖地面；空中飘雪：110×110×26m 体积发射器 + 1400 个微粒（ico 球实例）。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440。hero 41.9s / aerial 20.5s；scene 1115（临时对象已清，零破坏）。输出 `previews/m27_snow_hero.png`（5.06MB）+ `previews/m27_snow_aerial.png`（3.75MB）。**关键避坑**：长运行 Blender 实例中 `sc.world` 旧引用会被释放，restore 改用 `m06.build_lighting('day')` 重建白昼基线，避免 `sc.world = old_world` 报 `StructRNA of type World has been removed`。

- **M28 雨夜校园（Rainy Night Campus · OptiX）**（✅，2026-09-08）：`build/m28_rain.py`（非破坏，仅新建 `M28_` 前缀临时世界/雨丝/湿地，结束恢复白昼基线）+ `tools/run_m28.py`（Direct TCP 900s）。项目收官后新增第 6 种天气/时段氛围（继 day / dusk / night / golden / snow 之后）：暗调暴风冷蓝天光（`M28_RainWorld` 暗蓝灰渐变，strength 0.35）+ 阴雨冷月（M6_Sun energy 0.6、color (0.6,0.7,0.9)）+ AgX exposure -0.3；细雨条纹：1800 个冷色微自发光细长圆柱实例（略带风斜）覆盖全校园体积发射体；湿润反光地面：复制 `Ground` 为 `M28_GroundWet`（z +0.05）覆低糙度+清漆光泽材质，呈现雨夜湿地反光。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440。hero 28.6s / aerial 14.3s；像素统计 hero mean(24.2,24.6,25.0)/aerial mean(21.2,27.1,33.1)（暗调夜景、aerial 偏蓝冷天光反射）、过曝 0%、nonblack 89%/95%。**scene 1115（临时对象已清，零破坏）**。输出 `previews/m28_rain_hero.png`（4.45MB）+ `previews/m28_rain_aerial.png`（3.63MB）。**配套根因修复**：`m06.setup_world` 改为复用权威 `World`，避免天气里程碑每次 restore 删空临时天光后 fallback 新建 `World.NNN` 孤儿天光无限累积（自动化每小时跑会爆）；并一次性合并既有 3 个孤儿天光回单一 `World`。

- **M29 闪电抓拍（Lightning Flash Capture · OptiX）**（✅，2026-09-08）：`build/m29_lightning.py`（非破坏，仅新建 `M29_` 前缀临时世界/闪光灯/雨丝/湿地，结束恢复白昼基线）+ `tools/run_m29.py`（Direct TCP 900s）。项目收官后新增第 7 种天气/时段氛围（继 day/dusk/night/golden/snow/rain 之后）：在雨夜（M28 同款暗蓝灰暴风天光 + 阴雨冷月 + 1600 雨丝 + 湿地）之上叠加**峰值闪电**——一道强方向性 `M29_FlashSun`（SUN，置于场地一角高空 (55,45,95) 投影扫过校园）+ 天光瞬时微提 + 曝光微抬，抓拍一张戏剧化雷暴帧。⚠ **曝光调参实录（重要避坑）**：初版 `FLASH_ENERGY=2200 / WORLD=0.85 / EXP=-0.08` 实测 hero 过曝 66% 全白；经 6 轮像素统计收敛，根因有两层——① 近镜面湿地（rough 0.12 + clearcoat 1.0）把闪光 SUN 反射成全屏饱和高光，② AgX 高光压缩区使 hero 在 40%+ 像素剪裁时mean 对输入近乎无响应。最终解：`M29_` 湿地改为**湿而不镜面**（rough 0.32 / clearcoat 0.35）+ 天光保持暗（`WORLD=0.06` 不淹没湿地）+ 仅靠方向性 SUN(`ENERGY=90`) 打亮建筑 + `EXP=-0.34`。结果 hero meanLum 153.6 / 过曝 3.46% / dark 12.7%、aerial meanLum 59.0 / 过曝 3.66%（较雨夜 24 亮 6×，确为闪电），**scene 1115（零破坏）**。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440。输出 `previews/m29_lightning_hero.png`（4.77MB）+ `previews/m29_lightning_aerial.png`（3.66MB）。

- **M30 清晨薄雾校园（Morning Mist Dawn Campus · OptiX）**（✅，2026-09-08）：`build/m30_morning_mist.py`（非破坏，仅新建 `M30_` 前缀临时世界/雾盒/材质，结束恢复白昼基线）+ `tools/run_m30.py`（Direct TCP 900s）。项目收官后新增第 8 种时段/天气氛围（继 day/dusk/night/golden/snow/rain/lightning 之后）：柔和破晓天光（`M30_DawnWorld` 深蓝穹顶→柔蓝→暖桃地平线渐变，strength 0.5）+ 低角柔粉朝阳（M6_Sun loc (60,-40,16)、energy 2.2、color (1.0,0.68,0.48)）+ 贴地晨雾（两层体积雾盒：底层浓 z∈[-1,4] density 0.03 / 高层薄 z∈[3,17] density 0.012，偏冷白 (0.82,0.87,0.92)）+ AgX exposure 0.05。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440。hero 46.7s / aerial 24.0s；像素统计 hero meanRGB(71,64,62)/过曝 0.00%/dark 0.4%/max 224、aerial meanRGB(74,94,117)/过曝 0.00%/max 230（hero 微暖 R>B 9、aerial 冷蓝 B>R 43，确为破晓暖阳+晨雾冷调、零过曝），**scene 1115（零破坏，结束恢复白昼基线）**。输出 `previews/m30_morning_mist_hero.png`（4.77MB）+ `previews/m30_morning_mist_aerial.png`（3.38MB）。

- **M31 正午硬光校园（Midday Harsh Sunlight · OptiX）**（✅，2026-09-08）：`build/m31_noon_harsh.py`（非破坏，仅新建 `M31_` 前缀临时世界/材质，结束恢复白昼基线）+ `tools/run_m31.py`（Direct TCP 900s）+ `tools/stats_m31.py`（PIL 像素统计核验）。项目收官后新增第 9 种时段/天气氛围（继 day/dusk/night/golden/snow/rain/lightning/morning-mist 之后）：深蓝晴空（`M31_NoonWorld` 深蔚蓝穹顶→蔚蓝→苍白地平线渐变，strength 1.0）+ 高角硬光太阳（M6_Sun loc (28,38,92)、energy 4.0、color (1.0,0.97,0.92)、angle 0.01、shadow_soft_size 0.05 → 锐利短硬阴影）+ AgX exposure -0.05。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440。hero 33.3s / aerial 17.1s；像素统计 hero meanRGB(105.7,108.9,111.0)/过曝 0.00%/dark 0.62%/max 249、aerial meanRGB(108.7,141.6,172.3)/过曝 0.00%/max 251（hero 明亮近中性、aerial 强冷蓝 B>R 64，确为正午硬光高对比、零过曝），**scene 1115（零破坏，结束恢复白昼基线）**。输出 `previews/m31_noon_harsh_hero.png`（5.08MB）+ `previews/m31_noon_harsh_aerial.png`（3.71MB）。

- **M32 多帧闪电序列（Lightning Flash Sequence · OptiX）**（✅，2026-09-08）：`build/m32_lightning_seq.py`（非破坏，仅新建 `M32_` 前缀临时世界/闪光灯/雨丝/湿地/电弧，结束恢复白昼基线）+ `tools/run_m32.py`（Direct TCP 900s）+ `tools/assemble_m32.py`（imageio-ffmpeg 合成可循环 MP4）。项目收官后新增第 10 种时段/天气氛围，并把 M29 的"单帧闪电抓拍"升级为"多帧戏剧化序列"：在 M28/M29 已验证雨夜+闪电之上，按真实闪电时间线逐帧渲染 6 张英雄序列帧（pre 蓄暗→charge 微亮→peak 主闪峰→glow 余辉→flick 二次闪→resid 残光），叠加 12 段程序化可见电弧（`M32_BoltSeg_*`，仅峰/二次帧可见）。沿用 M29 获胜参数（峰帧 FLASH energy90/world0.06/exp-0.34）零过曝。Cycles GPU OptiX / 256 samples / 1920×1080(英雄序列)+2560×1440(鸟瞰峰帧) / AgX。像素统计 meanLum 序列 9.3→99.5→154.1(峰)→117.9→139.3→70.7，峰过曝仅 3.31%（与 M29 一致、无全白）。**scene 1115（零破坏，结束恢复白昼基线）**。输出 `previews/m32_lightning_loop.mp4`（6 帧循环，544KB）+ `previews/m32_lightning_peak.png`（2.85MB）+ `previews/m32_lightning_aerial_peak.png`（3.83MB）。

- **M33 暴风夜塔防作战（Storm Night Defense · OptiX）**（✅，2026-09-08）：`build/m33_storm_defense.py`（非破坏，仅新建 `M33_` 前缀临时世界/雨丝/湿地/塔基点光；结束恢复光照）+ `tools/run_m33.py`（Direct TCP 900s）。

- **M34 分叉电弧（Forking Lightning Bolts · OptiX）**（✅，2026-09-08）：`build/m34_forked_lightning.py`（非破坏，仅新建 `M34_` 前缀临时世界/闪光灯/雨丝/湿地/电弧；结束恢复光照）。项目收官后新增「闪电质感升级」里程碑——把 M32 的 12 段直段电弧升级为**程序化分叉/树状闪电**：主放电通道用递归中点位移生成锯齿主干（`forked_bolt()` 中段位移最大、两端收敛），沿主干中段随机派生分叉支络（带次级位移、半径骤减）；每段用 bmesh 直建细圆柱 emissive 几何表现，全程规避 MCP exec 内 `mode_set`。复用 M29 获胜峰值参数（energy90/world0.06/exp-0.34，零过曝），3 道分叉闪电分布于校园中/东南/西南，抓拍英雄+鸟瞰两视角暴风雷暴帧。Cycles GPU OptiX / 256 samples / 2560×1440 / AgX。像素统计 hero meanLum 155 / 过曝 4.48% / dark 12.5%、aerial meanLum 60 / 过曝 4.39%（与 M29 峰值一致、无全白），**scene 1115（零破坏，结束恢复白昼基线，单一 `World`）**。输出 `previews/m34_forked_lightning_hero.png`（4.78MB）+ `previews/m34_forked_lightning_aerial.png`（3.67MB）。

- **M36 分叉电弧多帧序列（Forked Lightning Sequence · OptiX）**（✅，2026-09-08）：
  `build/m36_forked_seq.py`（非破坏，仅新建 `M36_` 前缀临时世界/雨丝/湿地/三组电弧；结束恢复白昼基线）+ `tools/run_m36.py`（Direct TCP 900s）+ `tools/assemble_m36.py`（imageio-ffmpeg 合成 15 帧循环 MP4）+ `tools/stats_m36.py`（PIL 像素统计核验）。项目收官后新增「分叉电弧 + 多帧序列」合流里程碑——把 M32（多帧闪电序列，**但电弧是 12 段直线**）与 M34（程序化分叉/树状闪电，**但只有单帧**）合并，并按真实雷击三段式放电给出**三组不同电弧几何**：① 梯级先导（stepped leader）：主通道尚未击穿时的暗淡细通道，仅 charge 帧可见；**关键：先导与主回击共用同一条通道折线**（同 rng 路径，物理上"回击沿先导电离通道返回"）；② 主回击（return stroke）：3 道完整分叉主干（11 段主干 + 11 处分叉，共 85 段），seed 36，仅 peak 帧可见；③ 二次放电（subsequent stroke）：另 2 道独立分叉（47 段），seed 361（与主回击**不同 seed → 看起来像另一次雷击**，避免 M32 峰帧/二次帧复用同一道电弧的"同闪两次"感）。峰值曝光沿用 M29 经验，最终 v3：flash 32 / world 0.05 / exp -0.34 / 湿地湿而不镜面（rough 0.32 / cc 0.35，规避 AgX 高光压缩全屏白）。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / 1920×1080(序列)+2560×1440(鸟瞰峰) / AgX。**像素统计核验（v3 收敛）**：LUM 阶梯 pre:9.1 → charge:65.4 → peak:121.3 → glow:87.1 → flick:104.5 → decay:71.5 → resid:39.5（pre<charge<peak、flick 居中段、resid 回落，亮度阶梯成立）；over% 峰 0.84 / flick 0.32（远低于 5% 警戒）；PEAK_IS_MAX=True / PRE_IS_MIN=True。**scene 1115（零破坏，结束恢复白昼基线，单一 `World`）**。输出 `previews/m36_forked_seq_peak.png`(2.91MB)+ `m36_forked_seq_aerial_peak.png`(3.82MB)+ `m36_forked_seq_charge.png` + `m36_forked_seq_flick.png` + `m36_forked_seq_loop.mp4`(173KB, 15 帧 @ 8fps, 1.9s 循环)。
- **M35 树积雪帽（Tree Snow Caps · OptiX）**（✅，2026-09-08）：`build/m35_tree_snow.py`（非破坏，仅新建 `M35_` 前缀临时世界/雪盖/树积雪/飘雪；结束恢复白昼基线）。项目收官后新增「雪景质感补全」里程碑——M27 已给屋顶+地面铺雪，但散植的 22 株树（M11 重排后改名为 `M11_Tree{N}_Canopy`/`_Sat0`/`_Sat1`，旧 `M5_TreeFoliage` 已不存在）仍是光秃绿叶；本里程碑在每棵树冠顶部放一块压扁白色雪帽（flattened icosphere，scale (R×1.02, R×1.02, R×0.60)、仅上半球露出）让雪天的树也积了雪。⚠ **首跑踩坑（已修）**：按旧名 `M5_TreeFoliage` 探测 → tree_snow_caps=0（M11 早已改名）；改按 `M11_Tree*` + `_Canopy`/`_Sat` 动态读 AABB 后 66 顶全部生成（22 株×(主冠+2 卫星)=66）。屋顶雪盖 7 + 树积雪帽 66 + 地面积雪 1 + 飘雪 1400 粒子。复用已验证 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / 2560×1440 / AgX / exposure 0.0。**scene 1115（零破坏，结束恢复白昼基线，单一 `World`）**。输出 `previews/m35_tree_snow_hero.png`（5.07MB）+ `previews/m35_tree_snow_aerial.png`（3.75MB）。项目收官后新增综合展示里程碑——把 M28「雨夜」天气层 与 M24「夜间塔防发光」层 合成一帧：暴风冷暗夜天光（`M33_StormWorld` 暗蓝渐变，strength 0.26）+ 阴雨冷月（M6_Sun energy 0.7 / (0.55,0.68,1.0)）+ 湿润反光地面（`M33_WetMat` rough 0.18 / clearcoat 0.9，**湿而不镜面**，规避 M29 塔环反射全屏高光）+ 2000 雨丝 + 12 座 `Tower_*` 塔基冷光池（POINT energy 120）+ 防御塔发光环/辉光壳提亮（strength 9.0/6.0）。复用 `M19C_HeroDay`/`M11_CamAerial` 双机位，Cycles GPU OptiX / 256 samples / OptiX 降噪 / 2560×1440 / AgX / exposure -0.10。像素统计 hero meanLum 20.9 / 过曝 0.00% / dark 23.8%、aerial meanLum 15.0 / 过曝 0.00% / 强冷蓝(B>R 9.9)——确为暴风夜、零过曝（沿用 M29 教训），**scene 1115（零破坏，结束恢复白昼基线）**。输出 `previews/m33_storm_defense_hero.png`（4.40MB）+ `previews/m33_storm_defense_aerial.png`（3.65MB）。

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
13. **Blender 5.x 纹理节点输出/类型变更**：`ShaderNodeTexVoronoi` 输出 `Fac` → `Distance`；`ShaderNodeTexMusgrave` 节点已移除，功能并入 `ShaderNodeTexNoise` 的 Type（fBM），输出用 `Fac`。
14. **Blender 5.x 新版 Principled BSDF 输入名变更**：旧 `Transmission` → 新 `Transmission Weight`；`Emission` 拆为 `Emission Color` + `Emission Strength`；`Base Color`/`Roughness`/`Metallic`/`IOR` 保持不变。
15. **Blender 5.2 场景合成器已移除 `CompositorNodeComposite` 输出节点**（M6 实测）：`scene.compositing_node_group` 才是合成节点树（为 None 时需 `bpy.data.node_groups.new('CompositorNodeTree')` 再赋值）；`CompositorNodeGlare`(Bloom) 等必须接到 Composite 终端才生效，但该终端节点已不存在 → Compositor Bloom / 色彩分级无法落到最终画面。离线替代 = 程序化渐变天穹球(自发光 ColorRamp，兼背景+环境光) + 场景内 ADD 混合发光壳模拟 Bloom + AgX 色调映射（属色彩管理，不受合成器移除影响）。
16. **`clear_all` 按前缀删对象必须 `nm = o.name` 再 `bpy.data.objects.remove(o, do_unlink=True)`**（M7 实测）：删除后再访问 `o.name` 抛 `ReferenceError: StructRNA of type Object has been removed`，导致循环中断、剩余对象没清掉，留孤儿墙。另：动画帧采样自管 Catmull-Rom + 弧长累加，避免依赖 `spline.evaluate`；`frame_change_pre` 处理器按 `__name__` 去重避免双跑。
17. **建筑外壳 Bldg_*_WY±1/WX±1 是开放墙体盒，无门窗开洞**（M8 实测）：M2/M4 用 box+Boolean 切 ribbon 窗带，但**没有门洞**。人视相机从室内看出会撞 -Y 内墙呈黑带（"看到的不是书架而是墙"）。解决：在 WY-1 用 Boolean Difference 切矩形洞（cube cutter 居中于 wall.location.y，scale `(door_w, 0.8, door_h)`），apply modifier、删 cutter；同时把相机移到 y < 外墙 y（门外）向南看入，门洞自然形成取景框。Boolean 在 MCP headless 链路需 `select_all(DESELECT) → wall.select_set(True) → view_layer.objects.active=wall → modifier_apply`，漏 select 或 active 会 silently fail。因 clear_old 只清 M8_ 前缀、不会还原外壳，同会话内门洞用 `wall["m8_entry"]=True` 做幂等标记。

来源：uhiyama-lab 渲染指南、Blender-Artworks Rendering.md、reelmind EEVEE 摄影级、startingframe 程序化石材、strayspark 材质管线、oldetinkerer 程序化混凝土、blender.tekriss 程序化砖、imeshh EEVEE Next 室内、suzhar Walk Navigation、blender/blender-addons Archimesh。M1 执行实测又验证了第 13/14 条；M6 实测新增第 15 条（5.2 合成器 API 变更）；M7 实测新增第 16 条（clear_all ReferenceError + 动画采样器）；M8 实测新增第 17 条（外壳无门洞 + Boolean headless 三步法）。

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
