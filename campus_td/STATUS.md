# 结构化进度速查 · 高中校园塔防原型

> 抗上下文压缩的"项目大脑"副件。每次推进项目时更新本文件（当前进度 / 待办 / 关键决策及理由 / 上下文摘要）。
> 完整权威内容见 `PLAN.md`；详细流水见 `PROGRESS.md`；**玩法数值见 `DESIGN.md`**。最后更新：2026-09-07 08:13

---

## 一、当前进度（Current Progress）

- **M0 基础与管线**：✅ 已完成（v1）。46m 草地 + 3 段 U 形路径 + 6 栋示意教学楼 + 4 座发光防御塔 + 7 敌人 + 俯视相机；Cycles 64s 渲染 `render_campus_td.png`（930KB）。
- **M1 程序化材质库**：✅ 已完成（10 种程序化 PBR 材质 + 10 预览球 + 渲染预览 `previews/m01_materials.png`）。
- **M2 建筑外壳**：✅ 已完成。教学楼 Bldg_Teach(4F,64×16×15.6m) + 实验楼 Bldg_Lab(5F,48×14×19.5m)，每层 ribbon 窗 + 入口门 Boolean 切出，墙砖/屋顶混凝土 PBR 材质应用；预览 `previews/m02_archimesh.png`（1.55MB）。
- **M3 室内可进入**：✅ 已完成。Bldg_Teach 地面层 Int_Teach_Floor(瓷砖地板)+ Int_Teach_Part(砖隔墙+门洞)+ Int_Teach_Board(黑板)+ 18 桌椅(Furn_Teach_)+ 9 级楼梯 Stair_Teach_ + 临时室内补光；预览 `previews/m03_interior.png`（1.42MB）。
- **M4 其余建筑外壳**：✅ 已完成。行政楼 Bldg_Admin(4F,13×9×15.6m)、宿舍楼 Bldg_Dorm(6F,14×9×23.4m)、体育馆 Bldg_Gym(单带大玻璃,14×12×11.7m)、食堂 Bldg_Canteen(2F,14×10×7.8m)、图书馆 Bldg_Library(4F,15×11×15.6m)；全部置于前区广场 y[-23,5] 避让 Teach/Lab；同步修补 PBR_Brick/PBR_Concrete 缺 Vector 渲染发灰问题；预览 `previews/m04_buildings.png`。
- **M5 场地细化 + 环境光**：✅ 已完成。World 改 solid sky-blue Background；前庭院铺装（暖红砖, 38×11m）+ 校门牌坊（双砖柱 5m + 混凝土额枋 + 暗匾, y=-21）+ 旗杆（金属 10m + 红旗, 0,-18.5）+ 围墙（四向 2.4m 混凝土, 前向留 x[-7,7] 门洞）+ 花坛×4（砖身+土面）+ 树阵×10（木干+绿冠）；预览 `previews/m05_site.png`（鸟瞰 1920×1080, 160 obj）。
- **M6 电影级光照与后期**：✅ 已完成。程序化渐变天穹(替代 solid Background) + 金色时刻 SUN 灯 + AgX 色调映射 + 防御塔辉光壳(ADD 模拟 Bloom) + OID 降噪；白昼/暮色双时段预览 `previews/m06_lighting_day.png` / `previews/m06_lighting_dusk.png`（1920×1080）。注：5.2 合成器无 Composite 输出节点，Compositor Glare(Bloom) 不可用，改用场景内辉光壳。
- **M7 塔防层 refinement**：✅ 已完成（含 M7 收尾·塔→敌锁定光束）。敌人 U 形路径(Catmull-Rom 弧长匀速) + frame_change 动画(7 敌相位错开循环) + 路径发光管(M7_Path) + 四角射程全息穹顶(M7_Range_*, Fresnel 边缘辉光, r=13m) + 地面范围环(M7_Ring_*) + 类型信标(M7_Beacon_*: RAPID青/AOE橙/SLOW紫/BASIC金) + **塔→敌锁定光束(M7_Beam_*, frame_change 连射程内最近敌, ADD 发光)** + 出生点红环(M7_Spawn) + 基地核心(M7_Exit/M7_Core 绿)；白昼 `previews/m07_towerdefense_day.png` + 暮色 `previews/m07_towerdefense_dusk.png`（均 1920×1080）。
- **M8 室内扩展**：✅ 已完成。把 M3 教室样板扩展到 5 栋代表房间——行政楼办公室(办公桌+椅+文件柜+沙发+低隔断)、宿舍楼宿舍(2床+床垫+2衣柜+2书桌+2椅)、体育馆球场(木地板+白球场线+双侧阶梯看台+篮板篮筐)、食堂大厅(取餐台+4人桌+长凳+吊灯)、图书馆阅览室(两侧书架+阅读桌+椅)，每间铺可行走地板(M8_<B>_Floor, 抬离地面 0.14)+AREA 补光(防死黑)；并在**每栋南立面 WY-1 用 Boolean 切真实门洞**(便于 Walk Navigation + 人视镜头看穿)。验证预览：图书馆阅览室人视 `previews/m08_library_interior_day.png` + 体育馆球场人视 `previews/m08_gym_court_day.png`（均 1920×1080, 262 obj）。注：外壳原本无真实 门洞(仅 ribbon 窗带)，M8 新增南向入口。
- **M9 导航导出 + 整合**：✅ 已完成。`build/m09_walkthrough.py`(PREFIX=M9_, 幂等)定义 6 段关键帧相机路径：① SW z=14 无人机俯瞰 → ② 西南下降 → ③ 沿 x=-9 绕 Dorm 西墙北上 → ④ 走廊接近图书馆南立面 → ⑤ 图书馆南门洞(x=5)外看穿 → ⑥ 进入阅览室。位置 BEZIER 缓动，旋转四元数 LINEAR(slerp)。渲染走 EEVEE 输出 PNG 序列(本 Blender 5.2 构建无 FFmpeg 视频写入)→ `assemble_m09.py` 用 imageio-ffmpeg(自带 ffmpeg)合成 MP4。最终交付 `previews/m09_walkthrough.mp4`(1280×720, 120 帧@30fps, 4s, ~4.8MB) + 120 帧 PNG 序列 `previews/m09_frames/m09_####.png`。`blmcp_client.py` 新增 m09 / render_m09 分支。
- **M9 关键决策**：(a) 因校门 x[-7,7] 正对 Dorm(x[-7,7])，任何"穿门进入"都会撞 Dorm 西/南墙，故改用无人机式俯瞰 → 西南侧绕行(x=-9 走廊) → 图书馆南门(有真实 Boolean 门洞)的 6 段路径；(b) 本 Blender 5.2 构建 `image_settings.file_format` 无 FFMPEG 选项(实测枚举仅图像格式)→ 渲 PNG 序列 + 外部 imageio-ffmpeg 合成 MP4；(c) Action.fcurves 在 5.2 已移除，用 `action.layers[].strips[].channelbag.fcurves` 跨版本取关键帧点设插值。
- **M9 校验**：MP4 经 imageio 读取 frames=120 size=(1280,720) fps=30.0；关键帧抽检 m09_0078 显示图书馆南立面+走廊+塔辉；m09_0120 显示阅览室内部(桌+窗)。
- **M5B 场地细节精修**：✅ 已完成（可选 backlog 第 1 项）。① **树冠 box → icosphere 有机树丛**：每棵 1 主球（`subdivisions=3`, 半径 2.5–3.0）+ 2 卫星球（`subdivisions=2`, 半径 1.6–2.2, 偏移 ±1m），确定性 seed 保证幂等可复现，材质复用 `PBR_Leaf(0.18,0.42,0.16)`——M5 的 10 棵方块冠升级为有机圆冠。② **围墙压顶 (coping)**：`M5_WallBack/Left/Right/FrontL/FrontR` 各加 `M5B_Coping_*`（h=0.35, 宽出墙 0.25, 混凝土收口），墙顶有了"完成感"。③ **校门匾精修**：原 `M5_GatePlaque` 实际嵌在门枋体积内不可见（隐 bug，已记入避坑 #19），新建 `M5B_PlaquePanel`（青铜 metallic=1.0 rough=0.45, 4.4×0.12×0.85, PBR_Bronze）+ `M5B_PlaqueFrame`（深色石框 5.2×0.16×1.05, PBR_Concrete_Dark），置于门枋前脸 y<-20.3 处确保可见——匾文(校名)待 CJK 字体就位后深化。脚本 `campus_td/build/m05b_refine.py`（PREFIX=`M5B_`, 幂等）；scene 263→290 obj。预览 `previews/m05b_refine.png`（1920×1080 鸟瞰，圆冠+压顶+嵌板清晰可读）。`blmcp_client.py` 新增 `m05_refine` / `render_m05_refine` 两个 action。
- **M8B 室内补光精修**：✅ 已完成（可选 backlog 第 2 项，视觉杠杆最高）。把 M8 五间代表房间的 AREA 补光从 `energy=160` 提到 **240（普通房间）/ 300（体育馆，体积最大）**，并把矩形灯尺寸从固定 5m 按房间内净尺寸放大到 ~0.7×(内净宽,内净深)（覆盖更大地面比例，消除暗角与死黑）。脚本 `campus_td/build/m08b_light.py`（幂等 in-place 重设既有 `M8_*` AREA 灯参数，不重建几何）。验证预览：图书馆阅览室人视 `previews/m08b_library_interior_day.png` + 体育馆球场人视 `previews/m08b_gym_court_day.png`（均 1920×1080, 290 obj）。`blmcp_client.py` 新增 `m08b` / `render_m08b` / `render_m08b_gym` 三个 action（注意：render 组合里 `M08B` 必须在 `build_interiors()` 之后执行，否则补光会被重建覆盖回 160）。
- **M8C 上层重复房间扩展**：✅ 已完成（可选 backlog 最高优先级）。消灭"空壳楼"——M8 只建了每栋地面层，从 ribbon 窗看进去是"一层家具 + 一大片空"，剖面关系不成立。本步补真实楼层结构：① **楼板 (slab)**：每上层一块混凝土板（厚 0.25，顶面落在 `z = f×3.9` 即该层地面标高），沿 -x 侧留 **1.45m 楼梯井槽**（用"整块板右移 WELL/2、宽度减 WELL"实现，**不走 Boolean**，避 headless 失败）；② **上层简化家具**：按 `office/dorm/dining/reading` 四类型各放一组（原型级密度）；③ **楼梯体量 (stair)**：单 box 绕 X 轴旋转 `atan2(3.9, 3.2)` = **0.8837 rad** 斜置，从 `(f-1)` 层升到 `f` 层，读得出"跑梯"。覆盖 **Admin 4F / Dorm 6F / Canteen 2F / Library 4F**（**Gym 是 11.7m 通高单一体量球场，不加楼板**——加了反而错）。新增 **71 obj**（12 楼板 + 47 家具 + 12 楼梯），scene **290 → 361**。脚本 `campus_td/build/m08c_upper.py`（PREFIX=`M8C_`, 幂等）。预览 `previews/m08c_upper_floors.png`（1920×1080 西南中景 cam(-34,-46,20)→(-2,-14,10)，2.15MB）。`blmcp_client.py` 新增 `m08c` / `render_m08c`。
- **M8D 上层房间补光**：✅ 已完成（可选 backlog 最高优先级，M8C 的配套收尾）。M8C 建好 12 个上层后上层仍无补光（M8B 只调了地面层 5 盏 AREA），从 ribbon 窗看进去只有"结构剪影"，读不出材质与家具。本步给**每个上层补一盏 AREA 灯**：`energy=200`（低于地面层 240——上层四周均有 ribbon 窗、天然光进光量更大，且从室外是"透过玻璃"观察，过高会在玻璃上形成过曝亮块）；矩形灯尺寸沿用 M8B 口径 **0.7×(内净宽, 内净深)**；高度 = 该层地面 **+3.4m**（与 M8 地面层一致，距本层顶板 0.5m）；平面位于**楼板中心 `cx + WELL/2`**（避开 -x 侧 1.45m 楼梯井槽）。覆盖 Admin 3 / Dorm 5 / Canteen 1 / Library 3 共 **12 盏**。脚本 `campus_td/build/m08d_upperlight.py`（PREFIX=`M8D_`，幂等，只加灯不动几何）。scene **361 → 373**，场景灯光 **9 → 21**。预览 `previews/m08d_upper_light.png`（与 M8C 同机位 `cam(-34,-46,20)→(-2,-14,10)` 便于前后对比；因灯光增至 21 盏，降采样 64s + 1600×900 控时，1.54MB）。`blmcp_client.py` 新增 `m08d` / `render_m08d`。
- **M8E 书架"书条"精修**：✅ 已完成（可选 backlog 第 5 项）。M8 的 `M8_Library_Books_%d_%d` 是**一整块单色薄板**（0.9×0.06×1.8，纯红棕 `PBR_Books(0.55,0.20,0.16)`），从人视看就是一块平板，完全读不出"书"——书架像空木格子。本步删掉那 6 块平板，换成**多色书条**：6 个书架 × 4 层 × 3 本 = **72 本**，每本 0.26–0.30(宽) × 0.20(深) × 0.30(高)，摆在书架**前脸 -y 侧**（书条 y 中心 = 书架 y − 0.05），正对图书馆人视方向。配色用 **6 色确定性调色板**（暗红/藏青/橄榄/墨绿/米黄/紫褐），索引 `(书架序号*5 + 层*3 + 本*2) % 6`，跨运行可复现且相邻不同色。层高 0.45、最底层离地 0.19、最高层顶 1.84 < 书架顶 2.14，不穿帮。脚本 `campus_td/build/m08e_books.py`（PREFIX=`M8E_`，幂等）。scene **373 → 439**（−6 旧平板 + 72 书条）。预览 `previews/m08e_library_books.png`（1600×900, Cycles CPU 96s, 439 obj, 1.29MB）。**机位发现（重要）**：M8/M8B 的图书馆机位 `cam(5,-10,1.6)→(5,-3,1.2)` 视锥半宽仅约 2.5m，而书架在 **x=−4.3 / 8.3 均在画面外**——之前几轮"看不到书架"不是渲染问题，是机位根本没框到；本轮改专用侧向机位 `cam(5,-6,1.5)→(8.3,-3.5,1.1)` + 35mm 镜头才拍到书条。`blmcp_client.py` 新增 `m08e` / `render_m08e`。
- **同步**：乐享个人知识库 8/9 文本页已入库（diag 脚本因 WAF 未入）；GitHub 集成经实测为**只读**（私有仓 404、转 public 后 403 写被拒），无法 push——以 Lexiang 为工作镜像，本地文件为权威源。

