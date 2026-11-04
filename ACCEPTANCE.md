# 发布验收回执（ACCEPTANCE）

记录"最后一次通过的发布验收"的原始回执，用来回答外部审计的第一个问题：
**"验收全绿"到底有没有可复核的记录？**

（2026-11-04 外部结构审查把它列为"不可证实清单 #1"：38 PASS 只存在于聊天记录里，
没有归档，参数（是否带 `--live` / `--csv`）事后无法复考。本文件就是补这个洞。）

## v1.3.32 — 资产第三次替换（同日，不升版本：同步译者 12:45 正本）

- 译本 CSV 换成译者 `2026-11-04 12:45` 正本：**4,599,027 B / SHA-256 `b6527e69cabf7c6e1f383df4623ee50f569d94810fe06a1e327cd5a5fa4e8a04`**
  （28,248 行 / BOM 在 / CRLF 28,249 行，均未变）。
- 相对上一份共 **177 行**改动，只动「中文译文 + 审查备注」两列；词典改值 by_refkey 90 / display 172 / AT 172 / item_names 0，**四层键数不变**。
- `--scratch` 重建四本产物与仓库现状**逐字节相同**：
  display `82e750a3` / by_refkey `fb54cecf` / item `1f873fc4` / AT `97b6f42d`。
- 无 `--diag` 全参数验收：**39 PASS / 0 FAIL / 0 SKIP**，rc=0（重打包后复核）。
- `--diag` 仍需下次实机复跑（磁盘 DIAG 仍是旧 DLL 产生的）。

## v1.3.32 — 资产第二次替换（同日，不升版本）

命令与下方相同。**结果：39 PASS / 0 FAIL / 0 SKIP，退出码 0**（未带 `--diag`）。

- 改动：小游戏倒计时 `READY` / `GO!` / `ROUND N`、续关花费 `(NT)`、评级字母 `S/A/B/C/D`
  （display 25,297 → **25,304**）。见 `changelog.txt` v1.3.32「同日补充」一节。
- 预飞：两条新规则 + 7 个新键，对本次长时间实机 DIAG 的 5 条 miss 复算 —— **5/5 命中，0 条遗留**。
- 当前发布资产：zip **31,681,565 B / sha256 `1e8994a43b63d495b37c61d18719dab27a78f5958b5f75d00879b3934cd0b0c9`**；
  `LGTSChinese.dll` / sha256 前缀 `8e87d3e73d39`（版本号仍为 1.3.32，同版替换）。
- **`--diag` 复跑待补**：磁盘上的 `DIAG.txt` 是修复前（旧 DLL）产生的，必然 FAIL；
  下次跑完游戏后用带 `--diag` 的命令复核，期望 **42 PASS / 0 FAIL / 0 SKIP**，
  然后把结果补到本节，并删掉本行提示。

## v1.3.32 — 首版资产（2026-11-04）

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
