"""覆盖率证明（任务书 4.7）。

  1) manifest 覆盖 CSV 全部记录键，且每键只属于一个批次；
  2) 批次「已完成」= ledger.md 有该批记录，且 findings/ 与 minor/ 下都有 <批次号>.jsonl（无问题也要有空文件）；
  3) 输出 已完成批次覆盖的行数 / 总行数，以及未完成批次清单。
全部完成时退出码 0，否则 1。
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import COL_KEY, REVIEW, FINDINGS_DIR, load_rows, load_manifest, load_batches


def main():
    header, rows = load_rows()
    keys = [r[COL_KEY] for r in rows]
    man = load_manifest()
    bats = load_batches()
    assert set(man) == set(keys), 'manifest 与 CSV 记录键不一致：缺 %d，多 %d' % (len(set(keys) - set(man)), len(set(man) - set(keys)))
    cnt = Counter(m['批次号'] for m in man.values())
    for b, rec in bats.items():
        assert cnt[b] == int(rec['行数']), '批次 %s 行数不符' % b
    ledger = set()
    p = os.path.join(REVIEW, 'ledger.md')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            m = re.match(r'^\|\s*(\d{3})\s*\|', line)
            if m:
                ledger.add(m.group(1))
    minor_dir = os.path.join(REVIEW, 'minor')
    done = [b for b in bats if b in ledger and os.path.exists(os.path.join(FINDINGS_DIR, '%s.jsonl' % b))
            and os.path.exists(os.path.join(minor_dir, '%s.jsonl' % b))]
    covered = sum(cnt[b] for b in done)
    todo = [b for b in bats if b not in done]
    print('记录键 %d，manifest %d，批次 %d' % (len(keys), len(man), len(bats)))
    print('已完成批次 %d / %d，覆盖行 %d / %d（%.1f%%）' % (len(done), len(bats), covered, len(keys), 100.0 * covered / len(keys)))
    if todo:
        print('未完成批次：%s%s' % (' '.join(todo[:20]), ' …' if len(todo) > 20 else ''))
    sys.exit(0 if not todo else 1)


if __name__ == '__main__':
    main()
