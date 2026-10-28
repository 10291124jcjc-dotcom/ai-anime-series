# -*- coding: utf-8 -*-
"""series.json + episode.json → 即梦画布里直接复制的提示词。

用法：
  python make_prompts.py SERIES sheets              每个角色 / 群体角色 / 场景一份设定图提示词 → SERIES/prompts/
  python make_prompts.py SERIES ep01                故事板 + 视频提示词 → SERIES/ep01/prompts/
  python make_prompts.py SERIES ep01 panel 6        只重出故事板第 6 格（1 分钟的加 --part B）
  python make_prompts.py SERIES ep01 patch 5-6      只补拍第 5–6 格的短视频（1 分钟的加 --part B）

提示词不是死模板：@图 编号按这集出场的角色和场景排（没出场的不传不写，故事板排最后），
宫格的行列按镜头数定，视频提示词的镜头条数和故事板一一对应，并检查秒数。
参考图上限默认 9 张（第三方说法，以即梦当前限制为准），可用环境变量 JIMENG_MAX_REFS 改。
"""
import json
import math
import os
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

MAX_REFS = int(os.environ.get("JIMENG_MAX_REFS", 9))
MAX_SEG = 30          # 即梦 Seedance 一次最多 30 秒
CUT = "———————— 以下整段复制 ————————"
GRIDS = {4: (2, 2), 6: (2, 3), 8: (2, 4), 9: (3, 3), 10: (2, 5), 12: (3, 4)}
CN_NUM = {4: "四", 6: "六", 8: "八", 9: "九", 10: "十", 12: "十二"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def grid_of(n):
    if n in GRIDS:
        return GRIDS[n]
    cols = math.ceil(math.sqrt(n))
    return math.ceil(n / cols), cols


def grid_name(n):
    return f"{CN_NUM[n]}宫格" if n in CN_NUM else f"{n} 格"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
    print("写好了：" + path)


# ---------- 设定图 ----------

def sheets(series_dir, s):
    out = os.path.join(series_dir, "prompts")
    for c in s.get("characters", []):
        exp = "、".join(c.get("expressions") or ["开心", "惊吓", "生气", "委屈", "得意", "无奈"])
        pos = "、".join(c.get("poses") or ["站着", "奔跑", "抱东西", "跳起来"])
        ne, npos = len(c.get("expressions") or [1] * 6), len(c.get("poses") or [1] * 4)
        body = (f"角色设定图，同一个角色的全身三视图（正面、侧面、背面）、{ne} 个不同表情（{exp}）、"
                f"{npos} 个动作姿势（{pos}）和剪影，排版干净，左上角写角色名。\n"
                f"角色：{c['look']}。\n{s.get('sheet_style', '')}")
        head = f"【即梦画布｜图片生成｜比例 1:1 或 16:9｜出 4 张挑 1 张，下载存成 {c['ref']}】"
        write(os.path.join(out, f"设定_{c['name']}.txt"), f"{head}\n{CUT}\n\n{body}")
    for g in s.get("groups", []):
        if not g.get("ref"):
            continue
        body = (f"群体角色设定图：{g['look']}。画出 5 只不同姿势（站着、飞、啄、得意、惊吓），"
                f"外形统一，排版干净，左上角写名字。\n{s.get('sheet_style', '')}")
        head = f"【即梦画布｜图片生成｜比例 1:1 或 16:9｜出 4 张挑 1 张，下载存成 {g['ref']}】"
        write(os.path.join(out, f"设定_{g['name']}.txt"), f"{head}\n{CUT}\n\n{body}")
    for sc in s.get("scenes", []):
        if not sc.get("ref"):
            continue
        body = (f"场景设定图，没有任何角色：{sc['name']}，{sc['look']}。广角全景，白天，"
                f"{s.get('style', '')}画面中没有文字。")
        head = f"【即梦画布｜图片生成｜比例 {s.get('ratio', '16:9')}｜出 4 张挑 1 张，下载存成 {sc['ref']}】"
        write(os.path.join(out, f"场景_{sc['name']}.txt"), f"{head}\n{CUT}\n\n{body}")


# ---------- 一集 ----------

def pick(items, ids, what):
    by = {x["id"]: x for x in items}
    miss = [i for i in ids if i not in by]
    if miss:
        sys.exit(f"episode.json 里的{what} {miss} 在 series.json 里找不到")
    return [by[i] for i in ids]


def check_parts(e):
    parts = e["parts"]
    if not parts:
        sys.exit("episode.json 里没有镜头")
    per = e["duration"] / len(parts)
    for k, p in enumerate(parts):
        tag = "ABCDEFGH"[k]
        total = sum(sh["dur"] for sh in p["shots"])
        if abs(total - per) > 0.01:
            sys.exit(f"第 {tag} 段镜头加起来 {fmt(total)} 秒，应该是 {fmt(per)} 秒（总时长 {e['duration']} ÷ {len(parts)} 段）")
        if per > MAX_SEG:
            sys.exit(f"每段 {fmt(per)} 秒，超过即梦一次最多 {MAX_SEG} 秒，要拆成更多段")
        for i, sh in enumerate(p["shots"], 1):
            if sh["dur"] < 2:
                sys.exit(f"第 {tag} 段镜头 {i} 只有 {fmt(sh['dur'])} 秒，至少 2 秒，不然动作做不完、画面会碎")
            if sh["dur"] > 5:
                print(f"提醒：第 {tag} 段镜头 {i} 有 {fmt(sh['dur'])} 秒，没台词的动作戏超过 5 秒容易拖")
        n = len(p["shots"])
        if n not in GRIDS:
            print(f"提醒：第 {tag} 段 {n} 个镜头排不成整齐的宫格，建议 6 或 9 个")


def refs_for(series_dir, s, e, part_tag, multi):
    """按出场顺序排参考图：角色 → 有设定图的群体角色 → 场景图 → 故事板（最后）。"""
    cast = pick(s.get("characters", []), e.get("cast", []), "角色")
    groups = pick(s.get("groups", []), e.get("groups", []), "群体角色")
    scenes = pick(s.get("scenes", []), [e["scene"]] if e.get("scene") else [], "场景")
    refs = []
    for c in cast:
        refs.append({"kind": "char", "name": c["name"], "file": c["ref"], "item": c})
    for g in groups:
        if g.get("ref"):
            refs.append({"kind": "group", "name": g["name"], "file": g["ref"], "item": g})
    for sc in scenes:
        if sc.get("ref"):
            refs.append({"kind": "scene", "name": sc["name"], "file": sc["ref"], "item": sc})
    sb = f"故事板_{part_tag}.png" if multi else "故事板.png"
    refs.append({"kind": "board", "name": "故事板", "file": sb, "item": None})
    if len(refs) > MAX_REFS:
        sys.exit(f"这集要传 {len(refs)} 张参考图，超过上限 {MAX_REFS}。把配角的设定图用 "
                 f"`python grid.py grid 配角拼图.png 图1 图2 ...` 拼成一张，或者减少出场角色")
    for i, r in enumerate(refs, 1):
        r["n"] = i
        if r["kind"] != "board" and not os.path.exists(os.path.join(series_dir, r["file"])):
            print(f"提醒：{r['file']} 还不存在，先在即梦画布里出好设定图再生成视频")
    return refs, cast, groups, scenes


def storyboard_prompt(s, e, part, refs, cast, groups, scenes, ep_dir_name, tag, multi):
    shots = part["shots"]
    n = len(shots)
    rows, cols = grid_of(n)
    who = "，".join(f"图 {r['n']} 是{r['name']}" for r in refs if r["kind"] in ("char", "group"))
    lines = [
        f"生成 {s.get('ratio', '16:9')} {grid_name(n)}（{rows} 行 {cols} 列）动画分镜素描草图。"
        f"要求：黑白铅笔素描、画面干净不杂乱、不要复杂背景、无多余画面、无文字，每格左上角标镜头序号。"
        + (f"角色外形参考：{who}。" if who else ""),
    ]
    extra = [f"{g['name']}：{g['look']}" for g in groups if not g.get("ref")]
    place = scenes[0] if scenes else None
    if place:
        lines.append(f"全部 {n} 格在同一个{place['name']}，同一个{e.get('time', '时间')}。")
    if extra:
        lines.append("；".join(extra) + "。")
    lines.append("")
    for i, sh in enumerate(shots, 1):
        lines.append(f"镜头 {i}：{sh.get('sketch') or sh['desc']}。")
    sel = "、".join(f"{r['name']}设定图" for r in refs if r["kind"] != "board")
    out = f"{ep_dir_name}/故事板_{tag}.png" if multi else f"{ep_dir_name}/故事板.png"
    head = (f"【即梦画布｜图片生成｜框选节点：{sel}｜比例 {s.get('ratio', '16:9')}（1:1 也行）｜"
            f"出 4 张挑 1 张，下载存成 {out}，再拖回画布】")
    return head + "\n" + CUT + "\n\n" + "\n".join(lines)


def char_lines(refs, groups):
    out = []
    for r in refs:
        if r["kind"] == "char":
            out.append(f"@图{r['n']} 是{r['name']}，外形必须和参考图完全一致：{r['item']['look']}。")
        elif r["kind"] == "group":
            out.append(f"@图{r['n']} 是{r['name']}的设定图：{r['item']['look']}。")
    for g in groups:
        if not g.get("ref"):
            out.append(f"{g['name']}：{g['look']}。")
    return out


def video_prompt(s, e, shots, refs, groups, scenes, start, dur, seg_label, note=""):
    board = [r for r in refs if r["kind"] == "board"][0]
    sc = [r for r in refs if r["kind"] == "scene"]
    lines = [f"根据故事板 @图{board['n']} 生成分镜视频，仅参考其镜头设计、动作节奏、景别和运镜，禁止直接拼接故事板图片。{note}", ""]
    lines += char_lines(refs, groups)
    place = scenes[0] if scenes else None
    look = s.get("style", "")
    if not s.get("dialogue"):
        look += "没有台词。"
    if place:
        look += f"全片在同一个{place['name']}、同一个{e.get('time', '时间')}：{place['look']}。"
        if sc:
            look += f"场景参考 @图{sc[0]['n']}。"
    lines += ["", "风格：" + look, ""]
    if e.get("continuity"):
        lines += ["连贯要求：" + "；".join(e["continuity"]) + "。", ""]
    t = start
    for i, sh in enumerate(shots, 1):
        lines.append(f"镜头 {sh.get('_no', i)}｜{fmt(t)}-{fmt(t + sh['dur'])}s：{sh['desc']}。")
        lines.append(f"音效：{sh.get('sfx', '')}")
        lines.append("")
        t += sh["dur"]
    lines.append("画面里不要出现任何文字、字幕、商标。")
    sel = "、".join((f"@图{r['n']} {r['name']}设定图" if r["kind"] != "board" else f"@图{r['n']} 故事板") for r in refs)
    head = (f"【即梦画布｜视频生成｜Seedance 2.5 全能参考｜框选节点：{sel}｜{s.get('ratio', '16:9')}｜"
            f"{fmt(dur)} 秒｜先 480p，满意再超清｜{seg_label}】")
    return head + "\n" + CUT + "\n\n" + "\n".join(lines)


def episode(series_dir, s, ep, args):
    ep_dir = os.path.join(series_dir, ep)
    e = load(os.path.join(ep_dir, "episode.json"))
    check_parts(e)
    parts = e["parts"]
    multi = len(parts) > 1
    part_arg = "A"
    if "--part" in args:
        part_arg = args[args.index("--part") + 1].upper()
    out = os.path.join(ep_dir, "prompts")

    if args and args[0] == "panel":
        k = int(args[1])
        pi = "ABCDEFGH".index(part_arg)
        refs, cast, groups, scenes = refs_for(series_dir, s, e, part_arg, multi)
        sh = parts[pi]["shots"][k - 1]
        who = "，".join(f"图 {r['n']} 是{r['name']}" for r in refs if r["kind"] in ("char", "group"))
        n = len(parts[pi]["shots"])
        body = (f"生成一格动画分镜素描草图，比例和{grid_name(n)}里的一格相同。要求：黑白铅笔素描、画面干净、无文字，"
                f"左上角标序号 {k}。角色外形参考：{who}。\n\n镜头 {k}：{sh.get('sketch') or sh['desc']}。")
        write(os.path.join(out, f"故事板单格_{part_arg}{k}.txt"),
              "【即梦画布｜图片生成｜框选角色设定图节点｜出 4 张挑 1 张，用 grid.py grid 拼回宫格】\n" + CUT + "\n\n" + body)
        return

    if args and args[0] == "patch":
        a, b = (int(x) for x in args[1].split("-"))
        pi = "ABCDEFGH".index(part_arg)
        refs, cast, groups, scenes = refs_for(series_dir, s, e, part_arg, multi)
        shots = parts[pi]["shots"]
        sel = []
        start = sum(x["dur"] for x in shots[:a - 1])
        for i in range(a, b + 1):
            sh = dict(shots[i - 1])
            sh["_no"] = i
            sel.append(sh)
        dur = sum(x["dur"] for x in sel)
        if dur < 4:
            print("提醒：补拍不到 4 秒，即梦最短一般 4 秒，可以多带一个相邻镜头，剪的时候再切掉")
        note = f"这次只生成故事板第 {a}–{b} 格，开头和结尾都是硬切。"
        text = video_prompt(s, e, sel, refs, groups, scenes, 0, dur, f"补拍第 {part_arg} 段镜头 {a}–{b}", note)
        write(os.path.join(out, f"补拍_{part_arg}{a}-{b}.txt"), text)
        print(f"成片里要换掉的时间段：{fmt(start)}–{fmt(start + dur)} 秒（这一段内）。"
              f"用 python compile.py replace 成片.mp4 {fmt(start)} {fmt(start + dur)} 补拍.mp4 新成片.mp4")
        return

    ep_name = os.path.basename(os.path.normpath(ep_dir))
    per = e["duration"] / len(parts)
    for k, p in enumerate(parts):
        tag = "ABCDEFGH"[k]
        refs, cast, groups, scenes = refs_for(series_dir, s, e, tag, multi)
        sb = storyboard_prompt(s, e, p, refs, cast, groups, scenes, ep_name, tag, multi)
        label = f"第 {tag} 段（共 {len(parts)} 段）" if multi else "整集"
        vp = video_prompt(s, e, p["shots"], refs, groups, scenes, 0, per, label)
        suffix = f"_{tag}" if multi else ""
        write(os.path.join(out, f"1_故事板{suffix}.txt"), sb)
        write(os.path.join(out, f"2_视频{suffix}.txt"), vp)
        print(f"{label}：{len(p['shots'])} 格（{'×'.join(map(str, grid_of(len(p['shots']))))}），"
              f"参考图 {len(refs)} 张：" + "、".join(f"@图{r['n']} {r['name']}" for r in refs))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    series_dir, what = sys.argv[1], sys.argv[2]
    s = load(os.path.join(series_dir, "series.json"))
    if what == "sheets":
        sheets(series_dir, s)
    else:
        episode(series_dir, s, what, sys.argv[3:])


if __name__ == "__main__":
    main()
