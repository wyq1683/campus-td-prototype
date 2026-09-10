# 研究笔记 · 教程与避坑（GitHub / Web）

> 自动任务每周追加；人工也可补充。每条带日期 + 来源链接 + 可落地要点。

---

## 2026-09-10 13:22 M69 离线加固（相机创建改用纯 data API）

> 背景：Blender 仍离线（`:9876` 无 LISTENING、无 blender 进程），M69 脚本虽就绪但**从未成功实跑**（前两次均遇 Blender 中途离线/崩溃）。本轮离线分支不重复写脚本，改为对 `build/m69_flag_platform.py` 做**实跑前静态加固**，降低下次在线首次执行的失败率。

- **唯一一处 operator 调用 `bpy.ops.object.camera_add` 已改为纯 data API**：
  ```python
  cam_data = bpy.data.cameras.new(PREFIX + "Cam")
  cam = bpy.data.objects.new(PREFIX + "Cam", cam_data)
  bpy.context.scene.collection.objects.link(cam)
  ```
  理由：headless MCP exec 里 `bpy.ops.*` 依赖上下文/活动对象，偶发 poll fail；data API 零依赖、最稳。改后整脚本**完全没有 operator**，与 PLAN §8 pitfall #2「MCP exec 内不要调 mode_set」精神一致（其它 `bpy.ops` 早已规避）。
- **「若 Camera 不存在则创建」自满足**：M69_Cam 被 `clear_old(PREFIX)` 清掉后由本段重建，无需判断存在性。
- 其余部分经复核已稳：全 `bmesh.ops` 直建（含旗杆 `create_cone` 真圆柱）、`clear_old` 先 `nm=o.name` 再 remove（pitfall #16）、材质优先复用 `PBR_Concrete`/`PBR_Metal`（`make_pbr` 按名复用/重建，幂等）、`collision_check()` 模块级自检（>70m 假大盒跳过，不静默穿模）。
- 四件套（build / render / 两个 run_*）`python -m py_compile` 全通过。
- **下一步**：等 Blender 上线后实跑 `tools/run_m69_build.py` → `tools/run_m69_render.py`，据像素统计（aerial 无过曝、hero 台基/藏青校旗/金顶清晰）确认后回写 PLAN.md §7 + PROGRESS 顶部。旗台落主旗杆 (-3,0) 仍需人工先 relocate M46 自行车棚释放净空（破坏性变更，自动化不动）。

## 2026-09-10 M69 升旗台（Flag-Raising Platform）· 技术研究与避坑

> 状态：本里程碑脚本（`build/m69_flag_platform.py` + `m69_render.py` + `tools/run_m69_*.py`）已写完，但本运行 Blender 中途退出（进程消失、:9876 不再监听），转入离线分支等待下次在线时实跑。以下是可落地要点，供下次直接复用。

### 1. 几何构建（bmesh 直建，零 mode_set）
- 台基 / 踏步 / 讲台 / 旗杆 / 校旗全部用 `bmesh` 单位 cube（`bmesh.ops.create_cube`）经 4×4 仿射矩阵缩放平移得到；物体 `scale` 保持 (1,1,1)，避免 M10D 那种"scale 丢失导致网格退化"的坑。
- 旗杆用细长 box 近似圆柱（`POLE_R*2 × POLE_R*2 × POLE_H`），省去 `create_cone` 法线朝向处理；顶端球冠用 `bmesh.ops.create_icosphere(radius, subdivisions=2)`。
- 校旗用薄 box（0.04 厚）挂在杆顶 +X 侧；藏青色 + 弱 `Emission Strength 0.10` 保证阴面可读（沿用 M44/M49/M52/M54 的 CJK/标识"阴影面可读"思路，但本旗不用字体，纯色即可）。

### 2. 选址铁律（本里程碑核心教训）
- 校园主旗杆 `M11_FlagPole(-3,0)` 被 M46 自行车棚包围盒（x∈[-6.2,6.2] y∈[-16.05,1.8]）压住 —— 这是 M46 的已知选址 bug。**relocate M46 属破坏性变更，待人工决定，自动化不得擅自改**。
- 因此升旗台不能放在主旗杆处（会与自行车棚穿模）。改用**探针网格扫描**：排除 campus-wide 合并网格（`M50_`/`M51_` 自行车道/绿篱环）与扁平塔防标记（`M7_`/`Tower_`/`Enemy_`/`M10B_`），只对 SOLID 结构（`Bldg_*`/`M11_*`/`M38_`/`M41_`/`M43_`…）求交，得校园北侧净空 assembly ground **(0,28)**（1288 个 blocker 中无一与该 8×6m 台基重叠）。
- 脚本内再做**防御性碰撞自检**：构建前对台基+踏步+旗杆 AABB 再核一遍 `Bldg_*`/`M11_*` 等，冲突则 `ok=False` 跳过，绝不静默穿模。
- 坐标**不硬编码**、从探针读（M11 之后铁律），建筑再挪也贴合。

