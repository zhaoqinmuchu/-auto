# 开发、依赖、构建、备份与恢复

本文记录剃刀版（分支 `codex/razor-project`）的实际开发环境、构建方法、验证入口和恢复方式。整理阶段的原始记录仍保留在 `docs/VERIFICATION.md` 前半部分。

## 独立开发环境

以下命令在开发目录的 PowerShell 中执行。现有 `.venv` 使用 Python **3.14.10**，只在本项目安装 GUI 依赖和构建依赖，没有修改系统 Python。

```powershell
.\.venv\Scripts\python.exe -B .\App\ashare_bsp_scanner_gui.py
```

在新机器上重建环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements-gui.txt` 固定了本次独立环境实际安装并检查过的 22 个 GUI 依赖及传递依赖，包含旧清单遗漏的 PyQt6。pandas 不在 GUI 源码里直接 import，但 baostock 的元数据声明 `Requires-Dist: pandas>=0.18.0`，且 `import baostock` 会实际加载 pandas，所以不能从清单删除（文件内已加注释）。依赖决策证据见 [razor-dependency-evidence.md](razor-dependency-evidence.md) §2。

`requirements-build.txt` 在 `requirements-gui.txt` 之上增加：

```text
PyInstaller==6.22.3
pyinstaller-hooks-contrib==2026.8
```

该文件顶部的注释「未安装未重建」是整理阶段留下的历史说明；截至 2026-11-06，这两个版本已安装到 `.venv` 并用于实际构建。

### 本机安装 PyInstaller 的特殊情况

本机 `pip install` 在解包阶段被沙箱临时目录权限拦截，报错原文：

```text
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied:
'C:\Users\q8369\Documents\ChatGPT\chan.py-main\.local-validation\tmp\pip-unpack-sxpge94y\pyinstaller-6.22.3-py3-none-win_amd64.whl.metadata'
```

日志在 `.local-validation/razor/pip-install.log`。绕开 pip 临时解包步骤的办法：脚本 `.local-validation/razor/install_pyinstaller.py` 从 PyPI 下载 wheel 到 `.local-validation/wheels/`，再直接解压到 `.venv/Lib/site-packages/`。本次涉及的 wheel 包括 `pyinstaller-6.22.3-py3-none-win_amd64`、`pyinstaller_hooks_contrib-2026.8`、`altgraph-0.17.5`、`macholib-1.16.4`、`pefile-2024.8.26`、`pywin32_ctypes-0.2.3`、`setuptools-84.2.1`、`importlib_metadata-10.1.0`、`zipp-4.1.2`、`packaging-26.3`。这不是推荐做法，只用于绕开本机权限问题；pip 可正常工作的环境请使用 `pip install -r requirements-build.txt`。

旧桌面 EXE 内嵌 `python313.dll`，旧构建记录也指向 Python 3.13；本次源码和自动检查使用 Python 3.14.10。**候选 EXE 是 3.14 的新构建，不是旧 3.13 打包环境的复现。**

## 离线检查与剃刀验收

剃刀版总验收（基线 + 变更清单 + 语法 + 4 回归 + 三样本指纹）：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py
```

需要同时重新执行 Qt 离屏检查时：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py --gui
```

与已核验的参考快照做完整源码对照：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py --reference .\.local-backups\2026-11-06-baseline\restore-check\chan.py-main
```

旧的 `tools/verify_project.py` 仍保留：默认严格模式检查原 96 个 `.py` 逐字节不变，剃刀后**会按设计失败**（`Original source changed: App/ashare_bsp_scanner_gui.py`）。需要旧入口时加清单参数，不要改写基线 JSON：

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py --razor-changes docs\razor-source-changes.json
```

单独运行 Qt 离屏检查：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_gui_check.py --output .\.local-validation\razor\gui-after.json
```

`tools/gui_smoke.py` 是整理阶段使用的 GUI 检查；剃刀版的验收面已由 `tools/razor_gui_check.py` 覆盖（39 项）。离屏检查使用 Qt offscreen，不操作桌面现用窗口，也不等于真实鼠标操作。

## Git 日常使用

```powershell
git status
git log --oneline --decorate -8
git switch -c codex/describe-your-change
# 完成修改和相关检查后，明确选择要保存的文件：
git add PROJECT_GUIDE.md docs/RAZOR_ACCEPTANCE.md
git commit -m "docs: update Razor acceptance record"
```

