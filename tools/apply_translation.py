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


# 同形异义: 同一个英文串既是角色名又是道具名, 两层必须各取各的。
# Lebkuchen 作角色名是「斯佩尔特」(名牌 · 旁白 · 任务提示), 作食品 (ITM_F_N_08)
# 才是「姜饼」——后者归 item_names 层管。若放任 ITM_F_N_08 这一行参与 display
# 归并, pick() 会把 display["Lebkuchen"] 改写成「姜饼」, 名牌随之出错
# (v1.3.21 全量重建就是这样冲掉了 v1.3.20 及更早的正确值)。
NAME_OVERRIDE = {"Lebkuchen": "斯佩尔特"}

# 定名护栏: display 里有六千多条英文串不在译本里(历史 XUAT 残留), 这些值不受
# CSV 约束, 定名会随旧译文漂移。2026-10-25 审计实测: Rosmarine(错叫名)有 118 条
# 被写成真名「萝森玛琳」, Mercy 有 2 条被写成 Macy 的「梅西」——玩家会看到同一个
# 角色前后两种叫法。键里出现某个英文名时, 只把"串成别的角色名"的那个换回来,
# 其余措辞一律不动。
NAME_GUARD = [
    # (英文名, 串错的定名, 正确定名, 是否区分大小写)
    # mercy 小写是"仁慈"(19 条), 只有大写 Mercy 才是人名, 必须区分。
    ("Rosmarine", "萝森玛琳", "萝丝玛琳", False),
    ("Rozenmarine", "萝丝玛琳", "萝森玛琳", False),
    ("Mercy", "梅西", "默茜", True),
    ("Macy", "默茜", "梅西", True),
]
NAME_GUARD_RE = [(re.compile(r"\b" + en + r"\b", 0 if cs else re.I), wrong, right)
                 for en, wrong, right, cs in NAME_GUARD]

# Missy 的错法是泛化成"小丫头"而非串成别的名字, 短语级替换会误伤, 用整键覆盖。
KEY_OVERRIDE = {"Tell her what, Missy?": "告诉她什么呢，米茜？"}

# 遗留层标点: 半角括号 / 冒号 / 分号。CSV 层早已全角, 只有历史条目残留。
HALF_PAREN_RE = re.compile(r"\(([^()]*[一-鿿][^()]*)\)")
HALF_MARK_RE = re.compile(r"(?<=[一-鿿])[:;]|[:;](?=[一-鿿])")

# 游戏 TMP 不识别这三个标签, 会把它们当字面量显示在对话框里 (v1.3.8 实机确认)。
# <size>/<color>/<i>/<b>/<sprite> 是支持的, 必须保留。
# v1.3.21 全量重建时中文译文里的这些标签又被带了回来, 玩家侧看到 "&lt;wave a=0.3&gt;"
# 之类上屏, 所以这里统一剥掉 —— 剥的时候连同属性一起删, 只留内层文字。
BAD_TAG_RE = re.compile(r"</?(?:wave|shake|incr)\b[^>]*>")


def clean_zh(s):
    return BAD_TAG_RE.sub("", s or "").strip()


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


def punct_fix(s):
    s = HALF_PAREN_RE.sub(r"（\1）", s)
    return HALF_MARK_RE.sub(lambda m: "：" if m.group(0) == ":" else "；", s)


def legacy_fix(k, s):
    """只作用于不在译本里的遗留条目。"""
    if k in KEY_OVERRIDE:
        return KEY_OVERRIDE[k]
    for rx, wrong, right in NAME_GUARD_RE:
        if wrong in s and rx.search(k):
            s = s.replace(wrong, right)
    return punct_fix(s)


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
    eff = lambda r: clean_zh(((r.get("修订译文") or "").strip() or r["中文译文"]) if has_rev else r["中文译文"])

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
        if k in NAME_OVERRIDE:
            continue
        cands = norm_map.get(k)
        if not cands:
            new = legacy_fix(k, disp[k])
        else:
            new = pick(list(dict.fromkeys(cands)), disp[k])
        if new != disp[k]:
            disp[k] = new
            dchg += 1
    for k, v in NAME_OVERRIDE.items():
        if disp.get(k) != v:
            disp[k] = v
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
