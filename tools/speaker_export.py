# -*- coding: utf-8 -*-
"""导出「说话人映射」——把游戏对话资产里本来就有的 speaker 字段摊成表。

    python tools/extract_textassets.py --out <dir>              # 一次性: 从 data.unity3d 取出对话 JSON
    python tools/speaker_export.py --assets <dir> --csv "docs/译本.csv" \
           [--gridly <gridly_en_current.json>] --out tools/export

为什么有这张表
    译本底表 9 列里没有「说话人」「上一句」。外评留下的「待实机」行一半是
    「laddies 指不指女孩」「them/Is she 指谁」「您还是你」「old hag 是不是威尔玛」——
    这些都能由对话资产直接回答，不必进游戏。

数据来源（已实证，不是猜）
    data.unity3d 的 TextAsset 里有 1,261 个对白文件：
        { "ID": "DLG_5_3_VSQ_04",
          "Participants": ["Player", "Muffy"],
          "Conversation": { "1": { "Author": "Player", "Text": "DLG_5_3_VSQ_04_001",
                                   "Next": [2], "Action": "..." }, ... } }
    对照 Assembly-CSharp:
        StorySystem.Models.Nodes.Node{ID, Author, Text, IsThought, DisplayName, Next}
        StorySystem.Models.Intermediate.IntermediateConversation{ID, Participants, Conversation}
    节点的 Text 就是游戏按 recordID 去 Gridly 取的键，Author 就是这句的说话人，
    Participants 是该对话的同场人物。所以 `node(K).Author` 就是「游戏显示键 K 那行时的说话人」，
    与键→正文来自哪张表无关（这层关系是资产自己带的，不需要跨表推断）。

两条边界（都写进报告，不假装全覆盖）
    * XUAT_ 行不是对话节点，只能按「英文串与当前 Gridly 某键正文相同」反推，
      单独输出、标推断；同文才认，不按序号或相邻行猜。
    * 有 4,000+ 个键没有对话节点（I2-only 键、Timeline 直接播的 CUT 行等），
      这些行说话人留空 —— 空就是"资产里没有"，不补。

格式：UTF-8 TSV，一行一个「键 × 节点」；同一键被多个分支复用时多行。
"""
import argparse
import csv
import difflib
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

TAG_RE = re.compile(r"<[/#a-zA-Z][^>]*>")
WS_RE = re.compile(r"\s+")
NB = chr(92) + "n"

# 资产里只有内部 ID、没有显示名的说话人。**这里写了就以这里为准**，否则才去译本裸名行找。
# 每条都要能在译本里指到出处（见行内注释）—— 没有证据的宁可留空。
AUTHOR_NOTES = {
    # 游戏侧用 Player 表示玩家角色（伊莉丝），译本里没有 "Player" 这个裸名行
    "Player": "伊莉丝",
    "FlavourText": "环境/旁白（非人物）",
    "GoldenGirl": "金发女孩（过场）",
    # Lebkuchen 是「名字/食品」同形：作人物是斯佩尔特，作食品(ITM_F_N_08)才是姜饼。
    # 裸名行会取到食品那个「姜饼」，所以必须在这里钉住（同 NAME_GUARD/NAME_OVERRIDE 的口径）。
    "Lebkuchen": "斯佩尔特",
    # 资产写 ASCII "Grune"，译文里是 Grüne → 格吕妮（117 行）
    "Grune": "格吕妮",
    "Murim": "穆里姆",                 # DLG_4_5_WCR_A_04_012「去陪穆里姆大人吧」
    "?????": "未标注（资产未填）",
    # 以下 6 个在译本里没有「裸名行」（名字只以 <sprite> 或称呼出现），按译文口径钉住：
    # 名牌用的是英文串 "Father Hans"（display 已有该键 → 汉斯神父），所以显示名跟名牌一致。
    "Hans": "汉斯神父",
    "Aziel": "阿兹尔",                 # XUAT_00214「穆里姆大人和阿兹尔女士……」
    "Ozzy": "奥兹",                    # XUAT_01196 配音阵容串「……古斯塔夫\n奥兹」
    "Valerie": "瓦莱丽",               # CUT_END_GG_03_004~021 共 4 行
    "Demon": "恶魔",                   # 泛指：DEMON_PARADE=恶魔巡游、CUT_END_GG_02_003「恶魔」
    "Anonymous": "匿名",               # 译本没有出现；无具名说话人的兜底标签
}


def clean_cell(s):
    """TSV 单元格里不能有制表符/换行 —— 英文原文里两种都有（多行台词）。"""
    return (s or "").replace("\t", " ").replace("\r", " ").replace("\n", "⏎")


