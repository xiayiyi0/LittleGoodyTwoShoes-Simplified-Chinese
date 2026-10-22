"""生成 review/manifest.csv（记录键→批次）与 review/batches.csv（批次概览）。

分区（近似游玩顺序，见任务书 4.3）：
  S1 主线按天：键名带周和天的行（^(CUT|DLG|LVE|LVP|FLV|PIC|CSM)_周_天_），第 1 周第 5 天 → 第 8 周第 6 天；
     同一天内 CUT → DLG → LVE/LVP → FLV → PIC → CSM，类内按文件顺序。
     只带周、不带天且非结局的两组剧情（CUT_3_OWC_01、DLG_7_VCH_05）放在该周最后一天之后。
  S2 森林、梦境与金色少女：WSN / WSV / WCW / WDM / WDS / GG / CSM_01 等不带天数的场景，
     按场景（区域+分支字母）分组，组按首次出现的文件位置排序，组内同 S1 的类别顺序再按文件顺序。
  S3 结局：CUT_8_END* / FLV_8_END* / CUT_END_GG* / ENDING_*，以及结局前导 CUT_8_WDS_SAC、FLV_8_WDS_SAC、
     CUT_8_VCC_CSM（按结局线归组：B → L → SAC → SB → VCC_CSM → W → GG → 结局标题）。
  S4 村民日常 CHR_*：按 NPC 编号分组。
  S5 其余：道具、商店、任务、教程、地点、界面、旁白、字幕、测试残留等，按前缀分组。

批次：每批 ≤150 行。用动态规划在切点上取舍——优先切在场景组边界（类别_周_天_场景码，或 S2/S3 的场景组），
其次切在场景单元（_01_/_02_ 序列）边界，超过 150 行的单元（如 CUT_4_5_OCR_02，370 行）才在单元内部按行切开；
同时压低批数、避免过小的批。相邻两批属于同一场景组时，print_batch.py 多打印 10 行上文（只看不计数）。
可重复运行；输出确定。
"""
import math
import re
import sys
from collections import OrderedDict

sys.path.insert(0, __import__('os').path.dirname(__file__))
from lgts_common import (COL_KEY, COL_CAT, COL_STATE, load_rows, write_csv, MANIFEST, BATCHES, batch_id)

CAP = 150
CTX = 10

MAIN_RE = re.compile(r'^(CUT|DLG|LVE|LVP|FLV|PIC|CSM)_(\d+)_(\d+)_')
WEEK_ONLY_STORY = {'CUT_3_OWC_01': 3, 'DLG_7_VCH_05': 7}
CAT_ORDER = {'CUT': 0, 'DLG': 1, 'LVE': 2, 'LVP': 2, 'FLV': 3, 'PIC': 4, 'CSM': 5}

S3_BLOCKS = [
    ('END_B', lambda k: k.startswith(('CUT_8_END_B_', 'FLV_8_END_B_'))),
    ('END_L', lambda k: k.startswith(('CUT_8_END_L_', 'FLV_8_END_L_'))),
    ('WDS_SAC', lambda k: k.startswith(('CUT_8_WDS_SAC', 'FLV_8_WDS_SAC'))),
    ('END_SAC', lambda k: k.startswith(('CUT_8_END_SAC', 'FLV_8_END_SAC'))),
    ('END_SB', lambda k: k.startswith(('CUT_8_END_SB', 'FLV_8_END_SB'))),
    ('VCC_CSM', lambda k: k.startswith('CUT_8_VCC_CSM')),
    ('END_W', lambda k: k.startswith(('CUT_8_END_W', 'FLV_8_END_W'))),
    ('END_GG', lambda k: k.startswith('CUT_END_GG')),
    ('ENDING', lambda k: k.startswith('ENDING_')),
]

S2_RE = re.compile(r'^(CUT|DLG|FLV|PIC|CSM)_(D_)?(WSN|WSV|WCW|WDM|WDS|GG|CSM_01|01_)')


def cat_of(k):
    return k.split('_', 1)[0]


def unit_of(k):
    """场景单元 = 记录键去掉最后一节行号。"""
    return k.rsplit('_', 1)[0] if '_' in k else k