- **M10 玩法层（数值建模 + 平衡验证）**：✅ 已完成。此前 M0–M9 只做了"场景"，塔防没有数值——塔/敌人/波次全靠拍脑袋。本步写了**纯 Python 平衡模拟器** `campus_td/build/m10_balance.py`（不依赖 Blender，秒级迭代），把几何探针实测数据喂进去：路径 102m / 四塔覆盖 13-26-26-13m / 联合覆盖 76.5% / 盲区 `[13,25]` 与 `[77,89]`。**核心设计发现**：拐角塔覆盖 26m = 直腿塔 2 倍，但两拐角已被固定塔占满 → 玩家塔先天吃亏；且建满后覆盖达 100%，此后**减速是唯一全局杠杆**。据此重做 SLOW：从"只对目标 ±6m 的单体 debuff"改为**覆盖区全体减速力场 + 乘算叠加（上限 75%）**。引入**双策略对照**（熟练 vs 新手）验证平衡带：熟练玩家 **16/20 生命通关（漏 2）**，新手**第 9 波崩盘**，策略差 16 点生命 → 证明"建什么/升什么"是真决策而非假选择。难度曲线：1–6 波零漏怪 → **第 7 波「质量压力」首次破防** → 9–10 波靠投资追平，BOSS 被击杀。数值单一数据源导出 `campus_td/build/m10_config.json`（`--export`）。设计文档 `campus_td/DESIGN.md`（核心循环 / 系统关联 / 状态机 / 波次表 / 经济模型 / 心流曲线 / 痛点与优化建议）。
- **M10B 建塔位落地**：✅ 已完成。`campus_td/build/m10b_slots.py`（PREFIX=`M10B_`，幂等）把设计里的 4 个建塔位建进场景：建造台 + 内圈环 + **16 段射程虚线环 (r=13)** + 悬浮四棱锥标记（青绿 = 空位可建）。设计坐标在**路径中心线**上（1D 弧长模型），但塔不能立在敌人走的路中间 → 统一沿法向**内偏 4.5m** 到 U 形庭院侧；半径 13m 下每端仅损约 0.8m 覆盖。探针验证：实际覆盖 A`[6.8,31.2]` / B`[70.8,95.2]` / C`[38.8,63.2]` / D`[78.8,102.0]`，与设计值偏差 ≤2.2m；**8 塔联合覆盖率 100.0%**（实测略优于设计值 → 仿真偏保守，真实游玩稍轻松）。scene **439 → 515**。客户端新增 `m10b`。

