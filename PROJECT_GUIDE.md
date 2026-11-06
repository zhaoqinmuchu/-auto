# ChanScanner 中文项目指南

这是在 chan.py 缠论计算框架上定制的 Windows 图形分析程序。当前开发分支已按「剃刀计划」收敛到实际使用的功能：导入通达信 TXT、单只股票六周期在线分析、缠论元素显示与交互、导出通达信线段公式；全市场扫描和界面上的新旧笔切换已经移除。

## 当前版本与工作副本

| 位置 | 用途 |
| --- | --- |
| `C:\Users\q8369\Desktop\chan.py-main` | 日常继续使用的原版；本次剃刀计划没有修改、移动或替换它 |
| `C:\Users\q8369\Documents\ChatGPT\chan.py-main` | 剃刀开发副本；分支 `codex/razor-project`，装有独立 `.venv` |
| 开发副本的 `dist\razor-candidate\ChanScanner` | 2026-11-06 新构建的候选程序；离屏启动冒烟已通过，**真实可见窗口人工试用尚未完成**，暂不替代桌面原版 |
| 开发副本的 `.local-backups` | 完整快照、解压校验副本、Git bundle；不进入 Git |
| 开发副本的 `.local-validation` | 自动检查结果、测试图和临时导出；不进入 Git |

日常仍可双击桌面原项目内的 `dist\ChanScanner\ChanScanner.exe`。不要只移动这个 EXE：旁边的 `_internal` 也是程序的一部分。桌面原版和候选版可以并存，二者互不覆盖。

当前分支的关键提交（完整哈希见 [剃刀验收记录](docs/RAZOR_ACCEPTANCE.md)）：

| 提交 | 内容 |
| --- | --- |
| `24f9cee` | 整理阶段基线，标签 `baseline-2026-11-06`；整理完成标签为 `organized-2026-11-06` |
| `2c2aa75` | 删除全市场扫描，固定 GUI 使用新笔（`bi_strict=False`） |
| `66bb2d3` | 增加依赖证据与剃刀验收工具 |
| `5bb291a` | 删除上游演示、无用数据源、32 个 Debug 脚本并精简打包配置 |
| `1d4af35` | 同步依赖证据到 batch2 的工作区状态 |
| 本文档提交 | 剃刀说明、验收记录、变更清单入库（提交哈希见 `git log -1`） |

本分支没有合并回 `main`，也没有推送；是否合并/推送由用户另行决定。

## 候选 EXE 的运行方式

候选程序是目录式打包，必须保留完整目录：

```text
dist\razor-candidate\ChanScanner\
├── ChanScanner.exe
└── _internal\
```

运行 `dist\razor-candidate\ChanScanner\ChanScanner.exe` 即可启动，不能只复制 EXE 而丢掉 `_internal`。构建完成时间、文件数和 SHA-256 见 [剃刀验收记录](docs/RAZOR_ACCEPTANCE.md) 的「候选 EXE 与构建」一节。候选 EXE 已通过离屏启动冒烟（`QT_QPA_PLATFORM=offscreen`，12 秒后进程存活、无 traceback），但**真实可见窗口的启动、TXT 导入、导出和在线分析人工冒烟尚未完成**，因此当前只能称为候选版。

## 实际包含的功能

- 导入本地通达信 TXT：日线、分钟线和无年份的秒级 K 线，支持跨月、跨年日期推断。
- 联网分析单只 A 股：1/5/15/30/60 分钟用腾讯财经接口，日线用 baostock。
- 计算并显示 K 线、合并 K 线、笔、线段、线段中枢、线段买卖点、MACD。
- 笔划分固定使用新笔（`bi_strict=False`），界面不再提供新旧笔切换；框架层的 `bi_strict` 参数仍然存在，只是 GUI 不暴露它。
- 图表交互：滚轮缩放、左键拖动、右键框选、双击恢复视图、十字光标，以及 K 线/笔/线段/线段中枢/买卖点/MACD 六个显示开关。
- 将当前线段导出为 GBK 编码的通达信公式文本，默认扩展名 `.tni`；按程序提示复制到公式编辑器使用。这不是已验证的二进制公式安装包。
- 已移除：全市场扫描及专属按钮、线程、进度、股票列表、缓存、回调；界面上的旧笔严格模式开关；上游演示入口、32 个非离线回归 Debug 脚本，以及 CSV/ccxt/AKShare 三个无用数据源。

上述功能的源码级检查、Qt 离屏检查和候选 EXE 离屏启动冒烟已通过；**没有做真实可见窗口的桌面鼠标人工验证**。联网只在源码环境做了腾讯 1 分钟、baostock 日线各 1 次有界实测，候选 EXE 内未验证；详见 [docs/VERIFICATION.md](docs/VERIFICATION.md) 的剃刀小节。

### 固定分析参数

GUI 在 `App/ashare_bsp_scanner_gui.py` 的 `get_chan_config()` 中固定以下参数，界面不提供修改入口：

| 参数 | 固定值 | 说明 |
| --- | --- | --- |
| `bi_strict` | `False` | 新笔（非严格模式），剃刀计划的核心固定项 |
| `bi_fx_check` | `"half"` | 分型有效性校验方式 |
| `cal_bi_zs` | `False` | 不计算笔级别中枢 |
| `cal_bi_bsp` | `False` | 不计算笔级别买卖点 |

其余 `get_chan_config()` 键保持剃刀前的 GUI 默认值（`trigger_step=False`、`skip_step=0`、`divergence_rate=inf`、`bsp2_follow_1=False`、`bsp3_follow_1=False`、`min_zs_cnt=0`、`bs1_peak=False`、`macd_algo="peak"`、`bs_type="1,1p,2,2s,3a,3b"`、`print_warning=False`、`zs_algo="normal"`）。完整表格见 [剃刀验收记录](docs/RAZOR_ACCEPTANCE.md)。

