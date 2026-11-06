# 开发、依赖、备份与恢复

## 独立开发环境

以下命令在开发目录的 PowerShell 中执行。现有 `.venv` 使用 Python **3.14.10**，只在本项目安装 GUI 依赖，没有修改系统包。

```powershell
.\.venv\Scripts\python.exe -B .\App\ashare_bsp_scanner_gui.py
```

在新机器上，使用完整的 Python 3.14 重新创建环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements-gui.txt` 固定了本次独立环境实际安装并检查过的 GUI 依赖及传递依赖，包含旧清单遗漏的 PyQt6。候选版本来自本机旧 Microsoft Store Python 3.13 包目录的元数据；这并不证明它们全部就是 2026-08-27 打包时使用的版本。

原 EXE 包含 `python313.dll`，旧构建记录也指向 Python 3.13。本机可运行的独立 Python 3.13.16 是精简运行时，缺少 `venv`；旧 Store 启动别名无法从当前执行环境启动。因此这次选择完整 Python 3.14.10 建立虚拟环境。原目录和快照中的旧程序仍使用自身附带的运行时。

本次源码对照和 Qt 自动检查采用相同的 Python 3.14 环境运行参考源码与开发源码；它们不能替代对旧 EXE 的运行验证。依赖证据见 `dependency-evidence.json`。

`Script/requirements.txt` 保留上游版本，适用于框架例子，不能单独作为 GUI 完整依赖清单。`main.py` 是上游例子，会联网且可能保存图片，并非桌面 GUI 入口。机器学习例子还可能需要额外包，未安装到本次 GUI 环境。

## 离线检查

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py
```

默认只检查原有 96 个 Python 文件的基线校验值、Python 语法，以及四个明确选定的离线日期回归，不会批量执行全部 Debug 脚本。

完整样本对照（需要本机完整备份和三个行情 TXT）：

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py --reference .\.local-backups\2026-11-06-baseline\restore-check\chan.py-main
```

Qt 自动检查使用离屏平台，文件和年月对话框由检查程序替代，不操作桌面现用窗口：

```powershell
.\.venv\Scripts\python.exe -B .\tools\gui_smoke.py --source . --samples . --output .\.local-validation\gui-development.json
```

## Git 日常使用

```powershell
git status
git log --oneline --decorate -5
git switch -c codex/describe-your-change
# 完成修改和相关检查后，明确选择要保存的文件：
git add PROJECT_GUIDE.md
git commit -m "docs: update local usage guide"
```

保存源码、文档、打包配置和手写公式；不保存现用 EXE、依赖库、构建缓存、行情数据和本机备份。Git 不会自动给未提交的修改建立版本。继续修改业务源码时，先记录对应版本和新的行为预期，再有意识地更新基线检查；不要为让检查通过而直接改校验清单。

当前没有配置远程仓库，也没有上传到 GitHub。`main` 保存验收后的整理结果，`codex/organize-project` 保留本次工作分支。

## 本次完整快照

快照保存在开发目录的 `.local-backups/2026-11-06-baseline`：

- `chan.py-main-full.zip`：桌面原项目的完整快照，含 EXE、`_internal`、源码、样本、构建记录与原始忽略文件。
- `manifest.json`：逐文件相对路径、大小、SHA-256 和原始修改时间记录。
- `SHA256SUMS.txt`：压缩包 SHA-256。
- `snapshot-verification.json`：ZIP 完整性、实际解压文件和原目录逐文件校验结果。
- `restore-check/chan.py-main`：已解压并核验的程序目录，可用于独立检查。

恢复程序时解压到**新目录**，不要覆盖正在使用的版本：

```powershell
python -m zipfile -t .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip
python -m zipfile -e .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip .\.local-backups\manual-restore-new
```

恢复后的程序入口在新目录内的 `chan.py-main/dist/ChanScanner/ChanScanner.exe`，必须保留同目录全部配套文件。`zipfile -t` 是 ZIP 完整性检查；如需验证实际文件内容，按 manifest 中的 SHA-256 比较。

## Git bundle 与恢复源码

本次离线历史包为 `.local-backups/ChanScanner-history-2026-11-06.bundle`，对应校验文件为同名追加 `.sha256`。它包含创建时的全部本地分支和两个版本标签，不包含行情数据、虚拟环境和完整程序。

```powershell
git bundle verify .\.local-backups\ChanScanner-history-2026-11-06.bundle
git clone --config core.autocrlf=false .\.local-backups\ChanScanner-history-2026-11-06.bundle .\.local-backups\manual-source-restore-new
```

恢复命令显式设置 `core.autocrlf=false`，避免本机全局 Git 配置将原始 LF 换行转换为 CRLF，影响逐字节校验。若仓库已经用其他命令恢复，先在该新仓库内执行 `git config --local core.autocrlf false`。

要查看初始源码，可在**新恢复的仓库**内使用 `git switch --detach baseline-2026-11-06`。要恢复整理版，则使用 `organized-2026-11-06`。不要在有未提交修改的日常工作目录里执行覆盖性恢复操作。

以后完成新的提交和标签后，使用一个新的日期或版本文件名导出：

```powershell
git bundle create .\.local-backups\ChanScanner-history-NEW-VERSION.bundle --all
git bundle verify .\.local-backups\ChanScanner-history-NEW-VERSION.bundle
```

本次备份在本机磁盘上；若需要应对磁盘损坏，可自行把完整 ZIP、manifest、SHA256SUMS 和 Git bundle 另复制到其他介质。

## 打包说明

原 `ChanScanner.spec` 的入口是 `App/ashare_bsp_scanner_gui.py`，采用目录式打包，程序名为 ChanScanner。`requirements-build.txt` 记录旧环境发现的 PyInstaller 候选版本，**本次没有安装验证这些构建依赖，也没有重打包**。

未来需要构建时，在独立构建环境验证相应 Python、PyInstaller 和依赖组合，输出到开发副本的新目录。不要直接覆盖桌面现用程序。保存源码提交号、构建命令、依赖清单、完整程序目录和校验值后，才把结果视为新的发布版本。