### 3. Blender 5.2 API 要点
- Principled BSDF 输入名：`Base Color` / `Roughness` / `Metallic` / `Emission Color` + `Emission Strength`（**不是**旧 `Emission`）；`Metallic` 二值。
- **Cycles 渲染隐藏物体必须 `hide_render=True`**（`hide_viewport` 不影响 Cycles）—— 沿用 M67/M68 固化教训，hero 隐藏 overhead clutter（玩法层/看台/塔环）时两标志都设、渲染后恢复。
- 删旧物体先 `nm=o.name` 再 `objects.remove(o, do_unlink=True)`，删完别再访问 `o.name`（pitfall #16 StructRNA ReferenceError）；`clear_old` 只清 `M69_` 前缀，孤儿 mesh 顺手清。
- 渲染：`CYCLES` + `GPU` + `OPTIX` + `use_denoising` + `view_settings.look="AgX - Base Contrast"`，256 samples；白昼光照复用 `m06_lighting.build_lighting('day')` 避免孤儿天光累积（M28 教训）。

### 4. 来源
- Blender bmesh 文档：https://docs.blender.org/api/5.2/bmesh.ops.html
- Principled BSDF 5.x 输入：https://docs.blender.org/api/5.2/bpy.types.ShaderNodeBsdfPrincipled.html
- AgX 色调映射与曝光：https://docs.blender.org/manual/en/5.2/render/color_management.html

---

## 2026-09-06 立项调研

### A. 电影级渲染设置（EEVEE Next / Cycles）
- 来源：https://uhiyama-lab.com/en/notes/blender/rendering-settings-cycles-eevee/
- 来源：https://reelmind.ai/blog/blender-photorealism-mastering-eevee-high-resolution-output-for-next-gen-renders
- 来源：https://yelzkizi.org/?p=32108/ （Best Blender Render Settings）
- 要点：
  - **Bloom 在 EEVEE Next（4.2+/5.x）已从渲染设置移除**，改用 Compositor 的 **Glare 节点（Bloom 模式）**（来源 blenderartists Bloom 讨论 + Blender-Artworks Rendering.md）。
  - Cycles 终帧：GPU(OptiX) + Denoising，samples 256–1024，光钳制防 firefly。
  - EEVEE Next：Raytracing 替代旧 SSR；Ambient Occlusion（高样本）；Shadows cube/cascade ≥2048 + High Bit Depth；Irradiance Volume + Reflection Cubemap 探针烘焙 GI（静态全局光照近似）。
  - Color Management：AgX / Filmic 色调映射 + Exposure 微调；高分辨率时 Bloom 要收敛，避免过曝。
  - 文件：静帧 PNG，合成/后期 EXR。

### B. 程序化 PBR 材质（节点）
- 来源：https://startingframe.com/?p=1408 （付费 SF Stone 程序化石材，作质量参考；我们做免费版）
- 来源：https://www.strayspark.studio/blog/complete-blender-material-pipeline-create-age-export （材质管线：Create→Age→Bake→Export）
- 来源：https://oldetinkererstudio.com/?p=7106/ （程序化混凝土：Musgrave+Voronoi+ColorRamp+Bump）
- 来源：https://blender.tekriss.com/procedural-brick-texture-blender-2-81 （程序化砖：Brick Texture+Noise+ColorRamp+Normal/Displacement）
- 来源：https://imeshh.com/blog/create-a-modern-living-room-in-30-minutes-in-blender-eev-n （EEVEE Next 室内：Node Wrangler Ctrl+Shift+T 导入整套 PBR；HDRI + Light Path Is Camera Ray 混合让天空亮而照明贡献小）
- 要点：
  - PBR 合理 albedo：深木 0.1–0.2 / 混凝土 0.3–0.4 / 浅石 0.5–0.6；metallic 二值；禁止纯黑纯白。
  - 必须加变化：Noise/Voronoi/Musgrave 驱动 color & roughness；ColorRamp 控制范围；Normal/Bump 微观起伏；(Cycles) Displacement 真实几何起伏。
  - 使用痕迹：边缘磨损(edge wear)、角落积灰、渗水渍 → 材质"活"起来。
  - Brick Texture 节点参数：offset/frequency/squash/mortar size/bias/brick width/row height；UV 用 Cube Projection 防拉伸。
  - Triplanar（object space）投影免 UV 展开，几何体任意朝向都正确。

