// sim.js — 校园塔防「平衡模拟引擎」（M10/M19 共用，与 campus_td/build/m10_balance.py 逐行等价）
//
// 双运行环境：浏览器里挂到 window.TD_Sim；Node 里 module.exports = TD_Sim。
// 用于「波次编辑器」(web/wave_editor.html) 实时验算，以及自动化用 Node 交叉验证数值。
//
// 关键约定（务必与 m10_balance.py 一致，否则平衡带是假的）：
//   · DT = 0.05（步长必须收敛；DT=0.1 会把 RAPID 的有效射速量化掉 17% DPS）
//   · 护甲 = 每发伤害 ×(1-armor)（把塔 DPS 打折，不是把血量放大）
//   · SLOW = 覆盖区全体减速力场 + 乘算叠加，合成上限 combined_slow_cap(0.75)
//   · 减速塔收益按重叠区其他塔 DPS 折算停留时间增量（ROI 棋盘感知）
//   · 每波前：先按 plan 建塔 → 再每回合最多 3 次升级（熟练=按 ROI，新手=按最便宜）
// ===========================================================================
(function (global) {
  "use strict";

  const DT = 0.05;          // 仿真步长 (s)
  const V_REF = 3.0;        // ROI 估算参考敌速 (m/s)
  const SLOW_CAP = 0.75;    // 合成减速上限（实际取 cfg.towers.upgrade.combined_slow_cap）

  // 策略 A：熟练玩家（补盲区 → 叠减速力场 → 按 ROI 升级）
  const PLAN_GOOD = [
    ["SLOT_A", "AOE"], ["SLOT_B", "RAPID"], ["SLOT_C", "SLOW"], ["SLOT_D", "AOE"],
  ];
  // 策略 B：新手（只建便宜塔 → 按最便宜升级）
  const PLAN_NAIVE = [
    ["SLOT_A", "BASIC"], ["SLOT_B", "BASIC"], ["SLOT_D", "BASIC"], ["SLOT_C", "BASIC"],
  ];

  // ---- 塔 ----
  function makeTower(name, type, cover, pos, defs, upg) {
    const d = defs[type];
    return {
      name, type, cover: cover.slice(), pos: pos.slice(),
      dmg: d.dmg, rate: d.rate, splash: d.splash, slow: d.slow, slow_dur: d.slow_dur,
      base_cost: d.cost, level: 1, cd: 0,
      slow_hard_cap: upg.slow_hard_cap, dmg_mult: upg.dmg_mult,
      slow_add: upg.slow_add, slow_dur_add: upg.slow_dur_add,
    };
  }
  function towerDps(t) { return t.dmg * t.rate; }
  function towerNextCost(t) { return Math.max(1, Math.floor(t.base_cost * 0.8 * t.level)); }
  function towerRoi(t, all) {
    const cost = Math.max(1, towerNextCost(t));
    const a = t.cover[0], b = t.cover[1], clen = b - a;
    if (t.slow > 0) {
      const ds = Math.max(0, Math.min(t.slow_add, t.slow_hard_cap - t.slow));
      if (ds <= 0) return 0;
      let od = 0;
      for (const o of all) if (o !== t && o.cover[0] < b && o.cover[1] > a) od += o.dmg * o.rate;
      return od * (clen / V_REF) * ds / Math.pow(1 - t.slow, 2) / cost;
    }
    const gainDps = t.dmg * (t.dmg_mult - 1) * t.rate;
    let sm = 1.0;
    for (const o of all) if (o.slow > 0 && o.cover[0] < b && o.cover[1] > a) sm = Math.max(sm, 1 / (1 - o.slow));
    return (clen / V_REF) * gainDps * sm / cost;
  }
  function towerUpgrade(t) {
    if (t.slow > 0) {
      t.slow = Math.min(t.slow_hard_cap, t.slow + t.slow_add);
      t.slow_dur += t.slow_dur_add;
    } else {
      t.dmg *= t.dmg_mult;
    }
    t.level += 1;
  }

  // ---- 敌人 ----
  function makeEnemy(type, hpScale, spawnT, edefs) {
    const d = edefs[type];
    return {
      etype: type, max_hp: d.hp * hpScale, hp: d.hp * hpScale,
      base_speed: d.speed, armor: d.armor, reward: d.reward,
      pos: 0, spawn_t: spawnT, slows: {}, alive: true,
    };
  }
  function enemySpeed(e, now, cap) {
    let f = 1.0; const dead = [];
    for (const k in e.slows) {
      const s = e.slows[k];
      if (now < s[0]) f *= (1 - s[1]); else dead.push(k);
    }
    for (const k of dead) delete e.slows[k];
    return e.base_speed * Math.max(f, 1 - cap);
  }

  function buildSpawn(cfg, waveIdx) {
    const w = cfg.waves[waveIdx];
    const out = []; let t = 0;
    for (const c of w.composition) {
      const type = c[0], n = c[1];
      const gap = (cfg.spawn_gap[type] != null) ? cfg.spawn_gap[type] : 0.4;
      for (let i = 0; i < n; i++) { out.push([type, w.hp_scale, t]); t += gap; }
    }
    return out;
  }

  function runWave(cfg, waveIdx, towers, gold, lives) {
    const edefs = cfg.enemies;
    const cap = (cfg.towers.upgrade.combined_slow_cap != null) ? cfg.towers.upgrade.combined_slow_cap : SLOW_CAP;
    const PATH_LEN = cfg.level.path_len_m;
    const pending = buildSpawn(cfg, waveIdx);
    const active = [];
    let t = 0, killed = 0, leaked = 0, killGold = 0, pidx = 0;
    let dmgDealt = 0, overkill = 0, busy = 0, total = 0;
    while (true) {
      while (pidx < pending.length && pending[pidx][2] <= t) {
        const p = pending[pidx]; active.push(makeEnemy(p[0], p[1], t, edefs)); pidx++;
      }
      if (!active.length && pidx >= pending.length) break;
      for (const tw of towers) {
        total += DT;
        const a = tw.cover[0], b = tw.cover[1];
        if (active.some(e => e.alive && a <= e.pos && e.pos <= b)) busy += DT;
        tw.cd -= DT;
        if (tw.cd > 0) continue;
        const targets = active.filter(e => e.alive && a <= e.pos && e.pos <= b);
        if (!targets.length) continue;
        targets.sort((x, y) => y.pos - x.pos);   // 优先打最靠近基地的
        const tgt = targets[0];
        const dmg = tw.dmg * (1 - tgt.armor);
        if (dmg >= tgt.hp) { overkill += dmg - tgt.hp; dmgDealt += tgt.hp; }
        else dmgDealt += dmg;
        tgt.hp -= tw.dmg * (1 - tgt.armor);
        if (tw.splash > 0) {
          for (const e of targets) {
            if (e === tgt || e.hp <= 0) continue;
            if (Math.abs(e.pos - tgt.pos) <= tw.splash) {
              const d = tw.dmg * (1 - e.armor);
              if (d >= e.hp) { overkill += d - e.hp; dmgDealt += e.hp; }
              else dmgDealt += d;
              e.hp -= tw.dmg * (1 - e.armor);
            }
          }
        }
        if (tw.slow > 0) {
          for (const e of targets) e.slows[tw.name] = [t + tw.slow_dur, tw.slow];
        }
        tw.cd = 1 / tw.rate;
      }
      for (const e of active) {
        if (!e.alive) continue;
        if (e.hp <= 0) { e.alive = false; killed++; killGold += e.reward; continue; }
        e.pos += enemySpeed(e, t, cap) * DT;
        if (e.pos >= PATH_LEN) { e.alive = false; leaked++; lives -= (cfg.leak_cost[e.etype] != null ? cfg.leak_cost[e.etype] : 1); }
      }
      for (let i = active.length - 1; i >= 0; i--) if (!active[i].alive) active.splice(i, 1);
      t += DT;
      if (t > 600) break;
    }
    gold += killGold + cfg.waves[waveIdx].bonus;
    const w = cfg.waves[waveIdx];
    return {
      wave: waveIdx + 1, killed, leaked, gold, lives, dur_s: Math.round(t * 10) / 10,
      ehp: (w.hp_pool != null) ? w.hp_pool : 0, dealt: dmgDealt, overkill,
      util: total > 0 ? busy / total : 0,
    };
  }

  function playerTurn(cfg, towers, gold, built, plan, useRoi) {
    const defs = cfg.towers.defs, slots = cfg.towers.slots;
    const slotMap = {}; for (const s of slots) slotMap[s.name] = s;
    for (const pr of plan) {
      const slotName = pr[0], type = pr[1];
      if (built.has(slotName)) continue;
      const cost = defs[type].cost;
      if (gold >= cost) {
        const s = slotMap[slotName];
        towers.push(makeTower(slotName, type, s.cover, s.pos, defs, cfg.towers.upgrade));
        gold -= cost; built.add(slotName);
      }
    }
    for (let i = 0; i < 3; i++) {
      const cands = towers.filter(t => gold >= towerNextCost(t));
      if (!cands.length) break;
      let best = cands[0];
      if (useRoi) {
        let bv = -1e18;
        for (const c of cands) { const r = towerRoi(c, towers); if (r > bv) { bv = r; best = c; } }
      } else {
        let bc = 1e18;
        for (const c of cands) { const c2 = towerNextCost(c); if (c2 < bc) { bc = c2; best = c; } }
      }
      gold -= towerNextCost(best); towerUpgrade(best);
    }
    return gold;
  }

  function runStrategy(cfg, plan, useRoi) {
    const towers = cfg.towers.fixed.map(f => makeTower(f.name, f.type, f.cover, f.pos, cfg.towers.defs, cfg.towers.upgrade));
    let gold = cfg.economy.start_gold, lives = cfg.economy.lives;
    const built = new Set();
    const rows = [];
    for (let w = 0; w < cfg.waves.length; w++) {
      gold = playerTurn(cfg, towers, gold, built, plan, useRoi);
      const r = runWave(cfg, w, towers, gold, lives);
      gold = r.gold; lives = r.lives;
      rows.push(r);
      if (lives <= 0) break;
    }
    return { rows, lives: Math.max(lives, 0), gold, towers };
  }

  function simulate(cfg) {
    const skilled = runStrategy(cfg, PLAN_GOOD, true);
    const naive = runStrategy(cfg, PLAN_NAIVE, false);
    const band = cfg.balance_band || { target_skilled_lives: [12, 18], target_naive: "fail" };
    return { skilled, naive, band };
  }

  // 导出/重算：把编辑后的波次按权威公式补 hp_scale / bonus / hp_pool。
  // 注意：config.json 里 economy.hp_scale_formula 写的是 0.20（陈旧）；
  // 实际标定用的是 0.23（见 m10_balance.py HP_SCALE）。编辑后一律用 0.23 重算，避免漂移。
  function recomputeWave(waveIdx, comp, edefs) {
    const w = waveIdx + 1;
    const hpScale = 1.0 + 0.23 * (w - 1);
    const bonus = 28 + 8 * w;
    let hpPool = 0;
    for (const c of comp) hpPool += edefs[c[0]].hp * hpScale * c[1];
    return { hp_scale: hpScale, bonus, hp_pool: hpPool };
  }

  const TD_Sim = { DT, V_REF, SLOW_CAP, PLAN_GOOD, PLAN_NAIVE, simulate, runStrategy, runWave, recomputeWave,
                   makeTower, towerRoi, towerNextCost, towerDps, towerUpgrade };

  if (typeof module !== "undefined" && module.exports) module.exports = TD_Sim;
  else global.TD_Sim = TD_Sim;
})(typeof window !== "undefined" ? window : globalThis);
