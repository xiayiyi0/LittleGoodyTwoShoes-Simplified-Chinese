"""向 review/ledger.md 追加（或替换）一条批次记录，问题数按 findings/<批次号>.jsonl 自动统计。

用法：python3 ledger_add.py 001 "一句话剧情摘要"
同时校验 findings 分片：每条必须有 key/sev/cat/fix/why/ctx/conf，key 必须属于本批，sev/cat/conf 取值合法，why ≤60 字。
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import REVIEW, FINDINGS_DIR, load_manifest, load_batches, COL_KEY

SEVS = ('P0', 'P1', 'P2', 'P3')
CATS = ('串位', '误译', '漏译', '增译', '衍文', '人称称谓', '人名术语', '衔接', '分支', '语气', '翻译腔', '标点格式',
        '标签占位符', '显示层冲突', '源文问题')
CONFS = ('高', '中', '低')
HEAD = ['# 逐批精读台账', '',
        '一批一行；问题数由 `scripts/ledger_add.py` 按 findings 分片自动统计。', '',
        '| 批次 | 键范围 | 行数 | P0 | P1 | P2 | P3 | 剧情摘要 |',
        '| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |']


def check_findings(bid, man):
    p = os.path.join(FINDINGS_DIR, '%s.jsonl' % bid)
    if not os.path.exists(p):
        raise SystemExit('缺少 findings/%s.jsonl（没有问题也要建空文件）' % bid)
    out = []
    for n, line in enumerate(open(p, encoding='utf-8'), 1):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        miss = [k for k in ('key', 'sev', 'cat', 'fix', 'why', 'ctx', 'conf') if k not in d]
        assert not miss, '%s 第%d行缺字段 %s' % (bid, n, miss)
        assert d['key'] in man and man[d['key']]['批次号'] == bid, '%s 第%d行：%s 不属于本批' % (bid, n, d['key'])
        assert d['sev'] in SEVS and d['cat'] in CATS and d['conf'] in CONFS, '%s 第%d行取值非法' % (bid, n)
        assert len(d['why']) <= 60, '%s 第%d行 why 超过 60 字（%d）' % (bid, n, len(d['why']))
        assert isinstance(d['ctx'], list), '%s 第%d行 ctx 应为列表' % (bid, n)
        out.append(d)
    return out


def main():
    bid = '%03d' % int(sys.argv[1])
    summary = sys.argv[2]
    man = load_manifest()
    b = load_batches()[bid]
    fs = check_findings(bid, man)
    c = Counter(d['sev'] for d in fs)
    row = '| %s | %s ~ %s | %s | %d | %d | %d | %d | %s |' % (bid, b['首键'], b['末键'], b['行数'], c['P0'], c['P1'], c['P2'], c['P3'], summary)
    p = os.path.join(REVIEW, 'ledger.md')
    lines = open(p, encoding='utf-8').read().splitlines() if os.path.exists(p) else list(HEAD)
    import re
    isrow = re.compile(r'^\| \d{3} \|')
    lines = [ln for ln in lines if not ln.startswith('| %s |' % bid)]
    lines.append(row)
    head = [ln for ln in lines if not isrow.match(ln)]
    body = sorted(ln for ln in lines if isrow.match(ln))
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(head + body) + '\n')
    print(row)


if __name__ == '__main__':
    main()