- **【重要修正】M10 数值重新标定**：✅ 已完成。上面那条 M10 记录的 `HP_SCALE 0.20 / 熟练 16-20` 是**在错误步长下标定的**，已作废，以本条为准。根因：平衡模拟器原本用 `DT=0.1`，而 RAPID 射速 3.0/s（cd=0.333s）在 0.1 步长下要 4 步才够开火，**有效射速掉到 2.5 → 凭空 -17% DPS**。实测 DT=0.05 与 DT=0.02 结果完全一致（已收敛），DT=0.1 的"熟练 16/20 漏 2"纯属量化误差。修正后重新扫描标定：**HP_SCALE 0.20 → 0.23**（0.20 在收敛步长下熟练 20/20 零漏怪太易；0.25 起掉到 10/20 偏难）。新平衡带：熟练 **16/20 漏 2**✔，新手 **第 9 波崩 漏 14**✔。
- **M10C WebGL2 可玩原型**：✅ 已完成（原计划的"Blender 里做 HUD"被否决——Blender 是建模工具不是游戏引擎，在里面做 HUD 只能看不能玩）。产出 `campus_td/web/index.html`（单文件，WebGL2）：
  - **GLSL 渲染**：SDF 球体追踪（地面 + 塔柱）+ **解析 ray-AABB 把建筑当玻璃体**（本关路径本身就穿过建筑 footprint，不透明就全被挡住）+ 屏幕空间敌人光点（JS 投影，比着色器里做 SDF 求交便宜得多）+ 建筑足迹 AO / 太阳投影 cookie / 射程虚线环 / 路径流动光条 / 暗角 / ACES / 胶片颗粒。
  - **JS 跑同一套数值**：与 `m10_balance.py` 逐行对应的战斗·经济·波次逻辑，含减速力场乘算叠加、AOE 溅射、ROI 升级。
  - **可交互**：拖拽旋转 / 滚轮缩放 / 选塔型点空位建造 / 点已有塔升级 / 空格提前开波 / R 重开；HUD 显示金币·生命·波次·倒计时·本波构成·事件日志。
  - **单一数据源**：`campus_td/web/config.js` 由 `campus_td/build/m10c_webcfg.py` 从 `m10_config.json` + Blender 建筑轮廓生成。
  - **验证**：headless Chromium + SwiftShader 真编译无报错；截图像素统计确认画面有内容（中心区 100% 非黑、std 40）；**`?selftest=1` 无渲染跑完 10 波得 `lives=16 leaks=2`，与 Python 收敛值完全一致，连漏怪分布（第 7、8 波各 1）都对得上**——两份独立实现互相印证。
  - 预览 `campus_td/previews/m10c_webgl_prototype.png`。
