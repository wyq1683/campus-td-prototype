# m08b_light.py — M8B 室内补光精修
# 目标：把 M8 五间代表房间的 AREA 补光从 energy=160 提到 240(普通)/300(体育馆)，
#       并把矩形灯尺寸按房间内净尺寸放大到 ~0.7x 内净宽深，覆盖更大地面比例，
#       消除暗角与死黑（白昼靠 ribbon 窗天光 + 补光，本步只调补光强度/覆盖）。
# 幂等：直接重设既有 M8_* AREA 灯参数（设同值多次无副作用），不重建任何几何。
# 运行：
#   exec(compile(open(r"...campus_td/build/m08b_light.py").read(),"m08b","exec"))
#   tune()

import bpy

# 内净尺寸来自 m08 的 BUILDINGS：iw = w - 2*WALL_T(0.4)，id = d - 2*WALL_T
# 目标矩形灯半覆盖：size_x = iw*0.70，size_y = id*0.70
#   Admin   w13 d9  -> iw12.2 id8.2  -> 8.5 x 5.7
#   Canteen w14 d10 -> iw13.2 id9.2  -> 9.2 x 6.4
#   Dorm    w14 d9  -> iw13.2 id8.2  -> 9.2 x 5.7
#   Gym     w14 d12 -> iw13.2 id11.2 -> 9.2 x 7.8
#   Library w15 d11 -> iw14.2 id10.2 -> 9.9 x 7.1
TARGETS = {
    "M8_Admin":   (240.0, 8.5, 5.7),
    "M8_Canteen": (240.0, 9.2, 6.4),
    "M8_Dorm":    (240.0, 9.2, 5.7),
    "M8_Gym":     (300.0, 9.2, 7.8),
    "M8_Library": (240.0, 9.9, 7.1),
}


def tune():
    changed = {}
    for name, (energy, sx, sy) in TARGETS.items():
        lt = bpy.data.lights.get(name)
        if lt is None:
            changed[name] = "missing"
            continue
        old_e = lt.energy
        lt.energy = energy
        if lt.shape != "RECTANGLE":
            lt.shape = "RECTANGLE"
        lt.size = sx
        lt.size_y = sy
        # 复位朝向：AREA 灯默认局部 -Z 朝下（即世界向下），重建后若被旋转则归零
        lamp = bpy.data.objects.get(name)
        if lamp is not None:
            lamp.rotation_euler = (0.0, 0.0, 0.0)
        changed[name] = {"old_energy": round(old_e, 1), "new_energy": energy,
                         "size": (sx, sy)}
    g = globals()
    g["result"] = {"m8b": True, "lights": changed, "count": len(changed),
                   "scene_objects": len(bpy.data.objects)}
    return g["result"]


tune()
