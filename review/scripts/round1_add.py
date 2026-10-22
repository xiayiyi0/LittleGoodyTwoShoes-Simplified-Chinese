"""第一轮修正：录入决定（写进键所属批次的 review/round1/<批次号>.jsonl，同键已有则替换）。

从标准输入读，一行一条：  记录键 | 决定 | 定稿 | 备注
  决定：采 / 采纳、改 / 改写、不 / 不改、联 / 联动
  定稿：采纳、不改可留空（自动取建议译文 / 现译文）；单元格内换行写 ⏎
  空行和 # 开头的行忽略
逐条校验（决定、备注 ≤30 字、采纳 = 建议、改写 / 联动 ≠ 现译、check_text、名表、锁定行）；不过的不写入。
改写的定稿与建议相同时自动记为采纳。文件内按 manifest 顺序排列。

  python3 round1_add.py [--dry] < 决定.txt
  python3 round1_add.py --del KEY [KEY…]
  python3 round1_add.py --touch 001 [002…]     建空的决定文件（本批没有剩余条目时）
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round1_lib import (CHANGING, COL_EN, COL_ZH, NOTE_MAX, R1_DIR, Ctx, check_text, is_explained,  # noqa: E402
                        is_locked, load_decisions, name_term_checks, unflat, write_decision_file)

ABBR = {'采': '采纳', '采纳': '采纳', '改': '改写', '改写': '改写', '不': '不改', '不改': '不改', '联': '联动', '联动': '联动'}


def parse(c, line):
    parts = [p.strip() for p in line.split('|')]
    if len(parts) != 4:
        return None, '应为 4 段（键 | 决定 | 定稿 | 备注），得 %d 段' % len(parts)
    k, dec, final, note = parts
    final = unflat(final)
    if k not in c.rk:
        return None, '记录键不存在'
    if dec not in ABBR:
        return None, '决定不合法：%s' % dec
    dec = ABBR[dec]
    it = c.items.get(k)
    if dec == '联动' and it:
        return None, '清单内的键不能记联动'
    if dec != '联动' and not it:
        return None, '清单外的键只能记联动'
    cur = c.rk[k][COL_ZH]
    if dec == '采纳':
        if final and final != it['建议译文']:
            return None, '采纳但定稿 ≠ 建议译文（要改就记「改」）'
        final = it['建议译文']
    elif dec == '不改':
        if final and final != cur:
            return None, '不改但定稿 ≠ 现译文'
        final = cur
    else:
        if not final:
            return None, '改写 / 联动要写定稿'
        if final == cur:
            return None, '定稿 = 现译文（应记不改）'
        if dec == '改写' and final == it['建议译文']:
            dec = '采纳'
    if not note:
        return None, '备注为空'
    if len(note) > NOTE_MAX:
        return None, '备注超过 %d 字（%d）' % (NOTE_MAX, len(note))
    errs = []
    if dec in CHANGING:
        row = c.rk[k]
        errs += check_text(final, row[COL_EN], cur, is_explained(row))
        es, hs = name_term_checks(final, row[COL_EN], cur, note)
        errs += es
        for h in hs:
            print('  提示 %s：%s' % (k, h))
        if is_locked(row):
            errs.append('锁定行不能改')
    if errs:
        return None, '；'.join(errs)
    return {'key': k, 'decision': dec, 'final': final, 'note': note}, None


def rewrite(c, decs, files):
    by_file = defaultdict(list)
    for k, d in decs.items():
        by_file[d['_file']].append(d)
    for fn in files:
        recs = sorted(by_file.get(fn, []), key=lambda d: c.pos.get(d['key'], 10 ** 9))
        write_decision_file(fn, recs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--del', dest='dels', nargs='+')
    ap.add_argument('--touch', nargs='+')
    a = ap.parse_args()
    c = Ctx()
    decs, problems = load_decisions()
    for p in problems:
        print('决定文件问题：%s %s %s' % p)
    if a.touch:
        os.makedirs(R1_DIR, exist_ok=True)
        for b in a.touch:
            p = os.path.join(R1_DIR, '%03d.jsonl' % int(b))
            if not os.path.exists(p):
                open(p, 'w').close()
                print('建空文件 %s' % os.path.basename(p))
        return
    if a.dels:
        files = set()
        for k in a.dels:
            if k in decs:
                files.add(decs.pop(k)['_file'])
                print('删除 %s' % k)
            else:
                print('无此决定 %s' % k)
        rewrite(c, decs, files)
        return
    ok, bad, files = Counter(), 0, set()
    for n, line in enumerate(sys.stdin, 1):
        line = line.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        d, err = parse(c, line)
        if err:
            bad += 1
            print('拒绝 第%d行 %s：%s' % (n, line.split('|')[0].strip(), err))
            continue
        k = d['key']
        if k in decs:
            files.add(decs[k]['_file'])
        d['_file'] = '%s.jsonl' % c.batch_of(k)
        files.add(d['_file'])
        decs[k] = d
        ok[d['decision']] += 1
    if not a.dry:
        rewrite(c, decs, files)
    print('%s %d 条（%s），拒绝 %d 条' % ('校验通过' if a.dry else '写入', sum(ok.values()),
                                   '，'.join('%s %d' % x for x in ok.items()), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
