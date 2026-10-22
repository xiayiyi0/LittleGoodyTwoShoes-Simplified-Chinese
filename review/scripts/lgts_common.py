"""v8 全检共用工具：读 CSV、显示层匹配键、标签/占位符抽取、manifest 读取。

所有脚本只读 docs/ 下的译本，不写任何 docs/ BepInEx/ source/ 文件。
"""
import csv
import json
import os
import re
from collections import OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REVIEW = os.path.join(ROOT, 'review')
CSV_PATH = os.path.join(ROOT, 'docs', 'Little_Goody_Two_Shoes_汉化_双语译本版本8.csv')
DISPLAY_JSON = os.path.join(ROOT, 'BepInEx', 'plugins', 'LGTSChinese', 'translation', 'lgts_display.json')
MANIFEST = os.path.join(REVIEW, 'manifest.csv')
BATCHES = os.path.join(REVIEW, 'batches.csv')
FINDINGS_DIR = os.path.join(REVIEW, 'findings')
PRECHECK_DIR = os.path.join(REVIEW, 'precheck')

COL_KEY = '记录键'
COL_ZH = '中文译文'
COL_REV_STATE = '修订状态'
COL_REV_ZH = '修订译文'
COL_IDX = '全局序号'
COL_CAT = '分类'
COL_WEEK = '周/组'
COL_SCENE = '场景码'
COL_NOTE = '审查备注'
COL_STATE = '状态'
COL_EN = '英文原文'

# Plugin.cs: TagRe = "<[/#a-zA-Z][^>]*>", WsRe = "\s+"
TAG_RE = re.compile(r'<[/#a-zA-Z][^>]*>')
WS_RE = re.compile(r'\s+')
PH_RE = re.compile(r'\{\d+\}')
SPRITE_RE = re.compile(r'<sprite[^>]*>', re.I)


def load_rows():
    """返回 (header, rows)；rows 为 OrderedDict 列表，保持文件顺序。"""
    with open(CSV_PATH, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = []
        for i, rec in enumerate(reader):
            d = OrderedDict(zip(header, rec))
            d['_pos'] = i  # 文件内顺序（0 起）
            rows.append(d)
    return header, rows


def rows_by_key(rows):
    out = OrderedDict()
    for r in rows:
        out[r[COL_KEY]] = r
    return out


def norm(s):
    """显示层匹配键，与 Plugin.Norm 一致。"""
    if not s:
        return s
    if '<' in s:
        s = TAG_RE.sub('', s)
    s = WS_RE.sub(' ', s)
    return s.strip()


def canon_tag(t):
    """标签归一：小写、去空白、color value="#x" -> color=#x、去引号。"""
    t = t.strip()
    low = t.lower()
    low = re.sub(r'\s+', ' ', low)
    low = re.sub(r'<color\s+value\s*=\s*"?(#[0-9a-f]+)"?\s*>', r'<color=\1>', low)
    low = re.sub(r'\s*=\s*', '=', low)
    return low


def tags_of(s):
    return [canon_tag(m.group(0)) for m in TAG_RE.finditer(s or '')]


def placeholders_of(s):
    return PH_RE.findall(s or '')


def load_display():
    if not os.path.exists(DISPLAY_JSON):
        return {}
    with open(DISPLAY_JSON, encoding='utf-8') as f:
        return json.load(f)


def load_manifest():
    """返回 OrderedDict key -> dict(batch, order, section, scene)。"""
    out = OrderedDict()
    with open(MANIFEST, encoding='utf-8-sig', newline='') as f:
        for rec in csv.DictReader(f):
            out[rec[COL_KEY]] = rec
    return out


def load_batches():
    out = OrderedDict()
    with open(BATCHES, encoding='utf-8-sig', newline='') as f:
        for rec in csv.DictReader(f):
            out[rec['批次号']] = rec
    return out


def is_locked(r):
    k = r[COL_KEY]
    note = r[COL_NOTE]
    if k.startswith(('SUB_001_', 'SUB_002_')):
        return True
    if '定稿·锁定' in note or '锁定歌词' in note or '与 SUB 歌词记录重复' in note:
        return True
    return False


def is_explained(r):
    note = r[COL_NOTE]
    return any(x in note for x in ('有意偏离', '源文修复', '定稿·锁定'))


def write_csv(path, header, recs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(header)
        for rec in recs:
            w.writerow(rec)


def batch_id(n):
    return '%03d' % int(n)
