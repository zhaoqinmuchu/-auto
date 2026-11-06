# ChanScanner「剃刀计划」验收记录

- 记录日期：2026-11-06
- 分支：`codex/razor-project`；撰写本记录时 HEAD `1d4af3550467765f83d90987f314a8d854c52386`（`docs(razor): sync dependency evidence with batch2 workspace state`）
- 基线：`24f9cee4c978e8739a400030dd322a4589b56611`，标签 `baseline-2026-11-06`
- 环境：Python 3.14.10、PyInstaller 6.22.3、pyinstaller-hooks-contrib 2026.8
- 结论：源码级验收 PASS（9/9，含 Qt 离屏）；候选目录构建 PASS；候选 EXE 离屏启动冒烟 PASS；**真实可见窗口人工试用尚未执行**。
- 本文只记录剃刀阶段，不替代 [2026-11-06 整理检查记录](VERIFICATION.md) 的历史内容。

## 1. 范围与决策

剃刀计划的目标是收敛到用户实际使用的功能、减少无用界面与打包负担，同时保留一个可继续使用的稳定版本。范围决定见 [交接任务书](../RAZOR_HANDOFF.md) 与 [依赖审计证据](razor-dependency-evidence.md) §0、§4。

| 功能/内容 | 决定 | 说明 |
| --- | --- | --- |
| 本地通达信 TXT 导入（日线/分钟/秒级、跨月跨年推断） | 保留 | 优先保护；三条日期回归继续通过 |
| K 线、笔、线段、线段中枢、线段买卖点、MACD | 保留 | 默认只计算/显示线段级中枢与买卖点 |
| 缩放、拖动、框选、双击恢复、十字光标、六个显示开关 | 保留 | Qt 离屏检查覆盖 |
| 导出通达信线段公式（`.tni`，GBK） | 保留 | 三份导出与剃刀前逐字节一致 |
| 单只股票在线分析（腾讯 1/5/15/30/60 分钟、baostock 日线） | 保留 | 源码环境有界实测成功（腾讯 1 分钟、baostock 日线各 1 次）；候选 EXE 内未实测，5/15/30/60 分钟未逐一发真实请求 |
| 全市场扫描及专属界面、线程、进度、股票列表、缓存、回调 | **删除** | batch1 `2c2aa75` |
| GUI 新旧笔切换 | **删除** | `bi_strict` 固定 `False`（新笔）；框架参数仍在 |
| 上游演示入口 `main.py`、`Plot/AnimatePlotDriver.py`、`Script/requirements.txt` | **删除** | batch2 `5bb291a` |
| 32 个非离线回归 Debug 脚本 | **删除** | 只留 4 个离线日期回归 |
| `DataAPI/{csvAPI.py,ccxt.py,AkshareAPI.py}` | **删除** | 同步删 `Chan.py` 三分支和 `CEnum.DATA_SRC` 多余枚举 |
| `Image/` 40 个上游静态图 | 保留 | 仅 README 素材，不参与运行/打包 |
| `Seg/SegListDYH.py`、`Seg/SegListDef.py` | 保留 | 保守选择，避免动核心 `KLine_List.py` 分支（D1） |
| 内核 `bi_strict` 严格分支 | 保留 | 仅固定 GUI 默认路径，**不能声称内核旧笔已彻底删除** |
| `Math` 指标、`ChanModel/Features.py`、`DataAPI/CommonStockAPI.py` | 保留 | 仍有运行路径依赖，不能按名称删除 |

## 2. 分支与提交

