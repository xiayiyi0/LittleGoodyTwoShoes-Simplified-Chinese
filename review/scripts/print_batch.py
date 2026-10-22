"""打印批次供精读：`顺序 | 记录键 | 英文 | 中文`，不带备注。

用法：
  python3 print_batch.py 001            打印第 001 批第 1 段（单段 ≤25,000 字符）
  python3 print_batch.py 001 --part 2   打印第 2 段
  python3 print_batch.py --notes KEY…   查看指定行的备注（报问题前核对用）
  python3 print_batch.py --around KEY [-n 5]   按 manifest 顺序看某行前后 n 行（含备注）

标记：[锁]=锁定行  [缺源]=缺英文源/未译  [冲Dxx]=显示层冲突组  [候:代码…]=预扫候选（代码见 precheck/README.md）
单元格内换行显示为 ⏎。上文行（顺序为负）只看不计数。每段末尾打印本段行数与累计行数，用于核对未被截断。
"""
import argparse
import csv
import os
import sys
from collections import OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import (COL_KEY, COL_ZH, COL_EN, COL_NOTE, COL_STATE, PRECHECK_DIR, load_rows, rows_by_key,
                         load_manifest, load_batches, is_locked)

LIMIT = 25000


def flat(s):
    return (s or '').replace('\r', '').replace('\n', '⏎')


def load_cands():
    out = defaultdict(list)
    p = os.path.join(PRECHECK_DIR, 'candidates.csv')
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                code = rec['检查项'][:2]
                if code == 'D1':
                    continue
                out[rec['记录键']].append(code)
    conf = {}
    p = os.path.join(PRECHECK_DIR, 'display_conflicts.csv')
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                conf[rec['记录键']] = rec['冲突组'] + ('' if rec['类型'] == '措辞差异' else 't')
    return out, conf


def line_of(order, r, cands, conf):
    marks = []
    if is_locked(r):
        marks.append('[锁]')
    if r[COL_STATE] != '已译':
        marks.append('[缺源]' if r[COL_STATE] == '缺英文源' else '[未译]')
    if r[COL_KEY] in conf:
        marks.append('[冲%s]' % conf[r[COL_KEY]])
    if r[COL_KEY] in cands:
        marks.append('[候:%s]' % ','.join(sorted(set(cands[r[COL_KEY]]))))
    return '%s | %s%s | %s | %s' % (order, r[COL_KEY], (' ' + ''.join(marks)) if marks else '', flat(r[COL_EN]), flat(r[COL_ZH]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', nargs='?')
    ap.add_argument('--part', type=int, default=1)
    ap.add_argument('--notes', nargs='+')
    ap.add_argument('--around')
    ap.add_argument('-n', type=int, default=5)
    a = ap.parse_args()
    header, rows = load_rows()
    rk = rows_by_key(rows)
    man = load_manifest()
    order_keys = list(man.keys())
    if a.notes:
        for k in a.notes:
            r = rk[k]
            print('%s | %s | %s\n    备注：%s' % (k, flat(r[COL_EN]), flat(r[COL_ZH]), flat(r[COL_NOTE]) or '（无）'))
        return
    if a.around:
        i = order_keys.index(a.around)
        for k in order_keys[max(0, i - a.n): i + a.n + 1]:
            r = rk[k]
            mark = '>>' if k == a.around else '  '
            print('%s %s | %s | %s\n      备注：%s' % (mark, k, flat(r[COL_EN]), flat(r[COL_ZH]), flat(r[COL_NOTE])[:300] or '（无）'))
        return
    bid = '%03d' % int(a.batch)
    bats = load_batches()
    b = bats[bid]
    keys = [k for k, m in man.items() if m['批次号'] == bid]
    cands, conf = load_cands()
    lines = []
    ctx = int(b['上文行数'])
    if ctx:
        first = order_keys.index(keys[0])
        for j, k in enumerate(order_keys[max(0, first - ctx): first]):
            lines.append(('ctx', line_of(-(min(ctx, first) - j), rk[k], cands, conf)))
    for k in keys:
        lines.append(('row', line_of(man[k]['批内顺序'], rk[k], cands, conf)))
    # 分段
    parts, cur, size = [], [], 0
    for kind, ln in lines:
        if cur and size + len(ln) + 1 > LIMIT:
            parts.append(cur)
            cur, size = [], 0
        cur.append((kind, ln))
        size += len(ln) + 1
    if cur:
        parts.append(cur)
    p = parts[a.part - 1]
    print('== 批次 %s（%s，%s 行，%s）第 %d/%d 段 ==' % (bid, b['区段'], b['行数'], b['范围'], a.part, len(parts)))
    for kind, ln in p:
        print(ln)
    done = sum(1 for pp in parts[:a.part] for kind, _ in pp if kind == 'row')
    this = sum(1 for kind, _ in p if kind == 'row')
    print('== 本段计数行 %d，累计 %d/%d%s ==' % (this, done, len(keys), '' if a.part == len(parts) else '，还有下一段 --part %d' % (a.part + 1)))


if __name__ == '__main__':
    main()
