# m10_balance.py — M10 玩法层「平衡模拟器」v4（纯 Python，不依赖 Blender）
# 目的：把塔防数值从"拍脑袋"变成"可验算"。
#
# 所有几何来自对 Blender 场景的实测探针（campus_td/tools/blmcp_client.py）：
#   · 路径总弧长 102.0 m，U 形三直腿：
#       南腿 y=-13, x:-22→16  （弧长   0–38）
#       东腿 x=16,  y:-13→13  （弧长  38–64）
#       北腿 y=13,  x: 16→-22 （弧长  64–102）
#   · 四座固定塔（射程 13m）：
#       T1(-22,-13) 出生角 覆盖   0–13 ；T2(16,-13) 东南角 覆盖 25–51
#       T3( 16, 13) 东北角 覆盖  51–77 ；T4(-22,13) 基地角 覆盖 89–102
#   · 联合覆盖 76.5%，两段盲区 [13,25] 与 [77,89]（各 12m，共 24m）
#   · 关键结构发现：拐角塔（T2/T3）覆盖 26m = 直腿塔（T1/T4）13m 的 2 倍，
#     但两个拐角已被固定塔占满 → 玩家新建塔只能落在直腿上，先天吃亏。
#
# v4 相对 v3 的改动（设计层，不只是调数）：
#   1. SLOW 改为「减速力场」：命中覆盖区内全体敌人（原为只对目标 ±6m 生效）
#   2. 减速改为乘算叠加（多座 SLOW 覆盖同一区间时收益复合），总减速上限 75%
#   3. 建塔位 2 → 4：新增 SLOT_C（东路杀区）与 SLOT_D（基地前最后防线）
#   4. ROI 改为「棋盘感知」：SLOW 的收益按重叠区其他塔的 DPS 折算，
#      输出塔的收益按其覆盖区是否被减速力场覆盖而加权
#   5. 新增每波诊断：波次有效血量 / 实际投送伤害 / 塔空闲率 / 过量击杀
#
# 用法：
#   python campus_td/build/m10_balance.py             # 默认策略跑 10 波
#   python campus_td/build/m10_balance.py --verbose   # 逐波建造/升级明细

import os
import sys

BASE_BUILD = os.path.dirname(os.path.abspath(__file__))

# ===========================================================================
# 一、关卡常量（实测几何）
# ===========================================================================
PATH_LEN = 102.0
# DT 必须足够小，否则会把高射速塔的 DPS 系统性算低（射速量化误差）：
#   RAPID 射速 3.0/s → cd=0.333s。DT=0.1 时要 4 步才够（0.4s），有效射速掉到 2.5，**凭空 -17% DPS**。
#   实测 DT=0.05 与 DT=0.02 结果完全一致（已收敛），故取 0.05 兼顾精度与速度。
#   教训：调平衡前先做步长收敛性检查，否则整条平衡带都是假的。
DT = 0.05                     # 仿真步长 (s)
V_REF = 3.0                   # ROI 估算用的参考敌速 (m/s)
SLOW_CAP = 0.75               # 合成减速上限，避免堆 SLOW 直接锁死

FIXED_TOWERS = [
    # 名称       类型      覆盖弧长区间        世界坐标
    ("T1_RAPID", "RAPID", (0.0, 13.0),   (-22.0, -13.0)),   # 西南·出生点角
    ("T2_AOE",   "AOE",   (25.0, 51.0),  (16.0, -13.0)),    # 东南角（拐角，26m）
    ("T3_SLOW",  "SLOW",  (51.0, 77.0),  (16.0, 13.0)),     # 东北角（拐角，26m）
    ("T4_BASIC", "BASIC", (89.0, 102.0), (-22.0, 13.0)),    # 西北角·守基地
]

# 玩家可建塔位（弧长覆盖 / 世界坐标 / 定位说明）
SLOTS = {
    "SLOT_A": ((6.0, 32.0),   (-3.0, -13.0), "南腿中段·补盲区 A"),
    "SLOT_B": ((70.0, 93.0),  (-3.0, 13.0),  "北腿中段·补盲区 B"),
    "SLOT_C": ((38.0, 64.0),  (16.0, 0.0),   "东腿直道·与 T2/T3 叠杀区"),
    "SLOT_D": ((78.0, 102.0), (-11.0, 13.0), "基地前·最后防线（与 T4 叠加）"),
}

