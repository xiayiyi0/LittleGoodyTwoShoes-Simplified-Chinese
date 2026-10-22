"""机器预扫：只产出候选，不直接算问题。输出到 review/precheck/。

  candidates.csv          全部候选（候选号 = 检查项:记录键，稳定可复跑）
  display_conflicts.csv   显示层冲突组（按 Plugin.Norm 匹配键计算），含当前显示词典取值
  name_table.csv          人名表统计（英文含名行数 / 中文含译名行数）
  README.md               各检查项计数与说明

裁决列合并规则（每次复跑都重新计算）：
  1) verdicts.csv 里有显式裁决的，用显式裁决；
  2) 否则若该行所在批次已完成（ledger.md 有记录）：findings 里有该键 → 「成立→findings」，否则「已核无误」；
  3) 否则留空（待核）。
"""
import csv
import difflib
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict, Counter

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import (COL_KEY, COL_ZH, COL_EN, COL_NOTE, COL_STATE, PRECHECK_DIR, FINDINGS_DIR, REVIEW,
                         load_rows, norm, tags_of, placeholders_of, load_display, write_csv, is_locked,
                         is_explained, TAG_RE, MANIFEST)

# ---------------- 名表（rules.md 第 1 节） ----------------
# 英文正则 -> 允许的中文写法（任一命中即可）
NAMES = OrderedDict([
    (r'\bElise\b', ['伊莉丝']),
    (r'\bRozenmarine\b', ['萝森玛琳']),
    (r'\bRosmarine\b', ['萝丝玛琳']),
    (r'\bLebkuchen\b', ['斯佩尔特', '姜饼']),
    (r'\bLeb\b', ['佩佩']),
    (r'\bFreya\b', ['芙蕾雅']),
    (r'\bMuffy\b', ['穆菲']),
    (r'\bMuffs\b', ['穆芙丝']),
    (r'\bMubby\b', ['穆比']),
    (r'\bMuddy\b', ['穆迪']),
    (r'\bMiffy\b', ['米菲']),
    (r'\bMilly\b', ['米莉']),
    (r'\bMissy\b', ['米茜']),
    (r'\bMindy\b', ['明蒂']),
    (r'\bMandy\b', ['曼迪']),
    (r'\bMolly\b', ['莫莉']),
    (r'\bMelly\b', ['梅莉']),
    (r'\bMerry\b', ['麦莉']),
    (r'\bMacy\b', ['梅西']),
    (r'\bMercy\b', ['默茜']),
    (r'\bMaggie\b', ['玛姬']),
    (r'\bMurphy\b', ['墨菲']),
    (r'\bMartha\b', ['玛莎']),
    (r'\bWilma\b', ['威尔玛']),
    (r'\bWelma\b', ['薇尔玛']),
    (r'\bHolle\b', ['霍尔']),
    (r'\bGretel\b', ['格蕾特']),
    (r'\bFlocke\b', ['弗洛克']),
    (r'\bWalpurga\b', ['瓦尔普加']),
    (r'\bKieferberg\b', ['基弗伯格']),
    (r'\bPrimeldorf\b', ['普里梅尔多夫']),
    (r'\bApfel\b', ['阿普菲尔']),
    (r'\bLisbeth\b', ['莉丝贝特']),
    (r'\bJochen\b', ['约亨']),
    (r'\bEugen\b', ['欧根']),
    (r'\bOdilie\b', ['奥蒂莉']),
    (r'\bHans\b', ['汉斯']),
    (r'\bGustav\b', ['古斯塔夫']),
    (r'\bBrunhilde\b', ['布伦希尔德']),
    (r'\bBertha\b', ['贝尔塔']),
    (r'\bElma\b', ['埃尔玛']),
    (r'\bDorothea\b', ['多萝特娅']),
    (r'\bJakob\b', ['雅各布']),
    (r'\bMariele\b', ['玛丽勒']),
    (r'\bLudwig\b', ['路德维希']),
    (r'\bLinda\b', ['琳达']),
    (r'\bWilhelm\b', ['威廉']),
    (r'\bMechtilde\b', ['梅希蒂尔德']),
    (r'\bAriane\b', ['阿丽亚娜']),
    (r'\bLoreley\b', ['罗蕾莱']),
    (r'\bMarlen\b', ['玛尔伦']),
    (r'\bBernhard\b', ['伯恩哈德']),
    (r'\bHeinrich\b', ['海因里希']),
    (r'\bGuido\b', ['吉多']),
    (r'\bTristan\b', ['特里斯坦']),
    (r'\bStefan\b', ['斯特凡']),
    (r'\bFynn\b', ['芬恩']),
    (r'\bHenri\b', ['亨利']),
    (r'\bAngelika\b', ['安格莉卡']),
    (r'\bLina\b', ['莉娜']),
    (r'\bAnnika\b', ['安妮卡']),
    (r'\bValerie\b', ['瓦莱丽']),
    (r'\bAlpenrose\b', ['阿尔卑斯玫瑰']),
    (r'\bSanni\b', ['桑妮']),
    (r'\bLiedl\b', ['莉德尔']),
])
# 互斥组：英文是 A，中文却出现了同组另一个名字 → 真名/错叫用反或两人混淆
EXCLUSIVE = [
    ['萝森玛琳', '萝丝玛琳'],
    ['威尔玛', '薇尔玛'],
    ['穆菲', '穆芙丝', '穆比', '穆迪', '米菲', '米莉', '米茜', '明蒂', '曼迪', '莫莉', '梅莉', '麦莉', '梅西', '默茜', '玛姬', '墨菲', '玛莎'],
]

