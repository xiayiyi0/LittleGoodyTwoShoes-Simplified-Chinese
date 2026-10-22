# 跨会话交接

每个会话结束前更新本文件并推送 `review/v8-full-check`。新会话只需要把最下面「新会话提示词」整段贴进去。

## 当前进度（会话 1 结束时）

- 已完成：001–010（10 / 164 批，1,369 / 21,210 行，6.5%）。以 `ledger.md` 为准，`python3 review/scripts/coverage.py` 可核对。
- **下一批：011**（第 2 周第 3 天，`DLG_2_3_VIN`/`DLG_2_3_VSQ` 起）。
- 已记：findings 53 条（P0 4 / P1 10 / P2 34 / P3 5），小偏差 32 条。
- 下一个 10 批检查点：020 完成后（回看 011–020 尺度、更新 observed.md、merge、提交推送）。

## 已定尺度（详见 `rules.md` §10）

- 显示层冲突按组定级：任一场景显示错意 → 组内需改的行都记 P0；只丢标签、语气偏、同义替换 → P1。≤3 行的组读到就定，≥4 行的组留到 4.5。
- P3：每批 ≤3 条，改动小且明显更好才记。
- 小偏差：写 `minor/<批次号>.jsonl`（`sev` = 小偏差），不占 P3 名额；同键已有 findings 就并进那条 fix。「日安」、town/village 混用只在 summary 归纳。
- 独白 / FLV·PIC 自语里的附加问句（huh?、can I?、isn't it? 等）译成「是吧？/不是吗？/……吧？」→ P2 标点格式（预扫 `P9` 列出，打印里标 `[候:P9]`）。
- v8 口头禅：解释性 you see? 译「你知道吧？」、I wager 译「我敢打赌」、I'd say 以「，我倒觉得」收尾 → P2 翻译腔（备注里有 `[v8口头禅…]` 且是有意保留的除外）。
- 报问题前务必 `--notes` 看备注；`[v8…]`、`[语境修复]` 等标签说明是有意处理的，不重复报。
- 补丁里的 `lgts_display.json` / `lgts_zh_by_refkey.json` 是 v8 之前的旧表（措辞不同的英文键 2,444 个），summary 要写进部署结论。

## 跨批待补

`python3 review/scripts/validate_fixes.py` 的「待后续批次补齐」提示会列出同英文、还没读到的行；读到时按同一建议补记（批次号是估计，以 manifest 为准）：

| 匹配键 / 冲突组 | 已给建议 | 待补行 |
| :--- | :--- | :--- |
| `Right!`（D19） | 对！（P1 显示层冲突） | `DLG_4_4_VCH_01_067`（059）：它本身答「对吧？」却译「好啊！」，记 P1 显示层冲突，fix「对！」 |
| `What was?`（D29） | 什么事？（P0） | `DLG_8_3_VIN_07_007` |
| `What was, Mrs. Ariane?`（D03） | 您指什么，阿丽亚娜太太？（P0） | `DLG_7_1_VIN_01_002` |
| `What's that?`（D06） | 什么？（P0） | `FLV_D_WSN-A_01_002`（S2 区段） |
| `No, I haven't...`（D10） | 没有，我没有……（P0） | `DLG_3_4_VSQ_03_004`、`CUT_5_1_VCH_01_003` |
| `I won't, I won't!`（D31） | 不会的，不会的！（P1） | `LVE_2_4_HBY_R_047` |
| `What... are you...?`（D30） | 你……到底<i>是</i>什么……？（标签按该行英文，P1） | `CUT_WCW_E_PITFALLS_02_024`（现作「究竟」） |
| `Elise...!` | 伊莉丝……！（小偏差） | 其余 16 行，读到即补 |
| `Flocke...!` | 弗洛克……！（小偏差） | `CUT_3_5_OWE_02_004` |
| `Ah, Elise...! Wait...!` | 啊，伊莉丝……！等一下……！（小偏差） | `CUT_3_5_OWE_02_028` |

## 新会话提示词

```text
继续《Little Goody Two Shoes》简中 v8 双语译本的全量逐行检查（只读审查，跨会话接力）。

1. 准备：仓库 https://github.com/xiayiyi0/LittleGoodyTwoShoes-Simplified-Chinese 。
   工作区没有就 clone；然后在仓库目录执行 `git fetch origin && git checkout review/v8-full-check && git pull`。
   硬性约束：不改 docs/、BepInEx/、source/，不推 main，不用机器翻译服务生成或核对译文。
2. 先通读 review/HANDOFF.md（进度、已定尺度、跨批待补）、review/rules.md（含 §10 已定尺度）、
   review/observed.md、review/ledger.md、review/README.md。原任务书的标准已全部落在 rules.md 里。
3. 从 HANDOFF.md 写的「下一批」开始，按 manifest 顺序逐批精读，每批：
   - `cd review/scripts && python3 print_batch.py <批次号>`；多段时 `--part 2…`，核对末行「累计 x/x」等于本批行数；
   - 先通读英文弄清谁对谁说，再逐行对照中文（rules.md §8 清单）；报问题前 `python3 print_batch.py --notes KEY…` 看备注，
     需要上下文用 `--around KEY -n 10`；
   - 问题写 review/findings/<批次号>.jsonl，小偏差写 review/minor/<批次号>.jsonl（都没有也建空文件），
     字段 key/sev/cat/fix/why(≤60字)/ctx/conf；同一键只能有一条；
   - `python3 ledger_add.py <批次号> "一句话剧情摘要"`，再 `python3 precheck.py >/dev/null && python3 validate_fixes.py`
     （不能有「错误」；「待后续批次补齐」是正常提示）；
   - 打印里的 [候:…] 预扫候选逐条裁决，不成立又需要说明的写 review/precheck/verdicts.csv；
   - 读到 HANDOFF.md「跨批待补」表里的行，按表补记，并从表里删掉。
4. 每完成 10 批（020、030…）：回看这 10 批 findings 统一尺度，更新 observed.md，`python3 merge_findings.py`，
   提交（git add review，提交信息如「review: 精读 011–020」）并 `git push`。
5. 上下文快满、需要开新窗口时：停止精读，更新 HANDOFF.md（进度、下一批、跨批待补），merge、提交、推送，
   然后把 HANDOFF.md 里的「新会话提示词」原样输出给用户，不再继续读。
6. 164 批全部读完后：做任务书 4.5（显示层冲突逐组裁决、道具/地点/任务术语与人物称谓全剧一致性）、
   4.6（每条 P0/P1 重读前后 10 行和备注复核；validate_fixes.py 零错误）、
   4.7（coverage.py 证明 21,210/21,210；merge_findings.py 生成 findings.csv / minor.csv；写 review/summary.md；
   可选生成 review/apply_fixes.py，只生成不运行）。
```
