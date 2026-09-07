# 研究笔记 · 教程与避坑（GitHub / Web）

> 自动任务每周追加；人工也可补充。每条带日期 + 来源链接 + 可落地要点。

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