| 提交 | 日期 | 内容 |
| --- | --- | --- |
| `24f9cee4c978e8739a400030dd322a4589b56611` | 整理阶段 | 基线；标签 `baseline-2026-11-06`；整理完成标签 `organized-2026-11-06` |
| `2c2aa75034fc83ba42aa7a0b93716994c7e95c92` | 2026-11-06 | batch1：删除全市场扫描、固定 `bi_strict=False`（仅改 `App/ashare_bsp_scanner_gui.py`，+29/−387） |
| `66bb2d34ef64c3f0325f4e8d4b6d613a112e357b` | 2026-11-06 | 依赖证据 + 验收工具（`razor_acceptance.py`、`razor_gui_check.py`、`verify_project.py --razor-changes`） |
| `5bb291a386c6fcbb637f514977143232423d2134` | 2026-11-06 | batch2：删除 38 个文件、修改 `Chan.py`/`Common/CEnum.py`/`ChanScanner.spec`（41 文件，+515/−2736） |
| `1d4af3550467765f83d90987f314a8d854c52386` | 2026-11-06 14:11:21 | 仅同步依赖证据文档到 batch2 工作区状态（`docs/razor-dependency-evidence.*`） |

- 远程：`origin git@github.com:zhaoqinmuchu/-auto.git`（SSH）。当前分支没有 upstream。
- 未合并回 `main`、未推送；桌面原版 `C:\Users\q8369\Desktop\chan.py-main` 未改动。
- `RAZOR_HANDOFF.md`、`docs/RAZOR_ACCEPTANCE.md`、`docs/razor-source-changes.json` 初稿生成时未跟踪，随后与本文档一并提交入库；`docs/razor-source-changes.json` 是验收默认读取的变更清单，必须随源码一起存在。
- `1d4af35` 只改两份依赖证据文档；batch2 之后业务源码没有再变动。最终验收（14:16，带 `--gui`）按 HEAD 重新校验基线并重新生成 Qt 离屏报告（14:16:39）；构建于 14:12 完成，构建时源码同为 `1d4af35`。

## 3. 实际删除清单（38 个文件）

batch2 共删除 38 个文件：37 个 `.py` + 1 个 `.txt`。逐文件理由见 `docs/razor-source-changes.json` 与 [依赖审计证据](razor-dependency-evidence.md) §0.1、D2、D5、D6。

### 3.1 按目录分组

| 目录/位置 | 数量 | 文件 |
| --- | ---: | --- |
| 根目录 | 1 | `main.py` |
| `Plot/` | 1 | `AnimatePlotDriver.py` |
| `Script/` | 1 | `requirements.txt` |
| `DataAPI/` | 3 | `AkshareAPI.py`、`ccxt.py`、`csvAPI.py` |
| `Debug/` | 32 | 见下节 |
| **合计** | **38** | 37 个 `.py` + 1 个 `.txt` |

### 3.2 Debug 删除的 32 个脚本

| 类别 | 文件 |
| --- | --- |
| 项目内样本/相对路径诊断（4） | `debug_tdx.py`、`test_tdx_txt.py`、`test_seg_9310.py`、`test_seg_0723.py` |
| SCL9 区间诊断（8） | `test_seg_0723b.py`、`test_seg_0723c.py`、`test_seg_0723d.py`、`test_seg_0723e.py`、`test_seg_0723f.py`、`test_seg_0723g.py`、`test_seg_0723h.py`、`test_seg_0723i.py` |
| 桌面个人文件诊断（7） | `test_000688_fix.py`、`test_seg_diag.py`、`test_seg_diag2.py`、`test_seg_diag3.py`、`test_seg_diag4.py`、`test_seg_revert_fx_debug.py`、`test_seg_second_case.py` |
| 桌面个人文件/联网诊断（2） | `test_tdx_daily.py`、`test_tencent_kline.py` |
| baostock/股票列表联网诊断（5） | `test_baostock_chan.py`、`test_baostock_enc.py`、`test_baostock_enc2.py`、`test_baostock_list.py`、`test_get_stocks.py` |
| 上游策略/机器学习演示（6） | `strategy_demo.py`、`strategy_demo2.py`、`strategy_demo3.py`、`strategy_demo4.py`、`strategy_demo5.py`、`strategy_demo6.py` |