- 远程仓库：`origin` 为 `git@github.com:zhaoqinmuchu/-auto.git`（fetch/push，SSH）。
- 当前分支：`codex/razor-project`，没有设置 upstream；本地有标签 `baseline-2026-11-06`、`organized-2026-11-06`。
- 是否推送、是否合并回 `main` 由用户明确决定；剃刀计划默认不合入、不推送，不替换桌面原版。
- 保存源码、文档、打包配置和手写公式；不保存现用 EXE、依赖库、构建缓存、行情数据和本机备份。`build/`、`dist/`、`.venv/`、`.local-backups/`、`.local-validation/` 均被忽略。
- 继续修改业务源码时，先记录对应版本和新的行为预期，再有意识地更新基线检查；不要为让检查通过而直接改校验清单。

## 本次完整快照

快照保存在开发目录的 `.local-backups/2026-11-06-baseline`：

- `chan.py-main-full.zip`：桌面原项目在整理阶段的完整快照，含 EXE、`_internal`、源码、样本、构建记录与原始忽略文件；208,007,325 字节，SHA-256 `9bc6e8e41a143fb5395cd0a45453c9ef912071bf48ed0ef3398ceca6995c794a`。
- `manifest.json`：逐文件相对路径、大小、SHA-256 和原始修改时间记录。
- `SHA256SUMS.txt`：压缩包 SHA-256。
- `snapshot-verification.json`：ZIP 完整性、实际解压文件和原目录逐文件校验结果。
- `restore-check/chan.py-main`：已解压并核验的程序目录，可用作参考源码树。

恢复程序时解压到**新目录**，不要覆盖正在使用的版本：

```powershell
python -m zipfile -t .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip
python -m zipfile -e .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip .\.local-backups\manual-restore-new
```

恢复后的程序入口在新目录内的 `chan.py-main/dist/ChanScanner/ChanScanner.exe`，必须保留同目录全部配套文件。`zipfile -t` 是 ZIP 完整性检查；如需验证实际文件内容，按 manifest 中的 SHA-256 比较。

## Git bundle 与恢复源码

本次离线历史包为 `.local-backups/ChanScanner-history-2026-11-06.bundle`，7,349,586 字节，SHA-256 `a38c589fbd6f5996e32514bdcd527d97524db17fbe53d5efa75a8436f50390d8`；对应校验文件为同名追加 `.sha256`。它包含创建时的全部本地分支和两个版本标签，不包含行情数据、虚拟环境和完整程序。

```powershell
git bundle verify .\.local-backups\ChanScanner-history-2026-11-06.bundle
git clone --config core.autocrlf=false .\.local-backups\ChanScanner-history-2026-11-06.bundle .\.local-backups\manual-source-restore-new
```

恢复命令显式设置 `core.autocrlf=false`，避免本机全局 Git 配置将原始 LF 换行转换为 CRLF，影响逐字节校验。若仓库已经用其他命令恢复，先在该新仓库内执行 `git config --local core.autocrlf false`。

要查看整理完成状态，可在**新恢复的仓库**内使用 `git switch --detach organized-2026-11-06`；要查看整理前基线，使用 `baseline-2026-11-06`。不要在有未提交修改的日常工作目录里执行覆盖性恢复操作。

以后完成新的提交和标签后，使用一个新的日期或版本文件名导出：

```powershell
git bundle create .\.local-backups\ChanScanner-history-NEW-VERSION.bundle --all
git bundle verify .\.local-backups\ChanScanner-history-NEW-VERSION.bundle
```

本次备份仅在本机磁盘上；若需要应对磁盘损坏，可自行把完整 ZIP、manifest、SHA256SUMS 和 Git bundle 复制到其他介质。

## 回退剃刀改动

推荐在**新分支**上操作，不要重置 `main` 或改写已推送历史：

```powershell
git switch -c codex/restore-before-razor 24f9cee
# 或从当前分支按相反顺序撤销两个实现提交（保留其后的文档/工具提交）
git revert 5bb291a 2c2aa75
```

更彻底地回到整理完成版：

```powershell
git switch --detach organized-2026-11-06
```

`docs/razor-source-changes.json` 与 `docs/RAZOR_ACCEPTANCE.md` 是剃刀后新增的记录，不会随 `revert` 自动消失；如需完整还原，请使用上面的标签、完整 ZIP 或 bundle。桌面原版从未被修改，不需要恢复。

## 打包构建

`ChanScanner.spec` 的入口是 `App/ashare_bsp_scanner_gui.py`，采用目录式打包，程序名为 `ChanScanner`，`console=False`。剃刀后：