# ===========================================================================
# 二、塔数值
# ===========================================================================
TOWER_DEFS = {
    #            dmg   rate  splash slow  slow_dur cost  校园主题
    "BASIC": dict(dmg=22.0, rate=1.00, splash=0.0, slow=0.00, slow_dur=0.0, cost=80),   # 粉笔盒
    "RAPID": dict(dmg=9.0,  rate=3.00, splash=0.0, slow=0.00, slow_dur=0.0, cost=120),  # 试卷连发
    "AOE":   dict(dmg=30.0, rate=0.70, splash=4.0, slow=0.00, slow_dur=0.0, cost=150),  # 拖把横扫
    "SLOW":  dict(dmg=6.0,  rate=1.00, splash=0.0, slow=0.40, slow_dur=2.6, cost=100),  # 广播操/值日
}
UPGRADE_DMG_MULT = 1.40        # 每级伤害 ×1.4
UPGRADE_SLOW_ADD = 0.05        # SLOW 每级减速 +0.05（叠加上限见 SLOW_HARD_CAP）
UPGRADE_SLOW_DUR = 0.4         # SLOW 每级持续 +0.4s
SLOW_HARD_CAP = 0.60           # 单塔减速硬上限
UPGRADE_COST = lambda base, lv: int(base * 0.8 * lv)

# ===========================================================================
# 三、敌人数值（校园主题）
# ===========================================================================
ENEMY_DEFS = {
    #             hp    speed  reward armor
    "Swarm":  dict(hp=30,   speed=3.2, reward=5,   armor=0.00),  # 抄作业小队
    "Rusher": dict(hp=60,   speed=4.5, reward=7,   armor=0.00),  # 迟到生
    "Elite":  dict(hp=150,  speed=3.0, reward=16,  armor=0.15),  # 学霸（护甲）
    "Tank":   dict(hp=260,  speed=2.0, reward=20,  armor=0.10),  # 教导主任
    "Boss":   dict(hp=780,  speed=1.5, reward=150, armor=0.20),  # 校长（慢=输出窗口大）
}
SPAWN_GAP = {"Swarm": 0.35, "Rusher": 0.40, "Elite": 0.55, "Tank": 0.80, "Boss": 0.0}
LEAK_COST = {"Swarm": 1, "Rusher": 1, "Elite": 2, "Tank": 2, "Boss": 5}

# ===========================================================================
# 四、波次表（10 波，每波引入一个新机制）
# ===========================================================================
# 设计原则：102m 长路径 → 单波敌人必须"够密"，否则塔 3/4 时间在发呆（覆盖利用 <30% 即不合格）
WAVES = [
    ([("Swarm", 8)],                                 "教学：认识基础塔"),
    ([("Swarm", 10), ("Rusher", 4)],                 "引入快速单位"),
    ([("Rusher", 8), ("Swarm", 8)],                  "速度压力"),
    ([("Swarm", 14), ("Rusher", 6), ("Tank", 2)],    "引入坦克（高血量）"),
    ([("Elite", 6), ("Rusher", 8)],                  "引入精英（护甲）"),
    ([("Swarm", 18), ("Elite", 6)],                  "数量压力"),
    ([("Tank", 7), ("Rusher", 10)],                  "质量压力"),
    ([("Elite", 10), ("Swarm", 14)],                 "精英为主"),
    ([("Tank", 6), ("Elite", 8)],                    "混合高压"),
    ([("Boss", 1), ("Elite", 8), ("Tank", 2)],       "BOSS：校长视察"),
]
# 0.23 是在 DT 收敛（0.05）后重新标定出来的，勿回退到 0.20：
#   0.20 在收敛步长下熟练玩家 20/20 零漏怪，太易；0.25 起熟练掉到 10/20，偏难。
HP_SCALE = lambda w: 1.0 + 0.23 * (w - 1)   # 波次血量成长
# 经济：刻意收紧，让"补盲区 vs 叠杀区 vs 升级"三选一成为真决策
WAVE_BONUS = lambda w: 28 + 8 * w           # 清波奖励

START_GOLD = 240
LIVES = 20


