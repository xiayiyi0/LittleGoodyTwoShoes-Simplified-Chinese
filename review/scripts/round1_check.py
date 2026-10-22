"""第一轮修正：校验决定文件 review/round1/*.jsonl（FIX_ROUND1.md §5）。有错误时退出码 1。

用法（在 review/scripts/ 下）：
  python3 round1_check.py            接力中：只校验已写的决定；未定稿条目按批次汇总成提示；
                                     同键组还有清单行没定稿时，一致性问题记「待补」提示
  python3 round1_check.py --final    1,036 条必须全部有决定，「待补」也算错误
  python3 round1_check.py --post     写回 docs 后：核对写回的四列、不改的行没动、其余行与 BASE_REF 一致，
                                     并全表列出同英文而中文措辞不一的组
  -q   不逐条打印提示（只打印计数）

错误项：①键存在、属于文件名的批次、全局唯一，decision 合法，final / note 非空、note ≤30 字；
②采纳 = 建议译文，改写 / 联动 ≠ 现译文，不改 = 现译文，联动的键不在清单里（其余决定的键必须在清单里）；
③docs 现译文 = 清单现译文；④采纳 / 改写 / 联动的 final 过 check_text 与名表检查；⑤锁定行不能改；
⑥叠加全部非「不改」的 final 后，被触及的匹配键组内 norm(中文) 唯一（只差标签记提示）。
"""
import argparse
import os
import sys
from collections import Counter, OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round1_lib import (BASE_REF, CHANGING, COL_EN, COL_KEY, COL_NOTE, COL_REV_STATE, COL_REV_ZH, COL_ZH,  # noqa: E402
                        DECISIONS, NOTE_MAX, Ctx, check_text, counts_table, flat, git_base_rows, is_explained,
                        is_locked, name_term_checks, norm, note_tag)

WRITE_COLS = (COL_ZH, COL_REV_STATE, COL_REV_ZH, COL_NOTE)


def run_checks(c, mode):
    """mode: default / final / post。返回 (errors, hints)，元素为 (来源, 键, 信息)。"""
    errors, hints = list(c.dec_problems), []
    base = None
    if mode == 'post':
        b = git_base_rows()
        if b is None:
            hints.append(('-', '-', '读不到 %s 上的 docs CSV，跳过「其余行未动」核对' % BASE_REF))
        else:
            base = OrderedDict((r[COL_KEY], r) for r in b[1])

    def before(k):
        """写回前的行（post 时取 BASE_REF；否则就是 docs 现行）。"""
        if mode == 'post':
            if base is not None and k in base:
                return base[k]
            r = dict(c.rk[k])
            if k in c.items:
                r[COL_ZH] = c.items[k]['现译文']
            return r
        return c.rk[k]

    for k, d in c.decs.items():
        src = d['_src']
        if k not in c.rk:
            errors.append((src, k, '记录键不存在'))
            continue
        b = c.batch_of(k)
        if d['_file'] != '%s.jsonl' % b:
            errors.append((src, k, '应写在 %s.jsonl（manifest 批次）' % b))
        dec, final, note = d.get('decision'), d.get('final') or '', d.get('note') or ''
        if dec not in DECISIONS:
            errors.append((src, k, 'decision 不合法：%s' % dec))
            continue
        if not final:
            errors.append((src, k, 'final 为空'))
        if not note:
            errors.append((src, k, 'note 为空'))
        elif len(note) > NOTE_MAX:
            errors.append((src, k, 'note 超过 %d 字（%d）' % (NOTE_MAX, len(note))))
        it = c.items.get(k)
        if mode == 'post' and base is None and not it:
            continue  # 写回后又读不到基线：联动行的写回前现译无从核对，只做 post_checks
        row0 = before(k)
        cur = row0[COL_ZH]
        if dec == '联动':
            if it:
                errors.append((src, k, '联动的键在清单里（清单条目应记采纳 / 改写 / 不改）'))
        elif not it:
            errors.append((src, k, '键不在清单里（清单外的行只能记联动）'))
        if dec == '采纳' and it and final != it['建议译文']:
            errors.append((src, k, '采纳但 final ≠ 建议译文'))
        if dec in ('改写', '联动') and final == cur:
            errors.append((src, k, '%s但 final = 现译文' % dec))
        if dec == '改写' and it and final == it['建议译文']:
            hints.append((src, k, '改写的 final 与建议相同，应记采纳'))
        if dec == '不改' and final != cur:
            errors.append((src, k, '不改但 final ≠ 现译文'))
        if mode != 'post' and it and c.rk[k][COL_ZH] != it['现译文']:
            errors.append((src, k, 'docs 现译文与清单不同（docs 被别处改过？）'))
        if dec in CHANGING and final:
            en = c.rk[k][COL_EN]
            for e in check_text(final, en, cur, is_explained(row0)):
                errors.append((src, k, e))
            es, hs = name_term_checks(final, en, cur, note)
            errors += [(src, k, e) for e in es]
            hints += [(src, k, h) for h in hs]
            if is_locked(row0):
                errors.append((src, k, '锁定行不能改'))

    undecided = [k for k in c.items if k not in c.decs]
    if undecided:
        per = Counter(c.items[k]['批次号'] for k in undecided)
        msg = '未定稿 %d 条：%s' % (len(undecided), ' '.join('%s(%d)' % (b, n) for b, n in sorted(per.items())))
        (errors if mode in ('final', 'post') else hints).append(('-', '-', msg))

    # ⑥ 显示层：被触及（有任何决定）的匹配键组
    touched = OrderedDict()
    for k in c.decs:
        if k in c.rk and c.rk[k][COL_EN].strip():
            touched.setdefault(norm(c.rk[k][COL_EN]), k)
    zh_now = (lambda x: c.rk[x][COL_ZH]) if mode == 'post' else c.final_of
    for g, k0 in touched.items():
        ks = c.en_groups[g]
        if len(ks) < 2:
            continue
        variants = OrderedDict()
        for x in ks:
            variants.setdefault(norm(zh_now(x)), []).append(x)
        src = c.decs[k0]['_src']
        if len(variants) == 1:
            if len({zh_now(x) for x in ks}) > 1:
                hints.append((src, k0, '匹配键「%s」措辞一致，仅标签不同（显示层只能保留一种标签）' % g))
            continue
        detail = '；'.join('%s←%s' % (flat(v), ','.join(xs[:4]) + ('…' if len(xs) > 4 else ''))
                          for v, xs in variants.items())
        pend = [x for x in ks if x in c.items and x not in c.decs]
        settled = {norm(zh_now(x)) for x in ks if x not in pend}
        msg = '匹配键「%s」有 %d 种措辞：%s' % (g, len(variants), detail)
        if pend and len(settled) <= 1 and mode == 'default':
            hints.append((src, k0, '待补（未定稿 %s）：%s' % (','.join(pend[:6]), msg)))
        else:
            errors.append((src, k0, msg))

    if mode == 'post':
        post_checks(c, base, errors, hints)
    return errors, hints


