# 修正轮进度

- 阶段：一（同键组）
- 第一阶段：已定 0 / 67 组
- 第二阶段：已完成批次 无；下一批：001
- 最近一次 round1_check.py：错误 0，提示 1（未定稿 1,036 条）
- 跨批联动待补：

| 键 | 原因 |
| :--- | :--- |

- 交维护者（累积）：

| 键 | 类型 | 说明 |
| :--- | :--- | :--- |

## 下一步

第一阶段从 G01 开始：`python3 round1_show.py --groups --brief` 看组概况，`python3 round1_show.py --group Gxx` 逐组看语境定稿。

## 脚本（`review/scripts/`）

| 脚本 | 用途 |
| :--- | :--- |
| `round1_show.py` | `<批次号>` 列未定稿条目与上下文；`--groups [--brief]` / `--group Gxx` 看同键组 |
| `round1_add.py` | 录入决定：stdin 每行 `键 \| 决定 \| 定稿 \| 备注`（决定：采 / 改 / 不 / 联；采、不可留空定稿；换行写 ⏎）；`--touch 批次…` 建空文件；`--del 键…` |
| `round1_check.py` | 校验（默认 / `--final` / `--post`） |
| `round1_apply.py` | 写回 docs（先 `--dry-run`） |
| `round1_selftest.py` | 在临时副本上自测 check / apply 全流程 |