# ===========================================================================
# 五、仿真核心
# ===========================================================================
class Tower:
    def __init__(self, name, ttype, cover, pos=(0.0, 0.0)):
        d = TOWER_DEFS[ttype]
        self.name, self.ttype, self.cover, self.pos = name, ttype, cover, pos
        self.dmg, self.rate = d["dmg"], d["rate"]
        self.splash, self.slow, self.slow_dur = d["splash"], d["slow"], d["slow_dur"]
        self.base_cost = d["cost"]
        self.level = 1
        self.cd = 0.0

    def cover_len(self):
        return self.cover[1] - self.cover[0]

    def dps(self):
        return self.dmg * self.rate

    def upgrade(self):
        if self.slow > 0:
            self.slow = min(SLOW_HARD_CAP, self.slow + UPGRADE_SLOW_ADD)
            self.slow_dur += UPGRADE_SLOW_DUR
        else:
            self.dmg *= UPGRADE_DMG_MULT
        self.level += 1

    def next_upgrade_cost(self):
        return UPGRADE_COST(self.base_cost, self.level)

    # -----------------------------------------------------------------
    # ROI：棋盘感知版
    # -----------------------------------------------------------------
    def roi(self, all_towers):
        """每 1 金币能买到多少「额外投送伤害」（按一次通过全程估算）。"""
        cost = max(1, self.next_upgrade_cost())
        a, b = self.cover

        if self.slow > 0:
            # 减速力场：收益 = 重叠区其他塔 DPS × 停留时间增量
            ds = max(0.0, min(UPGRADE_SLOW_ADD, SLOW_HARD_CAP - self.slow))
            if ds <= 0:
                return 0.0
            overlap_dps = sum(
                o.dps() for o in all_towers
                if o is not self and o.cover[0] < b and o.cover[1] > a
            )
            # d(停留时间)/d(slow) = (L/v) / (1-s)^2
            gain = overlap_dps * (self.cover_len() / V_REF) * ds / (1.0 - self.slow) ** 2
            return gain / cost

        # 输出塔：收益 = DPS 增量 × 停留时间；若区间被减速力场覆盖则加权
        gain_dps = self.dmg * (UPGRADE_DMG_MULT - 1.0) * self.rate
        slow_mult = 1.0
        for o in all_towers:
            if o.slow > 0 and o.cover[0] < b and o.cover[1] > a:
                slow_mult = max(slow_mult, 1.0 / (1.0 - o.slow))
        return (self.cover_len() / V_REF) * gain_dps * slow_mult / cost


class Enemy:
    _id = 0

    def __init__(self, etype, hp_scale, spawn_t):
        d = ENEMY_DEFS[etype]
        Enemy._id += 1
        self.id = Enemy._id
        self.etype = etype
        self.max_hp = d["hp"] * hp_scale
        self.hp = self.max_hp
        self.base_speed = d["speed"]
        self.armor = d["armor"]
        self.reward = d["reward"]
        self.pos = 0.0
        self.spawn_t = spawn_t
        self.slows = {}          # tower_name -> (expiry, factor)，乘算叠加
        self.alive = True

    def speed(self, now):
        f = 1.0
        dead = []
        for k, (exp, fac) in self.slows.items():
            if now < exp:
                f *= (1.0 - fac)
            else:
                dead.append(k)
        for k in dead:
            del self.slows[k]
        return self.base_speed * max(f, 1.0 - SLOW_CAP)


def build_spawn_list(wave_idx):
    comps, _ = WAVES[wave_idx]
    hp_scale = HP_SCALE(wave_idx + 1)
    out, t = [], 0.0
    for etype, n in comps:
        gap = SPAWN_GAP[etype]
        for _ in range(n):
            out.append((etype, hp_scale, t))
            t += gap
    return out


def wave_hp(wave_idx):
    """该波全部敌人的「实际血量池」——即塔真正需要打掉的血量。

    注意：护甲是"每发伤害打折"，等价于把塔的 DPS 打折，而不是把血量放大，
    所以这里不再除以 (1-armor)。护甲的代价已在「投送伤害」端被吃掉。
    """
    comps, _ = WAVES[wave_idx]
    hs = HP_SCALE(wave_idx + 1)
    return sum(ENEMY_DEFS[e]["hp"] * hs * n for e, n in comps)