- **M11 总平重排**（修复上一条"场景缺陷"）：✅ 已完成。场地 46m → **96m**，7 栋楼按北/南/东/西四带重排到 U 形路径走廊之外；**路径/塔位/波次一个坐标不改**，故 M10 数值与 M10C 原型继续有效（浏览器自测仍 `lives=16 leaks=2`）。校验：无超界、无互穿、路径最小净距由 **0.0m → 7.5m**。scene 515 → 584。预览 `previews/m11_masterplan.png`。
- **M12 机位自适应 + 上层补光量化校验**：✅ 已完成。① 修 M11 连带问题：M8/M8B/M8C/M8D/M8E 的渲染相机全按旧坐标硬编码，场地重排后全部指向空地 → 改为从目标建筑**当前 AABB 动态推算**机位。② 上层补光 energy=200 结案：p50 73.7 落在室内合理带 (55,150)、过曝 0%、死黑 0%。
- **M13 地面层补光标定**：✅ 已完成，**结论是"不改"**。扫描证明提灯无效：补光 240→460(+92%) p50 只 +8% 且 p99 恒定；环境光需 ~5 倍才够且会波及全场景。根因是亮度由窗光主导、天花板 AREA 灯照不到垂直面（cosine 定律）。维持 `M8_Library` energy=240 / `World` strength=0.45。
- **M14 校门匾文**（补齐 M5B 遗留项）：✅ 已完成。金色立体字「晨光中学」+ 四周石框 + 特写机位。字体经探针实测定为 **SimHei**（VF 与 Deng 均不可用）；字排布按目标字高反算、换校名自动适配。量化收敛：匾面对比 **12.6:1**、字 avgRGB (174,149,89)、R/B 1.96；字宽实测 783px vs 投影估算 782px。预览 `previews/m14_plaque.png`。
- **M15 楼梯真实踏步（Array 修改器）**：✅ 已完成（中优先 backlog「楼梯改 Array 真实踏步」）。把 M8C 的 12 段 50.6° 示意斜板楼梯替换为带 Array 修改器的真实踏步（h=0.177 / d=0.28 / 跑长 6.16m / 坡度 32.3° / 22 级），含 Slope 斜面体量 + 24 段扶手 Rail + 专用机位 M15_Cam。约定（顺序铁律）：① 坐标全从场景旧楼梯读、不硬编码；② 命名避开 `Stair_`/`Int_`（否则被 M11 `owner()` 误挪），改用 `Slope`/`Steps`/`Rail`；③ M15 **必须排在 M11 之后**跑。脚本 `campus_td/build/m15_stairs.py`（PREFIX=`M15_`，幂等）。几何探针：`M15_*` 49 个（12 Slope+12 Steps+24 Rail+1 Cam），12 段 `_Steps` 的 Array `count` 全 = 22，旧 `M8C_*_Stair_*` 0 个（斜板全清）。scene 584 → **629**。预览 `previews/m15_stairs.png`。
- **M16 围墙垛口**：✅ 已完成（低优先 backlog「围墙垛口」）。给 M11 重建后的 5 段 perimeter 围墙加女儿墙/城垛质感——沿墙顶中线排一列 merlon（交替方块+空隙，0.55×0.47×0.55m、中心间距 1.25m、坐于 coping 顶面），坐标全部从 `M11_Wall*` AABB 动态读（墙再挪也贴合，与 M12/M15 同一思路）。前墙校门洞缺口（x∈[-8,8]）留 0.3m 余量跳过防悬空。脚本 `campus_td/build/m16_crenellations.py`（PREFIX=`M16_`，幂等）。几何探针：295 个 merlon（Back/Left/Right 各 77、FrontL/FrontR 各 32）+ `M16_Cam`（SE 角 (78,-78,9) 35mm）；全量 `render_m16` 出 `previews/m16_crenellations.png`（1600×900, Cycles CPU 128sp）。scene 629 → **925**。
- **（已解决）M11 前「Teach/Lab 超界」缺陷**：原 `Bldg_Teach`(64m)/`Bldg_Lab`(48m) 飘在 46m 场地外的问题，已随 **M11 总平重排**（场地扩到 96m、7 栋楼重排到 U 形路径之外）消除——两栋楼现均在场地内、路径最小净距 7.5m。此条归档，不再挂起。