### C. 可进入 / 行走（Walk Navigation & 室内）
- 来源：https://www.suzhar.com?p=604/ （Walk Navigation 实测：重力+视点高度；只碰水平面、垂直墙穿模；台阶低于视点高度自动上、高于穿；斜坡 ≤88° 可爬、89° 穿）
- 来源：https://www.blender.org/documentation/logic_editing_proposal.pdf （早期 BGE 第一人称进屋案例，多边形控制/逐房间光照层思路，可作参考）
- 来源：https://blenderartists.org/t/entering-building/364286/9 （FPS 进建筑：用不可见碰撞面围出可动范围；楼梯用不可见斜坡 ramp + 关楼梯碰撞）
- 要点：
  - **Walk Navigation（Blender 内置）** 是原型期"走进建筑"最快方案：开重力、设视点高度（~1.6m），视口里实时行走查看。
  - **垂直墙不碰撞** → 室内必须铺**地板面**才能走进去；楼梯用斜坡或分段台阶（低于视点自动上）。
  - 真正游戏碰撞要几何+碰撞面（BGE 已移除，2.8+ 无）；原型期 Walk Navigation 足够，导出游戏引擎再做物理。

### D. 程序化建筑生成（Archimesh）
- 来源：https://github.com/blender/blender-addons/blob/main/archimesh/__init__.py （官方仓库 __init__）
- 来源：https://github.com/dfelinto/blender-1/blob/master/archimesh/README.md （功能清单：Rooms/Houses/Columns/Stairs/Doors/Windows/Tile roofs/Kitchen…）
- 来源：https://projects.blender.org/blender/blender-addons/issues/37230 （Archimesh tracker）
- 要点：
  - **Archimesh 已是 Blender 官方内置插件**（Extensions 目录启用，无需外部下载）。
  - 生成：Room（可编辑、曲墙、Import/Export）、Door（单/双开）、Window（轨窗/叶窗）、Stairs（直/曲）、Column、Roof、Kitchen 等。
  - **Auto Hole** 给门窗在墙上自动开洞（boolean）；生成 Cycles 材质。
  - 用 modifier 驱动，创建后属性仍可改 → 适合迭代。
  - 注意：大量门窗时 boolean 偶尔失败，需重试/调位置。

---

## 2026-09-06 M9 实测：漫游视频与 Blender 5.2 构建差异
- 本机构建的 Blender 5.2 中 `scene.render.image_settings.file_format` 枚举**不含 `FFMPEG`**（仅有 PNG/JPEG/OPEN_EXR 等图片格式），无法从 Blender 直出视频。
- 解法：先渲染 PNG 图像序列（`scene.render.image_settings.file_format = "PNG"`），再用 `imageio-ffmpeg`（PyPI 包，自带静态 ffmpeg）编码为 MP4：`ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out.mp4`。
- Blender 5.2 中 EEVEE Next 的引擎枚举名仍为 `"BLENDER_EEVEE"`（不是所有文档里的 `"BLENDER_EEVEE_NEXT"`）。
- `blmcp_client.py` 顶层 `RENDER_M09_CODE` 的格式化 bug 会导致模块 import 崩溃；本次用最小 TCP sender `tools/send_blender.py` 绕过。

---

## 2026-09-10 M69 升旗台（离线分支·静态校验 + 旗杆圆柱化）
- 背景：M69 脚本（`build/m69_flag_platform.py` + `m69_render.py` + `tools/run_m69_*.py`）已于上轮写好，但上轮 Blender 中途离线未实跑。本轮 Blender 仍离线，故对脚本做静态校验而非实跑。
- 静态校验（无 Blender 依赖）：`python -m py_compile` 通过；复核与 PLAN §8 避坑清单一致——
  - 仅清 `M69_` 前缀（幂等、不破坏其它物体）；`clear_old` 先取 `nm=o.name` 再 `remove`（pitfall #16 ReferenceError 防护）。
  - 不调 `mode_set`；全部 bmesh 直建 + 旋转矩阵，物体 scale 保持 1。
  - 复用 `PBR_Concrete`/`PBR_Metal`（缺失才 `make_pbr` 自建），`make_pbr` 仅清/重建 `M69_` 自有材质，**绝不**清共享 `PBR_*`（避免 M18 同款材质槽悬空破坏）。
  - 防御性碰撞自检 `collision_check()`：仅与实体结构（Bldg_/M11_/M16–M68 等）求交、跳过任一维 >70m 的校园级虚假大盒（Ground/M25雾/M50·M51 环线/扁平塔防标记），命中则 `SystemExit(0)` 优雅跳过、不清也不建。