def run_wave(wave_idx, towers, gold, lives):
    pending = build_spawn_list(wave_idx)
    active = []
    t = 0.0
    killed = leaked = 0
    kill_gold = 0
    pending_idx = 0
    # --- 诊断计数器 ---
    dmg_dealt = 0.0      # 实际落到敌人身上的有效伤害
    overkill = 0.0       # 过量击杀浪费
    tower_busy = 0.0     # 塔·秒（有目标且开火）
    tower_total = 0.0    # 塔·秒（总）

    while True:
        while pending_idx < len(pending) and pending[pending_idx][2] <= t:
            et, hs, _ = pending[pending_idx]
            active.append(Enemy(et, hs, t))
            pending_idx += 1
        if not active and pending_idx >= len(pending):
            break

        for tw in towers:
            tower_total += DT
            a, b = tw.cover
            # 覆盖率利用：射程内有敌人即算"交战中"（不受射速影响）
            if any(e.alive and a <= e.pos <= b for e in active):
                tower_busy += DT
            tw.cd -= DT
            if tw.cd > 0:
                continue
            targets = [e for e in active if e.alive and a <= e.pos <= b]
            if not targets:
                continue
            targets.sort(key=lambda e: -e.pos)        # 优先打最靠近基地的
            tgt = targets[0]

            dmg = tw.dmg * (1.0 - tgt.armor)
            if dmg >= tgt.hp:
                overkill += dmg - tgt.hp
                dmg_dealt += tgt.hp
            else:
                dmg_dealt += dmg
            tgt.hp -= tw.dmg * (1.0 - tgt.armor)

            if tw.splash > 0:                          # 溅射（按弧长距离）
                for e in targets:
                    # 必须跳过已被主弹打死的：其 hp<=0，计入会污染伤害统计
                    if e is tgt or e.hp <= 0:
                        continue
                    if abs(e.pos - tgt.pos) <= tw.splash:
                        d = tw.dmg * (1.0 - e.armor)
                        if d >= e.hp:
                            overkill += d - e.hp
                            dmg_dealt += e.hp
                        else:
                            dmg_dealt += d
                        e.hp -= tw.dmg * (1.0 - e.armor)

            if tw.slow > 0:                            # 减速力场：覆盖区内全体
                for e in targets:
                    e.slows[tw.name] = (t + tw.slow_dur, tw.slow)

            tw.cd = 1.0 / tw.rate

        for e in active:
            if not e.alive:
                continue
            if e.hp <= 0:
                e.alive = False
                killed += 1
                kill_gold += e.reward
                continue
            e.pos += e.speed(t) * DT
            if e.pos >= PATH_LEN:
                e.alive = False
                leaked += 1
                lives -= LEAK_COST[e.etype]
        active = [e for e in active if e.alive]
        t += DT
        if t > 600:
            break

    gold += kill_gold + WAVE_BONUS(wave_idx + 1)
    return dict(wave=wave_idx + 1, killed=killed, leaked=leaked,
                gold_gain=kill_gold, bonus=WAVE_BONUS(wave_idx + 1),
                gold=gold, lives=lives, dur_s=round(t, 1),
                ehp=wave_hp(wave_idx), dealt=dmg_dealt, overkill=overkill,
                util=(tower_busy / tower_total if tower_total > 0 else 0.0))


# 策略 A：熟练玩家 —— 先补盲区 → 再叠减速力场 → 余钱按 ROI 升级
PLAN_GOOD = [
    ("SLOT_A", "AOE"),     # 补南盲区 + 溅射清小怪
    ("SLOT_B", "RAPID"),   # 补北盲区
    ("SLOT_C", "SLOW"),    # 东路减速力场，与 T2/T3 复合减速
    ("SLOT_D", "AOE"),     # 基地前最后防线
]
# 策略 B：新手 —— 只挑便宜的建，升级也只挑最便宜的（不懂 ROI、不懂减速价值）
PLAN_NAIVE = [
    ("SLOT_A", "BASIC"),
    ("SLOT_B", "BASIC"),
    ("SLOT_D", "BASIC"),
    ("SLOT_C", "BASIC"),
]
STRATEGIES = [
    ("熟练玩家", PLAN_GOOD,  True,  "补盲区→叠减速→按 ROI 升级"),
    ("新手玩家", PLAN_NAIVE, False, "只建便宜塔→按最便宜升级"),
]