## 二、未完成待办（Open Todos）

1. **M7 已交付（塔防层 + 收尾·锁定光束）**：路径动画/射程穹顶/类型信标/出生·基地/塔→敌锁定光束 已建（白昼 + 暮色预览）。剩余收尾：① 金钱/血量 HUD（屏幕空间，建议 M9 视频化叠加）；② 波次编辑器（spawn 节奏/敌人波数）。
2. **M8 室内扩展 ✅ + M8B 地面层补光 ✅ + M8C 上层结构 ✅ + M8D 上层补光 ✅ + M8E 多色书条 ✅ + M15 楼梯 Array ✅**：5 栋代表房间已建 + 每栋南门洞已切 + 地面层补光 160→240/300 + 上层楼板/家具/楼梯已建(+71) + 12 个上层各一盏 AREA 灯(+12) + 书架换成 72 本多色书条(+72−6) + 楼梯改 Array 真实踏步(12 段)。scene 629 / 灯光 21（M16 +295 merlon → 925）。剩余：目视确认上层亮度（过曝→160，仍暗→240）—— 已由 M8D 量化结案（p50 73.7/过曝 0/死黑 0，200 合适），M13 判定地面层维持原值不改。
4. **M9 导航导出 + 整合 ✅**：漫游相机视频 `previews/m09_walkthrough.mp4`（6 航点无人机俯瞰 → 西南下降 → 绕 Dorm 西墙 → 图书馆南门洞 → 阅览室，120 帧@30fps，4s）已完成；Godot/Unity 导出说明（M9 可选收尾）仍挂起。
5. **M5 细节精修**：树冠 box → icosphere 提升拟真；~~校门匾文~~（**M14 已补齐**：金色立体字「晨光中学」+ 石框，字体/材质均量化定稿）；~~围墙垛口/压顶~~（**M16 已补齐**：merlon 城垛 + coping 压顶，坐标从 `M11_Wall*` AABB 动态读）。
6. 把 `m04_fix_materials.py` 的 Texture Coordinate/Mapping 修补并入 `m01_materials.py`，使 PBR_Brick/PBR_Concrete 默认带 Vector。
7. 构建自动化现每 1 小时触发（最频繁且稳定的粒度，带防重叠锁）；每日 21:30 同步 / 周日 10:00 研究 持续运行。
8. GitHub 镜像已打通（本地 git + PAT，`D:/AI/campus-td-git` 克隆内嵌 PAT，首推成功 commit `0ffc725`），同步自动化走本地 git 推送；仓库 public 可按需转 private。
9. 补传 `diag_blender_mcp.py` 至乐享（绕 WAF，低优）。

