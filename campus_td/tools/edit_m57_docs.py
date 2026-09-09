# edit_m57_docs.py — append M57 entry to PLAN.md §7 and prepend to PROGRESS.md
import io, os
ROOT = r"D:/AI/WorkBuddy/Workspace/2026-09-05-23-46-59/campus_td"

M57_PLAN = ("- **M57 校门卫室门把手与门牌号（Gate Guardhouse Door Handle & Number Plate · OptiX）**"
            "（✅，2026-09-09）：`build/m57_guardhouse_details.py`（非破坏，仅新建 `M57_` 前缀门把手/门牌号，"
            "幂等：先清旧 `M57_` 再建）+ `build/m57_render.py`（仅渲染）+ `tools/run_m57_build.py` / `tools/run_m57_render.py`"
            "（经 `tools/blmcp_client.py` 直连 9876 socket，build/render 分离，沿用 M56 教训）。项目收官（M0–M56 ✅）后按 M56「下一步」首项新增——"
            "M52 木门 + M56 门套仍缺把手与编号，补：金属门把手（背板+连杆+竖拉手，复用 `PBR_Metal`）+ 前墙右侧暗金属门牌号"
            "（底板 `M57_Plate` + CJK「1号」白字微自发光 `M57_NumText`，SimHei 自检通过）。坐标全部从 `M52_Door` 世界 AABB 动态读取"
            "（M11 之后铁律，不硬编码）。复用 `M52_Cam` 特写 + `M19C_HeroDay` 校园语境图，临时 POINT 补光 energy 120 渲染后清理零孤儿。"
            "Cycles GPU OptiX / 256 samples / 1280×720 / AgX / 曝光 0.0。**scene 1581→1587（+5 常驻 `M57_` 物体："
            "HandlePlate/HandleStem/HandleBar/Plate/NumText，零破坏其它物体）**。"
            "输出 `previews/m57_guardhouse_details_closeup.png`(857KB) + `previews/m57_guardhouse_details_hero.png`(1.34MB)。")

PROG_ENTRY = (
"## 2026-09-09 21:00 [里程碑 M57 · 校门卫室门把手与门牌号 OptiX] 状态：完成\n"
"- 做了：项目收官（M0–M56 ✅）后按 M56「下一步」首项新增 M57。写 `build/m57_guardhouse_details.py`（仅建，非破坏，5 个 `M57_` 物体 = HandlePlate/HandleStem/HandleBar/Plate/NumText，幂等清旧 `M57_`）+ `build/m57_render.py`（仅渲染）+ `tools/run_m57_build.py`、`tools/run_m57_render.py`（经 `tools/blmcp_client.py` 直连 9876 socket，build/render 分离，沿用 M56 教训）。金属门把手（背板+连杆+竖拉手，复用 `PBR_Metal`）+ 前墙右侧暗金属门牌号（底板 `M57_Plate` + CJK「1号」白字微自发光 `M57_NumText`，`pick_font` SimHei 自检通过 h=0.854）。坐标全部从 `M52_Door` 世界 AABB 动态读取（M11 之后铁律），零硬编码。\n"
"- 遇坑：无（沿用 M52/M56 管线一次过）。\n"
"- 验证：n_removed_old=0、n_m57_objects=5、n_total 1581→1587（零破坏）；closeup meanRGB(102,94,89)/过曝0%/dark0%、hero meanRGB(81,78,74)/过曝0.03%/dark1.83%（与 M56 一致）。落盘 `previews/m57_guardhouse_details_closeup.png`(857KB)+`previews/m57_guardhouse_details_hero.png`(1.34MB)。\n"
"- 下一步：维持收官。可选：车道蓝色边线 / 围栏广告牌（需确认不侵占玩法区）/ 换卡真 4K（受 8GB VRAM 限）。\n"
)

# PLAN.md §7 : insert M57 after M56 anchor
plan_path = os.path.join(ROOT, "PLAN.md")
plan = io.open(plan_path, encoding="utf-8").read()
anchor = "输出 `previews/m56_guardhouse_frames_closeup.png`(855KB) + `previews/m56_guardhouse_frames_hero.png`(1.34MB)。"
assert anchor in plan, "M56 anchor not found in PLAN.md"
if "M57 校门卫室门把手与门牌号" not in plan:
    plan = plan.replace(anchor, anchor + "\n\n" + M57_PLAN + "\n", 1)
    io.open(plan_path, "w", encoding="utf-8").write(plan)
    print("PLAN.md: M57 entry inserted")
else:
    print("PLAN.md: M57 entry already present, skipped")

# PROGRESS.md : prepend
prog_path = os.path.join(ROOT, "PROGRESS.md")
prog = io.open(prog_path, encoding="utf-8").read()
if "M57 · 校门卫室门把手与门牌号" not in prog:
    io.open(prog_path, "w", encoding="utf-8").write(PROG_ENTRY + "\n" + prog)
    print("PROGRESS.md: M57 entry prepended")
else:
    print("PROGRESS.md: M57 entry already present, skipped")
