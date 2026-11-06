# ChanScanner「剃刀计划」交接任务书

交接日期：2026-11-06。本文可直接作为新 Codex 项目的任务说明。新会话应先核实实际状态，再持续完成实现与验证，不要仅输出另一份计划。

## 一、用户的目标与已经确认的决定

这个项目来自 chan.py 框架，用户日常主要使用已打包的 Windows EXE。希望将开发项目收敛到实际使用的功能，减少无用界面、演示、数据接口和打包负担，同时始终保留一个能继续使用的稳定版本。

用户已确认的功能范围如下，不需要再次询问：

| 功能 | 决定 |
| --- | --- |
| 导入本地通达信 TXT | 保留，优先保护 |
| 日线、分钟线、秒级数据及跨月跨年日期推断 | 保留 |
| K 线、笔、线段、线段中枢、线段买卖点、MACD | 保留现有计算及显示行为 |
| 缩放、拖动、框选、恢复视图、十字光标、显示开关 | 保留 |
| 导出通达信线段公式 | 保留现有格式、编码和时间条件 |
| 联网分析单只股票 | 保留；腾讯分钟线和 baostock 日线都属于保留范围 |
| 扫描全市场买点 | 删除该功能及专属界面、线程、列表、缓存和回调 |
| 新笔、旧笔切换 | 删除界面切换，固定使用当前 GUI 默认参数 |
| 上游演示和与保留功能无关的代码 | 完成依赖核查后精简 |

用户并不要求保留一个通用 chan.py 开发框架，也没有要求重写算法、增加策略、交易功能或重新设计全部界面。本任务以维护负担减少、使用结果稳定为目标，不承诺预设的 EXE 缩小比例。

## 二、工作位置与现用版保护

请将新 Codex 项目的工作目录和写入权限设置为：

```text
C:\Users\q8369\Documents\ChatGPT\chan.py-main
```

这是此前整理、建立 Git 并推送到 GitHub 的开发副本，已包含 `.git`、独立虚拟环境、本机样本和完整备份。用户所说的“GitHub 副本文件夹”就是这个位置，仍应通过 `git remote -v` 核实。

现用项目及程序：

```text
C:\Users\q8369\Desktop\chan.py-main
C:\Users\q8369\Desktop\chan.py-main\dist\ChanScanner\ChanScanner.exe
```

用户现在就要继续使用桌面原版。不要修改、清理、移动或覆盖这个目录及配套文件，不要关闭、操作或接管用户正在使用的窗口。

新候选 EXE 输出到开发副本内独立的、被 Git 忽略的目录，例如：

```text
dist\razor-candidate\ChanScanner\ChanScanner.exe
build\razor-candidate\
.local-validation\razor\
```

原程序采用目录式打包，完整程序包含 EXE 和 `_internal` 等配套文件。新候选版也应按完整目录交付。用户实际试用并决定切换前，日常继续使用桌面原版。

此前一次桌面自动化曾被用户按 Esc 停止。本任务不要恢复那次操作；自动验证优先使用开发环境和离屏检查。若需要真实窗口验证，只针对明确启动的候选程序，并遵守新会话中的授权与工具规则。

## 三、真实进度：剃刀计划还没有开始改代码

交接时仅完成了功能范围确认和源码阅读，**没有实施剃刀删改，没有创建剃刀分支，也没有重新打包**。不能把之前的“项目整理”验收结果当作剃刀版的验收结果。

交接前核实的 Git 状态：

```text
当前分支：main
main 与 codex/organize-project 的提交：24f9cee4c978e8739a400030dd322a4589b56611
origin：git@github.com:zhaoqinmuchu/-auto.git
基线标签：baseline-2026-11-06
整理标签：organized-2026-11-06
```

最近三个提交：

```text
24f9cee fix: preserve source bytes in baseline recovery instructions
a40cf66 chore: document ChanScanner and add offline verification tools
33ea607 chore: archive existing ChanScanner source baseline
```