## 三、关键决策及理由（Key Decisions & Rationale）

- **决策：项目升级为"完整可进入高中校园原型"而非仅塔防地图。**
  理由：用户要电影级真实质感、每个房间可进；塔防层作为叠加系统保留。
- **决策：材质全部程序化节点，不下载外部贴图。**
  理由：国内 CDN 慢、版权风险；程序化可控且符合质量基准（albedo 区间/变化/Bump/使用痕迹）。
- **决策：Blender MCP 三层链路（mcporter→blmcp→addon@9876），大段 bpy 写文件再 `exec(compile(open(...)))`。**
  理由：避 shell 多行缩进累积与引号转义；前缀隔离 + 幂等，互不破坏场景。
- **决策：保持最少自动化（每日构建 + 每周研究 + 每日同步 = 3 个），不按里程碑各建。**
  理由：用户明确的自动化数量纪律；执行优先于自动化定义。
- **决策：同步排除 `.workbuddy/memory` 个人记忆；二进制 png/zip 留本地。**
  理由：记忆属个人、不应入项目仓；文本 API 无法传二进制。
- **决策：冲突保护远程——本地永不覆盖远程已有内容。**
  理由：用户同步指令明确要求；GitHub 走真实 commit 保留历史，乐享为条目修订版（非 git 式）。
- **决策：修复 `blender-mcp-launch.sh` 中陈旧的 `blender-4.4.3` 路径为活动实例 `D:\建模\blender\blender.exe`。**
  理由：原路径与 5.2.1 活动实例不符，避免后续 MCP 启动找错 Blender。

- **决策：高中校园建筑语言 = 现代公立风（暖红砖基座 2 层 + 清水混凝土上部体量 + 每层 ribbon 玻璃带 + 玻璃入口门厅 + 平屋顶），层高 3.9m。**
  理由：贴合国内高中真实观感、电影级温暖基调；与 M1 材质库（砖/混凝土/玻璃）直接对应；概念效果图已出 `previews/Cinematic_architectural_concep_2026-09-06T08-01-01.png` 锁定方向。
- **决策：MCP 走 Direct TCP Socket（addon 9876），不依赖 blmcp/mcporter 链路。**
  理由：当前交互会话下 mcporter 不一定可用；直接读 addon 源码确认 `{"type":"execute","code":...,"strict_json":<bool>}\0` 协议后用受管 Python 写 `campus_td/tools/blmcp_client.py` 直连，最稳。已验证：objects 探针 + m02 执行 + 渲染均通。`strict_json` 必须是 bool（addon 会校验）。
- **决策：M2 改用"四周边墙 box + Boolean 切 ribbon 窗/门"而非 Archimesh op。**
  理由：Archimesh 需在 3D 视口上下文调（房间放置/门墙关联），MCP 链路调 bpy.ops 易 poll-fail；本环境也未装 archimesh（`ModuleNotFoundError`）。手动 box + Boolean 切洞在 headless 链路最稳，且直接控制层高/窗台/门高真实尺度。Archimesh 留给 M3 室内（房间/楼梯/家具）。
- **决策：曝光问题先扫描再调灯，不凭分位数直接改参数；本次扫描结论是"维持原值不改"。**
  理由：M12 据 p50=40.5 建议提 `M8_Library` 240→320，M13 扫描证明该建议无效——
  补光 energy 240→460（+92%）p50 只 40.5→43.7（**+8%**）且 p99 恒定 224.1；环境光 0.45→1.0/2.2 才 +17%/+32%，
  要到 p50=55 需约 5 倍且会波及全场景室外。根因是画面亮度由**窗光**主导，天花板 AREA 灯照不到
  书架/墙的垂直面（cosine 定律）。现状过曝 0%、死黑 0.93%，低 p50 是**内容偏暗**（深色书架占画面）。
  → 维持 `M8_Library` energy=240、`World` strength=0.45；判读器加护栏 `crush<2% 且 p90>100` → 判"内容偏暗，不建议提灯"。
  **复用要点：分位数只能回答"暗不暗"，扫描才能回答"改哪个旋钮有用、效率多高"。**
- **决策（M14 匾文）：CJK 字体必须「量实际字形尺寸」再选，绝不能只看"文件在不在"；匾额金字的饱和度靠压 base 亮度，不是调 metal。**
  理由：原候选链把 `NotoSerifSC-VF` 放首选、`Deng.ttf` 放兜底，探针实测**两个都是坏的** —— VF 在 Blender 里被缩到 0.32 倍且取最细(ExtraLight/Thin)实例，`Deng.ttf` glyph 解析为 0.0/0.0（空），`simsunb.ttf` 在 Windows 上其实是 **SimSun-ExtB** 缺常用汉字（4 字只有 1.91 宽）。不探针必然出空匾或细如发丝的匾。
  故 `pick_font()` 内建尺寸自检（单位字高 ≥0.55 且每字宽 ≥0.55），不合格自动换下一个；最终采用 **SimHei**（w=3.82 h=0.92，最饱满）。候选链 = 黑体 → 等线B → 雅黑B → 宋体。
  材质同理：金字的 metal 0.60→0.40 对色相几乎无效（R/B 1.45→1.47），因为字 L≈185 已进 **AgX 高光压缩区**、颜色被强制拉向白；改成压低 base 亮度把字拉回 L≈150，R/B 才升到 1.96。匾底也从青铜换深色哑光 —— 金属在阳光下反光强，会把"黑底金字"的对比吃光（实测对比 1.35:1 → 12.6:1）。
  **复用要点：跨版本/跨机器引入外部资源（字体、贴图）时，先跑一次性探针量实际产出尺寸，别信"文件存在"。**
