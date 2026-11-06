# 历史调试脚本索引

当前仓库的 `Debug/` 只保留 4 个离线日期回归。其余 32 个脚本（联网诊断、桌面个人文件诊断、上游策略/机器学习演示、SCL9 区间诊断等）已在剃刀 batch2 提交 `5bb291a` 中删除，工作区和 `git ls-files` 里都不再存在；本文不再逐个列出已删除脚本的用途，只在需要时从 Git 历史恢复。

不要直接批量运行 `pytest Debug` 或遍历执行 `Debug/test_*.py`：脚本名称中的 `test` 不表示它们都已整理成标准测试框架用例，历史脚本可能联网、读取个人文件或生成输出。默认验收只运行下表 4 个脚本。

| 类别 | 脚本 | 条件及用途 |
| --- | --- | --- |
| 默认离线回归 | `Debug/test_cross_year_infer.py` | 无年份日期跨月、跨年倒推 |
| 默认离线回归 | `Debug/test_cross_year_e2e.py` | 临时构造跨三个月的秒级 TXT 并完整读取 |
| 默认离线回归 | `Debug/test_user_2026_01.py` | 有年份历史数据不被参考年月误过滤 |
| 默认离线回归 | `Debug/test_with_year_filter.py` | 另一参考年月下保留有年份历史数据 |

这 4 个脚本只插入项目根到 `sys.path`，用 `tempfile` 自建 GBK 数据，不依赖 A111/CUL9/SCL9 样本，也不联网。它们由以下入口调用：

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py --razor-changes docs\razor-source-changes.json
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py
```

只跑 4 个回归本身：

```powershell
.\.venv\Scripts\python.exe -B .\Debug\test_cross_year_infer.py
.\.venv\Scripts\python.exe -B .\Debug\test_cross_year_e2e.py
.\.venv\Scripts\python.exe -B .\Debug\test_user_2026_01.py
.\.venv\Scripts\python.exe -B .\Debug\test_with_year_filter.py
```

## 从 Git 历史恢复已删除脚本

若需要排查历史问题，可在新分支或临时目录中按路径恢复，不要把整批脚本直接放回并批量执行：

```powershell
# 查看 batch2 删除了哪些 Debug 脚本
git show --stat --diff-filter=D 5bb291a -- Debug

# 恢复单个脚本（基线提交 24f9cee 中仍有这些文件）
git show 24f9cee:Debug/test_seg_9310.py > .\Debug\test_seg_9310.py
```

恢复 `test_tdx_txt.py`、`test_seg_9310.py` 等依赖 SCL9 样本或相对路径的脚本时，先确认对应样本在项目根目录，并在单独进程中运行。恢复文件只用于临时诊断，不要提交回当前分支；需要长期保留时先确认其用途和依赖。

被删除脚本的清单和逐文件删除理由见 [剃刀验收记录](RAZOR_ACCEPTANCE.md) 与 [依赖审计证据](razor-dependency-evidence.md) §0.1、D5。
