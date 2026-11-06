# 2026-11-06 整理检查记录

## 已通过的检查

| 检查 | 结果 |
| --- | --- |
| 完整快照 | 7,061 个文件、1,154 个目录，原文件总计 381,745,075 字节；ZIP 为 208,007,325 字节 |
| 压缩包完整性 | ZIP CRC 检查通过；实际解压后的每个文件 SHA-256 与源文件一致 |
| 桌面原目录 | 整理期间再次校验全部 7,061 个文件及文件清单，内容没有变化 |
| 原业务及调试源码 | 原有 96 个 Python 文件逐字节符合基线；原打包配置、许可证、快速指南无改动 |
| 语法 | 原有源码及新增检查工具通过 Python 语法检查 |
| 四项日期回归 | 跨年倒推、跨年完整读取、有年份历史数据两种参考年月：全部通过 |
| 真实样本一致性 | A111、CUL9、SCL9 各运行新笔和旧笔配置，共六组，参考源码与开发源码结果一致 |
| Qt 自动检查 | 参考源码与开发源码各通过 17 项离屏检查，结果一致 |
| 导出对照 | 期货样本、构造日线、跨年秒线的三份公式输出逐字节一致 |
| 绘图对照 | 两份离屏检查最终生成的图像 SHA-256 完全一致；已查看参考图确认有 K 线与分析线条 |
| 独立依赖 | GUI 依赖安装在项目 `.venv` 内；`pip check` 无冲突 |
| Git 产物排除 | 本地备份、虚拟环境、自动检查结果和三个个人行情 TXT 均被忽略；手写通达信公式已跟踪 |
| 恢复换行策略 | 恢复命令固定 core.autocrlf=false，防止本机全局设置改变旧基线的换行字节 |

原始 96 个 Python 文件的校验值保存在 `source-baseline-sha256.json`。完整快照的 SHA-256 为：

```text
9bc6e8e41a143fb5395cd0a45453c9ef912071bf48ed0ef3398ceca6995c794a
```

## 六组真实行情计算对照

| 样本 | 笔严格模式 | 原始 K 线 | 笔 | 线段 |
| --- | --- | ---: | ---: | ---: |
| A111 | 关闭 | 20,300 | 1,426 | 199 |
| A111 | 开启 | 20,300 | 1,160 | 161 |
| CUL9 | 关闭 | 10,500 | 534 | 73 |
| CUL9 | 开启 | 10,500 | 392 | 56 |
| SCL9 | 关闭 | 23,100 | 1,405 | 177 |
| SCL9 | 开启 | 23,100 | 1,029 | 134 |

除了数量，还对照了原始及合并 K 线的内容和顺序、首尾时间、笔和线段的端点/价格/方向/确定标志、两类中枢及两类买卖点。所有内容指纹一致。GUI 默认配置关闭笔级中枢和笔级买卖点计算，本次保留此行为，同时比较线段级结果。

## 17 项 Qt 离屏检查

- 取消文件选择、取消年月输入、留空年月取当前年月。
- 真实期货数据、构造日线、跨年秒级数据：各自完整导入并绘图。
- 三种数据分别导出线段公式，包含 73、6、6 条 DRAWLINE；秒级公式包含 TIME2 条件。
- K 线、笔、线段、中枢、买卖点、MACD 六个显示开关分别切换并恢复。
- 滚轮缩放后横轴范围改变，左键拖动后横轴范围改变。

这些检查在 Qt 离屏平台上通过程序接口和模拟 Matplotlib 事件执行，文件及年月对话框由检查工具替代，**不是实际桌面鼠标操作检查**。

## 未完成与未执行

- 备份 EXE 的实际桌面界面验证未完成：第一次工具授权等待超时；重试后窗口返回的身份仍指向桌面原项目，随后用户用物理 Esc 停止 Computer Use。所有桌面操作随即停止，没有继续对现用窗口执行导入、缩放或导出。
- 源码与现用 EXE 的完全对应关系未证实。时间戳和旧依赖元数据只作为证据记录，不作为等价证明。
- 旧 EXE 自带 Python 3.13；本次源码和 Qt 自动验证使用独立 Python 3.14.10 环境，不代表已复现旧打包环境。
- 未重打包、未替换 EXE，未运行全市场扫描或联网行情验证。
- 未运行依赖桌面个人文件的全部历史诊断；其中 600570.txt 在检查时不存在。
- 未把公式导入证券软件验证其显示效果；本次只验证程序生成的文本及时间定位条件。