注意：框架 `ChanConfig` 仍接受 `bi_strict`，核心 `KLine_List.py` 中的旧笔严格分支也没有删除。剃刀计划只固定了 GUI 默认路径，不能表述为「内核旧笔已彻底删除」。

## 常用流程：导入通达信文件看图

1. 在通达信导出 TXT，保留原编码和表头；不要用电子表格另存造成时间、价格或分隔符变化。
2. 打开 ChanScanner，点击“导入本地TXT数据”，选择文件。
3. “数据所属年月”填写**最后一根 K 线所属的年月**，如 `2026-01`。无年份秒级数据靠这个基准向前推断跨月、跨年日期。留空会使用运行当天的年月；导入历史文件时建议明确填写。
4. 等待分析完成。图形初始显示最近约 500 根 K 线，可缩放查看更早数据；显示范围不是只读取了 500 根。
5. 按需要切换 K 线、笔、线段、中枢、买卖点、MACD 显示开关。分析参数已固定，改显示开关不需要重新导入。
6. 需要带回通达信时，点击“导出通达信线段公式”，保存到自选的新文件。

取消文件选择或年月输入，应保留原状态。秒级 K 线导出使用精确到秒的时间条件；日线和分钟线也有各自的时间定位规则。

## 单只股票六周期在线分析

在代码输入框输入股票代码后点击单股分析，不运行全市场扫描。周期和数据源对应关系：

| 周期 | 数据源 |
| --- | --- |
| 1 / 5 / 15 / 30 / 60 分钟 | 腾讯财经接口（分钟数据最多约最近 320 根） |
| 日线 | baostock |

在线接口依赖网络和行情服务可用性；接口不可达时程序会给出失败反馈。本次在源码环境做了有界实测：腾讯 1 分钟 `sz.000001` 返回 71 根 K 线，baostock 日线（`sz.000001`，2026-09-01~2026-11-06，前复权）返回 28 根，详见 [剃刀验收记录](docs/RAZOR_ACCEPTANCE.md)。候选 EXE 内的联网行为未实测，5/15/30/60 分钟也未逐一发真实请求。

## 图表交互与公式导出

- 滚轮缩放；左键拖动平移；右键拖动框选放大；双击恢复初始视图；移动鼠标显示十字光标。
- 六个显示开关分别控制 K 线、笔、线段、线段中枢、线段买卖点、MACD；关闭再开启应恢复原有绘图。
- “导出通达信线段公式”写入 GBK 文本，内容包含 `DRAWLINE` 与时间定位条件；秒级数据保留 `TIME2` 条件。导出对照的三份文件与剃刀前逐字节一致（见验收记录）。

## 目录怎么看

| 名称 | 职责 | 本次处理 |
| --- | --- | --- |
| `App/ashare_bsp_scanner_gui.py` | PyQt6 界面、TXT 导入、单股分析线程、图表交互与导出 | 已删除扫描功能和旧笔切换；其余保留 |
| `Chan.py`、`ChanConfig.py` | 核心计算入口和配置 | 删除 CCXT/CSV/AKSHARE 三个无用数据源分支，其余保留 |
| `Bi`、`Seg`、`ZS`、`BuySellPoint` | 笔、线段、中枢和买卖点 | 保留；`Seg/SegListDYH.py`、`SegListDef.py` 作为框架兼容保留 |
| `KLine`、`Combiner`、`Common`、`Math` | K 线、合并、公共结构和指标 | 保留；`KLine_List.py` 旧笔严格分支保留 |
| `DataAPI` | 通达信 TXT、腾讯分钟线、baostock 日线 | 删除 CSV、ccxt、AKShare；保留 5 个文件 |
| `Plot` | 绘图 | 删除上游 IPython 动画演示 `AnimatePlotDriver.py`，其余保留 |
| `Debug` | 4 个离线日期回归 | 其余 32 个已在 batch2 删除，可从 Git 历史恢复 |
| `TDX` | 手写通达信公式源文件 | 保留 |
| `Image`、上游文档、`LICENSE` | 上游 README 图片、框架文档和许可证 | 保留；`Image` 不参与运行和打包 |
| `A111.txt`、`CUL9.txt`、`SCL9.txt` | 本机行情样本 | 原相对位置保留，不进入 Git |
| `tools`、`docs` | 检查/验收入口与维护记录 | 纳入 Git；`.local-validation` 下的运行结果不进入 Git |

## 验收与维护入口

- [剃刀验收记录（2026-11-06）](docs/RAZOR_ACCEPTANCE.md)：范围、删除清单、验证结果、候选 EXE、恢复方式、已知限制。
- [2026-11-06 整理检查记录](docs/VERIFICATION.md)：前半部分是整理阶段历史；末尾是剃刀版验收结果。
- [开发、依赖、构建、备份与恢复](docs/MAINTENANCE.md)。
- [调试脚本分类索引](docs/DEBUG_INDEX.md)：当前只有 4 个离线回归。

剃刀版总验收命令（在开发根目录执行）：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py
```

最终记录的验收使用 `--gui`（同时重跑 39 项 Qt 离屏检查）：

```powershell
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py --gui
```

`docs/source-baseline-sha256.json` 保持整理阶段的 96 文件原始哈希，故意不重签；剃刀改动由 `docs/razor-source-changes.json` 清单和 `tools/razor_acceptance.py` 解释。因此 `tools/verify_project.py` 的默认严格模式会按设计失败；需要时用 `--razor-changes docs\razor-source-changes.json`，不要为了让它通过而改基线清单。