def post_checks(c, base, errors, hints):
    for k, d in c.decs.items():
        if k not in c.rk:
            continue
        r, src = c.rk[k], d['_src']
        if d.get('decision') in CHANGING:
            if r[COL_ZH] != d['final']:
                errors.append((src, k, 'docs 中文译文 ≠ final'))
            if r[COL_REV_STATE] != '已修订':
                errors.append((src, k, '修订状态不是「已修订」'))
            if r[COL_REV_ZH] != d['final']:
                errors.append((src, k, '修订译文 ≠ final'))
            if '[全检' not in r[COL_NOTE]:
                errors.append((src, k, '审查备注缺 [全检 标签'))
        else:
            if k in c.items and r[COL_ZH] != c.items[k]['现译文']:
                errors.append((src, k, '不改的行中文被改了'))
            if '[全检' in r[COL_NOTE]:
                errors.append((src, k, '不改的行备注带了 [全检'))
    if base is not None:
        changed = {k for k, d in c.decs.items() if d.get('decision') in CHANGING}
        if list(base.keys()) != [r[COL_KEY] for r in c.rows]:
            errors.append(('-', '-', '行序或行数与 %s 不同' % BASE_REF))
        for r in c.rows:
            k = r[COL_KEY]
            b = base.get(k)
            if b is None:
                continue
            diff = [h for h in c.header if r[h] != b.get(h)]
            if k not in changed:
                if diff:
                    errors.append(('-', k, '不在决定里的行被改了：%s' % ','.join(diff)))
                continue
            bad = [h for h in diff if h not in WRITE_COLS]
            if bad:
                errors.append(('-', k, '改了四列以外的列：%s' % ','.join(bad)))
            want = (b[COL_NOTE] + '; ' if b[COL_NOTE] else '') + note_tag(c.items.get(k, {'严重度': '', '类别': ''}), c.decs[k])
            if r[COL_NOTE] != want:
                errors.append(('-', k, '审查备注与预期不符'))
    # 全表：同英文而措辞不一的组
    left = []
    for g, ks in c.en_groups.items():
        if len(ks) > 1 and len({norm(c.rk[x][COL_ZH]) for x in ks}) > 1:
            left.append((g, ks))
    for g, ks in left:
        vs = OrderedDict()
        for x in ks:
            vs.setdefault(norm(c.rk[x][COL_ZH]), []).append(x)
        hints.append(('全表', ks[0], '同英文措辞不一「%s」：%s' % (g, '；'.join(
            '%s←%s' % (flat(v), ','.join(xs[:3]) + ('…' if len(xs) > 3 else '')) for v, xs in vs.items()))))
    hints.append(('全表', '-', '同英文措辞不一的组共 %d 个' % len(left)))


def report(c, errors, hints, quiet):
    by_dec, by_sev = counts_table(c.decs, c.items)
    n_items = len(c.items)
    n_dec_items = sum(1 for k in c.items if k in c.decs)
    print('决定：%s；清单 %d 条，已定 %d，未定 %d；联动 %d 行' % (
        '，'.join('%s %d' % (d, by_dec.get(d, 0)) for d in DECISIONS), n_items, n_dec_items, n_items - n_dec_items,
        by_dec.get('联动', 0)))
    for sev in ('P0', 'P1', 'P2', 'P3', '小偏差', '联动'):
        if sev in by_sev:
            print('  %s：%s' % (sev, '，'.join('%s %d' % (d, by_sev[sev][d]) for d in DECISIONS if by_sev[sev][d])))
    cats = defaultdict(Counter)
    for k, d in c.decs.items():
        if k in c.items:
            cats[c.items[k]['类别']][d.get('decision')] += 1
    if cats:
        print('  按类别：' + '；'.join('%s %s' % (cat, '/'.join('%s%d' % (d[0], n) for d, n in cnt.items()))
                                   for cat, cnt in sorted(cats.items(), key=lambda x: -sum(x[1].values()))))
    for src, k, e in errors:
        print('错误 %s %s：%s' % (src, k, e))
    if not quiet:
        for src, k, e in hints:
            print('提示 %s %s：%s' % (src, k, e))
    print('错误 %d，提示 %d' % (len(errors), len(hints)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--post', action='store_true')
    ap.add_argument('-q', action='store_true')
    a = ap.parse_args()
    mode = 'post' if a.post else 'final' if a.final else 'default'
    c = Ctx()
    errors, hints = run_checks(c, mode)
    report(c, errors, hints, a.q)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
