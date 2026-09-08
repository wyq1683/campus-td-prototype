# 视觉资源全周期任务清单 · 高中校园塔防原型（campus_td）

> 生成日期：2026-09-07 ｜ 基于真实项目状态：M0–M19 + M1b(CC0 扫描贴图) 已完成，scene **925 obj**，
> Blender 5.2.1 MCP(:9876) 在线。当前缺口：**无角色模型/骨架动画、无粒子系统、材质仅 1k + 程序化**。
> 本清单覆盖「高精度材质 / 角色与场景动画 / 粒子特效」三大新方向，并按
> **开发 → 测试 → 构建 → 部署 → 运行维护** 全周期划分。机器可读版见 `roadmap_tasks.json`。

---

## 阶段总览

| 阶段 | 名称 | 关键产出 | 前置 |
|------|------|----------|------|
| P1 | 开发·高精度材质 | 2K/4K CC0 + 程序化细节图 + 位移微几何 | — |
| P2 | 开发·角色与场景动画 | 角色基础网格→骨架→循环动画；塔/场景环境动画 | P1（材质就位） |
| P3 | 开发·粒子特效 | 枪口火花/死亡爆裂/减速冰霜/路径流光/环境粒子 | P1 |
| P4 | 测试·视觉与性能验证 | 像素统计回归、WebGL FPS/显存剖析、headless 冒烟 | P1–P3 |
| P5 | 构建·打包与导出 | OptiX 4K 终帧、WebGL KTX2 压缩、Godot/Unity 刷新 | P4 |
| P6 | 部署交付 | 静态托管 + CI 部署、版本标签 | P5 |
| P7 | 运行维护 | 夜间自动构建+QA、资产热更、遥测反馈、CC0 合规审计 | P6 |

---

## P1 · 开发·高精度材质

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V1.1 | CC0 贴图升 2K/4K | 7 套材质各下 `diff/nor_gl/rough/arm/ao/disp`（金属加 `metal`）共 ≤50 张；单张 2K≤4MB / 4K≤16MB；`fetch_ph_textures.py` 增 `--res` 参数；重建 `Mat_CC0_*` 后预览球渲染像素 std≥40、近黑≤300px | — | `build`：`blmcp m01b --res 2k` |
| V1.2 | 扩充表面类型 | 新增 plaster 外墙 / roof tiles / 桌面木 / 椅布 / 跑道橡胶 5 类 CC0 或程序化材质；`manifest.json` 增条目；应用至对应对象（墙裙/屋顶/课桌/椅/跑道）各 ≥1 个 | V1.1 | `build`：`blmcp m01b --add plaster,roof,desk,chair,track` |
| V1.3 | 程序化细节图 | 为 m01 程序化材质生成 AO/Curvature 细节节点（不依赖外图），砖/混凝土法线细节 std 较现状 +15% | — | `build`：`blmcp m01 --detail-maps` |
| V1.4 | 位移微几何 | 英雄表面（校门匾/砖墙近景）接 disp 图 + Adaptive Subdivision（或 Bump 兜底）；近景渲染可见凹凸、无撕裂 | V1.1 | `build`：`blmcp m01b --disp` |
| V1.5 | 材质密度/LOD | 每类建筑独立 Mapping 密度参数（非全局统一）；远处对象降纹理分辨率（LOD 切换无 popping） | V1.1 | `build`：`blmcp m01b --lod` |

---

## P2 · 开发·角色与场景动画

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V2.1 | 角色基础网格 | 低模学生/教师/敌人各 1（≤1.5k tris），命名 `Char_Student/Teacher/Enemy`，可绑定骨架 | — | `build`：`blmcp char_base` |
| V2.2 | 骨架与循环动画 | V2.1 后：学生 idle/walk/run（各 ≥24 帧 @30fps，循环无缝）；敌人 attack/die（death ≤1.2s） | V2.1 | `build`：`blmcp char_rig` |
| V2.3 | 塔动画 | 炮塔旋转/后坐/充能脉冲关键帧（替代纯 frame_change 光束），与 M7 锁定光束同步 | — | `build`：`blmcp m07_anim` |
| V2.4 | 场景环境动画 | 校旗布料/风动着色器、树冠摆动、水面涟漪（若有）；每类 1 个可复用节点/修改器 | V1.1 | `build`：`blmcp m05_ambient_anim` |
| V2.5 | 电影机位序列 | 扩展 M9：波次开始/BOSS 两个关键镜头动画（贝塞尔缓动，≥90 帧） | — | `build`：`blmcp m09_anim` |
| V2.6 | 状态反馈动画 | HUD/选中塔升级脉冲（Web 端 CSS/Shader，非 Blender） | — | `build`：`web hud_anim` |

---

