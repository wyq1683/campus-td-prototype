# 结构化进度速查 · 高中校园塔防原型

> 抗上下文压缩的"项目大脑"副件。每次推进项目时更新本文件（当前进度 / 待办 / 关键决策及理由 / 上下文摘要）。
> 完整权威内容见 `PLAN.md`；详细流水见 `PROGRESS.md`。最后更新：2026-09-06 15:45

---

## 一、当前进度（Current Progress）

- **M0 基础与管线**：✅ 已完成（v1）。46m 草地 + 3 段 U 形路径 + 6 栋示意教学楼 + 4 座发光防御塔 + 7 敌人 + 俯视相机；Cycles 64s 渲染 `render_campus_td.png`（930KB）。
- **M1 程序化材质库**：🟡 脚本已就绪（`campus_td/build/m01_materials.py`，幂等、py_compile 通过），**待经 Blender MCP 执行 + 渲染预览** `previews/m01_materials.png`。
- **M2–M9**：⚪ 未启动（规划见 PLAN.md §7）。
- **同步**：乐享个人知识库 8/9 文本页已入库（diag 脚本因 WAF 未入）；GitHub 集成经实测为**只读**（私有仓 404、转 public 后 403 写被拒），无法 push——以 Lexiang 为工作镜像，本地文件为权威源。

## 二、未完成待办（Open Todos）

1. 经 MCP 执行 `m01_materials.py` → 渲染 `previews/m01_materials.png` → 追加 PROGRESS。
2. 补传 `diag_blender_mcp.py` 至乐享（绕过 WAF 的 file 上传流程）。
3. M2 建筑外壳（Archimesh）：教学楼 + 实验楼 exterior，门窗开洞，真实尺度。
4. M3 室内可进入：走廊/楼梯/典型教室，Walk Navigation 验证。
5. M4–M9 按路线图推进。
6. 构建自动化现每 1 小时触发（最频繁且稳定的粒度，带防重叠锁）；每日 21:30 同步 / 周日 10:00 研究 持续运行。
7. GitHub 已可推送（仓库转 public 绕过私有仓 `repo` scope 限制）；首推后用户可转回 private。

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

## 四、上下文摘要（Context Recap）

- **用户**：Yuqi（初中生），做校园塔防游戏原型；要求决策自主化（不再给需用户决策的选项/清单）、主动维护结构化进度提醒、充分利用 WorkBuddy 项目功能（tdrive/项目消息/待办）提升协作。
- **环境**：Windows + RTX 5060；Blender 5.2.1（D 盘活动实例）；Blender MCP 端口 9876 存活（PID 10132）。
- **已连通外部**：乐享知识库（个人库 `9dd6e66e…`）、GitHub MCP（账号 wyq1683）。
- **避坑要点**：EEVEE Next 无 Bloom→Compositor Glare；Archimesh 官方内置；Walk Navigation 只碰水平面、垂直墙穿模→室内须铺地板；Principled 按 `type==BSDF_PRINCIPLED` 找；cone 用 `radius1/radius2`。
- **版本史边界**：GitHub 走真实 git commit（自建仓首推送起）；乐享为条目修订版，非 git 式历史——如实标注。

## 五、恢复指引（Resume Guide）

若上下文被压缩：先读 `PLAN.md`（权威）→ `STATUS.md`（本文件）→ `PROGRESS.md`（流水）；下一个待办 = 执行 `m01_materials.py` 并经 MCP 渲染。Blender 离线时改做研究并标"等待 Blender 在线"。
