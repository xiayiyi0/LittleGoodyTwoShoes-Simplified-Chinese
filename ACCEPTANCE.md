# 发布验收回执（ACCEPTANCE）

记录"最后一次通过的发布验收"的原始回执，用来回答外部审计的第一个问题：
**"验收全绿"到底有没有可复核的记录？**

（2026-11-04 外部结构审查把它列为"不可证实清单 #1"：38 PASS 只存在于聊天记录里，
没有归档，参数（是否带 `--live` / `--csv`）事后无法复考。本文件就是补这个洞。）

## v1.3.32 — 2026-11-04

```
python tools/verify_release.py ^
  --stage temp_work_result/dist/stage_v1332 --version 1.3.32 ^
  --live "D:\steam\steamapps\common\Little Goody Two Shoes" ^
  --csv "docs/Little_Goody_Two_Shoes_汉化_双语译本版本11.csv" ^
  --diag "BepInEx/plugins/LGTSChinese/DIAG.txt"
```

**结果：42 PASS / 0 FAIL / 0 SKIP，退出码 0**

关键行（原样摘录）：

```
PASS live==stage==zip LGTSChinese.dll          | ee0db3f63b05
PASS live==stage==zip lgts_display.json        | 76e1d3179b53
PASS display 25297   | 25297
PASS by_refkey 21189 | item_names 79 | AT 24700 | UI_System 536
PASS 同归一键多译文=override 表 一致  | 未钉 0 [] / 陈旧 0 []
PASS 全部字符有字形  | {}
PASS DIAG 无 [TMP MISS]        | 前 3 条: []
PASS DIAG 无未登记 [DEGRADE]   | 未登记 0 条 [] / 良性 1 条
```

- **良性 1 条**：`[DEGRADE] 中文字体未注入 TMP 全局 fallback; 字形依赖 arialuni/UGUI 通道`
  —— Unity/TMP 版本差异导致 `CreateFontAsset` 返回空，字形由 `arialuni` 与 UGUI 系统字体承担，
  玩家侧无可见影响。已登记在 `verify_release.py` 的 `DEGRADE_OK` 白名单里。
- `DIAG.txt` 快照：9,082 B / sha256 `a20fe4191a86fa02…`（本次运行 2,500+ 次 TMP 写入）。

**运行时覆盖（取自心跳，非 `[FINAL]`，因为验收时游戏仍在运行）：**

| 计数 | 值 |
|---|---|
| TMP seen | 2,500+ |
| fixed（命中改写） | 241 |
| **miss（真漏译）** | **0** |
| missNoise（纯数字/标点，不需要译文） | 2,053 |
| cjkSkip（中文回流） | 205 |
| uniqHit | 103 |
| DEGRADE | 1（同上，良性） |

> **口径说明**：`0 miss` 只代表**本次运行实际渲染过的文本**没有漏译，不等于"全游戏无漏译"。
> 覆盖率取决于这次跑了哪些界面/章节；换一段内容后应重跑 `--diag`。

## 发布物

| 项 | 值 |
|---|---|
| zip | 31,681,166 B / sha256 `be243ef693bfbae63ea798c950fdfc1befe4cc06a801fd6ef7ac5644763e5520` |
| 包内 `SHA256SUMS.txt` | 1,463 B / sha256 `4970568d5e9525107f8e36bff4d4792a5ec3c466d5e29b53e751b53339a6c619` |
| `LGTSChinese.dll` | 41,984 B / 文件版本 1.3.32.0 |

## 约定

1. 每次发布后，把该次回执**追加到本文件顶部**（最新的在最上）。
2. 发布门槛必须带全参数：`--live` / `--csv` / `--diag` 缺一不可；
   省略参数会让检查项整块不执行，`verify_release.py` 会以 `rc=1` 或 `rc=2` 拒绝。
3. 退出码语义：`0` 全绿 / `1` 有 FAIL / `2` 有 SKIP 或检查未跑全。**未完成的验收不算通过。**
