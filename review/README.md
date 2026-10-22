# v8 全量逐行检查（review/v8-full-check）

只读审查，不改 `docs/`、`BepInEx/`、`source/`。脚本均可重复运行，在 `review/scripts/` 下执行。

| 文件 | 内容 |
| :--- | :--- |
| `rules.md` | 规则书摘要（名表、称谓、术语、感叹词、口头禅、D5、锁定项、严重度） |
| `observed.md` | 边读边记的人物关系、「您」的用法、反复出现的说法 |
| `manifest.csv` / `batches.csv` | 21,210 行 → 164 批（每批 ≤150 行，场景边界切分） |
| `precheck/` | 机器预扫候选、显示层冲突组、名表统计；`verdicts.csv` 为显式裁决 |
| `findings/<批次号>.jsonl` | 每批问题（无问题也有空文件） |
| `ledger.md` | 每批一行：键范围、行数、各级问题数、剧情摘要 |
| `findings.csv` / `minor.csv` | 合并结果（`merge_findings.py` 生成，英文/现译/批次号自动回填） |
| `minor/<批次号>.jsonl` | 每批小偏差（rules.md §10.3；无也有空文件） |
| `HANDOFF.md` | 跨会话交接：进度、跨批待补、新会话提示词 |
| `summary.md` | 结论：各级数量、P0/P1 要点、显示层冲突裁决、部署结论 |
| `apply_fixes.py` | 按「采纳」列把建议写进 v8 的副本（默认 `review/out/`，不改 `docs/`；审查方未运行） |
| `FIX_ROUND1.md` | 第一轮修正工作说明：逐条定稿（合人物口吻）后写回 `docs/`，含新会话提示词 |

续跑顺序：读 `rules.md`、`observed.md`、`ledger.md` → `python3 print_batch.py <下一批>` 精读 → 写 `findings/<批次号>.jsonl` → `python3 ledger_add.py <批次号> "摘要"` → `python3 precheck.py`（刷新候选裁决）→ `python3 validate_fixes.py` → `python3 coverage.py`。

`build_manifest.py` 只在需要重排批次时运行；批次一旦开读不要重排。
