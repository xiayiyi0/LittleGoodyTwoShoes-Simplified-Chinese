"""合并 review/findings/*.jsonl → review/findings.csv（按严重度、记录键排序）。

「英文原文」「现译文」「批次号」「显示层冲突组」按记录键从 CSV、manifest、precheck 回填，不手抄。
「采纳」列留空，供人工填「是 / 否」，apply_fixes.py 只处理「是」。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import (COL_KEY, COL_ZH, COL_EN, COL_NOTE, REVIEW, FINDINGS_DIR, PRECHECK_DIR, load_rows,
                         rows_by_key, load_manifest, write_csv)

SEV_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
CAT_ORDER = ['串位', '误译', '漏译', '增译', '衍文', '人称称谓', '人名术语', '衔接', '分支', '语气', '翻译腔', '标点格式',
             '标签占位符', '显示层冲突', '源文问题']


def main():
    header, rows = load_rows()
    rk = rows_by_key(rows)
    man = load_manifest()
    conf = {}
    p = os.path.join(PRECHECK_DIR, 'display_conflicts.csv')
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                conf[rec['记录键']] = rec['冲突组']
    out = []
    for fn in sorted(os.listdir(FINDINGS_DIR)):
        if not fn.endswith('.jsonl'):
            continue
        for line in open(os.path.join(FINDINGS_DIR, fn), encoding='utf-8'):
            if not line.strip():
                continue
            d = json.loads(line)
            r = rk[d['key']]
            out.append([d['sev'], d['key'], man[d['key']]['批次号'], d['cat'], r[COL_EN], r[COL_ZH], d['fix'], d['why'],
                        ' '.join(d['ctx']), d['conf'], conf.get(d['key'], ''), ''])
    out.sort(key=lambda x: (SEV_ORDER[x[0]], x[1]))
    write_csv(os.path.join(REVIEW, 'findings.csv'),
              ['严重度', '记录键', '批次号', '类别', '英文原文', '现译文', '建议译文', '理由', '依据行', '置信度', '显示层冲突组', '采纳'], out)
    print('findings.csv：%d 条' % len(out))


if __name__ == '__main__':
    main()