保留的 4 个离线回归：`test_cross_year_infer.py`、`test_cross_year_e2e.py`、`test_user_2026_01.py`、`test_with_year_filter.py`。恢复方法见 [DEBUG_INDEX.md](DEBUG_INDEX.md) 与本文第 7 节。

### 3.3 未删除但容易被误认为已删除的内容

- `Image/` 的 40 个静态图仍保留（README 图片引用），运行和打包都不使用。
- `Seg/SegListDYH.py`、`Seg/SegListDef.py` 仍保留；`KLine/KLine_List.py` 中 `seg_algo` 的兼容分支仍在。
- `KLine/KLine_List.py` 的旧笔严格分支、`ChanConfig.py` 的 `bi_strict` 参数仍保留；剃刀只固定 GUI 默认值。
- `ChanScanner.spec` 仍保留 10 个包的 `collect_all`（只删了 4 段冗余），产物会比理论最小值大。
- `DataAPI/CommonStockAPI.py` 仍保留，作为 `BaoStockAPI`/`TencentAPI` 的基类。

## 4. 保留功能与固定参数

### 4.1 保留功能

- 本地 TXT：日线、分钟线、无年份秒级；跨月/跨年日期推断；取消文件选择或年月输入保留原状态，空年月取当前年月。
- 在线单股：1/5/15/30/60 分钟 → 腾讯财经（最多约最近 320 根）；日线 → baostock。
- 显示：K 线、合并 K 线、笔、线段、线段中枢、线段买卖点、MACD。
- 交互：滚轮缩放、左键拖动、右键框选、双击恢复、十字光标、六个显示开关。
- 导出：GBK 编码 `.tni`，`DRAWLINE` 与时间条件；秒级保留 `TIME2`。
- 不再包含：全市场扫描入口/线程/进度/列表/缓存/回调，以及 GUI 新旧笔切换控件。

### 4.2 `get_chan_config()` 固定参数（15 个键）

| 键 | 值 | 说明 |
| --- | --- | --- |
| `bi_strict` | `False` | **剃刀固定项**：新笔（非严格模式），界面无切换 |
| `bi_fx_check` | `"half"` | 分型有效性校验方式 |
| `trigger_step` | `False` | 不启用逐步触发 |
| `skip_step` | `0` | — |
| `divergence_rate` | `inf` | 背驰比率 |
| `bsp2_follow_1` | `False` | 二类买卖点不跟随一类 |
| `bsp3_follow_1` | `False` | 三类买卖点不跟随一类 |
| `min_zs_cnt` | `0` | 最小中枢数量 |
| `bs1_peak` | `False` | — |
| `macd_algo` | `"peak"` | MACD 算法 |
| `bs_type` | `"1,1p,2,2s,3a,3b"` | 启用的买卖点类型 |
| `print_warning` | `False` | — |
| `zs_algo` | `"normal"` | 中枢算法 |
| `cal_bi_zs` | `False` | **剃刀前即固定**：不算笔级中枢 |
| `cal_bi_bsp` | `False` | **剃刀前即固定**：不算笔级买卖点 |

除 `bi_strict` 外，其余 14 个键与剃刀前 GUI 默认值一致；Qt 离屏检查逐项比对通过。

### 4.3 `get_plot_config()` 显示配置

| 键 | 值/来源 | 说明 |
| --- | --- | --- |
| `plot_kline` | K 线开关 | 默认开启 |
| `plot_kline_combine` | `True` | 显示合并 K 线 |
| `plot_bi` | 笔开关 | 默认开启 |
| `plot_seg` | 线段开关 | 默认开启 |
| `plot_zs` | `False` | 不显示笔级中枢 |
| `plot_segzs` | 线段中枢开关 | 默认开启 |
| `plot_macd` | MACD 开关 | 默认开启 |
| `plot_bsp` | `False` | 不显示笔级买卖点 |
| `plot_segbsp` | 线段买卖点开关 | 默认开启 |

