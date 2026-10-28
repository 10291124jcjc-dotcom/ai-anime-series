# -*- coding: utf-8 -*-
"""拼接：1 分钟的上下两段、合集；换掉成片里的一段。只用 ffmpeg。

用法：
  python compile.py concat 输出.mp4 A.mp4 B.mp4 ...            按顺序拼成一条（上下两段、几集拼合集都用它）
  python compile.py concat 输出.mp4 ep01.mp4 ep02.mp4 --titles "第1集 抢煎饼" "第2集 偷冰淇淋"
                                                                合集每集前加 1.5 秒黑底白字小标题
  python compile.py replace 成片.mp4 开始秒 结束秒 补拍.mp4 输出.mp4
                                                                把成片里 [开始, 结束) 这段换成补拍（补拍会裁成同样长度）

所有片段先统一成第一条的分辨率、30 帧、立体声再拼，避免花屏和音画不同步。
"""
import json
import os
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

FONTS = ["C:/Windows/Fonts/msyhbd.ttc", "/System/Library/Fonts/PingFang.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("ffmpeg 出错：\n" + r.stderr[-1500:])
    return r


def size(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "json", path])
    s = json.loads(r.stdout)["streams"][0]
    return s["width"], s["height"]


def has_audio(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(r.stdout.strip())


def normalize(src, dst, w, h, start=None, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if not has_audio(src):
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest"]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1,format=yuv420p",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-ar", "44100", "-ac", "2", dst]
    run(cmd)


def title_card(text, dst, w, h):
    from PIL import Image, ImageDraw, ImageFont
    font = next((ImageFont.truetype(p, h // 12) for p in FONTS if os.path.exists(p)), ImageFont.load_default())
    im = Image.new("RGB", (w, h), "black")
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=font)
    d.text(((w - tw) / 2, h / 2 - h // 20), text, fill="white", font=font)
    png = dst + ".png"
    im.save(png)
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "1.5", "-i", png, "-f", "lavfi", "-t", "1.5",
         "-i", "anullsrc=r=44100:cl=stereo", "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-c:a", "aac",
         "-ar", "44100", "-ac", "2", dst])
    os.remove(png)


def concat_files(parts, out):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in parts:
            f.write("file '%s'\n" % os.path.abspath(p).replace("\\", "/").replace("'", r"'\''"))
        lst = f.name
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    os.remove(lst)


def cmd_concat(args):
    titles = []
    if "--titles" in args:
        i = args.index("--titles")
        titles = args[i + 1:]
        args = args[:i]
    out, files = args[0], args[1:]
    if len(files) < 1:
        sys.exit("至少给一条视频")
    w, h = size(files[0])
    tmp = tempfile.mkdtemp()
    parts = []
    for k, f in enumerate(files):
        if k < len(titles):
            t = os.path.join(tmp, f"t{k}.mp4")
            title_card(titles[k], t, w, h)
            parts.append(t)
        n = os.path.join(tmp, f"{k}.mp4")
        normalize(f, n, w, h)
        parts.append(n)
    concat_files(parts, out)
    print(f"拼好了：{out}（{len(files)} 条，{w}×{h}）")


def cmd_replace(args):
    base, a, b, patch, out = args[0], float(args[1]), float(args[2]), args[3], args[4]
    w, h = size(base)
    tmp = tempfile.mkdtemp()
    p1, p2, p3 = (os.path.join(tmp, f"{i}.mp4") for i in range(3))
    normalize(base, p1, w, h, 0, a)
    normalize(patch, p2, w, h, 0, b - a)
    normalize(base, p3, w, h, b, None)
    concat_files([p1, p2, p3], out)
    print(f"换好了：{out}（{a:g}–{b:g} 秒换成补拍）")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    {"concat": cmd_concat, "replace": cmd_replace}.get(cmd, lambda a: sys.exit(__doc__))(args)


if __name__ == "__main__":
    main()