## 本地详细结果

以下文件仅在本机保存，不进入 Git：

- `.local-validation/verification.json`：语法、基线和日期回归结果。
- `.local-validation/reference-fingerprint.json`、`development-fingerprint.json`：六组真实样本各类元素的数量和内容指纹。
- `.local-validation/gui-reference.json`、`gui-development.json`：17 项 Qt 检查及三份公式摘要。
- `.local-validation/gui-reference.png`、`gui-development.png`：离屏生成的对照图。
- `.local-validation/final-integrity.json`：原目录、图形与公式一致性检查。
- `.local-backups/2026-11-06-baseline/snapshot-verification.json`：完整快照恢复校验。
- `.local-backups/bundle-verification.json`：最终提交和标签生成之后执行的 Git 历史包恢复检查；单独记录以免产生“提交包含自身哈希”的循环。

本记录描述实际完成的自动验证及其边界；最终版本号和历史包恢复结果以本机 Git 标签与上述交付记录为准。

# 剃刀版验收（2026-11-06）

上面的整理检查记录保留为历史证据：它验证的是「源码原样未改」的整理阶段。剃刀计划删除了文件、修改了 GUI 与核心数据源分支，因此**不能沿用整理阶段的「96 个 Python 文件逐字节不变」结论**。本节单独记录剃刀版的验收结果，完整说明见 [RAZOR_ACCEPTANCE.md](RAZOR_ACCEPTANCE.md)。

## 验证分层

源码通过、Qt 离屏通过、构建完成、打包产物运行通过是不同层次的检查，本节分别记录：

| 层次 | 检查内容 | 结果 | 证据 |
| --- | --- | --- | --- |
| 源码级 | 基线完整性 + 变更清单、Python 语法、4 个离线回归、3 样本 × 2 严格模式的分析指纹对照 | **PASS** | `.local-validation/razor/acceptance.json`（9/9 检查，含 `gui_checks`） |
| Qt 离屏 | 39 项 GUI 离屏检查（界面保留项、固定参数、周期映射、导入、导出、交互） | **PASS** | `.local-validation/razor/gui-after.json`（39/39，16.4 秒） |
| 构建 | PyInstaller 完整构建候选目录 | **PASS** | `.local-validation/razor/build.log`（sha256 `4d193882…6f68c`）、`dist/razor-candidate/ChanScanner/` |
| 产物启动 | 候选 EXE 离屏启动冒烟（`QT_QPA_PLATFORM=offscreen`，12 秒存活、无 traceback） | **PASS** | `.local-validation/razor/artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt` |
| 真实窗口 | 候选 EXE 可见窗口启动、TXT 导入、导出、在线分析人工冒烟 | **未验证 / 待用户试用** | 尚无真实窗口报告 |
| 联网单股 | 源码环境腾讯 1 分钟、baostock 日线有界实测 | **部分通过（仅源码环境）** | `.local-validation/razor/network_probe.py`、`network-probe.json` |

## 执行命令与结果

```powershell
# 源码级 + Qt 离屏总验收（当前 acceptance.json 由该命令生成，含 gui_checks）
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py --gui

# 只做源码级检查、不重跑 Qt 离屏检查
.\.venv\Scripts\python.exe -B .\tools\razor_acceptance.py
```

总验收（`acceptance.json`，生成于 2026-11-06 14:16:18–14:16:41，HEAD `1d4af35`，耗时 23.1 秒，`status=PASS`，9/9）：

| 检查 | 结果 |
| --- | --- |
| 基线 JSON 完整性 | PASS：`docs/source-baseline-sha256.json` 为 96 项，sha256 `4e500b6d…ba8866b0`，与 HEAD 中字节一致（未重签） |
| 基线与变更清单对照 | PASS：56 项未改、3 项按清单允许修改、37 个 `.py` 按清单允许删除、新增 2 个验收工具 |
| Python 语法 | PASS：64 个 `.py` 全部通过 `ast.parse` |
| 4 个离线日期回归 | PASS：4 个脚本全部 `returncode 0` |
| 三样本 × 两模式指纹 | PASS：6 组、114 个字段逐字段无差异；`analysis-before.json` 与 `analysis-after.json` 的 SHA-256 同为 `3d62ce00…1ce97` |
| Qt 离屏 GUI | PASS：39/39，16.4 秒（`gui-after.json`） |