def norm(s):
    return WS_RE.sub(" ", TAG_RE.sub("", s or "")).strip()


def loose(s):
    """比 Norm 再宽一档：折省略号/破折号/换行/标点，只用于「同文」反推 XUAT。"""
    s = (s or "").replace("\u2026", "...").replace(NB, " ").replace("<br>", " ")
    s = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def sanitize(txt):
    """去掉对象/数组尾逗号(字符串内的不动)。资产里有 145 个文件带尾逗号, 标准 json 解不开。"""
    out = []
    i, n = 0, len(txt)
    in_str = esc = False
    while i < n:
        ch = txt[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and txt[j] in " \t\r\n":
                j += 1
            if j < n and txt[j] in "}]":
                i = j
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_conversations(assets_dir, stats):
    convs = {}
    for path in sorted(glob.glob(os.path.join(assets_dir, "*.txt"))):
        base = os.path.basename(path)
        if base.startswith("_index"):
            continue
        try:
            txt = open(path, encoding="utf-8-sig").read()
        except UnicodeDecodeError:
            stats["skip_encoding"] += 1
            continue
        doc = None
        for attempt in (0, 1):
            try:
                doc = json.loads(txt if attempt == 0 else sanitize(txt), strict=False)
                break
            except Exception:
                continue
        if doc is None:
            stats["skip_json"] += 1
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("Conversation"), dict):
            stats["skip_nonconv"] += 1
            continue
        cid = doc.get("ID") or base.split("__")[0]
        nodes = {}
        for nid, node in doc["Conversation"].items():
            if not isinstance(node, dict):
                continue
            stats["nodes"] += 1
            nodes[str(nid)] = node
        convs[cid] = {"participants": [str(p) for p in (doc.get("Participants") or [])],
                      "nodes": nodes, "file": base}
        stats["conversations"] += 1
    return convs


def numeric(nid):
    return (0, int(nid)) if re.match(r"^\d+$", nid) else (1, nid)


def build_edges(nodes):
    """每个节点的「下一个有 Text 的节点」+ 反向索引。Action/START/END 要穿过。"""
    def has_text(nid):
        n = nodes.get(nid)
        return bool(n and n.get("Text"))

    memo = {}

    def next_texts(nid):
        if nid in memo:
            return memo[nid]
        memo[nid] = []
        out = []
        for nxt in (nodes.get(nid, {}).get("Next") or []):
            nxt = str(nxt)
            if has_text(nxt):
                out.append(nxt)
            elif nxt in nodes and nxt != nid:
                out.extend(next_texts(nxt))
        memo[nid] = list(dict.fromkeys(out))
        return memo[nid]

    prev_texts = defaultdict(list)
    for nid in nodes:
        if not has_text(nid):
            continue
        for s in next_texts(nid):
            if nid not in prev_texts[s]:
                prev_texts[s].append(nid)
    return lambda nid: prev_texts.get(nid, []), next_texts


def build_name_table(rows, authors):
    """显示名：AUTHOR_NOTES 优先（同形异义必须钉住），其余只用译本「裸名行」(英文原文 == ID)。"""
    by_norm = defaultdict(Counter)
    for r in rows:
        e, z = norm(r["英文原文"]), (r["中文译文"] or "").strip()
        if e and z:
            by_norm[e][z] += 1
    names = {}
    for a in authors:
        if a in AUTHOR_NOTES:
            names[a] = AUTHOR_NOTES[a]
            continue
        c = by_norm.get(a)
        names[a] = c.most_common(1)[0][0] if c else ""
    return names


def words(s):
    return re.findall(r"[0-9a-z']+", (s or "").lower())


def ngram_index(values, n=4):
    """4 词窗倒排: 旧串与现行正文若只改了几个词, 仍能靠共享词窗找回来。"""
    idx = defaultdict(set)
    for key, val in values:
        ws = words(val)
        for i in range(len(ws) - n + 1):
            idx[tuple(ws[i:i + n])].add(key)
    return idx


