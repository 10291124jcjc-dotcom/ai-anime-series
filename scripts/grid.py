# -*- coding: utf-8 -*-
"""拼宫格、改排版。只用 Pillow。

用法：
  python grid.py grid 输出.png 图1 图2 ... [--cols 3]      单格图拼成宫格，每格左上角标序号（故事板某格重出后拼回去；配角设定图拼成一张）
  python grid.py split 故事板.png 输出文件夹 [--rows 3 --cols 3]   把一张宫格故事板切成单格，方便只换其中一格
  python grid.py rewrap 宽图.png [--parts 4 --rows 2]       横向很长的图（比如车的四视图）等分后改排成几行，宽高比回到 0.4–2.5 以内

不传 --cols 时按格数自动定：4→2×2，6→2×3，9→3×3，其他取接近正方形。
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

GRIDS = {4: (2, 2), 6: (2, 3), 8: (2, 4), 9: (3, 3), 10: (2, 5), 12: (3, 4)}
FONTS = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/arialbd.ttf",
         "/System/Library/Fonts/PingFang.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def opt(args, name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return int(v)
    return default


def font(size):
    for p in FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def layout(n, cols):
    if cols:
        return math.ceil(n / cols), cols
    if n in GRIDS:
        return GRIDS[n]
    c = math.ceil(math.sqrt(n))
    return math.ceil(n / c), c


def cmd_grid(args):
    cols = opt(args, "--cols", 0)
    out, files = args[0], args[1:]
    if not files:
        sys.exit("至少给一张图")
    ims = [Image.open(f).convert("RGB") for f in files]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    rows, cols = layout(len(ims), cols)
    gap = max(8, w // 60)
    canvas = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), "white")
    d = ImageDraw.Draw(canvas)
    f = font(max(24, h // 12))
    for k, im in enumerate(ims):
        r, c = divmod(k, cols)
        x = gap + c * (w + gap) + (w - im.width) // 2
        y = gap + r * (h + gap) + (h - im.height) // 2
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + im.width - 1, y + im.height - 1], outline="black", width=max(2, w // 300))
        d.text((x + w // 40, y + h // 40), str(k + 1), fill="black", font=f,
               stroke_width=max(2, h // 150), stroke_fill="white")
    canvas.save(out)
    print(f"拼好了：{out}（{rows}×{cols}，{canvas.width}×{canvas.height}）")


def cmd_split(args):
    rows = opt(args, "--rows", 3)
    cols = opt(args, "--cols", 3)
    src, outdir = args[0], args[1]
    os.makedirs(outdir, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w, h = im.width / cols, im.height / rows
    k = 0
    for r in range(rows):
        for c in range(cols):
            k += 1
            im.crop((round(c * w), round(r * h), round((c + 1) * w), round((r + 1) * h))).save(
                os.path.join(outdir, f"{k:02d}.png"))
    print(f"切成 {k} 格：{outdir}")


def cmd_rewrap(args):
    parts = opt(args, "--parts", 4)
    rows = opt(args, "--rows", 2)
    src = args[0]
    im = Image.open(src).convert("RGB")
    cols = math.ceil(parts / rows)
    pw = im.width / parts
    tiles = [im.crop((round(i * pw), 0, round((i + 1) * pw), im.height)) for i in range(parts)]
    canvas = Image.new("RGB", (round(pw) * cols, im.height * rows), "white")
    for k, t in enumerate(tiles):
        r, c = divmod(k, cols)
        canvas.paste(t, (c * round(pw), r * im.height))
    base, ext = os.path.splitext(src)
    out = f"{base}_{rows}行{ext}"
    canvas.save(out)
    print(f"改好了：{out}（{canvas.width}×{canvas.height}，宽高比 {canvas.width / canvas.height:.2f}）")
    print("注意：是按宽度等分切的，如果几个角度之间间距不均，切口可能落在图上，改完看一眼")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    {"grid": cmd_grid, "split": cmd_split, "rewrap": cmd_rewrap}.get(cmd, lambda a: sys.exit(__doc__))(args)


if __name__ == "__main__":
    main()
