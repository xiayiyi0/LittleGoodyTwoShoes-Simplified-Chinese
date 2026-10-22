"""round1_check / round1_apply 自测：在 docs CSV 的临时副本和临时决定目录上跑，不碰 docs/ 与 review/round1/。

  python3 round1_selftest.py
1. 故意写错的决定 → round1_check 报出每一类错误；
2. 1,036 条全部「采纳」→ --final 零错误 → round1_apply --dry-run 不写 → round1_apply 写副本 → --post 零错误；
   并核对写回只动了预期的行和四列、未改动时与原文件逐字节一致。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from round1_lib import BASE_REF, CSV_PATH, CSV_REL, ROOT, Ctx, load_items, load_manifest  # noqa: E402


def run(args, env):
    p = subprocess.run([sys.executable] + args, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8')


def write(d, fn, recs):
    with open(os.path.join(d, fn), 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def main():
    tmp = tempfile.mkdtemp(prefix='r1test_')
    ok = True
    try:
        csv_copy = os.path.join(tmp, 'v8.csv')
        # 用写回前的基线（BASE_REF）做副本，docs 已写回后也能重跑；取不到基线才退回复制当前文件
        try:
            base = subprocess.run(['git', 'show', '%s:%s' % (BASE_REF, CSV_REL)], cwd=ROOT, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
            with open(csv_copy, 'wb') as f:
                f.write(base)
        except (OSError, subprocess.CalledProcessError):
            shutil.copyfile(CSV_PATH, csv_copy)
        r1 = os.path.join(tmp, 'round1')
        os.makedirs(r1)
        env = dict(os.environ, LGTS_R1_CSV=csv_copy, LGTS_R1_DIR=r1)
        items = load_items()
        man = load_manifest()
        c = Ctx()
        # ---- 1. 错误检测 ----
        g = [k for k in items if items[k]['显示层冲突组'] == 'D01']
        k_ok = next(k for k in items if not items[k]['显示层冲突组'] and items[k]['批次号'] == '001')
        b = lambda k: man[k]['批次号'] + '.jsonl'  # noqa: E731
        bad = {}
        bad.setdefault(b(k_ok), []).append({'key': k_ok, 'decision': '采纳', 'final': items[k_ok]['建议译文'] + 'x',
                                            'note': '采纳却改了字'})
        k2 = [k for k in items if items[k]['批次号'] == '001' and k != k_ok][0]
        bad.setdefault(b(k2), []).append({'key': k2, 'decision': '不改', 'final': '别的', 'note': '超' * 31})
        bad.setdefault('002.jsonl', []).append({'key': g[0], 'decision': '采纳', 'final': items[g[0]]['建议译文'],
                                                'note': '写错批次'})
        locked = next(r['记录键'] for r in c.rows if r['记录键'].startswith('SUB_001_'))
        bad.setdefault(b(locked), []).append({'key': locked, 'decision': '联动', 'final': '改歌词', 'note': '锁定行'})
        tag_k = next(k for k in items if '<' in c.rk[k]['英文原文'] and not items[k]['显示层冲突组'])
        bad.setdefault(b(tag_k), []).append({'key': tag_k, 'decision': '改写', 'final': '去掉了标签的定稿。', 'note': '标签'})
        for fn, recs in bad.items():
            write(r1, fn, recs)
        code, out = run(['round1_check.py', '-q'], env)
        want = ['采纳但 final ≠ 建议译文', 'note 超过', '不改但 final ≠ 现译文', '应写在', '锁定行不能改', '标签不符']
        miss = [w for w in want if w not in out]
        print('1. 错误检测：退出码 %d，%s' % (code, '全部报出' if not miss and code == 1 else '漏报 %s' % miss))
        ok &= not miss and code == 1
        # 同键组只采纳一行 → --final 报显示层错误；默认模式记「待补」
        shutil.rmtree(r1)
        os.makedirs(r1)
        write(r1, b(g[0]), [{'key': g[0], 'decision': '采纳', 'final': items[g[0]]['建议译文'], 'note': '组内一行'}])
        code, out = run(['round1_check.py'], env)
        okd = code == 0 and '待补' in out
        code, out = run(['round1_check.py', '--final', '-q'], env)
        okf = code == 1 and '种措辞' in out
        print('   同键组未齐：默认模式记待补 %s；--final 报错 %s' % (okd, okf))
        ok &= okd and okf
        # ---- 2. 全部采纳 → 写回副本 → --post ----
        shutil.rmtree(r1)
        os.makedirs(r1)
        per = {}
        for k, it in items.items():
            per.setdefault(it['批次号'] + '.jsonl', []).append(
                {'key': k, 'decision': '采纳', 'final': it['建议译文'],
                 'note': '源文修复（自测）' if it['类别'] == '源文问题' else '自测'})
        for fn, recs in per.items():
            write(r1, fn, recs)
        code, out = run(['round1_check.py', '--final', '-q'], env)
        print('2. 全部采纳 --final：退出码 %d（%s）' % (code, out.strip().splitlines()[-1]))
        ok &= code == 0
        before = open(csv_copy, 'rb').read()
        code, out = run(['round1_apply.py', '--dry-run'], env)
        same = open(csv_copy, 'rb').read() == before
        print('   apply --dry-run：退出码 %d，文件未变 %s' % (code, same))
        ok &= code == 0 and same
        code, out = run(['round1_apply.py'], env)
        print('   apply：退出码 %d（%s）' % (code, ' / '.join(out.strip().splitlines()[-2:])))
        ok &= code == 0 and '自检通过' in out
        code, out = run(['round1_check.py', '--post', '-q'], env)
        print('   --post：退出码 %d（%s）' % (code, out.strip().splitlines()[-1]))
        ok &= code == 0
        # 篡改一行 → --post 应报错
        import csv as _csv
        with open(csv_copy, encoding='utf-8-sig', newline='') as f:
            rows = list(_csv.reader(f))
        rows[1][1] = rows[1][1] + '改'
        with open(csv_copy, 'w', encoding='utf-8-sig', newline='') as f:
            w = _csv.writer(f, lineterminator='\n')
            w.writerows(rows)
        code, out = run(['round1_check.py', '--post', '-q'], env)
        print('   篡改一行后 --post：退出码 %d（应为 1）' % code)
        ok &= code == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('自测%s' % ('通过' if ok else '失败'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
