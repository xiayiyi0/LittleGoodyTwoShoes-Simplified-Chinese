# -*- coding: utf-8 -*-
"""把译本 CSV 落到三层词典 (by_refkey / display / item_names)。

    python tools/apply_translation.py --csv docs/译本.csv
    python tools/apply_translation.py --csv ... --live "D:\\game" --backup-suffix .bak_pre_v10

规则 (与历次发布一致):
  * by_refkey: 记录键 -> 译文, 直取覆盖。
  * display / item_names: 按 Norm(英文) 归一键匹配, 命中后用 pick() 选值 ——
    同一英文键有多条中文候选时, 优先选与现有值"去标点后相同"的候选, 以保留既有措辞;
    否则取第一条。这样重建不会因为标点差异把整表措辞洗一遍。
  * 空译文不入库, 也不覆盖。

译本列集: 2026-10-25 起为 9 列 (记录键/中文译文/全局序号/分类/周组/场景码/审查备注/状态/
英文原文)。此前的 11 列版本另有 修订状态/修订译文 两列, 若传入旧格式, 仍以 修订译文
优先 (那在该文件里才是有权威文本)。脚本会打印识别到的列集, 便于确认用的是哪一版。

写入前对每个文件做一次备份 (默认后缀 .bak_pre_apply, 已存在则不覆盖)。
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys
from collections import defaultdict

TAG_RE = re.compile(r"<[/#a-zA-Z][^>]*>")
WS_RE = re.compile(r"\s+")
PUNCT = set("、，。！？：；（）【】「」『』—…·“”‘’!?()[].,:;-\u3000 ")


def norm(s):
    return WS_RE.sub(" ", TAG_RE.sub("", s or "")).strip()


def depunct(s):
    return "".join(ch for ch in s if ch not in PUNCT)


def pick(cands, current):
    if current:
        for c in cands:
            if depunct(c) == depunct(current):
                return c
        if current in cands:
            return current
    return cands[0]


def backup(path, suffix):
    dst = path + suffix
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
        print("  备份 " + os.path.basename(dst))
    return dst


def dump(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=None, separators=(", ", ": "))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="译本 CSV (9 列)；旧 11 列格式亦可")
    ap.add_argument("--live", default=None, help="游戏根目录; 默认取仓库内自带的词典")
    ap.add_argument("--backup-suffix", default=".bak_pre_apply")
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tran = os.path.join(args.live, r"BepInEx\plugins\LGTSChinese\translation") if args.live \
        else os.path.join(repo, "BepInEx", "plugins", "LGTSChinese", "translation")

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    cols = rows[0].keys() if rows else []
    has_rev = "修订译文" in cols
    print("译本列集: %d 列%s" % (len(cols), " (旧 11 列格式, 以 修订译文 优先)" if has_rev else " (9 列格式)"))
    eff = lambda r: (((r.get("修订译文") or "").strip() or r["中文译文"]) if has_rev else r["中文译文"]).strip()

    refkey_map = {}
    norm_map = defaultdict(list)
    skipped = {"empty_zh": 0, "empty_en": 0}
    for r in rows:
        k, zh = r["记录键"], eff(r)
        if not zh:
            skipped["empty_zh"] += 1
            continue
        refkey_map[k] = zh
        en = r["英文原文"].strip()
        if not en:
            skipped["empty_en"] += 1
            continue
        norm_map[norm(en)].append(zh)

    print("CSV 行 %d | refkey 映射 %d | 英文归一键 %d | 跳过 %s"
          % (len(rows), len(refkey_map), len(norm_map), skipped))

    bp = os.path.join(tran, "lgts_zh_by_refkey.json")
    backup(bp, args.backup_suffix)
    live = json.load(open(bp, encoding="utf-8"))
    before = len(live)
    changed = added = 0
    for k, v in refkey_map.items():
        if k in live:
            if live[k] != v:
                live[k] = v
                changed += 1
        else:
            live[k] = v
            added += 1
    dump(live, bp)
    print("by_refkey: %d -> %d (改值 %d, 新增 %d)" % (before, len(live), changed, added))

    dp = os.path.join(tran, "lgts_display.json")
    backup(dp, args.backup_suffix)
    disp = json.load(open(dp, encoding="utf-8"))
    dchg = 0
    for k in list(disp):
        cands = norm_map.get(k)
        if not cands:
            continue
        new = pick(list(dict.fromkeys(cands)), disp[k])
        if new != disp[k]:
            disp[k] = new
            dchg += 1
    dump(disp, dp)
    print("display: %d 键, 改值 %d" % (len(disp), dchg))

    ip = os.path.join(tran, "lgts_item_names.json")
    if os.path.exists(ip):
        backup(ip, args.backup_suffix)
        itn = json.load(open(ip, encoding="utf-8"))
        ichg = miss = 0
        for k in list(itn):
            cands = norm_map.get(norm(k))
            if not cands:
                miss += 1
                continue
            new = pick(list(dict.fromkeys(cands)), itn[k])
            if new != itn[k]:
                itn[k] = new
                ichg += 1
        dump(itn, ip)
        print("item_names: %d 条, 改值 %d, 未匹配 %d" % (len(itn), ichg, miss))
    else:
        print("item_names: 文件不存在, 跳过")


if __name__ == "__main__":
    sys.exit(main())