def s2_group(k):
    """S2 场景组：(区域, 分支)。"""
    if k.startswith(('CSM_01_', 'PIC_CSM_01')):
        return ('CSM_01', '')
    if k.startswith('CSM_GG'):
        return ('CSM_GG', '')
    rest = k.split('_', 1)[1]
    d = ''
    if rest.startswith('D_'):
        d, rest = 'D_', rest[2:]
    if rest.startswith('WCW_WCW_'):
        rest = rest[4:]
    toks = re.split(r'[_\-]', rest)
    area = toks[0]
    if area in ('WDM', 'WDS'):
        return (d + area + '_' + toks[1], '')
    if area == 'WCW':
        sub = []
        for t in toks[1:]:
            if re.fullmatch(r'\d+', t):
                break
            sub.append(t)
        s = '_'.join(sub)
        if s.startswith('A_HOUSE'):
            s = 'A_HOUSE'
        return (d + 'WCW', s)
    sub = toks[1] if len(toks) > 1 else ''
    return (d + area, sub)


def section_of(k):
    if MAIN_RE.match(k):
        return 1
    if unit_of(k) in WEEK_ONLY_STORY:
        return 1
    for name, pred in S3_BLOCKS:
        if pred(k):
            return 3
    if S2_RE.match(k) or k.startswith(('CSM_GG', 'CSM_01_', 'PIC_CSM_01')):
        return 2
    if k.startswith('CHR_'):
        return 4
    return 5