## 5. 验证结果

状态说明：**通过**＝有实际执行证据；**部分通过**＝已验证其中一部分路径，其余仍未验证；**未通过**＝执行失败（本次无）；**未验证**＝没有执行，不能算通过。

| # | 检查项 | 方法/命令 | 状态 | 证据 |
| ---: | --- | --- | --- | --- |
| 1 | 基线 JSON 完整性 | `razor_acceptance.py` 校验 96 项哈希与 HEAD 字节 | **通过** | `acceptance.json` → `baseline_json_integrity` |
| 2 | 基线 vs 变更清单 | 56 未改 + 3 允许修改 + 37 允许删除 + 2 新增 | **通过** | `acceptance.json` → `baseline_bytes_vs_manifest` |
| 3 | Python 语法 | 64 个 `.py` 逐个 `ast.parse` | **通过** | `acceptance.json` → `python_syntax` |
| 4 | 4 个离线日期回归 | 4 个脚本独立进程运行 | **通过**（全部 `returncode 0`） | `acceptance.json` 4 条回归检查 |
| 5 | 三样本 × 两模式分析指纹 | 6 组、114 字段逐字段比较 | **通过**（0 差异） | `analysis-before.json`、`analysis-after.json` |
| 6 | Qt 离屏 GUI 检查 | `razor_gui_check.py`，39 项 | **通过**（39/39，16.4 秒） | `gui-after.json` |
| 7 | 候选目录构建 | PyInstaller 6.22.3 / Python 3.14.10 | **通过**（2026-11-06 14:12:41） | `build.log`、`dist/razor-candidate/` |
| 8 | 候选 EXE 离屏启动冒烟 | `QT_QPA_PLATFORM=offscreen` 启动 EXE，观察 12 秒 | **通过**（进程存活、无 traceback；stderr 仅沙箱临时目录的 matplotlib 字体缓存权限警告） | `artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt` |
| 9 | 候选 EXE 真实可见窗口人工试用 | 启动界面、TXT 导入、导出、在线分析 | **未验证（待用户人工冒烟）** | 无真实窗口报告 |
| 10 | 真实桌面鼠标操作 | 手动点击/缩放/框选 | **未验证** | 本次只做 Qt offscreen |
| 11 | 联网单股有界实测 | 源码 `.venv` 直接调用 `CChan`：腾讯 1 分钟、baostock 日线 | **部分通过（仅源码环境）**：腾讯 71 根、baostock 28 根；候选 EXE 内未实测，5/15/30/60 分钟未逐一请求 | `network_probe.py`、`network-probe.json` |
| 12 | 公式导回证券软件 | 通达信公式编辑器显示/导入 | **未验证** | 只验证文本、GBK、时间条件 |
| 13 | 旧 EXE 等价性 | 新候选与桌面旧版行为/运行时等同 | **不适用/未验证** | 旧 EXE 内嵌 Python 3.13，新候选为 3.14 新构建 |

### 5.1 三样本指纹对照

6 组 = 3 个样本 ×（非严格、严格）。下表列出主要数量；完整内容（原始/合并 K 线顺序与首尾时间、笔/线段端点、中枢、买卖点）由指纹逐字段比较。`analysis-before.json` 与 `analysis-after.json` 的 SHA-256 均为 `3d62ce004469c41a295f51bbedade5aa1630951f849812593b60b2c5b081ce97`，即 6 组 114 个字段完全一致。

| 样本 | 模式 | 原始 K 线 | 合并 K 线 | 笔 | 线段 | 线段中枢 | 线段买卖点 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A111 | 非严格 | 20,300 | 15,125 | 1,426 | 199 | 25 | 77 |
| A111 | 严格 | 20,300 | 15,125 | 1,160 | 161 | 18 | 61 |
| CUL9 | 非严格 | 10,500 | 5,336 | 534 | 73 | 8 | 34 |
| CUL9 | 严格 | 10,500 | 5,336 | 392 | 56 | 9 | 24 |
| SCL9 | 非严格 | 23,100 | 13,468 | 1,405 | 177 | 20 | 70 |
| SCL9 | 严格 | 23,100 | 13,468 | 1,029 | 134 | 17 | 55 |

