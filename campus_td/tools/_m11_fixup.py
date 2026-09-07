# m11_fixup.py — 一次性修复：撤销 m11_masterplan.py v1 的“重复平移”污染
#
# 事故原因（v1 的 MOVE_RULES 用子串匹配，且按 MASTERPLAN 顺序逐个 apply）：
#   Teach 规则含 "Stair_"，会把 M8C_Admin_Stair_1 / M8C_Dorm_Stair_2 ... 一起吃掉；
#   等轮到 Admin / Dorm 规则时这些楼梯又吃第二份 delta -> 相对本楼整体偏移。
#   结果：Admin/Dorm/Library/Teach/Canteen 的 AABB 被撑大 3~4 倍，互相穿插。
#
# 修复数学（精确，不是近似回退）：
#   记 D_BUG[b] = v1 实际施加给规则 b 的位移（可从日志复现）
#       recv(o) = sum(D_BUG[m] for m in 命中规则集合)      # 该物体实际吃到的总位移
#       should(o) = TARGET[owner(o)] - ORIG_C[owner(o)]    # 该物体本该吃到的总位移
#       correction(o) = should(o) - recv(o)
#   对只命中本楼规则的外壳对象，correction 恰好等于 (目标 - 当前外壳中心)。
#
# ORIG_C 取自 M11 执行前的实测探针（Bldg_<B>_* 的 AABB 中心）。

import bpy

ORDER = ["Teach", "Lab", "Admin", "Library", "Dorm", "Gym", "Canteen"]

TARGET = {"Teach": (0.0, -29.0), "Lab": (0.0, 31.0), "Admin": (-38.0, 31.0),
          "Library": (-38.0, 12.0), "Dorm": (-38.0, -4.0), "Gym": (32.0, 6.0),
          "Canteen": (36.0, -10.0)}

ORIG_C = {"Teach": (-18.0, 14.0), "Lab": (18.0, 14.0), "Admin": (-16.5, -15.0),
          "Library": (2.0, -3.0), "Dorm": (0.0, -15.0), "Gym": (15.0, -15.0),
          "Canteen": (-16.0, -3.0)}

# v1 日志里实际施加的 delta（2 位小数，误差 <= 0.005m，随后跑一次修正版 M11 会归零）
D_BUG = {"Teach": (18.0, -31.92), "Lab": (-18.0, 17.0), "Admin": (-24.68, 60.29),
         "Library": (-42.17, 28.79), "Dorm": (-40.67, 25.29), "Gym": (17.0, 21.0),
         "Canteen": (49.32, 7.04)}

# 复刻 v1 的出 bug 规则（子串 + MASTERPLAN 顺序）
BUG_PATS = {"Teach": ["Teach", "Int_", "Stair_"], "Lab": ["Lab"], "Admin": ["Admin"],
            "Library": ["Library", "M8E_Book"], "Dorm": ["Dorm"], "Gym": ["Gym"],
            "Canteen": ["Canteen"]}


def owner(name):
    """优先级归属：显式前缀优先，杜绝 M8C_X_Stair 被 Stair_ 抢走。"""
    for b in ORDER:
        for pre in ("Bldg_%s_" % b, "M8C_%s_" % b, "M8D_%s_" % b, "M8_%s_" % b,
                    "Furn_%s_" % b):
            if pre in name:
                return b
    if "M8E_Book" in name:
        return "Library"
    if "Int_" in name or "Stair_" in name:
        return "Teach"
    return None


moved = {}
for o in bpy.data.objects:
    if o.name.startswith("M11_") or o.name.startswith("Mat_Preview_"):
        continue
    b = owner(o.name)
    if b is None:
        continue
    rx, ry = 0.0, 0.0
    for m in ORDER:
        if any(p in o.name for p in BUG_PATS[m]):
            rx += D_BUG[m][0]
            ry += D_BUG[m][1]
    sx = TARGET[b][0] - ORIG_C[b][0]
    sy = TARGET[b][1] - ORIG_C[b][1]
    o.location.x += sx - rx
    o.location.y += sy - ry
    moved[b] = moved.get(b, 0) + 1

bpy.context.view_layer.update()

# 回读外壳中心，确认是否落到目标
import mathutils
back = {}
for b in ORDER:
    objs = [o for o in bpy.data.objects if o.name.startswith("Bldg_%s_" % b)]
    if not objs:
        back[b] = None
        continue
    mn = [1e9, 1e9]; mx = [-1e9, -1e9]
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            mn[0] = min(mn[0], w[0]); mx[0] = max(mx[0], w[0])
            mn[1] = min(mn[1], w[1]); mx[1] = max(mx[1], w[1])
    cx, cy = 0.5 * (mn[0] + mx[0]), 0.5 * (mn[1] + mx[1])
    back[b] = {"center": [round(cx, 3), round(cy, 3)],
               "target": list(TARGET[b]),
               "err": [round(cx - TARGET[b][0], 3), round(cy - TARGET[b][1], 3)],
               "bbox": [round(mn[0], 2), round(mn[1], 2), round(mx[0], 2), round(mx[1], 2)]}

result = {"fixup": True, "moved": moved, "shell": back}
print("M11 fixup:", result)