上述两个分支和两个标签此前已经成功推送到 GitHub，后续将 origin 从 HTTPS 切换成了 SSH。用户已在自己的 PowerShell 中通过 SSH 认证，GitHub 返回账号 `zhaoqinmuchu`。项目配置使用 `C:/Windows/System32/OpenSSH/ssh.exe`。密钥可能需要用户自己的口令，不能因此修改或绕过其密钥保护。

本交接文件是后续新增的本地文档，交接时未提交、未推送。因此新会话看到它是未跟踪文件属正常情况；仍需检查有无其他用户改动。不要将用户的变更覆盖或回滚。

`docs/MAINTENANCE.md` 中“没有远程仓库、没有上传”的说法属于较早阶段，现已过时，后续应修订。其他文档中“原源码全部未改动”也是整理阶段记录，保留其历史含义，并另写剃刀阶段记录。

## 四、已查明的入口与耦合点

GUI 入口和打包配置：

```text
App/ashare_bsp_scanner_gui.py
ChanScanner.spec
```

当前 GUI 主窗口类名仍是 `AkshareGUI`。名字有历史原因，不意味着它当前依赖 Akshare；不要仅按名称删除或重命名。

### 当前默认的笔规则

源码中 `bi_strict_cb` 默认 `setChecked(False)`，`get_chan_config()` 从该复选框写入 `bi_strict`，并固定 `bi_fx_check="half"`。源码注释将关闭严格模式称为“新笔”，开启称为“旧笔”。

因此剃刀版需要固定的是 **GUI 当前的 `bi_strict=False` 及其余全部默认参数**。不要直接依赖 `CChanConfig()` 的默认值：框架层的默认严格模式与 GUI 不同。也不要因术语理解不同而换一套算法。

默认 GUI 还设定 `cal_bi_zs=False`、`cal_bi_bsp=False`，但保留线段级中枢和买卖点。这些行为必须保持。

第一步可以移除切换入口并固定参数。核心算法内部的旧模式分支是否继续删除，要结合调用关系、回归工具和实际收益决定；不能为删净一个选项而改坏默认计算路径。若暂时保留核心兼容分支，明确记录原因，不能声称已从内核彻底删除旧笔。

### 全市场扫描与单股分析需要分开处理

全市场扫描相关入口包括：

```text
get_tradable_stocks()
ScanThread
start_scan / stop_scan
on_scan_progress / on_buy_point_found / on_scan_finished / on_stock_clicked
扫描按钮、停止按钮、进度条、买点股票表格、扫描缓存等
```

单股分析和 TXT 导入共用 `SingleAnalysisThread`。保留它以及 `analyze_single`、`analyze_stock`、TXT 导入和结果绘图路径。扫描日志区域中若有本地导入或单股分析还在使用的日志方法，需要保留或调整为普通分析日志。

不要随扫描功能一起误删 `DataAPI/BaoStockAPI.py`、`DataAPI/TencentAPI.py`。`PERIOD_OPTIONS` 中的 1、5、15、30、60 分钟及日线仍属于单股分析功能。

### 深层模块不能凭名称裁剪

需要从 GUI、打包配置、运行时导入共同核查依赖。特别注意：

- `Chan.py` 支持动态加载数据源，只搜索文件顶部 import 不够。
- `ChanScanner.spec` 当前大量使用 `collect_all` 收集整个包，可能把无用内容带入新包；精简时同时检查动态导入和 hiddenimports。
- `ChanModel/Features.py` 被买卖点对象使用，不能因为名字像机器学习模块就直接删除。
- `Math` 中部分未显示指标仍被配置、K 线单元或绘图模块导入，BOLL 还会在默认模型中构造。删除前先查调用，避免为了减文件数扩大计算变更。
- 非默认线段算法、动画绘图、其他数据接口和上游演示均可列为候选，但需要给出实际可达性与验证证据。
- `Debug` 中部分脚本依赖个人路径或会联网，不要直接批量运行所有 `test_*.py`。
- 不要为目录清爽大规模搬动核心模块。优先删除独立、已证明无用的内容，再处理深层耦合。

