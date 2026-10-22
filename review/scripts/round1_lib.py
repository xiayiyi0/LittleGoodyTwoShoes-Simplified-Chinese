"""第一轮修正（FIX_ROUND1.md）共用：清单、决定文件、同键组、校验。

清单 = review/findings.csv + review/minor.csv（1,036 条）；
决定 = review/round1/<批次号>.jsonl，一行一条 {"key", "decision", "final", "note"}。
"""
import csv
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lgts_common  # noqa: E402

CSV_REL = os.path.relpath(lgts_common.CSV_PATH, lgts_common.ROOT)  # git 里的路径（--post 读基线用）
# 自测用：LGTS_R1_CSV 指向 docs CSV 的副本、LGTS_R1_DIR 指向临时决定目录（round1_selftest.py）
if os.environ.get('LGTS_R1_CSV'):
    lgts_common.CSV_PATH = os.environ['LGTS_R1_CSV']
from lgts_common import (COL_EN, COL_KEY, COL_NOTE, COL_REV_STATE, COL_REV_ZH, COL_ZH, CSV_PATH, REVIEW, ROOT,  # noqa: E402,F401
                         is_explained, is_locked, load_manifest, load_rows, norm, rows_by_key, TAG_RE)
from validate_fixes import check_text  # noqa: E402

R1_DIR = os.environ.get('LGTS_R1_DIR') or os.path.join(REVIEW, 'round1')
DECISIONS = ('采纳', '改写', '不改', '联动')
CHANGING = ('采纳', '改写', '联动')
NOTE_MAX = 30
BASE_REF = 'origin/review/v8-full-check'
LONG_CTX_CATS = ('衔接', '分支')

# 名表：英文名（区分大小写、整词）→ 中文译名。用于「英文有、现译有、定稿丢了」的检查
NAMES = OrderedDict([
    ('Rozenmarine', '萝森玛琳'), ('Rosmarine', '萝丝玛琳'), ('Lebkuchen', '斯佩尔特'), ('Leb', '佩佩'),
    ('Freya', '芙蕾雅'), ('Muffy', '穆菲'), ('Muffs', '穆芙丝'), ('Mubby', '穆比'), ('Muddy', '穆迪'),
    ('Miffy', '米菲'), ('Milly', '米莉'), ('Missy', '米茜'), ('Mindy', '明蒂'), ('Mandy', '曼迪'),
    ('Molly', '莫莉'), ('Melly', '梅莉'), ('Merry', '麦莉'), ('Macy', '梅西'), ('Mercy', '默茜'),
    ('Maggie', '玛姬'), ('Murphy', '墨菲'), ('Martha', '玛莎'), ('Mucky', '穆奇'), ('Maddie', '玛蒂'),
    ('Nelly', '内莉'), ('Matilda', '玛蒂尔达'), ('Melissa', '梅丽莎'), ('Wilma', '威尔玛'), ('Welma', '薇尔玛'),
    ('Elise', '伊莉丝'), ('Holle', '霍尔'), ('Gretel', '格蕾特'), ('Flocke', '弗洛克'), ('Walpurga', '瓦尔普加'),
    ('Kieferberg', '基弗伯格'), ('Primeldorf', '普里梅尔多夫'),
])
# 定案术语：现译有、英文有对应词，定稿不应丢（只记提示，交人工看）
TERMS = [('赠礼', r'\bGifts?\b'), ('信物', r'\bTestaments?\b'), ('良伴', r'Good Company|good company'),
         ('鲜嫩的血肉', r'Tender Flesh'), ('最甜美的琼浆', r'Sweetest Nectar'), ('女巫夜骑', r'hag-?rid'),
         ('节庆', r'[Ff]estival')]
# 定稿里不该新出现的写法（只记提示）
DISCOURAGED = [('礼拜', '「礼拜」作「周」讲应改「星期」'), ('节日', 'festival 统一「节庆」'),
               ('仅此而已', 'is all 不用「仅此而已」'), ('就是这么回事', 'that\'s what 不用「就是这么回事」'),
               ('我敢打赌', 'I wager 并入句中'), ('，我倒觉得', '句尾 I\'d say 并入句中'), ('你知道吧？', '解释性 you see? 不用「你知道吧？」')]


def flat(s):
    return (s or '').replace('\r', '').replace('\n', '⏎')


def unflat(s):
    return (s or '').replace('⏎', '\n')


def load_items():
    """返回 OrderedDict 记录键 -> 清单行（findings 在前，minor 在后）。"""
    items = OrderedDict()
    for fn in ('findings.csv', 'minor.csv'):
        with open(os.path.join(REVIEW, fn), encoding='utf-8-sig', newline='') as f:
            for rec in csv.DictReader(f):
                items[rec['记录键']] = rec
    return items


def decision_files():
    if not os.path.isdir(R1_DIR):
        return []
    return sorted(fn for fn in os.listdir(R1_DIR) if re.fullmatch(r'\d{3}\.jsonl', fn))


