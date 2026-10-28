# -*- coding: utf-8 -*-
"""检查即梦生成的视频：每 0.5 秒抽一帧拼成一张图，再列出镜头切换点，给 Claude 用 Read 看。

用法：
  python review_clip.py SERIES ep01            检查 ep01/clips/ 里所有 mp4
  python review_clip.py SERIES ep01 某条.mp4    只检查一条

输出在 ep01/review/：<视频名>_帧.jpg（每 0.5 秒一帧，每行 8 帧），终端里打印时长、分辨率、切换点和该有几个镜头。
看什么：角色有没有变样、是不是照故事板拍的、动作有没有断、有没有乱码文字、镜头数和故事板对不对得上。
"""
import glob
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
             "-of", "json", path])
    info = json.loads(r.stdout or "{}")
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    return float(info.get("format", {}).get("duration", 0)), v.get("width"), v.get("height"), a


def cuts(path):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "select='gt(scene,0.3)',metadata=print",
             "-an", "-f", "null", "-"])
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    series, ep = sys.argv[1], sys.argv[2]
    ep_dir = os.path.join(series, ep)
    files = [sys.argv[3]] if len(sys.argv) > 3 else sorted(glob.glob(os.path.join(ep_dir, "clips", "*.mp4")))
    if not files:
        sys.exit(f"{ep_dir}/clips/ 里没有 mp4，先把即梦下载的视频放进去")
    shots = None
    epj = os.path.join(ep_dir, "episode.json")
    if os.path.exists(epj):
        e = json.load(open(epj, encoding="utf-8"))
        shots = [len(p["shots"]) for p in e["parts"]]
    out = os.path.join(ep_dir, "review")
    os.makedirs(out, exist_ok=True)
    for f in files:
        d, w, h, a = probe(f)
        name = os.path.splitext(os.path.basename(f))[0]
        rows = max(1, int(d * 2) // 8 + 1)
        img = os.path.join(out, f"{name}_帧.jpg")
        run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vf", f"fps=2,scale=240:-1,tile=8x{rows}",
             "-frames:v", "1", img])
        c = cuts(f)
        print(f"{os.path.basename(f)}：{d:.1f} 秒，{w}×{h}，{'有声音' if a else '没有声音'}")
        print(f"  镜头切换点：{', '.join('%.1f' % x for x in c) or '没有'}（约 {len(c) + 1} 个镜头）")
        if shots:
            print(f"  故事板每段格数：{shots}；切换点数明显少于格数，说明有镜头没拍出来或被合并了")
        print(f"  抽帧图：{img}")


if __name__ == "__main__":
    main()