三样本数量复核（非严格 / 严格，完整字段对比以指纹文件为准）：

| 样本 | 原始 K 线 | 笔（非严格/严格） | 线段（非严格/严格） |
| --- | ---: | ---: | ---: |
| A111 | 20,300 | 1,426 / 1,160 | 199 / 161 |
| CUL9 | 10,500 | 534 / 392 | 73 / 56 |
| SCL9 | 23,100 | 1,405 / 1,029 | 177 / 134 |

Qt 离屏检查（`gui-after.json`，2026-11-06 14:16:39 由最终 `--gui` 验收生成，39/39 PASS，约 16.4 秒，json sha256 `FA9761142464C70A49824DD3B32BD71C60A3EB4DB187BF7A8E8A2A4956499F30`）覆盖：扫描入口已移除（界面、属性、模块符号、回调、窗口文字）；保留控件；`get_chan_config()` 默认值与 `bi_strict` 恒为 `False`；`get_plot_config()`；六周期到腾讯/baostock 的映射；取消文件、取消年月、空年月取当前年月；期货/日线/跨年秒级三类本地 TXT 导入；三份 `.tni` 导出（GBK、`DRAWLINE`、秒级 `TIME2`，sha256 与 `gui-before.json` 一致）；滚轮缩放、拖动、右键框选、双击恢复、十字光标、六个显示开关。该检查使用 Qt offscreen，**不是实际桌面鼠标操作检查**。

构建（2026-11-06 14:12:41 完成）：构建源码 `1d4af35`；环境 Python 3.14.10、PyInstaller 6.22.3、pyinstaller-hooks-contrib 2026.8、PyQt6 6.11.0、matplotlib 3.11.1、numpy 2.5.1、pandas 3.0.5、baostock 0.9.3、requests 2.34.2；命令为 `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist\razor-candidate --workpath build\razor-candidate ChanScanner.spec`。产物 `dist/razor-candidate/ChanScanner/ChanScanner.exe`（14,123,471 字节，SHA-256 `1E445E14…F53FAE2B`），完整目录 1,133 个文件、179,650,198 字节；`_internal` 含 `python314.dll`、`python3.dll`、PyQt6 `platforms/qwindows.dll` 与 `matplotlib/mpl-data`。构建日志 `.local-validation/razor/build.log`（SHA-256 `4d193882…6f68c`），警告清单 `build/razor-candidate/ChanScanner/warn-ChanScanner.txt`。PYZ 抽查含 `DataAPI.BaoStockAPI`、`DataAPI.TencentAPI`、`DataAPI.TDX_TXT_API`、`ChanModel.Features`、`Plot.PlotDriver`，不含 `AkshareAPI`/`ccxt`/`csvAPI`/`AnimatePlotDriver`。这是 Python 3.14 的新构建，不是桌面旧 EXE（内嵌 Python 3.13）的复现。

候选 EXE 离屏启动冒烟（2026-11-06）：设置 `QT_QPA_PLATFORM=offscreen` 启动 `dist/razor-candidate/ChanScanner/ChanScanner.exe`，12 秒后进程仍存活、无 traceback；stderr 仅有沙箱临时目录导致的 matplotlib 字体缓存权限警告（`Could not save font_manager cache [Errno 13] Permission denied: ...fontlist-v3.11.0.json.matplotlib-lock`），不是程序错误。证据：`artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt`。**该冒烟不覆盖真实可见窗口的点击、导入、导出和在线分析。**

## 联网单股有界实测（源码环境）

