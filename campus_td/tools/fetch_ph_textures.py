# fetch_ph_textures.py  — 拉取 Poly Haven (CC0) PBR 贴图到本地
# 幂等：已存在且大小 > 1KB 的文件跳过；输出 manifest.json 供 Blender 材质脚本读取。
# V1.1 分辨率感知：1K 始终拉取并保留作 fallback；命令行传入 2k/4k 时额外拉取该分辨率。
#   已存在于磁盘的更高分辨率也会被记录（重复运行可累积，不会覆盖/误删）。
# 运行：
#   managed python fetch_ph_textures.py        # 仅确保 1K（fallback）
#   managed python fetch_ph_textures.py 2k     # 追加 2K
#   managed python fetch_ph_textures.py 4k     # 追加 4K
import json, os, urllib.request, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "assets", "textures")
os.makedirs(TEX, exist_ok=True)

# 目标 -> Poly Haven slug（与 m01_materials.MAT_BY_TARGET 对齐；glass 保留程序化不拉）
MY_SET = {
    "grass":    "leafy_grass",
    "asphalt":  "asphalt_01",
    "brick":    "brick_wall_04",
    "concrete": "brushed_concrete",
    "tile":     "floor_tiles_02",
    "metal":    "metal_plate",
    "wood":     "oak_wood_planks",
}

# 尝试下载的贴图角色 -> Poly Haven 后缀（jpg）。Blender 用 OpenGL 法线 -> 用 nor_gl
ROLE_SUFFIX = {
    "diff": "diff",        # 基础色 (sRGB)
    "nor":  "nor_gl",      # 法线 (非颜色)
    "rough":"rough",       # 粗糙度 (非颜色)
    "arm":  "arm",         # AO(R)+Rough(G)+Metal(B) 打包 (非颜色)
    "ao":   "ao",          # 环境光遮蔽 (非颜色)
    "disp": "disp",        # 位移/高度 (非颜色)
    "metal":"metal",       # 金属度 (非颜色)
}

# 支持的分辨率（CDN 路径段）
RES_LIST = ["1k", "2k", "4k"]
# 本次额外要拉取的目标分辨率（默认无 -> 仅确保 1K）
TARGET_RES = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in RES_LIST else None

CDN = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/{res}/{slug}/{slug}_{suf}_{res}.jpg"
UA = {"User-Agent": "campus-td-fetch/1.0 (educational, CC0)"}

# 1K 始终是项目基准/fallback，必须存在
WANT = ["1k"]
if TARGET_RES:
    WANT.append(TARGET_RES)


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1024:
        return "skip"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return "ok" if os.path.getsize(dest) > 1024 else "empty"
    except Exception as e:
        return f"err:{e}"


def main():
    manifest = {}
    total = 0
    for target, slug in MY_SET.items():
        folder = os.path.join(TEX, slug)
        os.makedirs(folder, exist_ok=True)
        res_roles = {}
        for res in RES_LIST:
            # 仅拉取 WANT 中的分辨率；但磁盘若已有该 res 的 diff 也记录（累积，不删）
            diff_dest = os.path.join(folder, f"{slug}_diff_{res}.jpg")
            if res not in WANT and not os.path.exists(diff_dest):
                continue
            roles = {}
            for role, suf in ROLE_SUFFIX.items():
                url = CDN.format(res=res, slug=slug, suf=suf)
                dest = os.path.join(folder, f"{slug}_{suf}_{res}.jpg")
                st = fetch(url, dest)
                if st in ("ok", "skip"):
                    roles[role] = os.path.relpath(dest, ROOT).replace("\\", "/")
                    if st == "ok":
                        total += 1
            if roles:
                res_roles[res] = {"slug": slug, "roles": roles}
        manifest[target] = {"slug": slug, "res": res_roles}
        got = ",".join(f"{r}({len(res_roles[r]['roles'])})" for r in sorted(res_roles))
        print(f"  {target:8s} {slug:18s} [{got}]")
    with open(os.path.join(TEX, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nmanifest.json written; newly downloaded files: {total}; target res: {TARGET_RES or '1k(only)'}")


if __name__ == "__main__":
    main()
