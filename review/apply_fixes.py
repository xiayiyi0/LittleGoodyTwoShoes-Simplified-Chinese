"""把审查建议写进 v8 译本的副本（任务书 4.7，可选）。审查方只生成本脚本，未运行。

读 review/findings.csv 与 review/minor.csv（merge_findings.py 生成），按「采纳」列挑行，
把「建议译文」写进 docs/ 下 v8 CSV 的**副本**；从不改 docs/、BepInEx/、source/。

用法（在仓库根目录）：
  python3 review/apply_fixes.py                     只采纳「采纳」=「是」的行
  python3 review/apply_fixes.py --sev P0,P1         另把这些级别视为采纳（「采纳」=「否」的仍跳过）
  python3 review/apply_fixes.py --dry-run           只检查、报告，不写文件
  python3 review/apply_fixes.py --out PATH          输出路径（默认 review/out/双语译本版本8_采纳审查.csv）
  --sync-rev   「修订译文」非空的行同步改「修订译文」（该列是中文译文的副本）
  --note       在「审查备注」末尾追加「[v8全检·采纳] 级别/类别」
  --force      检查 2、3 不过时仍写出（只报告）

检查（不过即中止，除非 --force）：
  1. 记录键存在、同一键只有一条建议（硬性，--force 也不跳过）；
  2. 译本里的现译文与 findings 记录时一致（防止译本已改动，建议过期）；
  3. 显示层：同一匹配键（Plugin.Norm(英文)）的行，采纳后中文（去标签）须一致——
     显示层冲突组要整组采纳，否则游戏里仍只显示一句。
"""
import argparse
import csv
import os
import sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'scripts'))
from lgts_common import (CSV_PATH, REVIEW, COL_KEY, COL_ZH, COL_EN, COL_REV_ZH, COL_NOTE, load_rows, norm)  # noqa: E402

TRUE = {'是', 'y', 'yes', '1', 'true'}
FALSE = {'否', 'n', 'no', '0', 'false'}


def read_sheet(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def line_terminator(path):
    with open(path, 'rb') as f:
        head = f.read(1 << 16)
    return '\r\n' if b'\r\n' in head else '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sev', default='', help='逗号分隔，如 P0,P1')
    ap.add_argument('--out', default=os.path.join(REVIEW, 'out', '双语译本版本8_采纳审查.csv'))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sync-rev', action='store_true')
    ap.add_argument('--note', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    sevs = {s.strip() for s in a.sev.split(',') if s.strip()}

    out_abs = os.path.abspath(a.out)
    for guard in ('docs', 'BepInEx', 'source'):
        if out_abs.startswith(os.path.join(os.path.dirname(REVIEW), guard) + os.sep):
            sys.exit('拒绝写入 %s/：请输出到 review/out/ 或仓库外' % guard)

    header, rows = load_rows()
    by_key = {r[COL_KEY]: r for r in rows}

    sheet = read_sheet(os.path.join(REVIEW, 'findings.csv')) + read_sheet(os.path.join(REVIEW, 'minor.csv'))
    picked, hard, soft = {}, [], []
    for s in sheet:
        flag = (s.get('采纳') or '').strip().lower()
        if flag in FALSE:
            continue
        if not (flag in TRUE or s['严重度'] in sevs):
            continue
        k = s['记录键']
        if k not in by_key:
            hard.append('记录键不存在：%s' % k)
            continue
        if k in picked:
            hard.append('同一键有两条建议：%s' % k)
            continue
        if by_key[k][COL_ZH] != s['现译文']:
            soft.append('现译文已变，建议可能过期：%s' % k)
        picked[k] = s

    # 显示层一致性：只查被采纳行触及的匹配键
    groups = defaultdict(list)
    for r in rows:
        if r[COL_EN].strip():
            groups[norm(r[COL_EN])].append(r[COL_KEY])
    final = {k: picked[k]['建议译文'] if k in picked else by_key[k][COL_ZH] for k in by_key}
    for g in {norm(by_key[k][COL_EN]) for k in picked if by_key[k][COL_EN].strip()}:
        ks = groups[g]
        if len({norm(final[x]) for x in ks}) > 1:
            left = [x for x in ks if x not in picked]
            soft.append('匹配键「%s」采纳后仍有多种措辞（未采纳的同键行：%s）' % (g, ','.join(left[:8]) or '无'))

    for m in hard:
        print('错误：' + m)
    for m in soft:
        print('提示：' + m)
    print('采纳 %d 条：%s' % (len(picked), dict(Counter(s['严重度'] for s in picked.values()))))
    if hard or (soft and not a.force):
        sys.exit('未写出：请先处理上面的问题%s' % ('' if hard else '（或加 --force）'))
    if a.dry_run:
        print('dry-run：未写文件')
        return

    for k, s in picked.items():
        r = by_key[k]
        r[COL_ZH] = s['建议译文']
        if a.sync_rev and r.get(COL_REV_ZH):
            r[COL_REV_ZH] = s['建议译文']
        if a.note:
            tag = '[v8全检·采纳] %s/%s' % (s['严重度'], s['类别'])
            r[COL_NOTE] = (r[COL_NOTE] + '; ' + tag) if r[COL_NOTE] else tag
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    with open(out_abs, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator=line_terminator(CSV_PATH))
        w.writerow(header)
        for r in rows:
            w.writerow([r[h] for h in header])
    print('已写出：%s（docs/ 未改）' % os.path.relpath(out_abs))


if __name__ == '__main__':
    main()