CJK = re.compile(r'[\u4e00-\u9fff]')
HALF_PUNCT = re.compile(r'[,\.\?!:;\(\)"]')
NEG_EN = re.compile(r"\b(not|no|never|nothing|nobody|none|neither|nor|without|nowhere|cannot|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|shouldn't|wouldn't|couldn't|mustn't|ain't|n't)\b|n't\b", re.I)
NEG_ZH = re.compile(r'[不没无非未别莫勿休甭毋否免难缺少]|才怪|哪儿|哪里|哪会|哪能|岂|何必|何须|罢了|算了|拉倒|住口|住手|闭嘴|省省|免了|空手|一干二净|白白|徒劳|休想|妄|绝')
NUM_EN = re.compile(r'\b(\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|dozen|twice|thrice|half|both|pair|couple)\b', re.I)
NUM_ZH = re.compile(r'[0-9一二三四五六七八九十百千万两半俩仨双对几]')
CONNECT = OrderedDict([
    ('可是', r'\b(but|yet|though|however|although)\b'), ('但是', r'\b(but|yet|though|however|although)\b'),
    ('不过', r'\b(but|yet|though|however|although|just|only)\b'), ('而且', r'\b(and|also|too|besides|plus|moreover)\b'),
    ('所以', r"\b(so|therefore|thus|that's why|hence)\b"), ('因为', r"\b(because|since|'cause|as|for)\b"),
    ('然后', r'\b(then|and|after)\b'), ('其实', r'\b(actually|in fact|truth|really|honestly)\b'),
    ('只是', r'\b(just|only|merely|simply|is all|but)\b'), ('反正', r'\b(anyway|anyhow|whatever|either way|in any case)\b'),
    ('总之', r'\b(anyway|anyhow|in any case|either way|all in all)\b'), ('毕竟', r'\b(after all)\b'),
    ('于是', r'\b(so|then|thus)\b'),
])


def strip_tags(s):
    return TAG_RE.sub('', s or '')


def completed_batches():
    p = os.path.join(REVIEW, 'ledger.md')
    done = set()
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            m = re.match(r'^\|\s*(\d{3})\s*\|', line)
            if m:
                done.add(m.group(1))
    return done