def player_turn(towers, gold, built, log, plan, use_roi):
    for slot_name, ttype in plan:
        if slot_name in built:
            continue
        cost = TOWER_DEFS[ttype]["cost"]
        if gold >= cost:
            cover, pos, _desc = SLOTS[slot_name]
            towers.append(Tower(slot_name, ttype, cover, pos))
            gold -= cost
            built.add(slot_name)
            log.append("建造 %s (%s) @%s -%d" % (slot_name, ttype, pos, cost))
    for _ in range(3):                                  # 每回合最多 3 次投入
        cands = [t for t in towers if gold >= t.next_upgrade_cost()]
        if not cands:
            break
        if use_roi:
            best = max(cands, key=lambda x: x.roi(towers))
        else:
            best = min(cands, key=lambda x: x.next_upgrade_cost())
        c = best.next_upgrade_cost()
        gold -= c
        best.upgrade()
        log.append("升级 %s → Lv%d (ROI %.2f) -%d" % (best.name, best.level, best.roi(towers), c))
    return gold


def run_strategy(plan, use_roi, verbose=False):
    """完整地跑一遍 10 波，返回 (rows, lives, gold, towers)。"""
    towers = [Tower(n, t, c, p) for n, t, c, p in FIXED_TOWERS]
    gold, lives, built = START_GOLD, LIVES, set()
    rows = []
    for w in range(len(WAVES)):
        log = []
        gold = player_turn(towers, gold, built, log, plan, use_roi)
        if verbose and log:
            for line in log:
                print("  [第%d波前] %s" % (w + 1, line))
        r = run_wave(w, towers, gold, lives)
        gold, lives = r["gold"], r["lives"]
        rows.append(r)
        if lives <= 0:
            break
    return rows, lives, gold, towers


CONFIG_PATH = BASE_BUILD + "/m10_config.json"


def export_config():
    """把验证过的数值导出为机器可读配置，供 Blender 层 / 后续引擎读取。

    单一数据源原则：Blender 与任何下游引擎都只读这份 JSON，
    不要再在脚本里手抄数字，避免数值漂移。
    """
    import json
    import os
    cfg = {
        "_meta": {
            "source": "campus_td/build/m10_balance.py",
            "version": "v4",
            "note": "数值经双策略仿真验证；几何来自 Blender 实测探针",
        },
        "level": {
            "path_len_m": PATH_LEN,
            "legs": [
                {"name": "南腿", "arc": [0.0, 38.0], "axis": "y=-13, x:-22→16"},
                {"name": "东腿", "arc": [38.0, 64.0], "axis": "x=16, y:-13→13"},
                {"name": "北腿", "arc": [64.0, 102.0], "axis": "y=13, x:16→-22"},
            ],
            "start": [-22.0, -13.0],
            "base": [-22.0, 13.0],
            "blind_spots": [[13.0, 25.0], [77.0, 89.0]],
        },
        "towers": {
            "fixed": [{"name": n, "type": t, "cover": list(c), "pos": list(p)}
                      for n, t, c, p in FIXED_TOWERS],
            "slots": [{"name": k, "cover": list(v[0]), "pos": list(v[1]), "desc": v[2]}
                      for k, v in SLOTS.items()],
            "defs": TOWER_DEFS,
            "upgrade": {
                "dmg_mult": UPGRADE_DMG_MULT,
                "slow_add": UPGRADE_SLOW_ADD,
                "slow_dur_add": UPGRADE_SLOW_DUR,
                "slow_hard_cap": SLOW_HARD_CAP,
                "combined_slow_cap": SLOW_CAP,
                "cost_formula": "int(base_cost * 0.8 * level)",
            },
        },
        "enemies": ENEMY_DEFS,
        "spawn_gap": SPAWN_GAP,
        "leak_cost": LEAK_COST,
        "waves": [{"index": i + 1, "composition": [list(x) for x in c], "desc": d,
                   "hp_scale": HP_SCALE(i + 1), "bonus": WAVE_BONUS(i + 1),
                   "hp_pool": wave_hp(i)}
                  for i, (c, d) in enumerate(WAVES)],
        "economy": {
            "start_gold": START_GOLD,
            "lives": LIVES,
            "hp_scale_formula": "1.0 + 0.20 * (wave - 1)",
            "wave_bonus_formula": "28 + 8 * wave",
        },
        "balance_band": {
            "target_skilled_lives": [12, 18],
            "target_naive": "fail",
        },
    }
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("\n[export] 已写出配置 → %s" % CONFIG_PATH)
    return CONFIG_PATH


