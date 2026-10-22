"""第一轮修正：打印待定稿条目与上下文（FIX_ROUND1.md §5）。

用法（在 review/scripts/ 下）：
  python3 round1_show.py 001                 第 001 批未定稿条目（跳过任何决定文件里已有的键）
  python3 round1_show.py 001 --all           连已定稿的也打印
  python3 round1_show.py --groups            全部同键组：组内各行（批次、键、现译、有无建议）+ 各行 ±3 上下文
  python3 round1_show.py --groups --brief    只列组概况（一组一行）
  python3 round1_show.py --group G15         单组（Gxx 或匹配键原文），-n 改上下文行数
  -w N   上下文行（非目标行）的英文、中文各截到 N 字（默认不截）

上下文按 manifest 顺序：P0 / P1 / 衔接 / 分支 ±8 行，其余 ±4，小偏差里的标点格式 ±2；相邻窗口合并打印。
目标行标 >>，并附完整备注；清单里的其他行标 ·；已定稿的行下一行印 ⇒[决定] 定稿。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from round1_lib import COL_EN, COL_NOTE, COL_ZH, Ctx, flat, norm  # noqa: E402


def cut(s, w):
    s = flat(s)
    return s if not w or len(s) <= w else s[:w] + '…'


def radius(item):
    if item['严重度'] in ('P0', 'P1') or item['类别'] in ('衔接', '分支'):
        return 8
    if item['严重度'] == '小偏差' and item['类别'] == '标点格式':
        return 2
    return 4


def item_header(c, k):
    it = c.items[k]
    gid = c.group_id_of(k)
    extra = []
    if it['显示层冲突组']:
        extra.append('冲突组 ' + it['显示层冲突组'])
    if gid:
        extra.append('同键 %s(%d)' % (gid, len(c.group_rows(k))))
    out = ['■ [%s %s] %s  批次 %s%s' % (it['严重度'], it['类别'], k, it['批次号'], ('  ' + '  '.join(extra)) if extra else ''),
           '  英：' + flat(c.rk[k][COL_EN]),
           '  现：' + flat(c.rk[k][COL_ZH]),
           '  议：' + flat(it['建议译文']),
           '  由：' + flat(it['理由']),
           '  据：' + (it['依据行'] or '（无）')]
    d = c.decs.get(k)
    if d:
        out.append('  定：[%s] %s ｜ %s' % (d.get('decision'), flat(d.get('final')), d.get('note')))
    return out


def ctx_line(c, k, targets, w):
    r = c.rk[k]
    if k in targets:
        out = ['>> %s | %s | %s' % (k, flat(r[COL_EN]), flat(r[COL_ZH])), '     备注：' + (flat(r[COL_NOTE]) or '（无）')]
    else:
        mark = '·' if k in c.items else ' '
        out = ['%s  %s | %s | %s' % (mark, k, cut(r[COL_EN], w), cut(r[COL_ZH], w))]
    d = c.decs.get(k)
    if d:
        out.append('     ⇒[%s] %s' % (d.get('decision'), flat(d.get('final'))))
    return out


def clusters(c, keys, rad):
    """keys 按 manifest 顺序；rad(k) 给半径。返回 [(目标键列表, 起, 止)]，窗口相接即合并。"""
    out = []
    for k in sorted(keys, key=lambda x: c.pos[x]):
        i, r = c.pos[k], rad(k)
        lo, hi = max(0, i - r), min(len(c.order) - 1, i + r)
        if out and lo <= out[-1][2] + 1:
            out[-1][0].append(k)
            out[-1][2] = max(out[-1][2], hi)
        else:
            out.append([[k], lo, hi])
    return out


def show_batch(c, bid, show_all, w):
    keys = [k for k, it in c.items.items() if it['批次号'] == bid and (show_all or k not in c.decs)]
    total = sum(1 for it in c.items.values() if it['批次号'] == bid)
    print('== 批次 %s：清单 %d 条，未定稿 %d 条%s ==' % (bid, total, sum(1 for k, it in c.items.items()
                                                    if it['批次号'] == bid and k not in c.decs),
                                             '（含已定稿）' if show_all else ''))
    for tk, lo, hi in clusters(c, keys, lambda k: radius(c.items[k])):
        print()
        for k in tk:
            print('\n'.join(item_header(c, k)))
        print('  -- 上下文 %s … %s --' % (c.order[lo], c.order[hi]))
        span = set(c.order[lo:hi + 1])
        for k in c.order[lo:hi + 1]:
            print('\n'.join(ctx_line(c, k, set(tk), w)))
        outside = []
        for k in tk:
            for x in (c.items[k]['依据行'] or '').split():
                if x in c.rk and x not in span and x not in outside:
                    outside.append(x)
        for x in outside:
            r = c.rk[x]
            print('  据外 %s [%s] | %s | %s' % (x, c.batch_of(x), flat(r[COL_EN]), flat(r[COL_ZH])))
            d = c.decs.get(x)
            if d:
                print('     ⇒[%s] %s' % (d.get('decision'), flat(d.get('final'))))
    print('\n== 批次 %s 打印完：%d 条 ==' % (bid, len(keys)))


def group_summary(c, gid, mk, ks):
    n_in = sum(1 for k in ks if k in c.items)
    n_dec = sum(1 for k in ks if k in c.decs)
    cg = sorted({c.items[k]['显示层冲突组'] for k in ks if k in c.items and c.items[k]['显示层冲突组']})
    variants = len({norm(c.rk[k][COL_ZH]) for k in ks})
    return '%s | %s | %d 行，清单 %d，已定 %d，现措辞 %d 种 | %s' % (gid, '/'.join(cg) or '-', len(ks), n_in, n_dec, variants, mk)


def show_group(c, gid, n, w, brief=False):
    mk, ks = c.groups()[gid]
    print('== ' + group_summary(c, gid, mk, ks) + ' ==')
    for k in ks:
        it = c.items.get(k)
        sug = ('议[%s %s] %s' % (it['严重度'], it['类别'], flat(it['建议译文']))) if it else '（不在清单）'
        print('  %s %s | 现：%s | %s' % (c.batch_of(k), k, flat(c.rk[k][COL_ZH]), sug))
        d = c.decs.get(k)
        if d:
            print('     ⇒[%s] %s ｜ %s' % (d.get('decision'), flat(d.get('final')), d.get('note')))
    if brief:
        return
    reasons = sorted({c.items[k]['理由'] for k in ks if k in c.items})
    for rs in reasons:
        print('  由：' + flat(rs))
    for tk, lo, hi in clusters(c, ks, lambda k: n):
        print('  -- %s --' % ' '.join(tk))
        for k in c.order[lo:hi + 1]:
            r = c.rk[k]
            if k in tk:
                print('>> %s | %s | %s' % (k, flat(r[COL_EN]), flat(r[COL_ZH])))
            else:
                print('%s  %s | %s | %s' % ('·' if k in c.items else ' ', k, cut(r[COL_EN], w), cut(r[COL_ZH], w)))
                d = c.decs.get(k)
                if d:
                    print('     ⇒[%s] %s' % (d.get('decision'), flat(d.get('final'))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--groups', action='store_true')
    ap.add_argument('--group')
    ap.add_argument('--brief', action='store_true')
    ap.add_argument('-n', type=int, default=3)
    ap.add_argument('-w', type=int, default=0)
    a = ap.parse_args()
    c = Ctx()
    if a.groups:
        for gid, (mk, ks) in c.groups().items():
            if a.brief:
                print(group_summary(c, gid, mk, ks))
            else:
                show_group(c, gid, a.n, a.w)
                print()
        print('== 同键组 %d 个，清单内 %d 条 ==' % (len(c.groups()), sum(1 for _, ks in c.groups().values()
                                                          for k in ks if k in c.items)))
        return
    if a.group:
        gs = c.groups()
        gid = a.group if a.group in gs else next((g for g, (mk, _) in gs.items() if mk == a.group), None)
        if not gid:
            sys.exit('找不到同键组：%s' % a.group)
        show_group(c, gid, a.n, a.w)
        return
    if not a.batch:
        ap.error('需要批次号，或 --groups / --group')
    show_batch(c, '%03d' % int(a.batch), a.all, a.w)


if __name__ == '__main__':
    main()