## 五、现有资料、环境和完整备份

优先阅读以下文件，按需读业务源码，不必重复开展整个项目的初始调查：

```text
PROJECT_GUIDE.md
docs/MAINTENANCE.md
docs/VERIFICATION.md
docs/DEBUG_INDEX.md
docs/dependency-evidence.json
docs/source-baseline-sha256.json
requirements-gui.txt
requirements-build.txt
tools/verify_project.py
tools/analysis_fingerprint.py
tools/gui_smoke.py
```

开发副本的 `.venv` 使用 Python 3.14.10，GUI 依赖此前已安装且 `pip check` 通过。现用 EXE 内嵌 Python 3.13；源码与现用 EXE 完全对应的关系尚未证实。不要凭时间戳认定一致。`requirements-build.txt` 的 PyInstaller 版本仅是旧环境候选，未安装验证，也没有成功重建记录。

在项目内的独立环境安装、验证必要依赖，不改系统 Python，不直接覆盖用户环境。选择构建 Python 版本时记录实际组合与结果；如果采用 3.14 构建，需要按新候选版验证，不能称为复现旧 3.13 构建。

完整快照与可读取的参考源码：

```text
.local-backups/2026-11-06-baseline/chan.py-main-full.zip
.local-backups/2026-11-06-baseline/manifest.json
.local-backups/2026-11-06-baseline/snapshot-verification.json
.local-backups/2026-11-06-baseline/restore-check/chan.py-main
```

完整 ZIP 的 SHA-256：

```text
9bc6e8e41a143fb5395cd0a45453c9ef912071bf48ed0ef3398ceca6995c794a
```

历史包：

```text
.local-backups/ChanScanner-history-2026-11-06.bundle
```

SHA-256：

```text
a38c589fbd6f5996e32514bdcd527d97524db17fbe53d5efa75a8436f50390d8
```

行情样本 `A111.txt`、`CUL9.txt`、`SCL9.txt` 位于开发根目录，不进入 Git。备份、虚拟环境、build、dist、验证输出同样已被忽略。保留手写公式 `TDX/chan_bi_simple.txt`，不要把所有 TXT 一概忽略或删除。

## 六、从新会话开始执行的步骤

1. 确认 cwd、实际权限、本地 AGENTS.md、Git 状态、入口文件及备份。若路径或状态与交接不同，先保留现场，再按实际情况推进。
2. 创建独立分支，建议 `codex/razor-project`。不要重置已有同名分支，不要改写 main、旧标签或已推送历史。
3. 修改前先取得当前源码的默认模式计算和 GUI 对照结果，输出到 `.local-validation/razor/` 的独立文件，保留先前整理记录。
4. 建立精简清单，将内容分为保留、已证明可删除、仍有耦合暂留；说明理由。不要在保留范围外无限研究，能确定的修改直接实施。
5. 第一批实现：删除全市场扫描路径；移除旧笔切换并固定当前默认参数；修正界面名称、说明、日志和文档中的扫描提示；保留单股分析和本地流程。
6. 按依赖证据删除无关演示、无用接口与资源，调整打包配置和依赖说明。许可证和必要上游署名必须保留，仍有价值的回归检查不得当作“用户不用的功能”删除。
7. 分批验证并提交，保持每批问题可定位。遇到失败应修复或撤回该批自己的变更，不把关键失败改成跳过以交付“通过”。
8. 在独立路径构建完整候选 EXE，验证候选产物；保留构建日志、版本与校验值。若确实因环境受阻，交付已完成工作并具体记录阻碍，不声称 EXE 已可用。
9. 更新使用说明和剃刀验收记录，交付源码分支、候选程序位置、实际删减内容、验证结果和恢复方法。默认不合入 main、不替换桌面稳定版；GitHub 推送范围以新会话明确指令为准，不把此前一次推送理解为无限授权。

