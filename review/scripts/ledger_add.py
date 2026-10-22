"""向 review/ledger.md 追加（或替换）一条批次记录，问题数按 findings/ 与 minor/ 分片自动统计。

用法：python3 ledger_add.py 001 "一句话剧情摘要"
同时校验两个分片：每条必须有 key/sev/cat/fix/why/ctx/conf；key 属于本批；sev/cat/conf 取值合法；why ≤60 字；
同一键在 findings 与 minor 中不得重复（小偏差应并进 findings 那条的 fix）。两个文件都必须存在（无问题建空文件）。
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import REVIEW, FINDINGS_DIR, load_manifest, load_batches

MINOR_DIR = os.path.join(REVIEW, 'minor')
SEVS = ('P0', 'P1', 'P2', 'P3')
CATS = ('串位', '误译', '漏译', '增译', '衍文', '人称称谓', '人名术语', '衔接', '分支', '语气', '翻译腔', '标点格式',
        '标签占位符', '显示层冲突', '源文问题')
CONFS = ('高', '中', '低')
HEAD = ['# 逐批精读台账', '',
        '一批一行；问题数由 `scripts/ledger_add.py` 按 findings/ 与 minor/ 分片自动统计。', '',
        '| 批次 | 键范围 | 行数 | P0 | P1 | P2 | P3 | 小偏差 | 剧情摘要 |',
        '| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |']
ISROW = re.compile(r'^\| \d{3} \|')


def check_file(path, bid, man, sevs):
    if not os.path.exists(path):
        raise SystemExit('缺少 %s（没有问题也要建空文件）' % os.path.relpath(path, REVIEW))
    out = []
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        tag = '%s 第%d行' % (os.path.relpath(path, REVIEW), n)
        miss = [k for k in ('key', 'sev', 'cat', 'fix', 'why', 'ctx', 'conf') if k not in d]
        assert not miss, '%s 缺字段 %s' % (tag, miss)
        assert d['key'] in man and man[d['key']]['批次号'] == bid, '%s：%s 不属于本批' % (tag, d['key'])
        assert d['sev'] in sevs, '%s：sev=%s 非法' % (tag, d['sev'])
        assert d['cat'] in CATS, '%s：cat=%s 非法' % (tag, d['cat'])
        assert d['conf'] in CONFS, '%s：conf=%s 非法' % (tag, d['conf'])
        assert len(d['why']) <= 60, '%s：why 超过 60 字（%d）' % (tag, len(d['why']))
        assert isinstance(d['ctx'], list), '%s：ctx 应为列表' % tag
        out.append(d)
    return out


def main():
    bid = '%03d' % int(sys.argv[1])
    summary = sys.argv[2]
    man = load_manifest()
    b = load_batches()[bid]
    fs = check_file(os.path.join(FINDINGS_DIR, '%s.jsonl' % bid), bid, man, SEVS)
    ms = check_file(os.path.join(MINOR_DIR, '%s.jsonl' % bid), bid, man, ('小偏差',))
    dup = set(d['key'] for d in fs) & set(d['key'] for d in ms)
    assert not dup, '同一键同时出现在 findings 与 minor：%s（把小偏差并进 findings 的 fix）' % sorted(dup)
    for lst, name in ((fs, 'findings'), (ms, 'minor')):
        c = Counter(d['key'] for d in lst)
        rep = [k for k, v in c.items() if v > 1]
        assert not rep, '%s 中同一键出现多次：%s（合并成一条）' % (name, rep)
    c = Counter(d['sev'] for d in fs)
    row = '| %s | %s ~ %s | %s | %d | %d | %d | %d | %d | %s |' % (
        bid, b['首键'], b['末键'], b['行数'], c['P0'], c['P1'], c['P2'], c['P3'], len(ms), summary)
    p = os.path.join(REVIEW, 'ledger.md')
    lines = open(p, encoding='utf-8').read().splitlines() if os.path.exists(p) else []
    body = [ln for ln in lines if ISROW.match(ln) and not ln.startswith('| %s |' % bid)]
    body.append(row)
    body.sort()
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(HEAD + body) + '\n')
    print(row)


if __name__ == '__main__':
    main()