## P3 · 开发·粒子特效

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V3.1 | 枪口/命中火花 | 塔开火触发 muzzle flash + 命中 sparks 粒子（≤800 粒/次，生命周期 ≤0.4s） | V1.1, V2.3 | `build`：`blmcp vfx_muzzle` |
| V3.2 | 敌人死亡爆裂 | 敌消亡爆裂/碎裂粒子（≤1200 粒，≤0.8s） | V2.2 | `build`：`blmcp vfx_death` |
| V3.3 | 减速冰霜场 | SLOW 力场可视冰霜粒子（覆盖区持续，密度随等级） | P1 | `build`：`blmcp vfx_slow` |
| V3.4 | 路径流光 | U 形路径能量流光粒子（沿弧长匀速，密度稳定） | — | `build`：`blmcp vfx_path` |
| V3.5 | 环境粒子 | 尘埃/落叶/体积光（god-rays）各 1 套，全天循环无突跳 | V1.1 | `build`：`blmcp vfx_ambient` |
| V3.6 | 出生/基地门 | 出生点红环 + 基地核心绿环脉冲特效（与 M7 一致） | — | `build`：`blmcp vfx_portal` |

---

## P4 · 测试·视觉与性能验证

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V4.1 | 像素统计回归 | 每次材质/场景变更自动渲染 + PIL 像素统计（mean/std/近黑/过曝），写入 `qa/<run>.json`；与基线偏差 >8% 报警 | P1–P3 | `test`：`blmcp qa_render` |
| V4.2 | WebGL 性能剖析 | `m10c` 原型 FPS≥30（中端 GPU）、draw call≤200、纹理显存≤120MB | P1,P3 | `test`：`playwright web_perf` |
| V4.3 | Headless 冒烟 | 每次构建后 headless Cycles 渲染 1 帧，检测节点树损坏/紫黑块（像素统计 + 日志） | P1–P3 | `test`：`blmcp smoke` |

---

## P5 · 构建·打包与导出

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V5.1 | OptiX 4K 终帧 | 剩余 backlog：Cycles GPU OptiX 渲染 campus 终帧 3840×2160，≤直连 540s/帧 | P1,P3 | `build`：`blmcp render_optix_4k` |
| V5.2 | WebGL 包优化 | 贴图转 KTX2/ETC2（单张≤1MB），合批 draw call，包体 ≤12MB | V1.1,P3 | `build`：`web build_optimized` |
| V5.3 | Godot/Unity 刷新 | `m19b_export.py` 重导出 glb 含新材质/动画（≤12MB），更新 EXPORT_GODOT_UNITY.md | P1–P3 | `build`：`blmcp m19b_refresh` |
| V5.4 | 资产清单版本化 | `assets/manifest.json` + `build/asset_version.json` 记录哈希，支持回滚 | P1–P3 | `build`：`blmcp asset_version` |

---

## P6 · 部署交付

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V6.1 | 静态托管 + CI | WebGL 构建产物部署 GitHub Pages/CDN；PR 合并触发 `gh-pages` 部署；可用 URL 返回 200 | V5.2 | `deploy`：`ci pages` |
| V6.2 | 桌面/移动构建 | 可选：导出桌面/移动可执行（若立项），启动 <3s | V5.3 | `deploy`：`ci package` |
| V6.3 | 发布说明与标签 | 每次发布写 `RELEASE_NOTES.md` + git tag `vX.Y.Z` | V5 | `deploy`：`ci release` |

---

## P7 · 运行维护

| ID | 目标 | 可量化交付物标准 | 前置 | 自动化调度提示 |
|----|------|------------------|------|----------------|
| V7.1 | 夜间自动构建+QA | 每日 02:00 自动跑 P5 构建 + P4 测试，失败告警 | V4,V5 | `automation`：每日 02:00 |
| V7.2 | 资产热更 | TDrive(`SSTDgvDolVsY`) 资产变更 → 自动同步 `assets/` + 重算 manifest | V5.4 | `automation`：on TDrive change |
| V7.3 | 遥测与反馈 | Web 嵌入报错上报 + 体验评分（均分≥4.0 目标），周报 | V6.1 | `automation`：每周一 |
| V7.4 | CC0 合规审计 | 季度扫描 `assets/textures/` 许可证，确认全 CC0、无商用违约 | V1 | `automation`：每季度 |

---

## 依赖关系图（文字）

```
P1(V1.1→V1.5) ──┬─> P2(V2.1→V2.2, V2.3, V2.4) ─┬─> P3(V3.1,V3.2)
                └─> P3(V3.3,V3.4,V3.5,V3.6) ───┘
P1–P3 ──> P4(V4.1,V4.2,V4.3) ──> P5(V5.1..V5.4) ──> P6(V6.1..V6.3) ──> P7(V7.1..V7.4)
V2.2 ──> V3.2 ; V2.3 ──> V3.1 ; P1 ──> V3.3/V3.5
```
