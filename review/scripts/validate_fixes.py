"""校验 findings 里的建议译文（任务书 4.6）。

逐条检查：
  标签   建议译文的标签多重集 = 英文（备注已说明有意偏离的行，以现译为准）
  占位符 {n} 与英文一致；换行数与英文一致
  标点   无半角 , . ? ! : ; ( ) "；省略号成对 …；破折号成对 —；?!/!? 作「？！」；无「！？」；D5（无省略号处不在 ！/？ 前加 ……）
  引号   「」『』（）成对
  显示层 同一匹配键（Plugin.Norm(英文)）的所有行，采纳建议后中文（去标签）必须一致：
         既查同组建议之间是否一致，也查「只改一行会不会新造冲突」
  其他   建议与现译相同、同一键多条建议互相矛盾
返回非零退出码表示有错误。用法：python3 validate_fixes.py [--quiet]
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict, OrderedDict

sys.path.insert(0, os.path.dirname(__file__))
from lgts_common import (COL_KEY, COL_ZH, COL_EN, FINDINGS_DIR, REVIEW, load_rows, rows_by_key, norm, tags_of,
                         placeholders_of, is_explained, load_manifest, TAG_RE)

HALF = re.compile(r'[,\.\?!:;\(\)"]')


def load_findings():
    """findings/ 与 minor/ 一起校验（小偏差的建议同样不能新造显示层冲突）。"""
    out = []
    for sub in (FINDINGS_DIR, os.path.join(os.path.dirname(FINDINGS_DIR), 'minor')):
        if not os.path.isdir(sub):
            continue
        for fn in sorted(os.listdir(sub)):
            if fn.endswith('.jsonl'):
                for n, line in enumerate(open(os.path.join(sub, fn), encoding='utf-8'), 1):
                    if line.strip():
                        d = json.loads(line)
                        d['_src'] = '%s/%s:%d' % (os.path.basename(sub), fn, n)
                        out.append(d)
    return out


def check_text(fix, en, cur, explained):
    errs = []
    exp = Counter(tags_of(cur if explained else en))
    got = Counter(tags_of(fix))
    if exp != got:
        errs.append('标签不符 应=%s 得=%s' % (sorted(exp.elements()), sorted(got.elements())))
    if Counter(placeholders_of(fix)) != Counter(placeholders_of(en)):
        errs.append('占位符不符')
    if fix.count('\n') != (cur if explained else en).count('\n'):
        errs.append('换行数不符')
    s = TAG_RE.sub('', fix)
    s2 = re.sub(r'\d[\.,:]\d', '', s)
    if HALF.search(s2):
        errs.append('含半角标点 %s' % ''.join(HALF.findall(s2)))
    for m in re.finditer(r'…+', s):
        if len(m.group(0)) % 2:
            errs.append('省略号不成对')
    for m in re.finditer(r'—+', s):
        if len(m.group(0)) != 2:
            errs.append('破折号不是两个—')
    for a, b in (('（', '）'), ('「', '」'), ('『', '』')):
        if s.count(a) != s.count(b):
            errs.append('%s%s 不成对' % (a, b))
    ens = TAG_RE.sub('', en)
    if re.search(r'\?!|!\?', ens) and '？！' not in s:
        errs.append('?! 未作「？！」')
    if '！？' in s:
        errs.append('「！？」应作「？！」')
    if '……' not in ens and '...' not in ens and '…' not in ens and re.search(r'……[！？]', s):
        errs.append('D5：原文无省略号，建议在！/？前加了……')
    return errs


def main():
    quiet = '--quiet' in sys.argv
    header, rows = load_rows()
    rk = rows_by_key(rows)
    groups = defaultdict(list)
    for r in rows:
        if r[COL_EN].strip():
            groups[norm(r[COL_EN])].append(r[COL_KEY])
    man = load_manifest()
    done = set()
    lp = os.path.join(REVIEW, 'ledger.md')
    if os.path.exists(lp):
        for line in open(lp, encoding='utf-8'):
            m = re.match(r'^\|\s*(\d{3})\s*\|', line)
            if m:
                done.add(m.group(1))
    fs = load_findings()
    by_key = defaultdict(list)
    for d in fs:
        by_key[d['key']].append(d)
    errors, warns = [], []
    for d in fs:
        k = d['key']
        if k not in rk:
            errors.append((d['_src'], k, '记录键不存在'))
            continue
        r = rk[k]
        fix = d['fix']
        if fix == r[COL_ZH]:
            errors.append((d['_src'], k, '建议与现译相同'))
        for e in check_text(fix, r[COL_EN], r[COL_ZH], is_explained(r)):
            errors.append((d['_src'], k, e))
    for k, ds in by_key.items():
        if len(set(d['fix'] for d in ds)) > 1:
            errors.append((ds[0]['_src'], k, '同一键有 %d 条互不相同的建议，需合并' % len(ds)))
    # 显示层一致性：采纳全部建议后，同匹配键的中文（去标签）应一致
    final = {k: by_key[k][0]['fix'] if k in by_key else rk[k][COL_ZH] for k in rk}
    touched = set()
    for k in by_key:
        if k not in rk or not rk[k][COL_EN].strip():
            continue
        g = norm(rk[k][COL_EN])
        if g in touched:
            continue
        touched.add(g)
        ks = groups[g]
        if len(ks) < 2:
            continue
        variants = OrderedDict()
        for x in ks:
            variants.setdefault(norm(final[x]), []).append(x)
        if len(variants) > 1:
            detail = '；'.join('%s←%s' % (v, ','.join(xs[:4]) + ('…' if len(xs) > 4 else '')) for v, xs in variants.items())
            unfixed = [x for x in ks if x not in by_key]
            msg = '匹配键「%s」采纳后仍有 %d 种措辞：%s' % (g, len(variants), detail)
            if unfixed:
                msg += '（未给建议的同键行：%s）' % ','.join(unfixed[:6])
            src = by_key[k][0]['_src']
            fixed_variants = set(norm(by_key[x][0]['fix']) for x in ks if x in by_key)
            pending = [x for x in unfixed if man.get(x, {}).get('批次号') not in done]
            # 1) 明确交人工的显示层冲突 → 提示；2) 已给的建议彼此一致、只差尚未读到的批次 → 待补提示；否则错误
            if all(dd['cat'] == '显示层冲突' and '人工' in dd['why'] for x in ks if x in by_key for dd in by_key[x]):
                warns.append((src, k, msg))
            elif len(fixed_variants) == 1 and unfixed and len(pending) == len(unfixed):
                warns.append((src, k, '待后续批次补齐：' + msg))
            else:
                errors.append((src, k, msg))
        else:
            tagv = set(final[x] for x in ks)
            if len(tagv) > 1:
                warns.append((by_key[k][0]['_src'], k, '匹配键「%s」措辞已一致，仅标签不同（显示层只能保留一种标签）' % g))
    for src, k, e in errors:
        print('错误 %s %s：%s' % (src, k, e))
    for src, k, e in warns:
        print('提示 %s %s：%s' % (src, k, e))
    print('共 %d 条建议，错误 %d，提示 %d' % (len(fs), len(errors), len(warns)))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
