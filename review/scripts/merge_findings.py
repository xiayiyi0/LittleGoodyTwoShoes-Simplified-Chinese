"""合并分片：findings/*.jsonl → review/findings.csv；minor/*.jsonl → review/minor.csv（按严重度、记录键排序）。

「英文原文」「现译文」「批次号」「显示层冲突组」按记录键从 CSV、manifest、precheck 回填，不手抄。
「采纳」列留空，供人工填「是 / 否」，apply_fixes.py 只处理「是」。
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import (COL_KEY, COL_ZH, COL_EN, REVIEW, FINDINGS_DIR, PRECHECK_DIR, load_rows, rows_by_key,
                         load_manifest, write_csv)

SEV_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3, '小偏差': 4}
HEADER = ['严重度', '记录键', '批次号', '类别', '英文原文', '现译文', '建议译文', '理由', '依据行', '置信度', '显示层冲突组', '采纳']


def collect(d, rk, man, conf):
    out = []
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.jsonl'):
            continue
        for line in open(os.path.join(d, fn), encoding='utf-8'):
            if not line.strip():
                continue
            x = json.loads(line)
            r = rk[x['key']]
            out.append([x['sev'], x['key'], man[x['key']]['批次号'], x['cat'], r[COL_EN], r[COL_ZH], x['fix'], x['why'],
                        ' '.join(x['ctx']), x['conf'], conf.get(x['key'], ''), ''])
    out.sort(key=lambda x: (SEV_ORDER[x[0]], x[1]))
    return out


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
    f1 = collect(FINDINGS_DIR, rk, man, conf)
    f2 = collect(os.path.join(REVIEW, 'minor'), rk, man, conf)
    write_csv(os.path.join(REVIEW, 'findings.csv'), HEADER, f1)
    write_csv(os.path.join(REVIEW, 'minor.csv'), HEADER, f2)
    print('findings.csv：%d 条；minor.csv：%d 条' % (len(f1), len(f2)))


if __name__ == '__main__':
    main()
