# -*- coding: utf-8 -*-
"""检查环境并建好系列文件夹。

用法：
  python setup_check.py SERIES          检查 Python / ffmpeg / Pillow；建 SERIES/refs、SERIES/log.md；复制 series.json 模板
  python setup_check.py SERIES ep02     再建一集：SERIES/ep02/（clips、prompts）+ 复制 episode.json 模板
"""
import os
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(os.path.dirname(HERE), "templates")


def ok(name, good, hint=""):
    print(("  OK  " if good else "  缺  ") + name + ("" if good else "：" + hint))
    return good


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    series = sys.argv[1]
    print("检查环境：")
    good = ok("Python 3.9+", sys.version_info >= (3, 9), "装新版 Python")
    for tool in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([tool, "-version"], capture_output=True, check=True)
            good &= ok(tool, True)
        except Exception:
            good &= ok(tool, False, "macOS: brew install ffmpeg；Windows: winget install Gyan.FFmpeg")
    try:
        import PIL  # noqa: F401
        good &= ok("Pillow", True)
    except ImportError:
        good &= ok("Pillow", False, "pip install pillow")

    os.makedirs(os.path.join(series, "refs"), exist_ok=True)
    os.makedirs(os.path.join(series, "prompts"), exist_ok=True)
    sj = os.path.join(series, "series.json")
    if not os.path.exists(sj):
        shutil.copy(os.path.join(TPL, "series.json"), sj)
        print("复制了 series.json 模板：" + sj)
    log = os.path.join(series, "log.md")
    if not os.path.exists(log):
        with open(log, "w", encoding="utf-8") as f:
            f.write("# 已拍记录\n\n| 集 | 名字 | 地点 | 目标 | 用到的招牌能力 | 结尾笑点 |\n| --- | --- | --- | --- | --- | --- |\n")
        print("建好了已拍记录：" + log)

    if len(sys.argv) > 2:
        ep = os.path.join(series, sys.argv[2])
        for d in ("clips", "prompts"):
            os.makedirs(os.path.join(ep, d), exist_ok=True)
        ej = os.path.join(ep, "episode.json")
        if not os.path.exists(ej):
            shutil.copy(os.path.join(TPL, "episode.json"), ej)
            print("复制了 episode.json 模板：" + ej)
    print("全部就绪。" if good else "有缺的，装好再继续。")


if __name__ == "__main__":
    main()