def nearest(query, gvals, idx, min_ratio=0.55, n=4):
    """返回 [(key, ratio)] —— 只留共享词窗最多的前两个候选, 避免拿噪声当证据。"""
    ws = words(query)
    if len(ws) < n:
        return []
    score = Counter()
    for i in range(len(ws) - n + 1):
        for key in sorted(idx.get(tuple(ws[i:i + n]), ())):
            score[key] += 1
    best = []
    # 排序必须完全确定: Counter 的 most_common 在计数相同时按插入/哈希顺序, 而字符串哈希
    # 每个进程都不同 —— 不定序会让两次导出的文件不一样(实测差 295 B)。
    for key, _cnt in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
        r = difflib.SequenceMatcher(None, " ".join(ws), " ".join(words(gvals[key]))).ratio()
        if r >= min_ratio:
            best.append((key, round(r, 3)))
    best.sort(key=lambda x: (-x[1], x[0]))
    return best[:2]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assets", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--gridly", default=None,
                    help="当前游戏磁盘上的 Gridly 英文表 (gridly_en_current.json), 给了才做 XUAT 推断")
    ap.add_argument("--i2", default=None,
                    help="当前游戏磁盘上的 I2 英文表 (i2_terms_en_current.json), 只用于交叉印证")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out or os.path.join(repo, "tools", "export")
    os.makedirs(out_dir, exist_ok=True)

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    has_rev = "修订译文" in rows[0].keys()
    eff = lambda r: (((r.get("修订译文") or "").strip() or r["中文译文"]) if has_rev else r["中文译文"]) or ""
    zh_by_key = {r["记录键"]: eff(r).strip() for r in rows}
    en_by_key = {r["记录键"]: (r["英文原文"] or "").strip() for r in rows}
    keyset = set(zh_by_key)

    stats = Counter()
    convs = load_conversations(args.assets, stats)

    hits = defaultdict(list)          # 键 -> [(对话ID, 节点ID, 作者, 显示名)]
    authors = set()
    for cid, c in convs.items():
        for nid in sorted(c["nodes"], key=numeric):
            node = c["nodes"][nid]
            t = (node.get("Text") or "").strip()
            if not t:
                continue
            if t not in keyset:
                stats["node_text_not_key"] += 1
                continue
            a = (node.get("Author") or "").strip() or "?"
            authors.add(a)
            hits[t].append((cid, nid, a, (node.get("DisplayName") or "").strip()))
    names = build_name_table(rows, authors)

    edge_cache = {cid: build_edges(c["nodes"]) for cid, c in convs.items()}
    lines = ["记录键\t说话人ID\t说话人显示名\t对话ID/节点ID\t上一行记录键\t下一行记录键"
             "\t同场人物\t键的节点数\t英文原文(CSV)\t备注"]
    multi_keys = multi_author_keys = 0
    for k in sorted(hits):
        lst = hits[k]
        if len(lst) > 1:
            multi_keys += 1
        authors_here = sorted(set(a for _, _, a, _ in lst))
        if len(authors_here) > 1:
            multi_author_keys += 1
        for cid, nid, a, dname in lst:
            prev_text, next_text = edge_cache[cid]
            cn = convs[cid]["nodes"]
            pv = [n for n in prev_text(nid) if cn[n].get("Text")]
            nx = [n for n in next_text(nid) if cn[n].get("Text")]
            pv_keys = [cn[n]["Text"] for n in sorted(pv, key=numeric)][:3]
            nx_keys = [cn[n]["Text"] for n in sorted(nx, key=numeric)][:3]
            note = []
            if len(authors_here) > 1:
                note.append("同键多作者: " + "/".join(authors_here))
            if a == "FlavourText":
                note.append("环境/旁白行")
            lines.append("\t".join([
                k, a, dname or names.get(a, ""), "%s/%s" % (cid, nid),
                " | ".join(pv_keys), " | ".join(nx_keys),
                ",".join(convs[cid]["participants"]), str(len(lst)),
                clean_cell(en_by_key.get(k, "")), "；".join(note),
            ]))
    main_tsv = os.path.join(out_dir, "说话人映射.tsv")
    with open(main_tsv, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    # ---- 可直接粘贴的一列: 行序与译本 CSV 逐行对齐 ----
    # 只填「节点直证」的键; XUAT 的同文推断/近似不在这一列(证据强度不同, 混进来会失真)。
    paste_tsv = os.path.join(out_dir, "说话人列_可粘贴.tsv")
    n_paste = 0
    with open(paste_tsv, "w", encoding="utf-8", newline="\n") as f:
        f.write("记录键\t说话人ID\t说话人显示名\t同场人物\n")
        for r in rows:                      # rows 就是译本原序
            k = r["记录键"]
            rs = hits.get(k)
            if rs:
                n_paste += 1
                f.write("\t".join([
                    k,
                    "/".join(sorted(set(x[2] for x in rs))),
                    "/".join(sorted(set(x[3] or names.get(x[2], "") for x in rs if (x[3] or names.get(x[2], ""))))),
                    ",".join(sorted(set(p for x in rs for p in convs[x[0]]["participants"]))),
                ]) + "\n")
            else:
                f.write(k + "\t\t\t\n")

    # ---- XUAT 推断: 只认「英文串与当前 Gridly 某键正文相同」，不按序号猜 ----
    bridge_tsv = os.path.join(out_dir, "说话人映射_推断XUAT.tsv")
    n_bridge = n_bridge_node = 0
    i2_key_by_norm = {}
    if args.i2 and os.path.exists(args.i2):
        for t, v in json.load(open(args.i2, encoding="utf-8")).items():
            if isinstance(v, str) and norm(v):
                i2_key_by_norm.setdefault(norm(v), []).append(
                    t.split("/", 1)[1] if "/" in t else t)
    if args.gridly and os.path.exists(args.gridly):
        grid = json.load(open(args.gridly, encoding="utf-8"))
        g_exact = defaultdict(list)
        g_loose = defaultdict(list)
        for gk, gv in grid.items():
            if not isinstance(gv, str):
                continue
            if norm(gv):
                g_exact[norm(gv)].append(gk)
            if loose(gv):
                g_loose[loose(gv)].append(gk)
        bl = ["记录键\t推断说话人ID\t说话人显示名\t依据(同文的当前键)\t该键的说话人\t同场人物"
              "\t置信度\t英文原文"]
        near = ["记录键\t最接近的当前键\t相似度\t该键正文\t该键的说话人\t同场人物\t置信度\t英文原文(旧)"]
        n_near = 0
        gvals = {k: v for k, v in grid.items() if isinstance(v, str) and v.strip()}
        idx = ngram_index(gvals.items())
        seen = set()
        for k in sorted(zh_by_key):
            if not k.startswith("XUAT_"):
                continue
            e = en_by_key.get(k, "")
            if not norm(e):
                continue
            cand = g_exact.get(norm(e), [])
            conf = "高"
            if not cand:
                cand = g_loose.get(loose(e), [])
                conf = "中"
            if not cand:
                for gk, ratio in nearest(e, gvals, idx):
                    node_n = hits.get(gk, [])
                    a_n = "/".join(sorted(set(x[2] for x in node_n))) if node_n else ""
                    # 交叉印证: I2 表里同一条英文挂在哪个键上? 与最近键一致就多一层证据
                    cross = ""
                    if i2_key_by_norm:
                        ks = i2_key_by_norm.get(norm(e), [])
                        if ks:
                            cross = "I2同键" if ks[0] == gk else ("I2异键:%s" % ks[0])
                    near.append("\t".join([
                        k, gk, "%.3f" % ratio, clean_cell(gvals[gk]), a_n,
                        ",".join(sorted(set(p for x in node_n for p in convs[x[0]]["participants"]))),
                        ("近似(高)" if ratio >= 0.85 else "近似(需人工确认)") + (("；" + cross) if cross else ""),
                        clean_cell(e)]))
                    n_near += 1
                    break
                continue
            n_bridge += 1
            key0 = cand[0]
            node = hits.get(key0, [])
            if node:
                n_bridge_node += 1
                a = "/".join(sorted(set(x[2] for x in node)))
                parts = ",".join(sorted(set(p for x in node for p in convs[x[0]]["participants"])))
            else:
                a, parts = "", ""
                conf += "（依据键无对话节点）"
            bl.append("\t".join([k, a, names.get(a, "") if a else "", " | ".join(cand[:4]),
                                 ",".join(sorted(set(x[2] for x in node))) if node else "",
                                 parts, conf, e]))
        with open(bridge_tsv, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(bl) + "\n")
        near_tsv = os.path.join(out_dir, "说话人映射_旧串对照.tsv")
        with open(near_tsv, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(near) + "\n")

    out = {
        "conversations": stats["conversations"],
        "nodes": stats["nodes"],
        "keys_covered": len(hits),
        "csv_keys": len(keyset),
        "multi_node_keys": multi_keys,
        "multi_author_keys": multi_author_keys,
        "node_text_not_key": stats["node_text_not_key"],
        "skip_json": stats["skip_json"],
        "skip_nonconv": stats["skip_nonconv"],
        "authors": len(authors),
        "bridge_rows": n_bridge,
        "bridge_with_node": n_bridge_node,
        "nearest_rows": n_near if args.gridly else 0,
    }
    print(json.dumps(out, ensure_ascii=False))
    print("TSV:", main_tsv, os.path.getsize(main_tsv), "B")
    print("TSV:", paste_tsv, os.path.getsize(paste_tsv), "B", "(填 %d 行 / 共 %d 行)" % (n_paste, len(rows)))
    if args.gridly:
        print("TSV:", bridge_tsv, os.path.getsize(bridge_tsv), "B")
        print("TSV:", near_tsv, os.path.getsize(near_tsv), "B")
    with open(os.path.join(out_dir, "_speaker_stats.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())