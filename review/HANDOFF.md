# 跨会话交接

每个会话结束前更新本文件并推送 `review/v8-full-check`。新会话只需要把下面「新会话提示词」整段贴进去。

## 当前进度

- 已完成批次：001–003（以 `ledger.md` 为准，`python3 review/scripts/coverage.py` 可核对）
- 下一批：004
- 最近一次推送：见 `git log -1`

## 已定尺度（详见 `rules.md` §10）

- 显示层冲突：显示意思没错、只丢标签或语气偏 → P1；显示意思明显错 → P0。
- P3：保持试跑水平，每批 ≤3 条。
- 小偏差：单独记到 `minor/<批次号>.jsonl`（`sev` 写「小偏差」），不占 P3 名额；同一键已有 findings 时并入那条的 fix。
- 「日安」、town/village 混用：不逐行记，summary 归纳。

## 跨批待补

`python3 review/scripts/validate_fixes.py` 的「待后续批次补齐」提示列出了同英文、但还没读到的行，读到时按同一建议补记：

| 匹配键 | 已给建议 | 待补行（所在批次） |
| :--- | :--- | :--- |
| `Right!` | 对！（P1 显示层冲突） | `DLG_4_4_VCH_01_067`（059）：它本身答「对吧？」却译「好啊！」，记 P1 误译 + 同步改「对！」 |
| `Elise...!` | 伊莉丝……！（小偏差） | 其余 18 行，读到即补 |
| `Flocke...!` | 弗洛克……！（小偏差） | `CUT_3_5_OWE_02_004` |
| `Ah, Elise...! Wait...!` | 啊，伊莉丝……！等一下……！（小偏差） | `CUT_3_5_OWE_02_028` |

## 新会话提示词

```text
继续《Little Goody Two Shoes》简中 v8 双语译本的全量逐行检查。

1. 准备：仓库 https://github.com/xiayiyi0/LittleGoodyTwoShoes-Simplified-Chinese ，
   若工作区没有就 clone，然后 `git fetch origin && git checkout review/v8-full-check && git pull`。
   只读审查：不改 docs/、BepInEx/、source/，不推 main。
2. 先通读 review/HANDOFF.md、review/rules.md（含 §10 已定尺度）、review/observed.md、review/ledger.md，
   以及 review/README.md 的续跑顺序；原任务书的标准都已落在 rules.md 里。
3. 从 HANDOFF.md 写的「下一批」开始，按 manifest 顺序逐批精读：
   - `cd review/scripts && python3 print_batch.py <批次号>`（多段时 --part 2…，核对「累计 x/x」等于本批行数）；
   - 报问题前用 `python3 print_batch.py --notes KEY…` 看备注，用 `--around KEY -n 10` 看上下文；
   - 问题写 review/findings/<批次号>.jsonl，小偏差写 review/minor/<批次号>.jsonl（都没有也建空文件）；
   - `python3 ledger_add.py <批次号> "一句话剧情摘要"`，再 `python3 precheck.py >/dev/null && python3 validate_fixes.py`；
   - 预扫候选（打印里的 [候:…]）逐条裁决，不成立且需说明的写 review/precheck/verdicts.csv；
   - 读到 HANDOFF.md「跨批待补」里的行，按表补记。
4. 每完成 10 批：回看这 10 批的 findings 统一尺度，更新 observed.md，merge_findings.py，提交并推送。
5. 上下文快满、需要开新窗口时：停止精读，更新 HANDOFF.md（进度、下一批、跨批待补、本提示词），
   提交推送，然后把 HANDOFF.md 里的「新会话提示词」原样输出给用户，不再继续读。
6. 全部 164 批读完后做任务书 4.5（跨场景一致性、显示层冲突逐组裁决）、4.6（P0/P1 复核、validate_fixes）、
   4.7（coverage.py 证明 21,210/21,210、merge_findings.py、summary.md、可选 apply_fixes.py 只生成不运行）。
```
