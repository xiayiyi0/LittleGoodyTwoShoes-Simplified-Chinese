# -*- coding: utf-8 -*-
"""把 data.unity3d 里全部 TextAsset 导出到一个目录（说话人映射的上游）。

    python tools/extract_textassets.py --out D:\\tmp\\lgts_textassets

为什么要单独一步：`data.unity3d` 有 6.2 GB、55 万个对象，UnityPy 光打开就要 ~6 分钟；
对白 JSON 只有 1,267 个、合计 3.5 MB。导一次落盘，后面反复解析不用再读那个包。
本脚本只读游戏文件，不写游戏目录。

输出：
    <out>/<名字>__<path_id>.txt     每个 TextAsset 一份原文
    <out>/_index.json               清单（名字/长度/开头 160 字），供核对条数

已知：1,267 个 TextAsset 里 1,261 个是对白 JSON。JSON 里带裸换行和尾逗号，
标准解析器会报错 —— 那是资产本来的样子，由 speaker_export.py 的容错解析处理。
"""
import argparse
import io
import json
import os
import sys
import time

import UnityPy

GAME = r"D:\steam\steamapps\common\Little Goody Two Shoes"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pkg", default=os.path.join(GAME, "LGTS_Data", "data.unity3d"))
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    os.makedirs(args.out, exist_ok=True)

    t0 = time.time()
    print("loading %s (6.2 GB, 约 6 分钟)" % args.pkg, flush=True)
    env = UnityPy.load(args.pkg)
    print("loaded %.1fs" % (time.time() - t0), flush=True)

    index, n_obj, n_ta = [], 0, 0
    for obj in env.objects:
        n_obj += 1
        if obj.type.name != "TextAsset":
            continue
        try:
            ta = obj.read()
        except Exception as e:
            print("  read fail pid=%s %s" % (obj.path_id, e), flush=True)
            continue
        n_ta += 1
        name = getattr(ta, "m_Name", None) or ("pid_%s" % obj.path_id)
        script = getattr(ta, "m_Script", None)
        text = script if isinstance(script, str) else (script or b"").decode("utf-8", "replace")
        safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in name)[:120]
        fn = "%s__%s.txt" % (safe, obj.path_id)
        with open(os.path.join(args.out, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        index.append({"name": name, "pid": obj.path_id, "len": len(text),
                      "head": text[:160].replace("\n", "\\n")})
        if n_ta % 200 == 0:
            print("  textassets=%d  %.1fs" % (n_ta, time.time() - t0), flush=True)

    with open(os.path.join(args.out, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print("objects=%d textassets=%d  %.1fs" % (n_obj, n_ta, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())