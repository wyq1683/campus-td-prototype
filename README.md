# 高中校园塔防原型 · Cinematic Enterable High School TD Prototype

> 用 **Blender + Blender MCP 链路**构建的真实可进入、电影级质感的高中校园 3D 原型；塔防玩法层（塔/敌人/路径）作为叠加系统保留。

## 项目目标

- 全校园可行走：每栋主建筑 exterior + interior 都建模，能用 Walk Navigation 走进去。
- 电影级材质：全场景程序化 PBR 节点材质库（草/沥青/砖/混凝土/玻璃/木/金属/瓷砖）。
- 电影级光照：HDRI 天光 + 阳光 + 室内补光，AgX 色调映射 + Compositor Bloom。
- 塔防层：防御塔布局、敌人路径、出生点/波次占位可视。
- 可交付预览：每个里程碑出一张渲染预览图，存 `campus_td/previews/`。

## 技术栈

| 层 | 选择 | 说明 |
|---|---|---|
| Blender | 5.2.1 LTS（`D:\建模\blender\blender.exe`） | 活动实例 |
| MCP 链路 | mcporter → blmcp → addon `blender_mcp_addon` @9876 | 见 `config/mcporter.json` |
| 建筑生成 | Archimesh（官方内置 Extensions） | rooms/doors/windows/stairs + Auto Hole |
| 材质 | 程序化 Shader Nodes | 不依赖外部贴图 |
| 渲染 | EEVEE Next / Cycles GPU OptiX | Bloom 走 Compositor Glare |

## 目录结构

```
.
├── README.md                 # 本文件
├── build_campus_td.py        # M0 v1 场景构建脚本（草地/路径/教学楼/塔/敌人/相机）
├── blender-mcp-launch.sh     # Blender MCP Server 启动器（stdio）
├── config/mcporter.json      # mcporter MCP 配置
├── campus_td/
│   ├── PLAN.md               # 权威计划书（背景/愿景/范围/技术栈/质量基准/里程碑 M0–M9/避坑）
│   ├── PROGRESS.md           # 进度日志（自动任务每次追加）
│   ├── RESEARCH.md           # 教程与避坑研究笔记
│   ├── STATUS.md             # 结构化进度速查（当前进度/待办/关键决策/上下文）
│   ├── build/                # 里程碑构建脚本 mNN_xxx.py（幂等、前缀隔离）
│   │   └── m01_materials.py  # M1 程序化 PBR 材质库
│   └── previews/             # 各里程碑渲染预览 PNG
└── render_campus_td.png      # M0 v1 俯视渲染（本地，未入库）
```

## 快速开始

1. 启动 Blender 活动实例（`D:\建模\blender\blender.exe`），在 Python Console 粘贴 `campus_td` 内存档里的 MCP 启动代码，使 addon 在 `localhost:9876` 监听。
2. 通过 mcporter 启动 `blmcp`（`config/mcporter.json` + `blender-mcp-launch.sh`）。
3. 经 MCP 执行构建脚本，例如：
   ```
   execute_blender_code(code='exec(compile(open(r"...campus_td/build/m01_materials.py").read(),"m01","exec"))')
   ```
4. 渲染预览：用 `render_viewport_to_path` 并读取返回的 `result.filepath`（该工具忽略传入路径）。

## 里程碑

- M0 基础与管线 ✅（v1）
- M1 程序化材质库（脚本就绪，待 MCP 执行）
- M2 建筑外壳 → M9 导航/导出（规划见 `campus_td/PLAN.md`）

## 说明

二进制资产（`render_campus_td.png`、Blender addon 压缩包）因文本 API 限制保留在本地，未同步至远程仓库。