默认 GUI 关闭笔级中枢和笔级买卖点，因此对照的是线段级结果；笔级元素在指纹中按默认配置为空。

### 5.2 Qt 离屏 39 项

`gui-after.json`（39/39 PASS，约 16.4 秒，2026-11-06 14:16:39 生成，文件 SHA-256 `FA9761142464C70A49824DD3B32BD71C60A3EB4DB187BF7A8E8A2A4956499F30`）覆盖：

- 扫描功能移除：界面文字、属性、模块符号、回调均不存在；`bi_strict_cb` 不存在。
- 保留控件：代码输入、周期选择、导入/导出按钮、绘图 canvas、工具栏、六个显示开关。
- `get_chan_config()`：15 个键与剃刀前默认一致，`bi_strict` 恒为 `False`。
- `get_plot_config()`：9 个键与默认一致。
- 周期选项：1/5/15/30/60 分钟 → 腾讯，日线 → baostock。
- 对话框：取消文件选择、取消年月输入、空年月取当前年月。
- 导入：CUL9 期货、构造日线、跨年秒级三份本地 TXT。
- 导出：三份 `.tni`，GBK、`DRAWLINE`、秒级 `TIME2`，sha256 与剃刀前 `gui-before.json` 一致。
- 交互：滚轮缩放、左键拖动、右键框选、双击恢复、十字光标、六个显示开关。

该检查在 Qt offscreen 平台通过接口和模拟事件执行，不是实际桌面鼠标操作。

### 5.3 构建

见第 6 节。构建日志（SHA-256 `4d1938827a77a5790df21755e070581a29e0065a4e18878c5a7c9c534ab6f68c`）没有失败 `ERROR`；`warn-ChanScanner.txt` 记录 PyInstaller 常规的未找到可选模块警告（49,434 字节），未逐条证明每个警告都无影响。候选 EXE 已做离屏启动冒烟（12 秒存活、无 traceback），但真实窗口交互仍需人工补充。

### 5.4 验收工具自检

`acceptance-selftest.json`、`acceptance-missing-manifest.json`、`verify-selftest-razor.json` 证明工具能拒绝清单外改动/缺失清单，属于工具自检，不计入「剃刀源码通过」的证据。

### 5.5 联网单股有界实测（源码环境）

- 目的：补上「联网路径是否可用」的最低限度实测；不是候选 EXE 内验证，也不是真实窗口点击。
- 环境：开发 `.venv` + 剃刀后源码，使用 GUI 默认计算参数（`bi_strict=False`、`bi_fx_check="half"`、`cal_bi_zs=False`、`cal_bi_bsp=False`）直接调用 `CChan`。
- 腾讯分钟线：`custom:TencentAPI.CTencent`，`sz.000001`，1 分钟，`begin=2026-11-05` → 成功，71 根 K 线，首根 2026/11/05 11:30，末根 2026/11/06 14:18，5 笔、1 段。
- baostock 日线：`DATA_SRC.BAO_STOCK`，`sz.000001`，2026-09-01~2026-11-06，前复权（QFQ）→ 成功，28 根日线，首根 2026/09/01，末根 2026/11/05，2 笔、0 段；login/logout success。
- 证据：`.local-validation/razor/network_probe.py`、`.local-validation/razor/network-probe.json`。
- 失败分类逻辑：探针按异常类型区分——socket/timeout/connection/http 类归为 network（网络/服务失败），其余归为 source（源码错误）。本次两项均成功，无需记录失败。
- 覆盖边界：5/15/30/60 分钟的真实请求未逐一发出；周期映射和 GUI 下拉由 39 项离屏检查覆盖。候选 EXE 内的联网行为未验证。全市场扫描未运行（功能已删除）。