def main():
    header, rows = load_rows()
    keys = [r[COL_KEY] for r in rows]
    assert len(keys) == len(set(keys)), '记录键重复'
    pos = {r[COL_KEY]: r['_pos'] for r in rows}
    sec = {k: section_of(k) for k in keys}

    # ---------- S1 ----------
    s1 = []
    for k in keys:
        if sec[k] != 1:
            continue
        m = MAIN_RE.match(k)
        if m:
            w, d = int(m.group(2)), int(m.group(3))
        else:
            w, d = WEEK_ONLY_STORY[unit_of(k)], 99
        s1.append(((w, d, CAT_ORDER[cat_of(k)], pos[k]), k))
    s1.sort()
    s1_items = []
    for (w, d, c, p), k in s1:
        g2 = '_'.join(k.split('_')[:4])   # 类别_周_天_场景码
        s1_items.append(dict(key=k, unit=unit_of(k), group=g2, label='第%d周第%s天' % (w, d if d != 99 else '末')))

    # ---------- S2 ----------
    s2keys = [k for k in keys if sec[k] == 2]
    area_first, sub_first = {}, {}
    for k in s2keys:
        a, s = s2_group(k)
        area_first.setdefault(a, pos[k])
        sub_first.setdefault((a, s), pos[k])
    s2 = sorted(s2keys, key=lambda k: (area_first[s2_group(k)[0]], sub_first[s2_group(k)],
                                       CAT_ORDER.get(cat_of(k), 9), pos[k]))
    s2_items = [dict(key=k, unit=unit_of(k), group='%s%s' % (s2_group(k)[0], ('-' + s2_group(k)[1]) if s2_group(k)[1] else ''),
                     label='森林/梦境 ' + s2_group(k)[0]) for k in s2]

    # ---------- S3 ----------
    s3 = []
    for k in keys:
        if sec[k] != 3:
            continue
        for bi, (name, pred) in enumerate(S3_BLOCKS):
            if pred(k):
                s3.append(((bi, CAT_ORDER.get(cat_of(k), 9), pos[k]), k, name))
                break
    s3.sort()
    s3_items = []
    for (bi, c, p), k, name in s3:
        u = unit_of(k)
        if name == 'ENDING':
            u = 'ENDING'
        if name == 'VCC_CSM':
            u = 'CUT_8_VCC_CSM'
        s3_items.append(dict(key=k, unit=u, group=name, label='结局 ' + name))

    # ---------- S4 ----------
    s4_items = []
    for k in keys:
        if sec[k] != 4:
            continue
        npc = '_'.join(k.split('_')[:2])
        s4_items.append(dict(key=k, unit=npc, group=npc, label='村民日常 ' + npc))

    # ---------- S5 ----------
    s5keys = [k for k in keys if sec[k] == 5]
    cat_rank = {}
    rowmap = {r[COL_KEY]: r for r in rows}
    order = ['商店与道具', '任务与引导', '场景与地点', '系统与界面', '旁白Timeline', '过场字幕SUB', '结局与其他']

    def pgroup(k):
        t = k.split('_')[0]
        if t in ('DLG', 'CUT'):
            return '_'.join(k.split('_')[:2])
        return t
    grp_first = {}
    for k in s5keys:
        c = rowmap[k][COL_CAT]
        g = (order.index(c) if c in order else 99, pgroup(k))
        grp_first.setdefault(g, pos[k])
    s5 = sorted(s5keys, key=lambda k: (order.index(rowmap[k][COL_CAT]) if rowmap[k][COL_CAT] in order else 99,
                                       grp_first[(order.index(rowmap[k][COL_CAT]) if rowmap[k][COL_CAT] in order else 99, pgroup(k))],
                                       pos[k]))
    s5_items = [dict(key=k, unit='_'.join(k.split('_')[:2]), group=rowmap[k][COL_CAT] + '/' + pgroup(k),
                     label='其余 ' + rowmap[k][COL_CAT]) for k in s5]

    # ---------- 打包（动态规划） ----------
    # 原子 = 场景单元（≤CAP 时不可拆）；超过 CAP 的单元拆成逐行原子。
    # 切点代价：场景组边界 0；组内单元边界 P_UNIT；超大单元内部 P_ROW。
    # 每批固定代价 W_BATCH，欠满代价 (CAP-行数)*W_FILL。最小化总代价。
    W_BATCH, P_UNIT, P_ROW, W_FILL = 100.0, 45.0, 60.0, 0.25
    batches = []   # list of dict(section, items)

    def pack(items, section):
        atoms = []          # list of (items, cut_cost_before)
        prev_group, prev_unit = None, None
        units = OrderedDict()
        for it in items:
            units.setdefault((it['group'], it['unit']), []).append(it)
        for (g, u), its in units.items():
            first_cost = 0.0 if g != prev_group else P_UNIT
            if len(its) > CAP:
                for i, it in enumerate(its):
                    atoms.append(([it], first_cost if i == 0 else P_ROW))
            else:
                atoms.append((its, first_cost))
            prev_group, prev_unit = g, u
        n = len(atoms)
        sizes = [len(a[0]) for a in atoms]
        INF = float('inf')
        dp = [INF] * (n + 1)
        back = [0] * (n + 1)
        dp[0] = 0.0
        for i in range(1, n + 1):
            tot = 0
            j = i
            while j > 0:
                tot += sizes[j - 1]
                if tot > CAP:
                    break
                cut = atoms[j - 1][1] if j - 1 > 0 else 0.0
                c = dp[j - 1] + W_BATCH + (CAP - tot) * W_FILL + cut
                if c < dp[i]:
                    dp[i], back[i] = c, j - 1
                j -= 1
        cuts = []
        i = n
        while i > 0:
            cuts.append((back[i], i))
            i = back[i]
        for a, b in reversed(cuts):
            its = [it for at in atoms[a:b] for it in at[0]]
            batches.append(dict(section=section, items=its))

    pack(s1_items, 1)
    pack(s2_items, 2)
    pack(s3_items, 3)
    pack(s4_items, 4)
    pack(s5_items, 5)

    # 上文：本批首行与上一批末行属同一 group 时打印 CTX 行上文
    man, summ = [], []
    total = 0
    prev_last = None
    for bi, b in enumerate(batches, 1):
        its = b['items']
        ctx = CTX if (prev_last is not None and prev_last['group'] == its[0]['group']) else 0
        bid = batch_id(bi)
        for oi, it in enumerate(its, 1):
            man.append([it['key'], bid, oi, 'S%d' % b['section'], it['group'], it['unit']])
        groups = list(OrderedDict.fromkeys(it['group'] for it in its))
        summ.append([bid, 'S%d' % b['section'], len(its), its[0]['key'], its[-1]['key'], ctx,
                     its[0]['label'] + ('' if its[0]['label'] == its[-1]['label'] else ' → ' + its[-1]['label']),
                     ' '.join(groups)])
        total += len(its)
        prev_last = its[-1]

    assert total == len(keys), (total, len(keys))
    assert len(set(m[0] for m in man)) == len(keys)
    write_csv(MANIFEST, [COL_KEY, '批次号', '批内顺序', '区段', '场景组', '场景单元'], man)
    write_csv(BATCHES, ['批次号', '区段', '行数', '首键', '末键', '上文行数', '范围', '场景组'], summ)
    by_sec = OrderedDict()
    for s in summ:
        by_sec.setdefault(s[1], [0, 0])
        by_sec[s[1]][0] += 1
        by_sec[s[1]][1] += s[2]
    print('总行数 %d，批次 %d，最大批 %d 行，最小批 %d 行' % (total, len(batches), max(s[2] for s in summ), min(s[2] for s in summ)))
    for k, (nb, nr) in by_sec.items():
        print('  %s：%d 批 / %d 行' % (k, nb, nr))


if __name__ == '__main__':
    main()