def load_decisions():
    """返回 (decs, problems)。decs: OrderedDict key -> dict(+_file, _line)；重复键不覆盖，记进 problems。"""
    decs, problems = OrderedDict(), []
    for fn in decision_files():
        for n, line in enumerate(open(os.path.join(R1_DIR, fn), encoding='utf-8'), 1):
            if not line.strip():
                continue
            src = '%s:%d' % (fn, n)
            try:
                d = json.loads(line)
            except ValueError as e:
                problems.append((src, '?', 'JSON 解析失败：%s' % e))
                continue
            d['_file'], d['_src'] = fn, src
            k = d.get('key', '')
            if k in decs:
                problems.append((src, k, '键重复（已见于 %s）' % decs[k]['_src']))
                continue
            decs[k] = d
    return decs, problems


def write_decision_file(fn, recs):
    os.makedirs(R1_DIR, exist_ok=True)
    with open(os.path.join(R1_DIR, fn), 'w', encoding='utf-8', newline='\n') as f:
        for d in recs:
            f.write(json.dumps({k: d[k] for k in ('key', 'decision', 'final', 'note')}, ensure_ascii=False) + '\n')


class Ctx:
    """一次性载入 docs、manifest、清单、决定。"""

    def __init__(self):
        self.header, self.rows = load_rows()
        self.rk = rows_by_key(self.rows)
        self.man = load_manifest()
        self.order = list(self.man.keys())
        self.pos = {k: i for i, k in enumerate(self.order)}
        self.items = load_items()
        self.decs, self.dec_problems = load_decisions()
        self.en_groups = defaultdict(list)
        for r in self.rows:
            if r[COL_EN].strip():
                self.en_groups[norm(r[COL_EN])].append(r[COL_KEY])
        for g in self.en_groups.values():
            g.sort(key=lambda k: self.pos.get(k, 10 ** 9))
        self._groups = None

    def batch_of(self, k):
        return self.man[k]['批次号'] if k in self.man else None

    def gkey(self, k):
        en = self.rk[k][COL_EN]
        return norm(en) if en.strip() else None

    def group_rows(self, k):
        g = self.gkey(k)
        return self.en_groups[g] if g is not None else [k]

    def groups(self):
        """同键组：同 norm(英文) ≥2 行且至少一行在清单里。返回 OrderedDict Gxx -> (匹配键, [键…])，按 manifest 首行排序。"""
        if self._groups is None:
            gs = [(g, ks) for g, ks in self.en_groups.items() if len(ks) >= 2 and any(k in self.items for k in ks)]
            gs.sort(key=lambda x: self.pos.get(x[1][0], 10 ** 9))
            self._groups = OrderedDict(('G%02d' % i, (g, ks)) for i, (g, ks) in enumerate(gs, 1))
        return self._groups

    def group_id_of(self, k):
        g = self.gkey(k)
        for gid, (mk, _) in self.groups().items():
            if mk == g:
                return gid
        return None

    def cur(self, k):
        return self.rk[k][COL_ZH]

    def final_of(self, k):
        """叠加后的中文：非「不改」的决定用 final，否则现译。"""
        d = self.decs.get(k)
        if d and d.get('decision') in CHANGING:
            return d.get('final', '')
        return self.rk[k][COL_ZH]


def name_term_checks(final, en, cur, note=''):
    """返回 (errors, hints)：名表丢失、真名/错叫混用；术语丢失、不鼓励的写法。
    note 含「源文」（源文修复）时，名表问题只记提示。"""
    errs, hints = [], []
    ens = TAG_RE.sub('', en)
    for e, z in NAMES.items():
        if re.search(r'(?<![A-Za-z])%s(?![A-Za-z])' % re.escape(e), ens) and z in cur and z not in final:
            errs.append('名表：英文有 %s、现译有「%s」，定稿丢了' % (e, z))
    if '萝森玛琳' in final and '萝森玛琳' not in cur and 'Rozenmarine' not in ens:
        errs.append('名表：英文无 Rozenmarine，定稿新出现「萝森玛琳」')
    if '萝丝玛琳' in final and '萝丝玛琳' not in cur and 'Rosmarine' not in ens:
        errs.append('名表：英文无 Rosmarine，定稿新出现「萝丝玛琳」')
    for z, pat in TERMS:
        if z in cur and z not in final and re.search(pat, ens):
            hints.append('术语：现译有「%s」，定稿没有' % z)
    for w, why in DISCOURAGED:
        if w in final and w not in cur:
            hints.append('写法：%s' % why)
    s = TAG_RE.sub('', final)
    if '『' in s and '「' not in s and '『赠礼』' not in s:
        hints.append('引号：『』只用于「」内再套（及『赠礼』）')
    if errs and '源文' in (note or ''):
        hints += [e + '（源文修复，按备注）' for e in errs]
        errs = []
    return errs, hints


def git_base_rows():
    """读 BASE_REF 上的 docs CSV（--post 用来确认其余行没动）；失败返回 None。"""
    try:
        data = subprocess.run(['git', 'show', '%s:%s' % (BASE_REF, CSV_REL)], cwd=ROOT, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''))
    header = next(reader)
    return header, [OrderedDict(zip(header, rec)) for rec in reader]


def note_tag(item, d):
    if d['decision'] == '联动':
        return '[全检·联动] %s' % d['note']
    return '[全检·%s%s] %s' % (item['严重度'], item['类别'], d['note'])


def counts_table(decs, items):
    by_dec = Counter(d.get('decision') for d in decs.values())
    by_sev = defaultdict(Counter)
    for k, d in decs.items():
        sev = items[k]['严重度'] if k in items else '联动'
        by_sev[sev][d.get('decision')] += 1
    return by_dec, by_sev