本任务书明确的范围已经确认，常规、可回退的开发、依赖检查、必要验证和候选打包应直接推进，无需逐项征求用户许可。用户未确认的额外删减不要自作主张扩大。

## 七、验证要求与工具注意事项

### 现有命令入口

以下命令在开发根目录的 PowerShell 中执行，先阅读脚本参数及硬编码行为：

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py
.\.venv\Scripts\python.exe -B .\tools\gui_smoke.py --source . --samples . --output .\.local-validation\razor\gui-before.json
```

`tools/analysis_fingerprint.py` 目前遍历三个本机样本与两种严格模式，`--source` 目录也用于查找样本。若要独立参考目录，使用已核验的完整恢复目录，或有意识地为工具增加单独的样本参数。

`tools/verify_project.py` 目前强制检查原始 96 个 Python 文件逐字节不变；这适用于之前的原样整理，不适合直接作为允许删改的剃刀总验收。要保留原始哈希证据，单独记录有意修改和删除的清单，继续验证应保持不变的核心，并增加行为对照。不得覆盖原始哈希清单、静默忽略缺失文件或仅删除失败断言。

### 必须覆盖的行为

- 四项离线日期回归：`test_cross_year_infer.py`、`test_cross_year_e2e.py`、`test_user_2026_01.py`、`test_with_year_filter.py`。
- 三个真实样本在 GUI 默认参数下，修改前后原始/合并 K 线内容与顺序、首尾时间、笔、线段、线段级中枢和买卖点的详细结果一致，不仅比较数量。
- 参考数量仅用于排查：默认非严格模式下 A111 为 20,300 根原始 K 线 / 1,426 笔 / 199 段；CUL9 为 10,500 / 534 / 73；SCL9 为 23,100 / 1,405 / 177。参考年月及完整参数以原工具为准。
- TXT 文件选择取消、年月取消、空年月取当前年月、日线、分钟/秒级数据及跨年读取。
- 六个显示开关、缩放、拖动、框选、恢复视图、十字光标；按工具能力区分自动覆盖与人工检查。
- 三类公式导出至少覆盖真实期货、日线、跨年秒级；比较内容与 GBK 编码，秒级保留 TIME2 条件。
- 全市场扫描入口和后台路径已移除；GUI 中旧笔切换已移除；保留计算参数与剃刀前 GUI 默认值一致。
- 单股分析的六种周期仍有正确数据源，成功和失败路径有反馈。允许为一次单股请求联网做有界检查，不运行全市场扫描；接口不可达时明确区分服务/网络失败与源码错误，并记录未验证范围。
- 候选 EXE 能从完整独立目录启动，保留动态数据接口、Qt 插件及绘图资源。源码通过、Qt 离屏通过、打包完成、打包产物运行通过是不同检查，分别记录。

之前已有六组计算对照和 17 项 Qt 离屏检查通过，但它们属于旧整理版。其中离屏检查不等于鼠标操作原生桌面，且未覆盖上述全部交互和真实联网服务。剃刀修改后需重新执行相关检查。

优先比较数据和导出结果。删除左侧扫描面板会改变图形区域尺寸，不能单凭整张窗口截图哈希改变就判定算法回归；需要统一图表条件再评估绘图差异。

## 八、最终交付标准

- 一个有提交记录、可回退的剃刀分支，以及可读的删减清单。
- 更新后的中文使用与构建说明，明确保留功能、删除功能和默认笔参数。
- 实际执行的验证报告，逐项说明通过、失败和未验证；与旧整理验收分开。
- 如构建成功，交付独立完整候选程序目录、源码提交号、实际 Python/依赖版本、构建命令和 SHA-256。若未通过候选程序验证，明确称为候选，不宣传为可替代稳定版。
- 桌面现用版本始终保持可供用户继续使用；本地备份、个人数据和密钥不进入 Git。

请从检查本地状态、建立开发分支和取得修改前对照开始，然后实施本任务。不要再次要求用户重述已经确认的范围。
