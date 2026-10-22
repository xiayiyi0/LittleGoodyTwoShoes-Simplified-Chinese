"""第一轮修正：把定稿写回 docs 双语译本（FIX_ROUND1.md §4.2、§5）。

用法（在 review/scripts/ 下）：
  python3 round1_apply.py --dry-run   只做 --final 的全部检查并报告计数，不写文件
  python3 round1_apply.py             检查通过后原地写回 docs CSV

只改采纳 / 改写 / 联动行的四列：中文译文 = final；修订状态 =「已修订」；修订译文 = final；
审查备注末尾追加「[全检·<级别><类别>] <note>」（联动为「[全检·联动] <note>」，原备注非空用「; 」连接）。
行序、列序、其余列不动；utf-8-sig、LF、QUOTE_MINIMAL（lgts_common.write_csv）。写后读回自检。
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round1_lib import (CHANGING, COL_KEY, COL_NOTE, COL_REV_STATE, COL_REV_ZH, COL_ZH, CSV_PATH, Ctx,  # noqa: E402
                        load_rows, note_tag)
from round1_check import WRITE_COLS, report, run_checks  # noqa: E402
from lgts_common import write_csv  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    c = Ctx()
    errors, hints = run_checks(c, 'final')
    report(c, errors, hints, True)
    if errors:
        sys.exit('有错误，拒绝写回')
    plan = [(k, d) for k, d in c.decs.items() if d['decision'] in CHANGING]
    cnt = Counter(d['decision'] for _, d in plan)
    print('将改 %d 行（%s）' % (len(plan), '，'.join('%s %d' % (x, cnt[x]) for x in CHANGING)))
    if a.dry_run:
        print('dry-run：未写文件')
        return
    before = {r[COL_KEY]: dict(r) for r in c.rows}
    for k, d in plan:
        r = c.rk[k]
        tag = note_tag(c.items.get(k, {'严重度': '', '类别': ''}), d)
        r[COL_ZH] = d['final']
        r[COL_REV_STATE] = '已修订'
        r[COL_REV_ZH] = d['final']
        r[COL_NOTE] = (r[COL_NOTE] + '; ' + tag) if r[COL_NOTE] else tag
    write_csv(CSV_PATH, c.header, [[r[h] for h in c.header] for r in c.rows])
    # 读回自检
    header2, rows2 = load_rows()
    problems = []
    if header2 != c.header:
        problems.append('表头变了')
    if [r[COL_KEY] for r in rows2] != [r[COL_KEY] for r in c.rows]:
        problems.append('行序或行数变了')
    expect = {k for k, _ in plan}
    changed = set()
    for r in rows2:
        k = r[COL_KEY]
        diff = [h for h in c.header if r[h] != before[k][h]]
        if diff:
            changed.add(k)
            if k not in expect:
                problems.append('%s 不该变却变了：%s' % (k, ','.join(diff)))
            elif any(h not in WRITE_COLS for h in diff):
                problems.append('%s 改了四列以外的列：%s' % (k, ','.join(diff)))
        elif k in expect:
            problems.append('%s 应改未改' % k)
    for p in problems:
        print('自检失败：' + p)
    print('写回 %s：改动 %d 行（预期 %d）' % (os.path.relpath(CSV_PATH), len(changed), len(plan)))
    if problems or len(changed) != len(plan):
        sys.exit(1)
    print('自检通过')


if __name__ == '__main__':
    main()