- 环境：开发 `.venv` + 剃刀后源码，GUI 默认计算参数（`bi_strict=False`、`bi_fx_check="half"`、`cal_bi_zs=False`、`cal_bi_bsp=False`），直接调用 `CChan`；不是候选 EXE 内验证，也不是真实窗口点击。
- 腾讯分钟线：`custom:TencentAPI.CTencent`，`sz.000001`，1 分钟，`begin=2026-11-05` → 成功，71 根 K 线，首根 2026/11/05 11:30，末根 2026/11/06 14:18，5 笔、1 段。
- baostock 日线：`DATA_SRC.BAO_STOCK`，`sz.000001`，2026-09-01~2026-11-06，前复权 → 成功，28 根日线，首根 2026/09/01，末根 2026/11/05，2 笔、0 段；login/logout success。
- 证据：`.local-validation/razor/network_probe.py`、`.local-validation/razor/network-probe.json`。
- 失败分类：探针按异常类型区分 network（socket/timeout/connection/http）与 source（其余）；本次两项均成功。
- 未覆盖：候选 EXE 内的联网行为；5/15/30/60 分钟的真实请求未逐一发出（周期映射由 39 项离屏检查覆盖）；全市场扫描未运行（功能已删除）。

工具自检：`acceptance-selftest.json`、`acceptance-missing-manifest.json`、`verify-selftest-razor.json` 用于确认验收工具能正确拒绝篡改/缺失清单，不作为剃刀源码通过证据。

## 为什么基线 JSON 不重签

`docs/source-baseline-sha256.json` 保持整理阶段生成的 96 个原始 `.py` 哈希，作为「原源码未被静默篡改」的历史证据；剃刀改动不通过改写它来「变绿」。剃刀版改用：

- `docs/razor-source-changes.json`：明确列出 3 个允许修改、37 个允许删除、2 个新增文件及理由；
- `tools/razor_acceptance.py`：按「原基线 + 变更清单」计算，清单外任何改动/缺失都失败，缺少清单也直接报错。

因此 `tools/verify_project.py` 的**默认严格模式会按设计失败**：它逐字节比对原 96 文件，遇到 `App/ashare_bsp_scanner_gui.py` 被剃刀修改会抛出 `RuntimeError: Original source changed: ...`。需要旧入口时加清单参数：

```powershell
.\.venv\Scripts\python.exe -B .\tools\verify_project.py --razor-changes docs\razor-source-changes.json
```

不要为了消除该错误而改基线 JSON、删断言或跳过缺失文件。

## 本次未验证的范围

- 未对候选 EXE 做真实可见窗口启动、鼠标操作、TXT 导入/导出人工冒烟；只做了离屏启动冒烟（12 秒存活、无 traceback），因此「真实窗口」一栏保持未验证。
- 联网仅在源码环境做了有界实测（腾讯 1 分钟、baostock 日线各 1 次）；候选 EXE 内未实测，5/15/30/60 分钟未逐一发真实请求，接口不可达时的失败反馈也未人工确认。
- 未把导出的 `.tni` 导入通达信等证券软件验证显示效果；只验证了文本内容、GBK 编码和时间条件。
- 未做桌面原版与候选版的并排对比；桌面原版本次未改动、未启动。
- `Image/` 40 个上游静态图、`Seg/SegListDYH.py`、`Seg/SegListDef.py` 以及内核 `KLine_List.py` 中的旧笔严格分支仍然保留；不能声称「内核旧笔已彻底删除」。
- 未合并回 `main`、未推送；候选目录不是正式发布版。

## 证据文件位置

以下文件仅在本机保存，不进入 Git：

- `.local-validation/razor/acceptance.json`（9/9 PASS，sha256 `23E4D9A9…82DE7F`）、`analysis-before.json`、`analysis-after.json`、`verify-before.json`
- `.local-validation/razor/gui-after.json`（39/39 PASS，sha256 `FA976114…499F30`）、`gui-after.png`、三份 `gui-after-*.tni`
- `.local-validation/razor/artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt`（候选 EXE 目录检查与离屏启动冒烟）
- `.local-validation/razor/network_probe.py`、`network-probe.json`（源码环境联网有界实测）
- `.local-validation/razor/build.log`（sha256 `4d193882…6f68c`）、`pip-install.log`、`acceptance-selftest.json`、`acceptance-missing-manifest.json`、`verify-selftest-razor.json`
- `dist/razor-candidate/ChanScanner/`、`build/razor-candidate/ChanScanner/warn-ChanScanner.txt`
- `.local-backups/2026-11-06-baseline/chan.py-main-full.zip`（SHA-256 `9bc6e8e4…5c794a`）
- `.local-backups/ChanScanner-history-2026-11-06.bundle`（SHA-256 `a38c589f…0390d8`）