- 改进（可信离线可落）：旗杆由「细长 box 方截面」改为 **`bmesh.ops.create_cone(radius1==radius2, segments=16)` 真圆柱**（12m/φ0.12），消除方柱生硬感；纯 bmesh 无场景操作、无 mode_set，MCP 安全。杆顶金顶改为**独立金色 `M69_Finial` 物体**（gold 材质），不再并入 `bm_pole`（避免与金属杆顶 icosphere 在杆顶重合 z-fighting；见 2026-09-10 19:42 小节）。
- 出图方案（沿用 M56–M68 已验证）：`tools/run_m69_build.py`→`run_m69_render.py` 经 `blmcp_client.py` 直连 9876 socket，build/render 分离；render 内 `sc.render.filepath` 直写 `previews/m69_flag_platform_{hero,aerial}.png`（1920×1080 / Cycles OptiX / 256 samples / `build_lighting("day")` 复用 m06 权威基线防孤儿天光），不走 `render_viewport_to_path`。
- 下一步：Blender 在线后由下一轮自动化实跑 `run_m69_build.py`→`run_m69_render.py`，据像素统计（aerial 无过曝、hero 台基/藏青校旗/金顶清晰）确认后回写 PLAN §7 + PROGRESS 顶部。可选：若要把旗台落到主旗杆 (-3,0)，需人工先 relocate M46 自行车棚释放净空。

## 2026-09-10 14:25 M69 升旗台（最终离线预检 · 待在线首跑）
> 状态：Blender 仍离线（`:9876` 无 LISTENING，无 blender 进程）。M69 四件套自 11:02 写好、经 12:16/13:22 两轮加固（圆柱旗杆 + 纯 data-API 相机 + zero operator）后，本轮做**最终离线预检**，确认可进入"在线即首跑"状态。

- **四件套 `python -m py_compile` 全部通过**（build / render / run_m69_build / run_m69_render）。
- **禁止调用扫描（最终核验）**：`build/m69_flag_platform.py` 中 `mode_set` / `bpy.ops.object.camera_add` / `select_all` / `bpy.ops` **仅出现在注释/docstring，无任何实际调用**——整脚本维持零 operator（MCP headless 最稳形态）。
- **关键加固点逐条命中**：
  - `clear_old()` 内 `nm2 = o.name` 先于 `objects.remove()`（pitfall #16 StructRNA ReferenceError 防护）。
  - 旗杆 = `bmesh.ops.create_cone(radius1==radius2, segments=16)` 真圆柱（非方柱）。
  - 相机 = `bpy.data.cameras.new()` + `bpy.data.objects.new()` + `collection.objects.link()`（纯 data API，M69_Cam 被 clear_old 清后由本段重建，满足"Camera 不存在则创建"）。
  - `collision_check()` 模块级自检：仅与实体结构求交、跳过 >70m 虚假大盒，命中即 `SystemExit(0)` 优雅跳过。
- **结论**：M69 已达"Blender 一上线即可首跑"状态，无需再改脚本。下一步纯属环境等待——在线后直接 `run_m69_build.py`→`run_m69_render.py` 出 `previews/m69_flag_platform_{hero,aerial}.png`，据像素统计确认后回写 PLAN §7 + PROGRESS 顶部。

## 2026-09-10 19:42 [M69] 离线分支（首跑前逻辑复检 · 修金顶重影 bug · 待在线首跑）
> 状态：Blender 仍离线（`:9876` 无 LISTENING）。本轮对 M69 四件套做**首次运行时才会暴露的逻辑级复检**（py_compile 之外）：
- **发现并修复真 bug——金顶球冠重影（z-fighting）**：原 `m69_flag_platform.py` 把金色球冠 icosphere 同时① 并入 `bm_pole`（该 mesh 仅挂 `metal` 材质，故球冠实为金属色）② 又作为独立 `M69_Finial`（gold 材质）建在杆顶同一位置 → 两球重合。修法：删除并入 `bm_pole` 的那份球冠（保留纯圆柱），金顶只由 `M69_Finial` 提供，消除重影。`py_compile` 复检通过、`bm_pole.verts.new` 现仅 1 处（圆柱）。
- **render 脚本复核无误**：`m69_render.py` 沿用 M56–M68 已验证范式——`bpy.ops.render.render(write_still=True)` 为合法出图调用（非禁用的 `mode_set`），GPU/OptiX/256s/AgX/`build_lighting('day')` 复用 m06 基线防孤儿天光，结尾恢复 `M19C_HeroDay` 活动相机。`.look="AgX - Base Contrast"` 若无效仅回落默认 AgX、不报错。
- 结论：脚本现已为"在线即首跑"最终形态，且比上轮更干净（无重影金顶）。RESEARCH 已更正 12:16 小节"金顶并入同 mesh"的旧描述。
- 下一步：Blender 在线（`:9876` 监听）后 `tools/run_m69_build.py`→`run_m69_render.py` 直连 9876 socket，落盘 `previews/m69_flag_platform_{hero,aerial}.png`（1920×1080 / OptiX / 256s），据像素统计（aerial 无过曝、hero 台基/藏青校旗/金顶清晰）确认后回写 PLAN §7 + PROGRESS 顶部。
