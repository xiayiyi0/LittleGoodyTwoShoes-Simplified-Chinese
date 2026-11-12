# -*- coding: utf-8 -*-
"""零 Unity 依赖的自检: 编译 Core.cs + selftest/SelfTest.cs 成控制台程序并跑用例。

    python tools/selftest.py

为什么要这个 (v1.3.33 结构侧):
    Norm / ParseFlatJson / 六条模板规则 原先埋在 Plugin.cs 里, 而 Plugin.cs 依赖
    UnityEngine + BepInEx + Harmony —— 这些纯逻辑只能"进游戏看那一屏显示对不对"
    才能验证, 反馈周期以分钟计且要人眼。现在同样的源码被单独编译成 selftest.exe,
    不引用任何 Unity 程序集, 在游戏外 1 秒内跑完一百多条用例。

本脚本做四件事:
  1. 用 in-box csc 编译 source/LGTSChinese/Core.cs + source/LGTSChinese/selftest/SelfTest.cs
     -> source/LGTSChinese/build/selftest.exe (不入库, build/ 已 gitignore);
  2. 让 exe 把三本真词典用 Core.ParseFlatJson 解析一遍并按 Core.DumpFlat 规范转储;
  3. 用标准库 json 解析同一批文件, 与转储逐字节比对 —— 这是"解析器等价性"证明:
     C# 侧读出来的键值必须与 json 一模一样, 否则键丢失/转义错会在这一步炸;
  4. 把用例结果 + 两个源文件的 sha256 写成 tools/acceptance/selftest_v<VER>.txt。
     报告入库, verify_release.py 的 I 组据此断言"自检通过且绑定的是当前源码"。

退出码: 0 = 全绿; 1 = 有用例失败/编译失败/词典比对不一致; 2 = 环境问题(缺 csc 等)。
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source", "LGTSChinese")
BUILD = os.path.join(SRC, "build")
CORE = os.path.join(SRC, "Core.cs")
SELFTEST = os.path.join(SRC, "selftest", "SelfTest.cs")
TRANSLATION = os.path.join(ROOT, r"BepInEx\plugins\LGTSChinese\translation")
ACCEPTANCE = os.path.join(ROOT, "tools", "acceptance")

DICTS = ["lgts_zh_by_refkey.json", "lgts_display.json", "lgts_item_names.json"]

DEFAULT_CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
DEFAULT_FW = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319"


def _out(line):
    try:
        print(line)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(line.encode(enc, "backslashreplace").decode(enc, "replace"))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ver():
    """版本号的唯一来源是 Core.VER; 这里读它, 保证报告与代码一致。"""
    text = io.open(CORE, encoding="utf-8").read()
    m = re.search(r'internal\s+const\s+string\s+VER\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text)
    if not m:
        raise SystemExit("Core.cs 里找不到 internal const string VER = \"x.y.z\";")
    return m.group(1)


def _esc(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _dump(m):
    return "".join("%s\t%s\n" % (k, _esc(m[k])) for k in sorted(m))


def compile_exe(csc, fw):
    exe = os.path.join(BUILD, "selftest.exe")
    os.makedirs(BUILD, exist_ok=True)
    cmd = [csc, "/nologo", "/target:exe", "/langversion:5", "/optimize+",
           "/out:" + exe,
           "/reference:" + os.path.join(fw, "System.dll"),
           "/reference:" + os.path.join(fw, "System.Core.dll"),
           CORE, SELFTEST]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    for line in (p.stdout or "").splitlines():
        _out("  csc: " + line)
    for line in (p.stderr or "").splitlines():
        _out("  csc! " + line)
    if p.returncode != 0 or not os.path.exists(exe):
        return None, p.returncode
    return exe, 0


def main():
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csc", default=DEFAULT_CSC)
    ap.add_argument("--fw", default=DEFAULT_FW)
    ap.add_argument("--report", default=None, help="默认 tools/acceptance/selftest_v<VER>.txt")
    args = ap.parse_args()

    for p in (CORE, SELFTEST):
        if not os.path.exists(p):
            _out("缺少源文件: " + p)
            return 2
    ver = read_ver()
    report = args.report or os.path.join(ACCEPTANCE, "selftest_v%s.txt" % ver)
    _out("自检版本 v%s" % ver)

    exe, rc = compile_exe(args.csc, args.fw)
    if exe is None:
        _out("编译失败 (csc rc=%d), 自检未执行" % rc)
        return 2

    # 中间文件放 build/ 下, 不用系统 %TEMP% —— 本机 %TEMP% 会被清理,
    # 且实测沙箱对 %TEMP% 的写入可能被拒(exe 报"访问被拒绝"而用例根本没跑)。
    tmp = os.path.join(BUILD, "_selftest_tmp")
    os.makedirs(tmp, exist_ok=True)
    body = os.path.join(tmp, "body.txt")
    cmd = [exe, body]
    dumps = []
    for d in DICTS:
        jp = os.path.join(TRANSLATION, d)
        op = os.path.join(tmp, d + ".dump")
        dumps.append((d, jp, op))
        cmd += ["--dump", jp, op]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if not os.path.exists(body):
        _out("自检程序未产出报告 (rc=%s)\n%s\n%s" % (p.returncode, p.stdout, p.stderr))
        return 1
    body_text = io.open(body, encoding="utf-8", newline="").read()

    # ---- 词典等价性: C# 解析 vs 标准库 json ----
    eq_lines, eq_ok = [], True
    for name, jp, op in dumps:
        try:
            want = _dump(json.load(io.open(jp, encoding="utf-8")))
            got = io.open(op, encoding="utf-8", newline="").read() if os.path.exists(op) else None
        except Exception as e:
            eq_lines.append("FAIL %s 比对异常: %s" % (name, e))
            eq_ok = False
            continue
        ok = got == want
        eq_ok &= ok
        detail = "%d 键 / %d B" % (len(want.split("\n")) - 1, len(got.encode("utf-8"))) if got is not None else "无转储"
        eq_lines.append("%s %s C#解析 == json 解析 (%s)" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            la = want.split("\n")
            lb = (got or "").split("\n")
            for i in range(min(len(la), len(lb))):
                if la[i] != lb[i]:
                    eq_lines.append("  首个差异第 %d 行: json=%r / c#=%r"
                                    % (i + 1, la[i][:120], lb[i][:120]))
                    break

    m = re.search(r"^RESULT=(PASS|FAIL) cases=(\d+) fail=(\d+)$", body_text, re.M)
    if not m:
        _out("自检输出里没有 RESULT 行, 视为失败")
        _out(body_text[-800:])
        return 1
    result, cases, nfail = m.group(1), int(m.group(2)), int(m.group(3))
    all_ok = result == "PASS" and nfail == 0 and eq_ok

    head = []
    head.append("=== LGTS Core 自检 v%s ===" % ver)
    head.append("core_sha256=" + sha256(CORE))
    head.append("selftest_sha256=" + sha256(SELFTEST))
    head.append("plugin_ver=" + ver)
    head.append("csc=" + os.path.basename(args.csc))
    head.append("--- 用例 (Case.cs 纯函数) ---")
    tail = ["", "--- 词典等价 (Core.ParseFlatJson vs json) ---"] + eq_lines
    tail.append("")
    tail.append("RESULT=%s cases=%d fail=%d" % ("PASS" if all_ok else "FAIL", cases, nfail))

    os.makedirs(ACCEPTANCE, exist_ok=True)
    io.open(report, "w", encoding="utf-8", newline="").write(
        "\n".join(head) + "\n" + body_text + "\n".join(tail) + "\n")

    for line in eq_lines:
        _out("  " + line)
    _out("\n%s  cases=%d fail=%d  ->  %s"
         % ("RESULT=PASS" if all_ok else "RESULT=FAIL", cases, nfail,
            os.path.relpath(report, ROOT)))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())