## 6. 候选 EXE 与构建

| 项目 | 值 |
| --- | --- |
| 候选目录 | `dist\razor-candidate\ChanScanner\`（`ChanScanner.exe` + `_internal\`） |
| EXE | 14,123,471 字节，SHA-256 `1E445E1495E97702E1304C2B9EA67E1283F3C29A785B316F44BEE281F53FAE2B` |
| 完整目录 | 1,133 个文件，179,650,198 字节（约 171 MiB） |
| 构建完成 | 2026-11-06 14:12:41 |
| 构建源码 | `1d4af3550467765f83d90987f314a8d854c52386`（构建时 docs 改动尚未提交，不影响 EXE） |
| 构建环境 | Python 3.14.10 (tags/v3.14.10:b703b2c, Oct 25 2026) [MSC v.1944 64 bit (AMD64)]；PyInstaller 6.22.3；pyinstaller-hooks-contrib 2026.8；PyQt6 6.11.0；matplotlib 3.11.1；numpy 2.5.1；pandas 3.0.5；baostock 0.9.3；requests 2.34.2 |
| 构建命令 | `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist\razor-candidate --workpath build\razor-candidate ChanScanner.spec` |
| 构建日志 | `.local-validation/razor/build.log`，SHA-256 `4d1938827a77a5790df21755e070581a29e0065a4e18878c5a7c9c534ab6f68c` |
| 目录完整性 | `_internal\python314.dll`、`python3.dll`、PyQt6 `platforms\qwindows.dll`、`matplotlib\mpl-data` 均存在（见 `artifact-checks.json`） |
| PYZ 抽查 | 含 `DataAPI.BaoStockAPI`、`DataAPI.TencentAPI`、`DataAPI.TDX_TXT_API`、`ChanModel.Features`、`Plot.PlotDriver`；不含 `AkshareAPI`、`ccxt`、`csvAPI`、`AnimatePlotDriver` |
| 产物运行验证 | 离屏启动冒烟：**通过**（`QT_QPA_PLATFORM=offscreen`，12 秒后进程存活、无 traceback；stderr 仅沙箱临时目录的 matplotlib 字体缓存权限警告）；真实可见窗口人工试用：**未验证** |
| 与旧 EXE 关系 | 桌面旧 EXE 内嵌 Python 3.13；本次是 Python 3.14 新构建，不是旧构建复现；不做体积缩小比例承诺 |

构建命令（在项目根目录、使用 `.venv` 执行；构建记录已确认此命令）：

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist\razor-candidate --workpath build\razor-candidate ChanScanner.spec
```

