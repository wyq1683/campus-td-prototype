# _font_probe.py — 一次性探针：量各候选 CJK 字体在 Blender 里的实际字形尺寸
# 目的：VF(NotoSerifSC-VF) 加载成 ExtraLight 且字形被缩到 size 的 0.34 倍，明显异常。
#       匾额要「够粗 + 字形尺寸正常」，所以逐个字体建临时 text 量 dimensions 再挑。
# 运行：exec(compile(open(r"...\\campus_td\\tools\\_font_probe.py").read(), "probe", "exec"))

import bpy

CANDS = [
    r"C:\Windows\Fonts\simsunb.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\NotoSerifSC-VF.ttf",
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
]

TEXT = "晨光中学"   # 4 字，size=1.0 时理想宽 ~4.0、高 ~1.0


def probe():
    out = []
    for p in CANDS:
        try:
            f = bpy.data.fonts.load(p)
        except Exception as e:
            out.append({"file": p.split("\\")[-1], "ok": False, "err": str(e)[:60]})
            continue
        bpy.ops.object.text_add(location=(0.0, 0.0, 0.0))
        o = bpy.context.active_object
        o.name = "_ProbeTmp"
        o.data.body = TEXT
        o.data.font = f
        o.data.size = 1.0
        o.data.align_x = "CENTER"
        bpy.context.view_layer.update()
        d = o.dimensions
        nm = o.name
        bpy.data.objects.remove(o, do_unlink=True)
        out.append({"file": p.split("\\")[-1], "ok": True, "font": f.name,
                    "w": round(d.x, 4), "h": round(d.y, 4),
                    "n_chars": len(TEXT)})
    return out


result = {"text": TEXT, "probes": probe()}
print("FONT PROBE:", result)
