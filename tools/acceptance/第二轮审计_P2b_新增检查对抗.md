# P2b：2026-11-15 五项对抗验证

已核实：基线为 53 PASS / 0 FAIL / 0 SKIP，rc=0。使用合成 DIAG；这不替代实机回执。

|检查|源码|最小破坏|实际|证据|
|---|---|---|---|---|
|zip 文件集与发布树精确一致 (71)|source=tools/verify_release.py:185|zip 用 AUDIT_EXTRA 替换 .gitignore，条目数仍为71|rc=1 FAIL|work\p2\case_01\mutation.log|
|stage==zip 全部发布文件 (71)|source=tools/verify_release.py:238|stage BepInEx/core/BepInEx.dll 尾附审计字节，不重打包|rc=1 FAIL|work\p2\case_12\mutation.log|
|live==stage 运行树 (62, 不含 config)|source=tools/verify_release.py:260|live BepInEx/core/BepInEx.dll 尾附审计字节|rc=1 FAIL|work\p2\case_19\mutation.log|
|SHA256SUMS 覆盖全部发布文件|source=tools/verify_release.py:224|SHA256SUMS 用哈希正确的 .gitignore 行替换末行，仍15行|rc=1 FAIL|work\p2\case_11\mutation.log|

`--release` 强制参数源码 tools/verify_release.py:151–157；下列拒绝均已实际运行：

- 只改live config豁免：rc=0，PASS；预期 PASS rc=0
- SUMS增加哈希正确的无关行：rc=1，FAIL；预期 FAIL
- --release 缺 --diag：rc=1，REJECT；预期 REJECT
- --release 缺 --live：rc=1，REJECT；预期 REJECT
- --release 缺 --csv：rc=1，REJECT；预期 REJECT
- --release 缺 --live,--csv,--diag：rc=1，REJECT；预期 REJECT
- --release 全参数合成DIAG正对照：rc=0，PASS；预期 PASS（仅证明语法与资产绑定，不是实机证据）

复现全部：`python -B review_out/work/p2_prepare.py` 然后 `python -B review_out/work/p2_audit.py`；工作目录为 SNAP 同级目录。单项复现见 CSV notes 的 --only；每次只改一文件，原始字节位于各 case 的 backup，finally 恢复并断言相等。

53 项从源码 check(...) 调用展开：见 work/p2/check_inventory.json（保留源码行和原表达式）。正常路径 53 项，源码共有 58 个调用节点（含 mutually exclusive 分支、错误分支和自断言）；不可把 AST 节点数直接当正常门禁数。六条 FILES 同路径抽样 DLL/display 两条，其余四条明确标未单独执行。

## 补充复测

复现：`python -B review_out/work/p2_supplement.py`。stage词典改值、zip内词典改值、`--release --diag` 指向缺文件分别独立运行。

- stage_dictionary_changed：rc=1；FAIL=['SHA256SUMS 自举一致', 'stage==zip 全部发布文件 (71)', 'live==stage==zip lgts_display.json', 'live==stage 运行树 (62, 不含 config)', '仓库==发布树 共有文件一致']；Traceback=False；日志 work\p2\stage_dictionary_changed.log。
- zip_dictionary_changed：rc=1；FAIL=['SHA256SUMS 自举一致', 'stage==zip 全部发布文件 (71)', 'live==stage==zip lgts_display.json', '仓库==发布树 共有文件一致']；Traceback=False；日志 work\p2\zip_dictionary_changed.log。
- missing_diag_file：rc=1；FAIL=['DIAG 行数 > 20', 'DIAG 无 [TMP MISS]', 'DIAG 无未登记 [DEGRADE]', 'DIAG 首行版本绑定', 'DIAG DLL 绑定 (sha256)', 'DIAG TMP 钩子已挂', '应跑检查项 53 (实跑 52)']；Traceback=False；日志 work\p2\missing_diag_file.log。

缺DIAG文件时错误分支仅记6项，漏记Gridly项，随后应跑53/实跑52自断言也红（tools/verify_release.py:640、:712）；仍拒绝发布，但错误分支检查数与正常路径不一致。
三份完整副本最终均126文件，与快照逐字节一致，见work/p2/supplement_summary.json。