def finding_keys():
    ks = defaultdict(list)
    if os.path.isdir(FINDINGS_DIR):
        for fn in sorted(os.listdir(FINDINGS_DIR)):
            if fn.endswith('.jsonl'):
                for line in open(os.path.join(FINDINGS_DIR, fn), encoding='utf-8'):
                    line = line.strip()
                    if line:
                        d = json.loads(line)
                        ks[d['key']].append('%s/%s' % (d['sev'], d['cat']))
    return ks


def load_verdicts():
    p = os.path.join(PRECHECK_DIR, 'verdicts.csv')
    out = {}
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                out[rec['候选号']] = (rec['裁决'], rec.get('说明', ''))
    return out


def main():
    header, rows = load_rows()
    disp = load_display()
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                manifest[rec[COL_KEY]] = rec['批次号']
    cands = OrderedDict()   # id -> dict

    def add(check, r, detail, pre=''):
        cid = '%s:%s' % (check, r[COL_KEY])
        if cid in cands:
            cands[cid]['详情'] += '；' + detail
            return
        cands[cid] = dict(候选号=cid, 检查项=check, 记录键=r[COL_KEY], 批次号=manifest.get(r[COL_KEY], ''),
                          详情=detail, 英文=r[COL_EN], 中文=r[COL_ZH], 备注摘要=r[COL_NOTE][:100], 预判=pre)

    # ---------- 显示层冲突 ----------
    groups = OrderedDict()
    for r in rows:
        if r[COL_EN].strip():
            groups.setdefault(norm(r[COL_EN]), []).append(r)
    conf_rows = []
    gid = 0
    conflict_of = {}
    for k, rs in groups.items():
        zhs = list(OrderedDict.fromkeys(x[COL_ZH] for x in rs))
        if len(zhs) < 2:
            continue
        gid += 1
        kind = '标签差异' if len(set(norm(z) for z in zhs)) == 1 else '措辞差异'
        dv = disp.get(k)
        for x in rs:
            shown = dv if dv is not None else ''
            same = (x[COL_ZH] == dv) if dv is not None else None
            same_norm = (norm(x[COL_ZH]) == norm(dv)) if dv is not None else None
            conflict_of[x[COL_KEY]] = 'D%02d' % gid
            conf_rows.append(['D%02d' % gid, kind, k, len(rs), len(zhs), x[COL_KEY], manifest.get(x[COL_KEY], ''),
                              x[COL_ZH], shown,
                              '是' if same else ('仅标签不同' if same_norm else ('否' if dv is not None else '词典无此键')),
                              '锁定' if is_locked(x) else ''])
            add('D1显示层冲突', x, 'D%02d %s：同英文 %d 行 %d 种译法；显示词典=%s' % (gid, kind, len(rs), len(zhs), dv),
                '锁定行' if is_locked(x) else '')
    write_csv(os.path.join(PRECHECK_DIR, 'display_conflicts.csv'),
              ['冲突组', '类型', '匹配键', '同键行数', '译法数', '记录键', '批次号', '本行中文', '显示词典值', '本行能否正确显示', '锁定'],
              conf_rows)

    # ---------- 名表统计 ----------
    name_stats = []
    for pat, zhs in NAMES.items():
        ne = sum(1 for r in rows if re.search(pat, strip_tags(r[COL_EN])))
        nz = sum(1 for r in rows if any(z in r[COL_ZH] for z in zhs))
        name_stats.append([pat.replace(r'\b', ''), '/'.join(zhs), ne, nz])
    write_csv(os.path.join(PRECHECK_DIR, 'name_table.csv'), ['英文', '译名', '英文含名行数', '中文含译名行数'], name_stats)

    # ---------- 逐行检查 ----------
    by_zh = defaultdict(list)
    ratios = []
    for r in rows:
        en, zh = r[COL_EN], r[COL_ZH]
        k = r[COL_KEY]
        if r[COL_STATE] != '已译':
            # 缺英文源 / 未译：只查显示风险
            z = zh.strip()
            if r[COL_STATE] == '缺英文源' and z:
                if re.fullmatch(r'[A-Za-z0-9_\-]+', z):
                    add('M1缺源显示风险', r, '译文是记录键指针「%s」，若被显示会露出键名' % z, '缺英文源')
                elif re.search(r'(成功\s*){3,}', z):
                    add('M1缺源显示风险', r, '开发测试残留文本', '缺英文源')
                if HALF_PUNCT.search(strip_tags(z)):
                    add('P1半角标点', r, '缺英文源行含半角标点', '缺英文源')
            continue
        if not en.strip():
            continue
        locked = is_locked(r)
        pre = '锁定行' if locked else ('备注已说明' if is_explained(r) else '')
        ens, zhs_ = strip_tags(en), strip_tags(zh)

        # T 标签/占位符/换行
        te, tz = Counter(tags_of(en)), Counter(tags_of(zh))
        if te != tz:
            miss = list((te - tz).elements())
            extra = list((tz - te).elements())
            add('T1标签不一致', r, '英有中无=%s 中有英无=%s' % (miss, extra), pre)
        if Counter(placeholders_of(en)) != Counter(placeholders_of(zh)):
            add('T2占位符不一致', r, '英=%s 中=%s' % (placeholders_of(en), placeholders_of(zh)), pre)
        ne_, nz_ = en.count('\n'), zh.count('\n')
        if ne_ != nz_:
            add('T3换行不一致', r, '英 %d 处换行，中 %d 处' % (ne_, nz_), pre)
        for t in ('b', 'i', 'u', 's', 'color', 'size', 'shake', 'wave', 'incr'):
            o = len(re.findall(r'<%s(?:[\s=][^>]*)?>' % t, zh, re.I))
            c = len(re.findall(r'</%s\s*>' % t, zh, re.I))
            if o != c:
                oe = len(re.findall(r'<%s(?:[\s=][^>]*)?>' % t, en, re.I))
                ce = len(re.findall(r'</%s\s*>' % t, en, re.I))
                add('T4标签不配对', r, '<%s> 开 %d 闭 %d（英文开 %d 闭 %d）' % (t, o, c, oe, ce), pre)

        # P 标点
        hp = HALF_PUNCT.findall(re.sub(r'\d[\.,:]\d', '', zhs_))
        if hp:
            add('P1半角标点', r, '半角：%s' % ''.join(hp), pre)
        for a, b in (('（', '）'), ('「', '」'), ('『', '』'), ('“', '”')):
            if zhs_.count(a) != zhs_.count(b):
                add('P2括号引号不成对', r, '%s %d / %s %d' % (a, zhs_.count(a), b, zhs_.count(b)), pre)
        if '“' in zhs_ or '”' in zhs_:
            add('P2括号引号不成对', r, '用了弯引号“”，规则要求「」', pre)
        for m in re.finditer(r'…+', zhs_):
            if len(m.group(0)) % 2:
                add('P3省略号', r, '省略号「%s」不是成对的…' % m.group(0), pre)
        if re.search(r'\.\.|。。|·{3,}|．', zhs_):
            add('P3省略号', r, '非「……」省略号', pre)
        for m in re.finditer(r'—+', zhs_):
            if len(m.group(0)) != 2:
                add('P4破折号', r, '破折号「%s」不是两个—' % m.group(0), pre)
        if re.search(r'[\u4e00-\u9fff]\s*[-–―－]\s*[\u4e00-\u9fff]|[–―－]', zhs_):
            add('P4破折号', r, '用了 - – ― － 作破折号', pre)
        if re.search(r'\?!|!\?', ens) and '？！' not in zhs_:
            add('P5问叹号', r, '英文 ?!/!? 未译作「？！」', pre)
        if '！？' in zhs_:
            add('P5问叹号', r, '「！？」应作「？！」', pre)
        en_end = ens.rstrip().rstrip('"”’\')）').rstrip()
        zh_end = zhs_.rstrip().rstrip('」』）)').rstrip()
        en_has_ell = ('...' in ens) or ('…' in ens)
        if re.search(r'……[！？]+$', zh_end) and not re.search(r'(\.\.\.|…)\s*[!?]+$', en_end):
            add('P6省略号D5', r, '原文句末无「...!/...?」，译文句末加了「……！/……？」', pre)
        if re.search(r'(\.\.\.|…)$', en_end) and re.search(r'！$', zh_end):
            add('P6省略号D5', r, '原文以省略号收尾，译文以「！」收尾', pre)
        if '『' in zhs_ and '「' not in zhs_ and '赠礼' not in zhs_:
            add('P7单层用『』', r, '无外层「」却用了『』', pre)
        if re.search(r'，，|。。|、、|；；|！。|？。|。！|。？', zhs_):
            add('P8重复标点', r, '标点叠用', pre)

        # E 残留英文
        lat = re.findall(r'[A-Za-z]{2,}', zhs_)
        lat = [w for w in lat if w not in ens and w.lower() not in ('shoe',)]
        if lat:
            add('E1中文含英文', r, '残留：%s' % ' '.join(lat[:5]), pre)
        if not zh.strip():
            add('E2中文为空', r, '有英文无中文', pre)

        # N 人名
        for pat, zl in NAMES.items():
            if re.search(pat, ens):
                if not any(z in zhs_ for z in zl):
                    add('N1人名缺失', r, '英文有 %s，中文无「%s」' % (pat.replace(r'\b', ''), '/'.join(zl)), pre)
            else:
                hit = [z for z in zl if z in zhs_]
                if hit:
                    # 中文出现了译名但英文没有该名（排除同组其他英文写法，如 Lebkuchen/Leb）
                    other = [p for p, zz in NAMES.items() if p != pat and set(zz) & set(hit) and re.search(p, ens)]
                    if not other and not (hit == ['姜饼']):
                        add('N2人名增译', r, '中文有「%s」，英文无 %s' % ('/'.join(hit), pat.replace(r'\b', '')), pre)
        for grp in EXCLUSIVE:
            en_names = [z for pat, zl in NAMES.items() for z in zl if z in grp and re.search(pat, ens)]
            zh_names = [z for z in grp if z in zhs_]
            wrong = [z for z in zh_names if z not in en_names]
            if en_names and wrong:
                add('N3真名错叫混用', r, '英文对应 %s，中文出现 %s' % (en_names, wrong), pre)

        # L 长度/否定/数字
        words = re.findall(r"[A-Za-z']+", ens)
        ncjk = len(CJK.findall(zhs_))
        if len(words) >= 6:
            ratios.append((ncjk / len(words), r))
        if NEG_EN.search(ens) and not NEG_ZH.search(zhs_) and len(words) >= 3:
            add('L2否定缺失', r, '英文有否定词，中文无常见否定字', pre)
        nums = [m.group(0) for m in NUM_EN.finditer(ens)]
        if nums and not NUM_ZH.search(zhs_):
            add('L3数字缺失', r, '英文 %s，中文无数字' % ' '.join(nums), pre)

        # R 衍文/重复
        for c, pat in CONNECT.items():
            nzc = zhs_.count(c)
            if nzc >= 2 and len(re.findall(pat, ens, re.I)) < nzc:
                add('R1连接词重复', r, '「%s」×%d，英文对应词 %d 个' % (c, nzc, len(re.findall(pat, ens, re.I))), pre)
        m = re.search(r'([\u4e00-\u9fff]{2,6})\1', zhs_)
        if m and not re.search(r'(\b\w+\b)[\s,!?.…-]*\1', ens, re.I):
            add('R2相邻重复', r, '「%s」相邻重复' % m.group(0), pre)

        by_zh[zhs_.strip()].append(r)

    # L1 长度比例：取两端约 0.5%
    ratios.sort(key=lambda x: x[0])
    nlo = max(1, len(ratios) // 200)
    for v, r in ratios[:nlo]:
        add('L1长度比例异常', r, '中文 %.2f 字/英文词（偏短）' % v, '锁定行' if is_locked(r) else '')
    for v, r in ratios[-nlo:]:
        add('L1长度比例异常', r, '中文 %.2f 字/英文词（偏长）' % v, '锁定行' if is_locked(r) else '')

    # C1 疑似照抄：中文完全相同，英文差异大
    for z, rs in by_zh.items():
        if len(CJK.findall(z)) < 6 or len(rs) < 2:
            continue
        ens = OrderedDict()
        for r in rs:
            ens.setdefault(re.sub(r'[^a-z ]', '', norm(r[COL_EN]).lower()), []).append(r)
        if len(ens) < 2:
            continue
        keys_ = list(ens.keys())
        for i in range(len(keys_)):
            for j in range(i + 1, len(keys_)):
                sim = difflib.SequenceMatcher(None, keys_[i], keys_[j]).ratio()
                if sim < 0.75:
                    for r in ens[keys_[i]] + ens[keys_[j]]:
                        others = [x[COL_KEY] for x in rs if x[COL_KEY] != r[COL_KEY]][:4]
                        add('C1疑似照抄', r, '中文与 %s 完全相同，英文相似度 %.2f' % (','.join(others), sim),
                            '锁定行' if is_locked(r) else '')

    # ---------- 裁决合并 ----------
    done = completed_batches()
    fk = finding_keys()
    verd = load_verdicts()
    out = []
    cnt = Counter()
    for cid, c in cands.items():
        if cid in verd:
            v = verd[cid][0] + (('：' + verd[cid][1]) if verd[cid][1] else '')
        elif c['批次号'] in done:
            if c['记录键'] in fk:
                v = '成立→findings（%s）' % ','.join(fk[c['记录键']])
            elif c['检查项'].startswith('D1'):
                v = '逐行已读，待 4.5 组裁决'
            else:
                v = '已核无误'
        else:
            v = ''
        c['裁决'] = v
        cnt[c['检查项']] += 1
        out.append([c[x] for x in ('候选号', '检查项', '记录键', '批次号', '详情', '英文', '中文', '备注摘要', '预判', '裁决')])
    out.sort(key=lambda x: (x[3], x[2], x[1]))
    write_csv(os.path.join(PRECHECK_DIR, 'candidates.csv'),
              ['候选号', '检查项', '记录键', '批次号', '详情', '英文', '中文', '备注摘要', '预判', '裁决'], out)

    # ---------- README ----------
    ng = len(set(x[0] for x in conf_rows))
    ntag = len(set(x[0] for x in conf_rows if x[1] == '标签差异'))
    nword_rows = sum(1 for x in conf_rows if x[1] == '措辞差异')
    lines = ['# 机器预扫候选（自动生成，勿手改）', '',
             '由 `review/scripts/precheck.py` 生成；只是候选，逐批精读时裁决。裁决列规则见脚本头注释，',
             '显式裁决写在 `verdicts.csv`（列：候选号,裁决,说明）。', '',
             '显示层冲突：%d 组（标签差异 %d 组，措辞差异 %d 组共 %d 行），明细见 `display_conflicts.csv`。' % (ng, ntag, ng - ntag, nword_rows), '',
             '| 检查项 | 候选数 | 已裁决 |', '| :--- | ---: | ---: |']
    judged = Counter(x[1] for x in out if x[9])
    for k in sorted(cnt):
        lines.append('| %s | %d | %d |' % (k, cnt[k], judged[k]))
    lines.append('| 合计 | %d | %d |' % (sum(cnt.values()), sum(judged.values())))
    with open(os.path.join(PRECHECK_DIR, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