**待补占位**：候选 EXE 的真实可见窗口试用（启动界面、TXT 导入、导出、在线分析）仍由用户人工执行；在完成前不得把候选版称为已验证可替代稳定版。离屏启动冒烟只证明进程能启动并存活，不覆盖点击与业务交互。构建缓存/警告目录：`build\razor-candidate\ChanScanner\`（含 `warn-ChanScanner.txt`）；spec 为入口 `App\ashare_bsp_scanner_gui.py`、`hiddenimports` 3 项、`collect_all` 10 个包、目录模式 `ChanScanner`、`console=False`。

## 7. 恢复方式

桌面原版从未被修改，日常继续使用即可。开发副本按以下任一方式恢复：

### 7.1 Git revert（保留历史，推荐）

在**新分支**上按相反顺序撤销实现提交，不要 `reset` 或改写已推送历史：

```powershell
git switch -c codex/restore-before-razor
git revert 5bb291a 2c2aa75
```

这会恢复 38 个删除文件和两批源码改动；其后的文档/工具提交（`66bb2d3`、`1d4af35` 以及本次文档）不会自动撤销。若需要整理完成版的完整状态，使用标签：

```powershell
git switch --detach organized-2026-11-06
```

### 7.2 完整程序 ZIP

```text
.local-backups/2026-11-06-baseline/chan.py-main-full.zip
SHA-256: 9bc6e8e41a143fb5395cd0a45453c9ef912071bf48ed0ef3398ceca6995c794a
大小: 208,007,325 字节
```

解压到**新目录**，不要覆盖桌面现用目录：

```powershell
python -m zipfile -t .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip
python -m zipfile -e .\.local-backups\2026-11-06-baseline\chan.py-main-full.zip .\.local-backups\manual-restore-new
```

配套证据：`manifest.json`（逐文件 SHA-256）、`SHA256SUMS.txt`、`snapshot-verification.json`、`restore-check/chan.py-main`（已解压核验的参考树）。

### 7.3 Git bundle

```text
.local-backups/ChanScanner-history-2026-11-06.bundle
SHA-256: a38c589fbd6f5996e32514bdcd527d97524db17fbe53d5efa75a8436f50390d8
大小: 7,349,586 字节
校验: 同名 .sha256 文件；bundle-verification.json
```

```powershell
git bundle verify .\.local-backups\ChanScanner-history-2026-11-06.bundle
git clone --config core.autocrlf=false .\.local-backups\ChanScanner-history-2026-11-06.bundle .\.local-backups\manual-source-restore-new
```

恢复出的仓库包含创建时的本地分支与 `baseline-2026-11-06`、`organized-2026-11-06` 两个标签；不包含行情数据、虚拟环境或完整程序。必须显式设置 `core.autocrlf=false`，避免换行转换影响逐字节校验。

## 8. 已知限制与未验证范围

- **真实窗口未验证**：候选 EXE 只做了离屏启动冒烟（`QT_QPA_PLATFORM=offscreen`，12 秒后进程存活、无 traceback；stderr 仅有沙箱临时目录的 matplotlib 字体缓存权限警告），没有真实可见窗口的点击、TXT 导入、导出、在线分析人工验证。源码级、Qt offscreen 和启动冒烟都不代表实际桌面交互通过。
- **联网验证不完整**：源码环境已做有界实测（腾讯 1 分钟 71 根、baostock 日线 28 根，见 §5.5）；但候选 EXE 内未实测，5/15/30/60 分钟未逐一发真实请求，接口不可达时的失败反馈也未人工确认。
- **未把 `.tni` 导入通达信等软件**验证显示效果；只验证生成文本、GBK 编码与时间条件。
- **未与桌面旧 EXE 做行为等价比较**：旧 EXE 内嵌 Python 3.13，新候选是 3.14 新构建；源码与旧 EXE 的完全对应关系仍未证实。
- **保留项可能被误读**：`Image/` 40 个静态图、`Seg/SegListDYH.py`、`Seg/SegListDef.py`、`KLine_List.py` 旧笔严格分支、`ChanConfig.bi_strict` 参数仍在。剃刀只固定 GUI 路径，不能说「内核旧笔已彻底删除」。
- **打包配置仍非最小**：`ChanScanner.spec` 保留 10 个包的 `collect_all`，只删除了 4 段冗余；产物 171 MiB，不能据此承诺体积收益。
- **基线 JSON 故意不重签**：`docs/source-baseline-sha256.json` 仍是整理阶段 96 文件证据；`tools/verify_project.py` 默认严格模式会按设计失败，需用 `--razor-changes docs\razor-source-changes.json` 或 `tools/razor_acceptance.py`。
- **构建命令记录**：构建命令已由构建记录确认，见第 6 节；日志内没有失败 `ERROR`。
- **Qt 报告时间**：最终 `gui-after.json` 由 14:16 的 `--gui` 验收重新生成（14:16:39，39/39）；构建完成于 14:12，构建时源码同为 `1d4af35`。此后仅改文档，不影响已生成的源码级、Qt 与构建结果。
- **清单入库**：`docs/razor-source-changes.json` 初稿生成时未跟踪，最终随文档一并提交；若新克隆中缺失该清单，`razor_acceptance.py` 会明确报错，不会静默跳过。
- **未合并/未推送**：`main` 未被改动，`origin` 未更新；本分支不自动成为发布版。

## 9. 如何试用候选

1. 保留桌面原版不动，继续从 `C:\Users\q8369\Desktop\chan.py-main\dist\ChanScanner\ChanScanner.exe` 启动日常版本。
2. 试用时双击 `dist\razor-candidate\ChanScanner\ChanScanner.exe`；不要只复制 EXE，必须连同 `_internal` 整个目录一起使用。
3. 建议冒烟顺序：启动看主界面 → 导入 `CUL9.txt`（数据所属年月按文件最后一根 K 线填写）→ 缩放/框选/双击恢复/六个显示开关 → 导出 `.tni` 并检查文本 → 日线在线分析一只股票 → 分钟线（腾讯）一次。
4. 把实际结果（成功/失败、报错文本、截图）反馈给维护者；失败时保留 `.local-validation` 日志，不要删除候选目录。
5. 在用户明确决定切换前，桌面原版始终是稳定版；候选版不覆盖、不替换、不推送。

## 10. 证据文件索引

| 证据 | 路径 | 说明 |
| --- | --- | --- |
| 总验收 | `.local-validation/razor/acceptance.json` | 9/9 PASS（`--gui`，2026-11-06 14:16:18–14:16:41，23.1 秒）；sha256 `23E4D9A9DA2D3681638AD96E545EA5BABE91192BB3491B7EB025B4EE6F82DE7F` |
| 分析指纹 | `.local-validation/razor/analysis-before.json`、`analysis-after.json` | 6 组 114 字段；两者 sha256 均为 `3d62ce00…081ce97` |
| GUI 离屏 | `.local-validation/razor/gui-after.json`、`gui-after.png`、三份 `gui-after-*.tni` | 39/39 PASS（16.4 秒，14:16:39）；json sha256 `FA976114…499F30` |
| 剃刀前基线 | `.local-validation/razor/gui-before.json`、`verify-before.json` | 整理阶段/剃刀前对照 |
| 构建 | `.local-validation/razor/build.log`、`build/razor-candidate/ChanScanner/warn-ChanScanner.txt` | 构建时间、版本、警告；日志 sha256 `4d193882…6f68c` |
| 产物检查 | `.local-validation/razor/artifact-checks.json`、`exe-smoke.out.txt`、`exe-smoke.err.txt` | 目录 1,133 文件 / 179,650,198 字节；`python314.dll`、`qwindows.dll`、`mpl-data` 均在；离屏启动 12 秒存活，stderr 仅字体缓存权限警告 |
| 联网探针 | `.local-validation/razor/network_probe.py`、`.local-validation/razor/network-probe.json` | 腾讯 1 分钟 71 根、baostock 日线 28 根；仅源码环境，不是候选 EXE |
| 安装日志 | `.local-validation/razor/pip-install.log` | pip 临时目录权限失败原文 |
| 工具自检 | `.local-validation/razor/acceptance-selftest.json`、`acceptance-missing-manifest.json`、`verify-selftest-razor.json` | 验收工具拒绝能力 |
| 变更清单 | `docs/razor-source-changes.json` | 3 修改 / 37 删除 / 2 新增，随文档提交入库 |
| 依赖证据 | `docs/razor-dependency-evidence.md`、`.json` | 全量决策表、包级依赖、spec 修改、局限 |
| 快照/ZIP | `.local-backups/2026-11-06-baseline/` | ZIP、manifest、SHA256SUMS、snapshot-verification、restore-check |
| 历史包 | `.local-backups/ChanScanner-history-2026-11-06.bundle` | 分支与标签的离线备份 |

以上 `.local-validation`、`.local-backups`、`build`、`dist` 内容均被 `.gitignore` 忽略，只在本机保留。
