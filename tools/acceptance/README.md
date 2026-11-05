# 实机验收证据归档

**规则**：每在游戏里跑完一轮（验收或试玩），就把 `BepInEx/plugins/LGTSChinese/DIAG.txt`
的**原文**复制到这里，命名 `DIAG_<日期>_<时分>.txt`，并更新 `tools/待实机验证.md` 的条目状态。

为什么必须归档：DIAG 是**覆盖写**的，跑一次新的就没了。2026-11-04 那份 207 行、
`seen=8,213` 的 DIAG 已经因为一次重启（62 行新会话）永久丢失，仓库里只剩它的哈希。
哈希对的原文没了，就再也证明不了任何事。

每条证据的价值点：

- 首行 `=== LGTS DIAG v<版本> 启动 ===` 与 `DLL=` / `DLL time=` → 证明它对应哪份发布资产
- `[FINAL]` 的 seen / fixed / miss / missNoise / cjkSkip → 本轮覆盖量与漏译数
- `[TMP MISS]` / `[DEGRADE]` → 有英文没取到译文 / 插件降级
- `[xxx HIT]` 明细 → 规则是否按预期触发（`[NUMTPL HIT]`、`[SAVETIME HIT]`、`[DAYTIME HIT]`…）

`verify_release.py --diag` 会自动核「首行版本」「DLL sha256」「`TMP hook OK`」三件事，
所以归档时**不要改写** DIAG 内容。