- **决策：M8/M8B/M8C/M8D/M8E 的渲染机位不再硬编码坐标，改由目标建筑当前 AABB 动态推算（`m12_uppercheck.py`）。**
  理由：M11 总平重排把 7 栋楼整体挪走后，这批按旧坐标写死的相机全部指向空地，所有室内预览一次性失效。机位算式 = 取 `Bldg_<B>_*` 包围盒 → 中心 cx/cy、南墙 `mn[1]`、进深 `depth` → 站房间内南侧 `south_y+1.8`、视高 `层地面+1.55`，朝北看向 `south_y+depth*0.85`，20mm 广角保证整个进深入画。建筑再挪也不失效。
- **决策：灯光"合不合适"用亮度直方图分位数判定，不靠目视。**
  理由：上层补光 energy=200 一直是 backlog 里唯一无法客观结案的高优先级项。做法 = 同一栋楼、同一进深、同一镜头，只差楼层做对照（上层 3F E=200 vs 地面 1F E=240 基准），比 p10/p50/p75/p90/p99 + 过曝(>248) + 死黑(<8) 占比。判读带：室内 p50 ∈ (55,150)、过曝 ≤3%、死黑 ≤6%。
  **护栏：基准层自身不在合理带时，"与基准一致"这条相对判据必须降级为参考**，否则会把"上层比偏暗基准亮 82%"误判成"200 偏高，建议 110"。
  **对照实验前提：两张机位必须同一相对位置** —— 初版地面层站门外、上层站房间内，门框背光造成 15% 死黑假象。
  结果：上层 p50 73.7 / 过曝 0% / 死黑 0% → **200 合适，M8D 结案**；顺带查出基准层 1F 自身 p50 40.5（低于合理带 26%）、p99 224 → 窗光刺眼+室内欠曝，列为新 backlog。
- **决策：M11 总平重排 = 场地 46m→96m + 7 栋楼重排到 U 形路径之外，路径/塔位/波次一个坐标都不改。**
  理由：实测 Ground 仅 46×46（2116 m²），而 7 栋楼占地 2682 m²（覆盖率 127%），且 Teach 65m / Lab 49m 各有 20~28m 探出场地、两者互穿 21×15m；同时 U 形路径穿 Admin/Dorm/Gym/Teach/Lab 五栋 footprint。缩楼无解（46m 场地扣除路径走廊后只剩两条 6m 窄带），故扩容。路径几何保持 102m 三段 U 形不变，使 M10 平衡数值、M10B 建塔位、M10C WebGL 原型全部继续有效（浏览器自测仍 `lives=16 leaks=2`，与 Python 收敛值一致）。楼群按"北带/南带/东带/西带"重排，四周留 2m 退线，实测路径最小净距由 0.0m 提升到 7.5m，7 栋两两无重叠。
- **决策：M11 建筑归属用「前缀优先级 owner()」，绝不用「子串匹配 + 按楼顺序逐个 apply」。**
  理由：v1 用子串匹配时，Teach 规则含 `Stair_` 会把 `M8C_Admin_Stair_1` / `M8C_Dorm_Stair_2` 一起吃掉，等轮到 Admin/Dorm 规则时这些楼梯又吃第二份 delta，导致 7 栋楼 AABB 被撑大 3~4 倍、互相穿插（事故）。修复：`owner()` 按 `Bldg_X_` > `M8C_X_` > `M8D_X_` > `M8_X_` > `Furn_X_` 优先级判定，一个对象只属于一栋楼、只吃一份 delta；delta 由「当前外壳 AABB 中心 → 目标中心」算出，故重复运行收敛（delta→0）。已用一次性补偿脚本 `tools/_m11_fixup.py` 按 `correction = should − received` 精确撤销污染（外壳误差 ≤5mm）。
- **决策：M4 五栋楼全部置于前区广场 y[-23,5]，不外扩场地。**
  理由：复用 M2 真实尺度（13–15m 宽），后方 Teach/Lab 已占 y[5.5,22]；前区是唯一开放带（46×28m）。先在纸上算 x/y 区间重叠确认无碰撞再写入 loc，保证体育馆/宿舍楼大尺度与行政楼/图书馆小尺度能塞下。M4 后续场地细化（M5）才扩铺装与围墙。
- **决策：M4 体育馆用 `single_band` 模式（3 层高 + 仅首层一道 8m 大玻璃带）。**
  理由：体育馆是单大空间（不像教学楼分层），floors=1 会让 8m 窗带切穿 3.9m 矮墙；floors=3 + 顶部收口更真实。参数化复用：M5 起其他大空间场所（食堂大堂、图书馆中庭）可同款。
- **决策：材质节点必须显式连 Vector 输入。**
  理由：M4 渲染发现 PBR_Brick 没连 Vector → 默认采样 (0,0,0) 落在 mortar(0.22) 上 → 整面发灰；M1 漏了 Texture Coordinate 节点。`m04_fix_materials.py` 补 Generated→Mapping→Texture.Vector，并把修补并入 m01 列入待办，避免后续新材料复发。