- `hiddenimports` 精简为 3 项：`DataAPI.BaoStockAPI`、`DataAPI.TencentAPI`、`DataAPI.TDX_TXT_API`。其中 `TencentAPI` 通过 `custom:TencentAPI.CTencent` 动态导入，静态分析不可见，必须显式保留。
- `collect_all` 精简为 10 个包：`Common`、`Bi`、`Seg`、`ZS`、`KLine`、`Combiner`、`Math`、`Plot`、`DataAPI`、`BuySellPoint`；移除了 `Chan`、`ChanConfig`、`App`、`ChanModel` 四段。

2026-11-06 实际构建结果：

| 项目 | 值 |
| --- | --- |
| 构建完成时间 | 2026-11-06 14:12:41（`build.log` 末行 `INFO: Build complete!`） |
| 构建源码 | `1d4af35`（构建时 docs 改动尚未提交，不影响 EXE） |
| 构建环境 | Python 3.14.10；PyInstaller 6.22.3；pyinstaller-hooks-contrib 2026.8；PyQt6 6.11.0；matplotlib 3.11.1；numpy 2.5.1；pandas 3.0.5；baostock 0.9.3；requests 2.34.2 |
| 构建命令 | `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist\razor-candidate --workpath build\razor-candidate ChanScanner.spec` |
| 产物入口 | `dist\razor-candidate\ChanScanner\ChanScanner.exe` |
| EXE 大小 / SHA-256 | 14,123,471 字节 / `1E445E1495E97702E1304C2B9EA67E1283F3C29A785B316F44BEE281F53FAE2B` |
| 完整目录 | 1,133 个文件，179,650,198 字节 |
| 目录内容 | `_internal` 含 `python314.dll`、`python3.dll`、PyQt6 `platforms/qwindows.dll`、`matplotlib/mpl-data` |
| 构建缓存 | `build\razor-candidate\ChanScanner\`，警告清单 `warn-ChanScanner.txt` |
| 构建日志 | `.local-validation/razor/build.log`，SHA-256 `4d1938827a77a5790df21755e070581a29e0065a4e18878c5a7c9c534ab6f68c` |

构建命令即上表命令，在项目根目录执行。构建日志中有 PyInstaller 的常规警告（写入 `warn-ChanScanner.txt`，49,434 字节），没有构建失败的 `ERROR`。PYZ 抽查确认含 `DataAPI.BaoStockAPI`、`DataAPI.TencentAPI`、`DataAPI.TDX_TXT_API`、`ChanModel.Features`、`Plot.PlotDriver`，不含 `AkshareAPI`/`ccxt`/`csvAPI`/`AnimatePlotDriver`。

候选 EXE 已做离屏启动冒烟：`QT_QPA_PLATFORM=offscreen` 启动后 12 秒进程仍存活、无 traceback；stderr 仅有沙箱临时目录导致的 matplotlib 字体缓存权限警告（`Could not save font_manager cache [Errno 13] ...`），不是程序错误。证据在 `.local-validation/razor/artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt`。**真实可见窗口的启动、TXT 导入、导出、在线分析人工冒烟仍未执行**，结果记录到 `docs/RAZOR_ACCEPTANCE.md`；在此之前，桌面原版 `C:\Users\q8369\Desktop\chan.py-main\dist\ChanScanner\ChanScanner.exe` 继续作为日常版本。

未来重新构建时：

1. 确认 `.venv` 的 Python/PyInstaller 版本与 `requirements-build.txt` 一致。
2. 输出到新目录（如 `dist\razor-candidate-2`），不要覆盖桌面现用程序。
3. 保存源码提交号、构建命令、依赖清单、完整程序目录和 SHA-256。
4. 按 `docs/RAZOR_ACCEPTANCE.md` 的试用清单做产物冒烟后，才把结果视为新的发布版本。

## 当前文件规模

截至 2026-11-06（HEAD `1d4af35`；此后仅文档变更，并随本次文档提交入库）：

- `git ls-files` 跟踪 124 个文件（含本次新增的交接、验收记录与变更清单 3 个文档）；其中 `git ls-files "*.py"` 为 64 个 Python 文件。
- `Debug/` 只剩 4 个离线回归；`DataAPI/` 剩 5 个文件；`Image/` 保留 40 个上游静态图。
- batch2 提交 `5bb291a` 删除 38 个文件（37 个 `.py` + `Script/requirements.txt`），详见 [RAZOR_ACCEPTANCE.md](RAZOR_ACCEPTANCE.md)。
