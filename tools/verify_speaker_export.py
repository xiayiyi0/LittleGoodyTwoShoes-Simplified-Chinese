# -*- coding: utf-8 -*-
"""校验说话人导出: 字段数、键都在译本里、说话人非空、可复算(两次输出逐字节一致)。"""
import csv, hashlib, os

REPO = r"D:\steam\steamapps\common\Little Goody Two Shoes\temp_work_result\github_repo_v1321"
EXP = os.path.join(REPO, "tools", "export")
CSV = os.path.join(REPO, "docs", "Little_Goody_Two_Shoes_汉化_双语译本版本11.csv")

keyset = set(r["记录键"] for r in csv.DictReader(open(CSV, encoding="utf-8-sig")))
fails = []


def check(path, need_cols, key_col="记录键", speaker_col=None):
    rows, ncol = 0, None
    bad_cols = 0
    not_in_csv = 0
    empty_spk = 0
    keys = set()
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        head = next(rd)
        ncol = len(head)
        for c in need_cols:
            if c not in head:
                fails.append("%s 缺列 %s" % (os.path.basename(path), c))
        ik = head.index(key_col)
        isp = head.index(speaker_col) if speaker_col and speaker_col in head else None
        for row in rd:
            rows += 1
            if len(row) != ncol:
                bad_cols += 1
            k = row[ik]
            keys.add(k)
            if k not in keyset:
                not_in_csv += 1
            if isp is not None and not row[isp].strip():
                empty_spk += 1
    print("%-28s 行=%6d 列=%d 错列=%d 键不在译本=%d 空说话人=%d"
          % (os.path.basename(path), rows, ncol, bad_cols, not_in_csv, empty_spk))
    for name, cond, msg in [("错列", bad_cols == 0, "有行列数不对"),
                            ("键不在译本", not_in_csv == 0, "有键不在译本 CSV")]:
        if not cond:
            fails.append("%s: %s %d" % (os.path.basename(path), msg,
                                        bad_cols if name == "错列" else not_in_csv))
    if empty_spk and speaker_col:
        fails.append("%s: 说话人空 %d 行" % (os.path.basename(path), empty_spk))
    return rows, keys


main_rows, main_keys = check(os.path.join(EXP, "说话人映射.tsv"),
                             ["记录键", "说话人ID", "说话人显示名", "对话ID/节点ID",
                              "上一行记录键", "下一行记录键", "同场人物", "英文原文(CSV)"],
                             speaker_col="说话人ID")
b_rows, b_keys = check(os.path.join(EXP, "说话人映射_推断XUAT.tsv"),
                       ["记录键", "推断说话人ID", "依据(同文的当前键)", "置信度"])
n_rows, n_keys = check(os.path.join(EXP, "说话人映射_旧串对照.tsv"),
                       ["记录键", "最接近的当前键", "相似度", "该键的正文" if False else "该键正文"])

print("\n覆盖: 主表唯一键 %d | 推断 %d | 旧串对照 %d" % (len(main_keys), len(b_keys), len(n_keys)))
print("三表并集(不同键总数): %d" % len(main_keys | b_keys | n_keys))

# 可复算: 两份文件的 sha256 应与报告里记录的一致(由调用方比对)
for fn in ("说话人映射.tsv", "说话人映射_推断XUAT.tsv", "说话人映射_旧串对照.tsv"):
    p = os.path.join(EXP, fn)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    print("  %-26s %s  %d B" % (fn, h[:16] + "...", os.path.getsize(p)))

print("\nFAIL:", len(fails))
for x in fails:
    print("  -", x)