- **决策：M5 环境光先用 solid sky-blue Background 而非 Sky Texture / HDRI。**
  理由：Blender 5.x Sky Texture 渲出来偏灰白（试过 HOSEK_WILKIE + PREETHAM 都灰），NISHITA 已移除；离线无 HDRI 文件可下。solid Background(0.58,0.78,0.92) 保证可见蓝天 + 简化链路；M6 升级 HDRI 写真实天光与太阳方向。
- **决策：M5 树冠用 box 占位而非 icosphere。**
  理由：M5 一遍跑通为目标，box canopy 拟真度低但已在 M5 备注列为精修项；M6 升级时同步换 icosphere + 叶片 PBR。
- **决策：M6 光照离线化、不用 HDRI/Compositor。**
  理由：5.x 无内置 HDRI、Sky Texture 渲灰（NISHITA 已移除），且 **5.2 合成器已移除 CompositorNodeComposite 输出节点** → Compositor Glare(Bloom)/色彩分级链路无法落到最终画面。改用：① 程序化渐变天穹球(自发光 ColorRamp) 当环境光+背景；② 金色时刻 SUN 灯主光+阴影；③ AgX 色调映射；④ 场景内 ADD 叠加辉光壳模拟 Bloom（绕开合成器）。多时段 = 改 SUN 方向/色温 + 天穹 ColorRamp 实现白昼/暮色。
- **决策：M8 在每栋南立面 WY-1 用 Boolean 切真实门洞，相机置于门外看入。**
  理由：M2/M4 外壳是四边墙+屋顶的开放盒(仅 ribbon 窗带)，原本无门洞；若相机从室内向南看(传统人视)，会撞到 -Y 内墙呈黑带。把相机移到 -Y 墙外(y < 外墙 y)向南看 + 在 WY-1 切矩形门洞(布尔 Difference 切开 + apply + 删 cutter)，即可透过门洞看到内部家具+远端窗光。同时为 M9 Walk Navigation 提供了真实入口。Library 门洞故意偏右(x=5)且移除中柱书架，便于沿右书架通道看入。M8 清旧不清壳(clear_old 只删 M8_ 前缀)，所以门洞在同一会话内用 custom prop `m8_entry` 做幂等标记，避免重复 Boolean。

## 四、上下文摘要（Context Recap）

- **用户**：Yuqi（初中生），做校园塔防游戏原型；要求决策自主化（不再给需用户决策的选项/清单）、主动维护结构化进度提醒、充分利用 WorkBuddy 项目功能（tdrive/项目消息/待办）提升协作。
- **环境**：Windows + RTX 5060；Blender 5.2.1（D 盘活动实例）；Blender MCP 端口 9876 存活（PID 10132）。
- **已连通外部**：乐享知识库（个人库 `9dd6e66e…`）、GitHub MCP（账号 wyq1683）。
- **避坑要点**：EEVEE Next 无 Bloom→Compositor Glare；Archimesh 官方内置（本机无）；Walk Navigation 只碰水平面、垂直墙穿模→室内须铺地板；Principled 按 `type==BSDF_PRINCIPLED` 找；cone 用 `radius1/radius2`；Boolean 切洞删 cutter 前先存 `nm = o.name`（删后 StructRNA ReferenceError）；`clear_all` 用前缀删避免失败留孤儿墙；**换网格时 `obj.data = new.data` 只搬网格、不搬 scale** —— builder 给临时物体设的非 1 scale 必须先烘进顶点，否则外形退化；**`obj.parent = p` 后要显式 `obj.matrix_parent_inverse = Matrix()`**，否则子物体按"保留世界坐标"处理、会被留在世界原点而不跟随父物体（M10D 血条/尖刺踩过）；**批量移动建筑时归属判定必须用"前缀优先级 owner()"**，用子串匹配会让 `M8C_X_Stair` 这类名字被多条规则命中、吃到多份 delta（M11 v1 事故）。
- **版本史边界**：GitHub 走真实 git commit（自建仓首推送起）；乐享为条目修订版，非 git 式历史——如实标注。

## 五、恢复指引（Resume Guide）

若上下文被压缩：先读 `PLAN.md`（权威）→ `STATUS.md`（本文件）→ `PROGRESS.md`（流水）；**M0–M16 全路线图 + M5B + M8B/C/D/E + M10B/C/D + M11–M16 均完成**（scene **925** obj）。下一轮候选 = ① PBR_Brick/PBR_Concrete Vector 修补并入 `m01_materials.py` 防复发；② M7 HUD（金钱/血量）+ 波次编辑器；③ M9 Godot/Unity 导出说明（glTF + 碰撞体 + 导航网格）；④ Cycles GPU OptiX 终帧画质升级；⑤ 更高质量 Cycles 静帧/视频；⑥ 课桌/食堂「碎化」道具。⚠ **回归铁律**：任何重跑 `M06→…→M11` 之后的链，都必须保证 `m08`/`m08d`/`m08e` 从场景读 `Bldg_*` 当前坐标（`bldg_center()`），不能硬编码 `BUILDINGS[...]["center"]`——M11 后室内坐标脱节 regression 已修（见 MEMORY.md 铁律）。Blender 离线时改做研究并标"等待 Blender 在线"。