def main():
    verbose = "--verbose" in sys.argv
    print("=" * 100)
    print("M10 校园塔防 · 平衡模拟 v4（路径 %.0fm ｜ 固定塔覆盖 76.5%% ｜ 4 建塔位）" % PATH_LEN)
    print("起始金币 %d · 基地生命 %d ｜ SLOW = 减速力场(全体) · 乘算叠加 · 上限 %d%%"
          % (START_GOLD, LIVES, int(SLOW_CAP * 100)))
    print("=" * 100)

    summary = []
    for sname, plan, use_roi, sdesc in STRATEGIES:
        print("\n【%s】%s" % (sname, sdesc))
        print("-" * 100)
        print("%-6s %-22s %5s %5s %8s %12s %8s %7s %6s %7s"
              % ("波次", "构成", "击杀", "漏怪", "波次EHP", "投送伤害(比)", "覆盖利用", "金币", "生命", "用时"))
        rows, lives, gold, towers = run_strategy(plan, use_roi, verbose)
        for r in rows:
            comps, _desc = WAVES[r["wave"] - 1]
            comp_str = "+".join("%s×%d" % (e, n) for e, n in comps)
            ratio = r["dealt"] / r["ehp"] if r["ehp"] > 0 else 0
            print("第%2d波 %-22s %5d %5d %8.0f %7.0f(%.2fx) %7.0f%% %7d %5d %6.1fs"
                  % (r["wave"], comp_str[:22], r["killed"], r["leaked"],
                     r["ehp"], r["dealt"], ratio, r["util"] * 100,
                     r["gold"], r["lives"], r["dur_s"]))
        t_leak = sum(r["leaked"] for r in rows)
        t_ehp = sum(r["ehp"] for r in rows)
        t_dealt = sum(r["dealt"] for r in rows)
        t_ok = sum(r["overkill"] for r in rows)
        verdict = "通关" if lives > 0 else "失败"
        print("  → %s | 剩余生命 %d/%d | 累计漏怪 %d | 终局金币 %d | 投送比 %.2fx | 过量击杀 %.0f%%"
              % (verdict, max(lives, 0), LIVES, t_leak, gold,
                 t_dealt / max(1, t_ehp), 100 * t_ok / max(1, t_dealt + t_ok)))
        summary.append((sname, verdict, max(lives, 0), t_leak, len(rows)))
        if sname == "熟练玩家":
            print("  终局塔配置：")
            for tw in towers:
                extra = ("slow=%.2f dur=%.1fs" % (tw.slow, tw.slow_dur)) if tw.slow > 0 \
                    else ("dmg=%.1f" % tw.dmg)
                print("     %-9s %-5s Lv%-2d %-18s dps=%6.1f  覆盖 %.0f-%.0fm  @%s"
                      % (tw.name, tw.ttype, tw.level, extra, tw.dps(),
                         tw.cover[0], tw.cover[1], tw.pos))

    print("\n" + "=" * 100)
    print("平衡带校验（目标：熟练玩家险胜留 12–18 生命，新手失败）：")
    for sname, verdict, hp, leak, nw in summary:
        flag = ""
        if sname == "熟练玩家":
            flag = "  ✔ 落在目标带" if 12 <= hp <= 18 else "  ✘ 需调整"
        else:
            flag = "  ✔ 有策略深度" if verdict == "失败" else "  ✘ 太宽容"
        print("  %-8s %-4s 抵达第%2d波  剩余生命 %2d/%d  漏怪 %d%s"
              % (sname, verdict, nw, hp, LIVES, leak, flag))
    print("=" * 100)

    if "--export" in sys.argv:
        export_config()
    return 0


if __name__ == "__main__":
    sys.exit(main())
