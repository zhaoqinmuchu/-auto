# 剃刀计划 · 依赖审计证据表（决策 + 包级结论 + spec 修改）

- 审计员：dep-audit（teammate of lead） · 任务：task-1 · 基线：分支 `codex/razor-project` HEAD `2c2aa75`
- GUI 快照：`App/ashare_bsp_scanner_gui.py` sha256 `5a495fca9bae3e6efd1a1391df5938ad2e2813243f8fa4a906c98a7ced6a6e2a`（1088 行 / 45984 B）
- 覆盖：tracked 159 个文件逐行判定（.py 101 个）；结论 KEEP=72 / REMOVE=75 / COUPLED=12
- 机器可读版：`docs/razor-dependency-evidence.json`（字段与本表一致，便于脚本复核）

**结论图例**：`KEEP`=保留；`REMOVE`=可直接删（无运行路径引用）；`COUPLED`=保留但必须同步改（spec/验证工具/文档），或须与其他文件成组删除——**单独删会留断链**。

## 0. 结论速览

### 0.1 可直接删除（REMOVE，无需改任何代码）

- **上游演示入口（2）**：`main.py`、`Plot/AnimatePlotDriver.py`
- **Debug 脚本（32，只留 4 个离线回归）**：`Debug/` 下除 `test_cross_year_infer.py`、`test_cross_year_e2e.py`、`test_user_2026_01.py`、`test_with_year_filter.py` 外的全部：
  `debug_tdx.py`、`test_tdx_txt.py`、`test_seg_0723.py`、`test_seg_0723b.py`、`test_seg_0723c.py`、`test_seg_0723d.py`、`test_seg_0723e.py`、`test_seg_0723f.py`、`test_seg_0723g.py`、`test_seg_0723h.py`、`test_seg_0723i.py`、`test_seg_9310.py`、`test_000688_fix.py`、`test_seg_diag.py`、`test_seg_diag2.py`、`test_seg_diag3.py`、`test_seg_diag4.py`、`test_seg_revert_fx_debug.py`、`test_seg_second_case.py`、`test_tdx_daily.py`、`test_baostock_chan.py`、`test_baostock_enc.py`、`test_baostock_enc2.py`、`test_baostock_list.py`、`test_get_stocks.py`、`test_tencent_kline.py`、`strategy_demo.py`、`strategy_demo2.py`、`strategy_demo3.py`、`strategy_demo4.py`、`strategy_demo5.py`、`strategy_demo6.py`
- **上游旧依赖清单（1）**：`Script/requirements.txt`
- **README 静态图（40，约 6.3MB）**：`Image/` 整个目录（若要求 README 完整可读则改 KEEP，见 D4）

> 删除后另有 3 处「必须同步」：`ChanScanner.spec`（L6）、`tools/verify_project.py`（基线）、`docs/*`（索引与哈希结论）——见 §3、§5、D10。

> **执行状态（生成时刻 git status 快照）**：REMOVE 的 75 个文件中，已有 35 个从工作区删除（未提交）；剩余 40 个仍在，主要是 `Image/`（40 个）。COUPLED 中已删除 3 个（3 个死数据源）。

### 0.2 成组改动后才能删（COUPLED）

| 路径 | 成组删除条件 / 必须同步的改动 |
| --- | --- |
| `ChanScanner.spec` | 不改则打包后分钟线分析 ImportError |
| `tools/verify_project.py` | 不改则剃刀后无法运行；方案见 D10 |
| `README.md` | 保留则文档过时；删除 Image/ 则 39 处图链失效 → 与 Image/ 成组处置（D4/D7） |
| `docs/DEBUG_INDEX.md` | 不改则文档与仓库不一致（不影响运行） |
| `docs/MAINTENANCE.md` | 不改则文档过时 |
| `docs/VERIFICATION.md` | 不改则记录与现实不符 |
| `docs/source-baseline-sha256.json` | 需重签或改名保留原证据（D10） |
| `Seg/SegListDYH.py`、`Seg/SegListDef.py` | 同时删 `KLine/KLine_List.py:23-30` 两个 deprecated 分支（否则选到 seg_algo=1+1/break 时 ImportError）；保守可 KEEP（D1） |
| `DataAPI/csvAPI.py`、`ccxt.py`、`AkshareAPI.py` | 同时删 `Chan.py:176-184` 的 CCXT/CSV/AKSHARE 分支 + spec L6 的 `DataAPI.csvAPI`；保守可 KEEP（D2） |

### 0.3 保留（KEEP）

共 72 个文件：GUI 入口 1、核心框架 27、线段/中枢、绘图、数据源、空 `__init__.py` 10、工具、文档与元数据、参考素材、Debug 回归 4（明细见 §1）。

## 1. 全量决策表（tracked 155 个文件，逐行）

> 引用证据格式 `文件:行号`，来自 `.local-validation/razor/refs-report.json`（AST 反向引用，parse_errors=0）或本次人工 grep/实测。`（共 N 处）` = 被静态 import 的总次数。

### 1.1 入口与 GUI

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `App/ashare_bsp_scanner_gui.py` | 唯一 GUI 入口（PyQt6，1088 行）：单股在线分析 / 本地通达信 TXT 导入 / 六周期 / 绘图 / 六个显示开关 / 缩放平移框选恢复 / 十字光标 / 导出通达信线段公式 | ChanScanner.spec:37（Analysis 入口）、tools/gui_smoke.py:26、tools/razor_gui_check.py:1 | **KEEP** | 程序唯一入口；扫描与新旧笔切换已在本文件内移除（HEAD 2c2aa75）；随后所有保留功能都靠它 | 无：删除即无程序 |

### 1.2 核心框架（Chan / ChanConfig / Common / Bi / BuySellPoint / ChanModel / Combiner / KLine / Math）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `Chan.py` | CChan 核心：加载数据、逐K递推、组装笔/线段/中枢/买卖点、pickle 存档；L171-194 按 DATA_SRC 动态分派数据源 | App/ashare_bsp_scanner_gui.py:62、Plot/AnimatePlotDriver.py:4、Plot/PlotDriver.py:9（共 30 处） | **KEEP** | 全项目 30 处静态引用（GUI/Plot/Debug），核心不可替换 | 无 |
| `ChanConfig.py` | CChanConfig：策略/指标参数解析 + GetMetricModel 构造指标模型（BOLL/MACD 恒建，Demark/RSI/KDJ 按开关） | App/ashare_bsp_scanner_gui.py:63、Chan.py:9、KLine/KLine_List.py:7（共 30 处） | **KEEP** | 30 处静态引用；GUI:63 直接使用 | 无 |
| `Common/CEnum.py` | 全项目枚举中心：DATA_SRC / KL_TYPE / BI_TYPE / BSP_TYPE / MACD_ALGO / DATA_FIELD / TREND_TYPE 等 | App/ashare_bsp_scanner_gui.py:64、App/ashare_bsp_scanner_gui.py:64、App/ashare_bsp_scanner_gui.py:64（共 155 处） | **KEEP** | 155 处静态引用，所有模块的公共词汇表 | 无 |
| `Common/CTime.py` | CTime 时间戳；跨周期、跨月跨年日期与秒级时间的基础类型 | Chan.py:12、DataAPI/AkshareAPI.py:5、DataAPI/BaoStockAPI.py:4（共 11 处） | **KEEP** | 运行路径依赖：被 11 处静态 import | 无 |
| `Common/ChanException.py` | CChanException + ErrCode 错误码 | Bi/Bi.py:5、Bi/Bi.py:5、Bi/BiConfig.py:2（共 36 处） | **KEEP** | 运行路径依赖：被 36 处静态 import | 无 |
| `Common/func_util.py` | str2float / has_overlap / kltype 比较 / _parse_inf / revert_bi_dir 等工具函数 | BuySellPoint/BSPointConfig.py:4、BuySellPoint/BSPointList.py:6、Chan.py:13（共 18 处） | **KEEP** | 运行路径依赖：被 18 处静态 import | 无 |
| `Common/cache.py` | make_cache 装饰器（笔、合并K线的重复计算缓存） | Bi/Bi.py:3、Combiner/KLine_Combiner.py:3 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无 |
| `Bi/Bi.py` | CBi 笔：端点、幅度、内部K线、MACD 关联 | Bi/BiList.py:6、BuySellPoint/BSPointList.py:3、BuySellPoint/BS_Point.py:3（共 12 处） | **KEEP** | 运行路径依赖：被 12 处静态 import | 无 |
| `Bi/BiConfig.py` | CBiConfig 笔参数（bi_strict / bi_fx_check 等） | Bi/BiList.py:7、ChanConfig.py:3 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无 |
| `Bi/BiList.py` | CBiList 笔列表与成笔判定 | BuySellPoint/BSPointList.py:4、KLine/KLine_List.py:5、Seg/EigenFX.py:4（共 14 处） | **KEEP** | 运行路径依赖：被 14 处静态 import | 无 |
| `BuySellPoint/BS_Point.py` | CBS_Point 买卖点（含 CFeatures 特征） | Bi/Bi.py:29、BuySellPoint/BSPointList.py:11、Chan.py:8（共 6 处） | **KEEP** | 运行路径依赖：被 6 处静态 import | 无 |
| `BuySellPoint/BSPointConfig.py` | CBSPointConfig 买卖点参数（bs_type / macd_algo / divergence_rate 等） | BuySellPoint/BSPointList.py:12、BuySellPoint/BSPointList.py:12、ChanConfig.py:4（共 4 处） | **KEEP** | 运行路径依赖：被 4 处静态 import | 无 |
| `BuySellPoint/BSPointList.py` | CBSPointList 买卖点计算与列表 | KLine/KLine_List.py:6 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无 |
| `ChanModel/Features.py` | CFeatures 字典容器（仅 18 行，无任何 ML 依赖；名字像机器学习但不是） | BuySellPoint/BS_Point.py:4（共 3 处） | **KEEP** | 被 BuySellPoint/BS_Point.py:4 静态 import；不是 ML 模块，不能按名字删 | 无：删除会使买卖点模块 ImportError |
| `Combiner/Combine_Item.py` | CCombine_Item：K线包含关系抽象 | Combiner/KLine_Combiner.py:8 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无 |
| `Combiner/KLine_Combiner.py` | CKLine_Combiner 合并K线（包含关系处理） | KLine/KLine.py:1、Seg/Eigen.py:4 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无 |
| `KLine/KLine.py` | CKLine 合并K线（三K/方向/重叠判定） | Bi/Bi.py:6、Bi/BiList.py:4、KLine/KLine_List.py:15（共 8 处） | **KEEP** | 运行路径依赖：被 8 处静态 import | 无 |
| `KLine/KLine_List.py` | CKLine_List 全量K线列表与各级别联动；L18-32 按 seg_algo 动态分派线段算法 | Chan.py:15、Plot/PlotMeta.py:7 | **KEEP** | Chan.py:15、Plot/PlotMeta.py:7；线段算法分派唯一入口（删分支见争议项 D1） | 无（删除需同时处理 SegList 分支，见 D1） |
| `KLine/KLine_Unit.py` | CKLine_Unit 单根K线 + 指标挂载；L7-12 无条件 import 全部指标类 | Bi/Bi.py:7、Chan.py:16、Combiner/Combine_Item.py:7（共 16 处） | **KEEP** | 运行路径依赖：被 16 处静态 import | 无 |
| `KLine/TradeInfo.py` | CTradeInfo 成交量/成交额等扩展成交字段 | KLine/KLine_Unit.py:14 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无 |
| `Math/BOLL.py` | BOLL 指标模型；ChanConfig.py:91 无条件构造 BollModel | ChanConfig.py:8、KLine/KLine_Unit.py:7、KLine/KLine_Unit.py:7 | **KEEP** | ChanConfig.py:91 无条件构造；删则模块导入即失败 | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/Demark.py` | TD Demark 序列/计数指示；Plot/PlotDriver.py:13 无条件 import | ChanConfig.py:9、KLine/KLine_Unit.py:8、KLine/KLine_Unit.py:8（共 5 处） | **KEEP** | 即使 cal_demark=False，PlotDriver.py:13 也无条件 import，逻辑绘制必须存在 | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/KDJ.py` | KDJ 指标（cal_kdj 开关控制是否计算，但 import 无条件） | ChanConfig.py:10、KLine/KLine_Unit.py:9 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/MACD.py` | MACD 指标（默认启用；笔/段/买卖点判定与 GUI MACD 显示依赖） | ChanConfig.py:11、KLine/KLine_Unit.py:10、KLine/KLine_Unit.py:10 | **KEEP** | 运行路径依赖：被 3 处静态 import | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/RSI.py` | RSI 指标（cal_rsi 开关控制计算，import 无条件） | ChanConfig.py:12、KLine/KLine_Unit.py:11 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/TrendModel.py` | CTrendModel 均线/趋势指标 | ChanConfig.py:13、KLine/KLine_Unit.py:12 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |
| `Math/TrendLine.py` | CTrendLine 趋势线拟合（线段趋势线判定） | Seg/Seg.py:7 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无：删需改 ChanConfig/KLine_Unit/PlotDriver 的 import 与构造逻辑 |

### 1.3 线段与中枢（Seg / ZS）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `Seg/Seg.py` | CSeg 线段（端点、特征序列、趋势线、内部中枢/买卖点） | Bi/Bi.py:26、BuySellPoint/BSPointList.py:7、BuySellPoint/BS_Point.py:6（共 9 处） | **KEEP** | 运行路径依赖：被 9 处静态 import | 无：删除会中断静态 import |
| `Seg/SegConfig.py` | CSegConfig：seg_algo（默认 chan）、left_method | ChanConfig.py:14、KLine/KLine_List.py:11、Seg/SegListChan.py:5（共 6 处） | **KEEP** | 运行路径依赖：被 6 处静态 import | 无：删除会中断静态 import |
| `Seg/SegListChan.py` | 默认线段算法 chan | KLine/KLine_List.py:21 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无：删除会中断静态 import |
| `Seg/SegListComm.py` | 线段列表公共基类（add_new_seg / update 等） | BuySellPoint/BSPointList.py:8、KLine/KLine_List.py:12、Seg/SegListChan.py:6（共 6 处） | **KEEP** | 运行路径依赖：被 6 处静态 import | 无：删除会中断静态 import |
| `Seg/Eigen.py` | CEigen 特征序列元素 | Plot/PlotMeta.py:8、Seg/EigenFX.py:9 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无：删除会中断静态 import |
| `Seg/EigenFX.py` | CEigenFX 特征序列分型（线段成段判定） | Plot/PlotMeta.py:9、Seg/Seg.py:9、Seg/SegListChan.py:4（共 6 处） | **KEEP** | 运行路径依赖：被 6 处静态 import | 无：删除会中断静态 import |
| `ZS/ZS.py` | CZS 中枢（区间、级别、延展判定） | BuySellPoint/BSPointList.py:9、Plot/PlotMeta.py:11、Seg/Seg.py:24（共 4 处） | **KEEP** | 运行路径依赖：被 4 处静态 import | 无：删除会中断静态 import |
| `ZS/ZSConfig.py` | CZSConfig 中枢参数（zs_algo / one_bi_zs 等） | ChanConfig.py:15、ZS/ZSList.py:8 | **KEEP** | 运行路径依赖：被 2 处静态 import | 无：删除会中断静态 import |
| `ZS/ZSList.py` | CZSList 中枢计算与列表 | KLine/KLine_List.py:13 | **KEEP** | 运行路径依赖：被 1 处静态 import | 无：删除会中断静态 import |
| `Seg/SegListDYH.py` | DYH“1+1”线段算法（KLine_List.py:23-25 的 deprecated 分支） | KLine/KLine_List.py:25（动态分支）、ChanConfig.py:32（默认 chan） | **COUPLED** | 仅当 seg_algo=="1+1" 时才被动态导入；GUI/4 回归/fingerprint 全部只用默认 "chan"（ChanConfig.py:32、SegConfig.py:6），产品内运行时不可达 | 删除需同时删 KLine/KLine_List.py:23-25 分支；只删文件则选到该配置时 ImportError |
| `Seg/SegListDef.py` | “break”线段算法（KLine_List.py:27-29 的 deprecated 分支） | KLine/KLine_List.py:29（动态分支）、Seg/SegConfig.py:6（默认 chan） | **COUPLED** | 仅当 seg_algo=="break" 时才被动态导入；产品内同样不可达 | 删除需同时删 KLine/KLine_List.py:27-29 分支（同上） |

### 1.4 绘图（Plot / 上游入口）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `Plot/PlotDriver.py` | matplotlib 绘图驱动：CPlotDriver、draw_klu/klc/bi/seg/zs/macd/bsp、redraw、save2img | App/ashare_bsp_scanner_gui.py:765（函数内 import）、tools/gui_smoke.py:86（canvas.figure 断言） | **KEEP** | GUI plot_chart（L765 函数内 import）使用；redraw 供缩放/框选后重绘，交互也依赖它 | 无：删除则绘图与交互全部失效 |
| `Plot/PlotMeta.py` | 画图数据适配层（CChanPlotMeta：klc/bi/seg/eigen/zs/bsp 元数据） | Plot/PlotDriver.py:15、Plot/PlotDriver.py:15、Plot/PlotDriver.py:15 | **KEEP** | 运行路径依赖：被 3 处静态 import | 无：删除会中断静态 import |
| `main.py` | 上游演示入口：拉 baostock sz.000001 → CPlotDriver → save2img('./test.png') → input() 阻塞 | 仅自身 __main__（main.py:7）；docs/MAINTENANCE.md:25 | **REMOVE** | 仅自身 __main__（L7）；联网取数、写图片、阻塞式演示，不是 GUI 入口；docs/MAINTENANCE.md:25 已注明其为上游例子 · *工作区已删除* | 无：无模块引用；须与 Plot/AnimatePlotDriver.py 成对删除（后者仅被本文件 :4 引用） |
| `Plot/AnimatePlotDriver.py` | 上游 IPython 动画演示驱动（CAnimateDriver） | main.py:4；实测 import Plot.AnimatePlotDriver → No module named 'IPython' | **REMOVE** | 仅 main.py:4 引用；L2 `from IPython.display import clear_output, display`，本环境未安装 IPython → 模块当前不可导入（实测 ModuleNotFoundError） · *工作区已删除* | 无：无运行路径引用；须与 main.py 成对删除 |

### 1.5 数据源（DataAPI）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `DataAPI/CommonStockAPI.py` | 数据源抽象基类 CCommonStockApi（do_init/get_kl_data/do_close/SetBasciInfo） | Chan.py:14、DataAPI/AkshareAPI.py:9、DataAPI/BaoStockAPI.py:8（共 7 处） | **KEEP** | 运行路径依赖：被 7 处静态 import | 无：删除会中断静态 import |
| `DataAPI/BaoStockAPI.py` | baostock 日线数据源（GUI 日线在线分析，用户确认保留） | Chan.py:174、App/ashare_bsp_scanner_gui.py:192（data_src=DATA_SRC.BAO_STOCK） | **KEEP** | Chan.py:174 的 DATA_SRC.BAO_STOCK 分支 + GUI 日线分支；用户明确要求保留 | 无：用户明确要求保留 |
| `DataAPI/TencentAPI.py` | 腾讯分钟线数据源（1/5/15/30/60 分钟；不支持日线） | App/ashare_bsp_scanner_gui.py:179（custom:TencentAPI.CTencent）、Chan.py:193（importlib.import_module） | **KEEP** | 静态引用 0，仅由 GUI L179 的 data_src="custom:TencentAPI.CTencent" 字符串动态导入；全部分钟级在线分析走它 | 无替代：唯一动态导入数据源，删除则全部分钟级在线分析失效 |
| `DataAPI/TDX_TXT_API.py` | 本地通达信 TXT 导入（时间约定识别、跨月/跨年推断，用户优先保护功能） | App/ashare_bsp_scanner_gui.py:158、tools/analysis_fingerprint.py:39、Debug/test_cross_year_*.py | **KEEP** | 11 处静态引用（GUI L158、4 个保留回归、tools/analysis_fingerprint） | 无：用户第一优先保护功能 |
| `DataAPI/csvAPI.py` | CSV 文件数据源（读 {code}_{k_type}.csv） | Chan.py:180（DATA_SRC.CSV 分支） | **COUPLED** | 仅被 Chan.py:180 的 DATA_SRC.CSV 分支导入；GUI 只用 BAO_STOCK 与 custom:，从不选 CSV · *工作区已删除* | 删除需同时删 Chan.py:179-181 分支；只删文件则选 CSV 时 ImportError（无人会选） |
| `DataAPI/ccxt.py` | ccxt 交易所数据源 | Chan.py:177；实测 import DataAPI.ccxt → No module named 'ccxt' | **COUPLED** | 仅被 Chan.py:177 的 DATA_SRC.CCXT 分支导入；ccxt 未安装 → 实测 import 即 ModuleNotFoundError（现为死代码） · *工作区已删除* | 删除需同时删 Chan.py:176-178 分支；否则仅留警告级死引用 |
| `DataAPI/AkshareAPI.py` | akshare 数据源 | Chan.py:183、DataAPI/AkshareAPI.py:1-2；实测 import → No module named 'akshare' | **COUPLED** | 仅被 Chan.py:183 的 DATA_SRC.AKSHARE 分支导入；akshare 未安装（且直接 import pandas，是 GUI 之外唯一 pandas 直接引用）→ 当前不可导入 · *工作区已删除* | 删除需同时删 Chan.py:182-184 分支；删后 numpy/pandas 仍因 baostock/matplotlib 必需（见 §2） |

### 1.6 包标记（__init__.py）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `BuySellPoint/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `Combiner/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `Common/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `DataAPI/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `KLine/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `Math/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `Plot/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `Seg/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `ZS/__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |
| `__init__.py` | __init__.py（0 字节）包标记 | 所有 `from <pkg>.<mod> import` 语句（如 Chan.py:8-16） | **KEEP** | 300+ 处点分导入（如 `from Common.CEnum import ...`）依赖这些目录被当作常规包；PyInstaller 亦然 | 低但无收益：0 字节文件，保留 |

### 1.7 工具、打包与依赖清单

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `tools/razor_gui_check.py` | Lead 的离屏 Qt 剃刀验收脚本（40KB）：扫描移除/保留功能/配置/对话框/导入导出哈希/交互/可选联网 | 文件自述；不引用 Debug/main/Image | **KEEP** | 剃刀批次的端到端验收工具（本次审计时未跟踪，现已纳入版本管理） | 无：验收工具必须保留 |
| `tools/razor_acceptance.py` | Lead 的剃刀总验收脚本（batch2 配套） | 文件自述（batch2 新增） | **KEEP** | 与 razor_gui_check 配套的一键验收入口 | 无 |
| `ChanScanner.spec` | PyInstaller 目录模式打包配置（入口 App GUI；collect_all；EXE+COLLECT=ChanScanner） | ChanScanner.spec:6（hiddenimports）、:7-34（14 段 collect_all）、:37（Analysis 入口） | **COUPLED** | 删除文件后必须同步：L6 hiddenimports 去掉 DataAPI.csvAPI；TencentAPI 只能靠 hiddenimports 兜住（动态字符串导入） | 不改则打包后分钟线分析 ImportError |
| `tools/verify_project.py` | 离线验收：96 文件字节基线 + AST 语法 + 4 项回归（+可选 fingerprint 等价） | tools/verify_project.py:22-27、docs/source-baseline-sha256.json（96 项） | **COUPLED** | L22-27 遍历 docs/source-baseline-sha256.json 并 read_bytes()：当前已因 GUI 改写 1 项 changed，删除任何 .py 后直接 FileNotFoundError → 必须改造或换基线 | 不改则剃刀后无法运行；方案见 D10 |
| `tools/analysis_fingerprint.py` | 三样本（A111/CUL9/SCL9）缠论分析指纹：raw_kline/combined_kline/bi/seg/zs/bsp 计数 | tools/analysis_fingerprint.py:26（三样本）、:39（custom:TDX_TXT_API） | **KEEP** | 剃刀行为等价的主要证据工具；依赖 custom:TDX_TXT_API 与三样本文件 | 无：删除会中断静态 import |
| `tools/gui_smoke.py` | 离屏 Qt 冒烟：导入/绘图/导出 .tni/六开关/缩放/拖拽 | tools/gui_smoke.py:26、:69-133 | **KEEP** | 验证保留功能的最小闭环 | 无：删除会中断静态 import |
| `requirements-gui.txt` | 22 条精确锁定的 GUI 运行依赖（含传递依赖） | requirements-gui.txt 22 行 + §2 证据链 | **KEEP** | 6 个顶层依赖全部仍必需；pandas/numpy 由 baostock/matplotlib 传递强制（见 §2），一条都不能删 | 无：删任何一条都可能使离线安装不完整，且不减小打包体积 |
| `requirements-build.txt` | 构建依赖：-r requirements-gui.txt + PyInstaller 6.22.3 + hooks-contrib 2026.8 | requirements-build.txt:1-4 | **KEEP** | 重建 EXE 的唯一依据（Lead 已手动安装 PyInstaller 6.22.3） | 无：删除会中断静态 import |

### 1.8 Debug 脚本

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `Debug/test_cross_year_infer.py` | 跨年/跨月日期推断离线回归 | tools/verify_project.py:12、:36、docs/DEBUG_INDEX.md（标记必留） | **KEEP** | tools/verify_project.py:12 的 REGRESSIONS 四件套之一（:36 拼 Debug/{name} 运行）；自建 tempfile fixture，完全离线、不依赖样本/网络 | 无：删除会直接导致验收工具失败 |
| `Debug/test_cross_year_e2e.py` | 跨年端到端离线回归 | tools/verify_project.py:12、:36、docs/DEBUG_INDEX.md（标记必留） | **KEEP** | tools/verify_project.py:12 的 REGRESSIONS 四件套之一（:36 拼 Debug/{name} 运行）；自建 tempfile fixture，完全离线、不依赖样本/网络 | 无：删除会直接导致验收工具失败 |
| `Debug/test_user_2026_01.py` | 用户 2026-01 场景离线回归 | tools/verify_project.py:12、:36、docs/DEBUG_INDEX.md（标记必留） | **KEEP** | tools/verify_project.py:12 的 REGRESSIONS 四件套之一（:36 拼 Debug/{name} 运行）；自建 tempfile fixture，完全离线、不依赖样本/网络 | 无：删除会直接导致验收工具失败 |
| `Debug/test_with_year_filter.py` | 年份过滤离线回归 | tools/verify_project.py:12、:36、docs/DEBUG_INDEX.md（标记必留） | **KEEP** | tools/verify_project.py:12 的 REGRESSIONS 四件套之一（:36 拼 Debug/{name} 运行）；自建 tempfile fixture，完全离线、不依赖样本/网络 | 无：删除会直接导致验收工具失败 |
| `Debug/debug_tdx.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_tdx_txt.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723b.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723c.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723d.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723e.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723f.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723g.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723h.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_0723i.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_seg_9310.py` | 项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“项目内样本一次性诊断（SCL9.txt / 写 _debug_out.txt）” | **REMOVE** | 一次性线段/日期诊断脚本，硬编码本项目样本 SCL9.txt 与特定区间；同类能力已由 4 个保留回归 + tools/analysis_fingerprint.py 覆盖 · *工作区已删除* | 无模块引用；删除后 docs/DEBUG_INDEX.md 需同步删行 |
| `Debug/test_000688_fix.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_diag.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_diag2.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_diag3.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_diag4.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_revert_fx_debug.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_seg_second_case.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_tdx_daily.py` | 桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“桌面硬编码路径（000688.txt / 999999.txt / 600570.txt，均不在仓库）” | **REMOVE** | 硬编码本机桌面文件路径（不在仓库），在新环境直接 FileNotFoundError；与用户本机数据强绑定、不可复现 · *工作区已删除* | 无；建议随剃刀清理 |
| `Debug/test_baostock_chan.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/test_baostock_enc.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/test_baostock_enc2.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/test_baostock_list.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/test_get_stocks.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/test_tencent_kline.py` | 联网脚本（baostock / 腾讯接口） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“联网脚本（baostock / 腾讯接口）” | **REMOVE** | 需要联网/外部接口；交接书明确禁止批量运行；离线回归不需要 · *工作区已删除* | 无；若保留会误导“离线可复现” |
| `Debug/strategy_demo.py` | 上游框架演示 | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游框架演示” | **REMOVE** | 上游框架演示（多数据源/画图示例），与用户保留的单股分析功能无关；仅供演示内部能力 · *工作区已删除* | 无：无模块引用 |
| `Debug/strategy_demo2.py` | 上游框架演示 | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游框架演示” | **REMOVE** | 上游框架演示（多数据源/画图示例），与用户保留的单股分析功能无关；仅供演示内部能力 · *工作区已删除* | 无：无模块引用 |
| `Debug/strategy_demo3.py` | 上游框架演示 | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游框架演示” | **REMOVE** | 上游框架演示（多数据源/画图示例），与用户保留的单股分析功能无关；仅供演示内部能力 · *工作区已删除* | 无：无模块引用 |
| `Debug/strategy_demo4.py` | 上游框架演示 | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游框架演示” | **REMOVE** | 上游框架演示（多数据源/画图示例），与用户保留的单股分析功能无关；仅供演示内部能力 · *工作区已删除* | 无：无模块引用 |
| `Debug/strategy_demo5.py` | 上游 ML 演示（需 xgboost，未安装） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游 ML 演示（需 xgboost，未安装）” | **REMOVE** | 上游机器学习演示，import xgboost（本环境未安装，实测不可导入）；与缠论 GUI 功能无关 · *工作区已删除* | 无：无模块引用且当前无法运行 |
| `Debug/strategy_demo6.py` | 上游 ML 演示（需 xgboost，未安装） | 无静态引用（仅自身 __main__）；docs/DEBUG_INDEX.md 分类：“上游 ML 演示（需 xgboost，未安装）” | **REMOVE** | 上游机器学习演示，import xgboost（本环境未安装，实测不可导入）；与缠论 GUI 功能无关 · *工作区已删除* | 无：无模块引用且当前无法运行 |

### 1.9 文档与仓库元数据

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `.gitattributes` | 行尾/编码属性（保证源码字节稳定） | 仓库根配置文件 | **KEEP** | 影响 checkout 行为与字节基线 | 无 |
| `.gitignore` | 忽略样本/生成物/本地验证目录 | 仓库根配置文件 | **KEEP** | 防止 A111/CUL9/SCL9/test.png/.local-* 入库 | 无 |
| `LICENSE` | 上游开源许可证（MIT 文本） | 仓库根配置文件 | **KEEP** | 合规要求，随代码保留 | 无 |
| `README.md` | 上游框架 README（77KB，含 39 处 Image/ 插图与扫描/多数据源/ML 功能说明） | README.md 内 39 处 Image/ 引用；docs/MAINTENANCE.md:25 已注明上游文档属性 | **COUPLED** | 纯文档、零运行依赖；但内容已与剃刀后功能不一致（仍描述已删的全市场扫描等），且引用 Image/ 全部插图 | 保留则文档过时；删除 Image/ 则 39 处图链失效 → 与 Image/ 成组处置（D4/D7） |
| `quick_guide.md` | 上游快速指南（28KB，偏完整版功能：多数据源/自动交易等） | 上游文档；PROJECT_GUIDE.md:24 说明上游文档属性 | **KEEP** | 纯文档；对个人使用价值低但无害，是否重写由 Lead 定（D7） | 无（不影响运行与打包） |
| `PROJECT_GUIDE.md` | 本项目（开发副本）指南：入口/环境/验证命令 | PROJECT_GUIDE.md:1-61 | **KEEP** | Lead 维护的本地文档；剃刀后需小幅更新（入口未变） | 无 |
| `docs/DEBUG_INDEX.md` | 36 个 Debug 脚本分类索引（4 必留/样本/桌面路径/联网/演示/ML） | docs/DEBUG_INDEX.md:1-23 | **COUPLED** | 删除 32 个脚本后本表失效，必须同步缩减为 4 项 | 不改则文档与仓库不一致（不影响运行） |
| `docs/MAINTENANCE.md` | 维护手册：环境安装、验证命令、打包说明 | docs/MAINTENANCE.md:15、:25、:30、:38、:44、:105 | **COUPLED** | L25 提到 main.py / Script/requirements.txt 为上游例子；若删除这两项需改该段；L30/38/44 验证命令依赖 verify_project.py | 不改则文档过时 |
| `docs/VERIFICATION.md` | 验证记录：原始 96 个 Python 文件哈希快照与验证结论 | docs/VERIFICATION.md:21 | **COUPLED** | L21 的“原始 96 个 Python 文件”在删除后不再成立，需更新为剃刀后基线 | 不改则记录与现实不符 |
| `docs/source-baseline-sha256.json` | 原始 96 个 .py 的 SHA-256 基线（verify_project.py 读取） | tools/verify_project.py:22-27；实测 96 项、1 项已变（App/ashare_bsp_scanner_gui.py） | **COUPLED** | 删除任何 .py 后该基线缺项；且当前 App GUI 已改写（changed=1）→ verify_project.py 现在就会失败 | 需重签或改名保留原证据（D10） |
| `docs/razor-dependency-evidence.md` | 本次审计交付物（人读版）：全量决策表 + 包级结论 + spec 修改 + 争议项 | 本文件 | **KEEP** | 新增文件（本表自身）；Lead 已在 66bb2d3 提交 | 无 |
| `docs/razor-dependency-evidence.json` | 本次审计交付物（机器可读版）：与 md 同构的 157 条决策 + packages/spec/disputes 字段 | 本文件 | **KEEP** | 新增文件（本表自身）；供脚本复核 | 无 |
| `docs/dependency-evidence.json` | 已核实的环境依赖事实（venv 版本、旧 EXE 内嵌 Python 3.13 等） | docs/dependency-evidence.json（PyQt6 6.11.0 / baostock 0.9.3 / matplotlib 3.11.1 / numpy 2.5.1 / pandas 3.0.5 / requests 2.34.2） | **KEEP** | 本次审计复用其环境事实，仍然有效 | 无：删除会中断静态 import |

### 1.10 Image 静态图（40 个文件，逐个列出）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `Image/answer_pic.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_1.svg` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_10.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_11.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_12.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_13.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_14.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_15.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_16.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_17.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_18.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_2.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_3.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_4.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_5.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_6.gif` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_7.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_8.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan.py_image_9.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_coding_time.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_commit_cnt.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_gotify_info.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_issue_cnt.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_qujiantao.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/chan_trendline.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/coffee.jpeg` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/demark.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/feature_cnt.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/frame.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/futu_sim_snapshot.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/hk_sim_result.jpeg` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/marker.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/notion_table.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/open_send_msg.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/plot_cbsp.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/question_pic.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/repository.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/summary_b_us_test.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/us_sim_result.jpeg` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |
| `Image/zs_algo.png` | 上游 README 静态插图/示意图（png/svg/gif/jpeg） | `.py` 零引用；README.md 39 处引用；ChanScanner.spec 无 Image datas | **REMOVE** | 全项目 .py 零引用（grep 无 “Image/”），不参与运行、不进入 PyInstaller datas；仅 README.md 引用 | 仅 README 预览图失效（约 -6.3MB 仓库体积）；若要求 README 完整可读则改 KEEP（D4） |

### 1.11 参考素材（TDX / Script）

| path | 现状作用 | 引用证据（file:line） | 结论 | 理由 | 删除/改动风险 |
| --- | --- | --- | --- | --- | --- |
| `TDX/chan_bi_simple.txt` | 通达信「缠论简化版画笔指标」公式源码（GBK，1.7KB） | 无代码引用（人工保留的参考素材） | **KEEP** | 无代码引用，但主题与保留的“导出通达信线段公式”功能直接相关，可作公式写法参考 | 无（1.7KB） |
| `Script/requirements.txt` | 上游旧依赖清单（baostock/ipython/matplotlib/numpy/pandas/requests 下限） | 无引用；docs/MAINTENANCE.md:25 | **REMOVE** | 无任何引用；docs/MAINTENANCE.md:25 已明确它不能作为 GUI 依赖清单（含未使用的 ipython） · *工作区已删除* | 无：GUI 依赖由 requirements-gui.txt 独立锁定 |

## 2. 包级依赖结论（requirements-gui.txt 22 行）

**总判断：不改动（22 条全部必要；无一条可删）**

| 包 | 结论 | 证据 | 理由 |
| --- | --- | --- | --- |
| **pandas** | KEEP（不能删） | baostock-0.9.3.dist-info/METADATA: `Requires-Dist: pandas>=0.18.0`；baostock/data/resultset.py:9 `import pandas as pd`；baostock/__init__.py:32 → corpreport.corp_performance（:14 导入 resultset）；实测 `import baostock` → 'pandas loaded: True'（pandas 3.0.5） | 用户确认保留 baostock 日线在线分析；只要 import baostock 就必然加载 pandas。删 pandas 会使日线分析运行时 ImportError；且 PyInstaller 静态分析会经 baostock 收集 pandas，删清单条目并不会减小包体。 |
| **numpy** | KEEP（不能删） | matplotlib-3.11.1.dist-info/METADATA: `Requires-Dist: numpy>=1.25`；全项目 .py 无任何直接 `import numpy`（仅作 matplotlib/pandas 传递依赖） | GUI 绘图核心依赖 matplotlib；matplotlib 必拉 numpy。pandas 3.0.5 亦依赖 numpy。 |
| **requests** | KEEP（必须） | DataAPI/TencentAPI.py:20 `import requests`（唯一源码引用） | 腾讯分钟线在线分析唯一 HTTP 客户端；删则 1/5/15/30/60 分钟周期全部失效。 |
| **baostock** | KEEP（必须） | DataAPI/BaoStockAPI.py:1 `import baostock as bs`；GUI 日线分支 data_src=DATA_SRC.BAO_STOCK | 日线在线分析数据源，用户确认保留。 |
| **matplotlib** | KEEP（必须） | App/ashare_bsp_scanner_gui.py:57-60（qtagg 后端 + Figure + pyplot）；Plot/PlotDriver.py:4-7（plt/Axes/Figure/Rectangle） | 绘图与交互（缩放/框选/重绘）全部基于 matplotlib。 |
| **PyQt6** | KEEP（必须） | App/ashare_bsp_scanner_gui.py:50（QtWidgets 批量导入）、:55（QtCore） | GUI 框架，无替代。 |

### 2.1 pandas 专项（任务重点）

**能否删：不能删。** 结论链：

1. 源码层：GUI 已无 `import pandas`（HEAD 2c2aa75 删除了旧 L61）；全项目仅剩 `DataAPI/AkshareAPI.py:2` 一处直接引用，而该文件因 akshare 未安装本就不可导入。TDX_TXT_API / BaoStockAPI / TencentAPI 三个保留数据源均**不使用** pandas（TDX 只用 stdlib `os/re/datetime`；Tencent 只用 `os/requests`；BaoStock 由 baostock 库内部处理）。
2. 传递层（决定性）：`baostock-0.9.3.dist-info/METADATA` 声明 `Requires-Dist: pandas>=0.18.0`；`baostock/data/resultset.py:9` 为 `import pandas as pd`；`baostock/__init__.py:32` 导入 `corpreport.corp_performance`，后者 `:14` 导入 `baostock.data.resultset`。
3. 实测：`.venv\Scripts\python.exe -B -c "import baostock"` → `pandas loaded: True`（pandas 3.0.5）。
4. 结论：用户确认保留 baostock 日线在线分析 → 只要 `import baostock` 就必拉 pandas → 运行环境与打包都必须有 pandas。删 requirements 里的 pandas 只会让离线安装不完整，不会减小包体（PyInstaller 会经 baostock 收集 pandas）。
5. 仅在放弃 baostock 日线时才可同时删：仅当同时放弃 baostock 日线（改为纯本地TXT + 腾讯分钟线）时，才可同时删 baostock、pandas 条目并移除 GUI 日线周期。

### 2.2 其余顶层依赖

- **numpy 不能删**：`matplotlib-3.11.1.dist-info/METADATA` 要求 `numpy>=1.25`；源码无直接 import（仅传递依赖）。
- **requests 必须**：`DataAPI/TencentAPI.py:20`，腾讯分钟线唯一 HTTP 客户端。
- **baostock 必须**：`DataAPI/BaoStockAPI.py:1` + GUI 日线分支。
- **matplotlib 必须**：GUI:57-60（qtagg/Figure/pyplot）+ `Plot/PlotDriver.py:4-7`。
- **PyQt6 必须**：GUI:50/:55。

### 2.3 传递依赖（16 条）

全部 KEEP：锁定清单的一部分，删任何一条都可能使离线安装不完整，且不减小打包后体积：certifi / charset-normalizer / idna / urllib3 ← requests；contourpy / cycler / fonttools / kiwisolver / packaging / pillow / pyparsing / python-dateutil ← matplotlib；python-dateutil → six；pandas → tzdata / python-dateutil；PyQt6-Qt6 / PyQt6_sip ← PyQt6。

### 2.4 未安装/未在清单中的包

| 包 | 状态 | 影响 |
| --- | --- | --- |
| akshare | 未安装 | 未安装（AkshareAPI.py 因此不可导入） |
| ccxt | 未安装 | 未安装（ccxt.py 因此不可导入） |
| IPython | 未安装 | 未安装（AnimatePlotDriver / main.py 因此不可导入） |
| xgboost | 未安装 | 未安装（strategy_demo5/6 因此不可运行） |
| PyInstaller | 未安装 | Lead 已手动安装 6.22.3（本审计脚本运行前未安装，故 spec 结论先按静态推理；见 §3 实测补充） |

> 建议：建议在 requirements-gui.txt 顶部加注释：pandas 由 baostock 传递必需（本 GUI 源码不再直接 import pandas），避免后续误删。

## 3. 删除文件后 ChanScanner.spec 怎么改

当前 spec：入口 `Analysis(['App\\ashare_bsp_scanner_gui.py'], pathex=['.'])`（L37-49）；L6 `hiddenimports`；L7-34 逐个 `collect_all` 并累加 datas/binaries/hiddenimports。

### 3.0 生成时刻工作区已执行的改动（未提交）

- **以下为生成时刻 `git status` 快照（未提交的 batch2 工作区改动），非本审计的待办要求，仅供 Lead 核对执行进度。**
- 工作区已删除 41 个文件：DataAPI/{AkshareAPI,ccxt,csvAPI}.py、main.py、Plot/AnimatePlotDriver.py、Script/requirements.txt、Debug 下除 4 个离线回归外的全部 32 个。→ 与本表 REMOVE 清单一致；Debug/test_tdx_txt.py 与 test_seg_9310.py 也被删（本表允许，D5 的保守保留建议未被采纳）。
- Chan.py 已删 DATA_SRC 的 CCXT/CSV/AKSHARE 三分支，GetStockAPI 现只剩 BAO_STOCK（L173-175）+ custom:（L179-186）→ 与 D2 推荐一致。
- Common/CEnum.py 的 `class DATA_SRC` 现只剩 `BAO_STOCK = auto()` → 与 D2 一致。
- ChanScanner.spec：hiddenimports 已改为 ['DataAPI.BaoStockAPI','DataAPI.TencentAPI','DataAPI.TDX_TXT_API']；collect_all 精简为 10 个包（Common/Bi/Seg/ZS/KLine/Combiner/Math/Plot/DataAPI/BuySellPoint），Chan/ChanConfig/App/ChanModel 四段已移除 → 与 §3.1 及 §3.2 建议方向一致。
- 仍未执行：Image/ 未删（40 个文件）、Seg/SegListDYH+Def 与 KLine/KLine_List.py 分支保留（保守选择 D1，正确）、README/quick_guide 未重写、docs/DEBUG_INDEX/MAINTENANCE/VERIFICATION 未更新、verify_project.py 基线未重签（D10）、requirements 未加 pandas 注释。

### 3.1 必须改（mandatory；batch2 工作区已按此执行，见 3.0）

- **L6**
  - 现状：`hiddenimports = ['DataAPI.BaoStockAPI', 'DataAPI.csvAPI', 'DataAPI.TencentAPI', 'DataAPI.TDX_TXT_API']`
  - 改为：hiddenimports = ['DataAPI.BaoStockAPI', 'DataAPI.TencentAPI', 'DataAPI.TDX_TXT_API']
  - 原因：① 删除 DataAPI/csvAPI.py 后建议移除 'DataAPI.csvAPI'（否则 PyInstaller 报 `Hidden import 'DataAPI.csvAPI' not found`，警告级、构建不中断，属脏配置）；② 必须保留 'DataAPI.TencentAPI'——它只通过 data_src="custom:TencentAPI.CTencent"（GUI:179）字符串动态导入，静态分析不可见，漏掉则打包后分钟线分析 ImportError；③ TDX_TXT_API 在 GUI:158 有函数内静态 import（PyInstaller 可发现），保留亦无害。
- **L（保守路径）**
  - 改为：若本轮不删 DataAPI 三文件，spec 一行都不用改，继续打包。
  - 原因：csvAPI 是 spec L6 中唯一与“可删文件”冲突的项。

### 3.2 建议改（可选优化）+ collect_all 实测（PyInstaller 6.22.3）

- 方法：`.venv\Scripts\python.exe -B .local-validation\razor\probe_collect_all.py`（PyInstaller 6.22.3，cwd=项目根）对 14 个名字调用 collect_all()，打印 datas/binaries/hiddenimports 数量与样本。
- datas：14 个名字全部 datas>0，且内容就是**包内 .py 源文件本身**（例：Common datas=6 全是 Common\*.py；Math datas=8 全是 Math\*.py；App/ChanModel 因无 __init__.py 同一文件出现两条重复项）。→ dist 里多出一整套源码副本，运行时并不加载，纯冗余；删掉 collect_all 即可消除。
- binaries：全部为 0 → 这些包确实没有二进制/动态库资源，spec 中 `binaries+=` 的累加始终为空。
- hiddenimports 数量：Chan 1、ChanConfig 1、Common 6、Bi 4、Seg 9、ZS 4、KLine 5、Combiner 3、Math 8、Plot 4、DataAPI 8、ChanModel 2、BuySellPoint 4、App 2。其中含现役死模块 DataAPI.AkshareAPI / DataAPI.ccxt / DataAPI.csvAPI 与 Plot.AnimatePlotDriver → collect_all 会强制分析它们（删文件后自然消失；未删时对未安装的 ccxt/akshare/IPython 会报 `Hidden import ... not found` 警告，非致命）。
- 单文件模块 Chan / ChanConfig 各触发 2 条 WARNING：`collect_data_files - skipping data collection for module 'Chan' as it is not a package`、`collect_dynamic_libs - skipping library collection ...`（共 4 条）。
- 关键联动：只要保留 `DataAPI` 段的 collect_all，DataAPI 全部子模块（含 TencentAPI）都会自动进入 hiddenimports，此时 L6 的 'DataAPI.TencentAPI' 是冗余保险；一旦删掉 collect_all，L6 的 TencentAPI 条目就成为分钟线功能的唯一保障。→ **L6 的 TencentAPI 与 DataAPI 段 collect_all 不可同时删除。**

- **L7-34**：删除 14 段 collect_all(...)（Chan/ChanConfig/Common/Bi/Seg/ZS/KLine/Combiner/Math/Plot/DataAPI/ChanModel/BuySellPoint/App），必要时用一行显式 hiddenimports 列表替代。
  - 原因：① 实测（3.2）：Chan、ChanConfig 是单文件模块，collect_all 触发 “not a package” 警告；App、ChanModel 无 __init__.py，collect_all 把同一 .py 收了两次；② 其余包 datas 收集到的只是 .py 源码副本（运行时不用），binaries 全为 0，这些累加语句对产物无功能贡献；③ 从入口 App GUI 出发的静态 import（含函数内 import，PyInstaller 可静态发现）已覆盖全部核心模块，真正需要 hiddenimports 的只有动态导入目标（即 L6）。
  - 风险：低：功能等价，仅缩短构建时间、减少 4 条 warning 与冗余源码副本；但删除后 L6 的 'DataAPI.TencentAPI' 变成必需项（见 3.2 最后一条）。重建后按 3.4 冒烟确认。

### 3.3 不需要动

- Analysis 入口 App\\ashare_bsp_scanner_gui.py（L37-49）
- pathex=['.']（模块均为顶层目录导入）
- EXE/COLLECT（目录模式、name='ChanScanner'、console=False、upx=True）
- excludes=[]
- datas=[] / binaries=[]（删除 Image/ 不影响，Image 从未进入 datas）

### 3.4 重建与冒烟清单

- 1) .venv 安装 requirements-build.txt（PyInstaller 6.22.3 + hooks-contrib 2026.8）。
- 2) 按上表改 spec 后：.venv\Scripts\pyinstaller.exe ChanScanner.spec --noconfirm
- 3) 冒烟（≈ tools/razor_gui_check.py 的验收面）：启动 dist\ChanScanner\ChanScanner.exe → 导入 CUL9.txt(2026-08) 画图 → 导出 .tni（GBK/DRAWLINE/TIME2）→ 日线在线分析一次 → 分钟线（腾讯）一次 → 缩放/框选/双击恢复。
- 4) 记录 EXE 产物体积与启动时间；与旧 EXE（Python 3.13 内嵌）对比仅作参考。

## 4. 需 Lead 决策的争议项（含保守建议与最小风险选项）

### D1 Seg/SegListDYH.py + Seg/SegListDef.py（2 文件、156 行）

- 涉及路径（2）：`Seg/SegListDYH.py`、`Seg/SegListDef.py`
- 建议：REMOVE：同时删 KLine/KLine_List.py:23-30 两个 deprecated 分支，使 get_seglist_instance 只保留 chan（+ else 抛错）。
- 证据：seg_algo 全项目只出现过 "chan"（ChanConfig.py:32、SegConfig.py:6 默认，Debug/9 个诊断脚本显式写 "chan"）；"1+1"/"break" 仅存在于 KLine_List.py:23/27 分支内，且运行时打印 deprecated 警告。
- 保守选项：KEEP：两文件无外部依赖、import 正常，保留零风险；仅多 156 行死代码。
- **最小风险选项：KEEP（最小风险）；REMOVE 需动核心 KLine_List.py，由 Lead 决定是否值得。**

### D2 DataAPI/csvAPI.py + ccxt.py + AkshareAPI.py（3 个死数据源）

- 涉及路径（3）：`DataAPI/csvAPI.py`、`DataAPI/ccxt.py`、`DataAPI/AkshareAPI.py`
- 建议：REMOVE：同时把 Chan.py L176-184 的 CCXT/CSV/AKSHARE 三分支删掉（GetStockAPI 只保留 BaoStockAPI + custom:），并同步 spec L6。
- 证据：三文件均只被 Chan.py 分支 import（:177/:180/:183）；ccxt、akshare 未安装 → 实测 import 即 ModuleNotFoundError；GUI 只用 DATA_SRC.BAO_STOCK 与 custom:。
- 保守选项：KEEP：不改核心 Chan.py 就无法完全删除；保留时行为与现状一致（选中即失败），仅多 PyInstaller “module ccxt/akshare not found” 警告（现状已如此，不致命）。
- **最小风险选项：KEEP（不动核心）；REMOVE 需改 Chan.py 约 10 行，收益是去掉 3 个死文件 + 2 个未安装依赖的死引用。**

### D3 Math 指标 7 个文件（BOLL/Demark/KDJ/MACD/RSI/TrendModel/TrendLine）

- 涉及路径（7）：`Math/BOLL.py`、`Math/Demark.py`、`Math/KDJ.py`、`Math/MACD.py`、`Math/RSI.py`、`Math/TrendModel.py`…
- 建议：KEEP 全部。GUI 虽默认只开 MACD，但 ChanConfig.py:8-13 与 KLine/KLine_Unit.py:7-12 是“无条件 import + 按开关计算”，Plot/PlotDriver.py:13 还无条件 import Demark；删除需改 3 处核心 import 与 GetMetricModel/绘图分支。
- 证据：ChanConfig.py:8-13、KLine_Unit.py:7-12、PlotDriver.py:13、Seg/Seg.py:7（TrendLine）。
- 保守选项：KEEP（推荐）。
- **最小风险选项：KEEP。**

### D4 Image/ 40 个静态图（约 6.3MB）

- 涉及路径（40）：`Image/answer_pic.png`、`Image/chan.py_image_1.svg`、`Image/chan.py_image_10.png`、`Image/chan.py_image_11.png`、`Image/chan.py_image_12.png`、`Image/chan.py_image_13.png`…
- 建议：REMOVE：纯 README 素材，.py 零引用、不打包。
- 证据：全项目 .py grep 无 “Image/”；README.md 39 处引用；ChanScanner.spec 无任何 Image datas。
- 保守选项：KEEP：若希望 README 打开时图片仍显示则保留；对运行/打包零影响。
- **最小风险选项：KEEP（不占运行时成本）；REMOVE 唯一副作用是 README 预览图裂。**

### D5 Debug 非必需 32 个脚本

- 涉及路径（32）：`Debug/debug_tdx.py`、`Debug/strategy_demo.py`、`Debug/strategy_demo2.py`、`Debug/strategy_demo3.py`、`Debug/strategy_demo4.py`、`Debug/strategy_demo5.py`…
- 建议：REMOVE 全部 32 个；只保留 4 个离线回归（tools/verify_project.py 依赖）。
- 证据：反向引用 0（无模块 import）；docs/DEBUG_INDEX.md 已标注其桌面路径/联网/上游演示属性；4 个保留回归自建 tempfile，无样本依赖。
- 保守选项：可额外保留 2 个离线诊断：Debug/test_tdx_txt.py（SCL9 样本）与 Debug/test_seg_9310.py（SCL9 区间），便于继续排查线段算法；其余仍建议删。
- **最小风险选项：删除（无引用、不影响验收）；若后续仍要调线段，保留上述 2 个。**

### D6 main.py + Plot/AnimatePlotDriver.py（上游演示入口）

- 涉及路径（2）：`main.py`、`Plot/AnimatePlotDriver.py`
- 建议：REMOVE 成对删除。
- 证据：main.py 仅自身 __main__（L7），拉 baostock sz.000001 并 save2img("./test.png") L82、input() L83；AnimatePlotDriver 仅被 main.py:4 引用，且 L2 依赖未安装的 IPython（实测两者 import 均 ModuleNotFoundError）。
- 保守选项：KEEP：无风险但纯死代码，不建议。
- **最小风险选项：REMOVE（成对，互不影响其他文件）。**

### D7 README.md / quick_guide.md（上游文档，105KB）

- 涉及路径（2）：`README.md`、`quick_guide.md`
- 建议：保留文件但剃刀后重写（仍宣传全市场扫描/多数据源/ML/自动交易）；删除会丢失上游文档参考。
- 证据：纯 .md，无 import；README 引用 Image/ 39 处；PROJECT_GUIDE.md:24 已说明其为上游文档。
- 保守选项：原样保留（零运行影响），把“文档更新”列为后续任务。
- **最小风险选项：不改（最小风险）；删 Image/ 时需接受 README 图裂。**

### D8 TDX/chan_bi_simple.txt（通达信画笔公式源码）

- 涉及路径（1）：`TDX/chan_bi_simple.txt`
- 建议：KEEP：与保留的“导出通达信线段公式”功能主题一致，1.7KB，可作公式参考。
- 证据：无代码引用（无任何 .py 读它）；人工参考素材。
- 保守选项：KEEP。
- **最小风险选项：KEEP。**

### D9 根 __init__.py（0 字节）

- 涉及路径（1）：`__init__.py`
- 建议：KEEP：零风险；删则某些以根目录为包的临时导入/工具会受影响，收益为零。
- 证据：无引用；仅为目录标记。
- 保守选项：KEEP。
- **最小风险选项：KEEP。**

### D10 docs/source-baseline-sha256.json + tools/verify_project.py（原 96 文件字节基线）

- 涉及路径（3）：`docs/source-baseline-sha256.json`、`tools/verify_project.py`、`docs/VERIFICATION.md`
- 建议：方案A（推荐）：把原基线改名 docs/source-baseline-sha256.original.json 作为“原始 96 文件未被篡改”的历史证据；按剃刀后源码树重新生成 docs/source-baseline-sha256.json（只含保留文件）；verify_project.py 的 L22-27 改为“缺失条目跳过 + 打印 WARN”，并把剃刀后基线视为新起点。方案B：给 verify_project.py 加 --baseline 参数默认指向新文件。
- 证据：实测：基线 96 项、0 missing、1 changed（App/ashare_bsp_scanner_gui.py，因剃刀改写）→ 眼下 `python -B tools/verify_project.py` 已必然失败；删除 .py 后 L24 read_bytes() 会 FileNotFoundError。
- 保守选项：至少先让 verify_project.py 能在剃刀后跑通（否则无法做最终验收）。
- **最小风险选项：方案A（新基线 + 旧基线留档），改动最小且保留证据链。**

### D11 requirements-gui.txt / requirements-build.txt 是否需因剃刀改动

- 涉及路径（2）：`requirements-gui.txt`、`requirements-build.txt`
- 建议：都不改。所有顶层依赖仍被保留功能需要（pandas 经 baostock 传递、numpy 经 matplotlib、requests 经 TencentAPI、baostock/PyQt6/matplotlib 直接需要）。可只在顶部加注释说明 pandas 来源。
- 证据：见 §2 证据链。
- 保守选项：不改。
- **最小风险选项：不改。**

### D12 打包重建与 EXE 验证

- 涉及路径（2）：`ChanScanner.spec`、`requirements-build.txt`
- 建议：Lead 已手动安装 PyInstaller 6.22.3，collect_all 语义已实测（§3.2）；可按 §3.4 rebuild_checklist 重建并冒烟；本次审计未执行完整构建（避免与 Lead 并行占用）。
- 证据：requirements-build.txt 注释“未安装未重建”；旧 EXE 为 Python 3.13 内嵌，未随本次源码更新；probe_collect_all.py 实测结果见 §3.2。
- 保守选项：保留 spec 现状不改，先完成源码剃刀；打包作为独立阶段。
- **最小风险选项：若本轮不做构建验证：仅按 §3 mandatory 改 L6，其余 collect_all 保持原样即可继续打包。**

## 5. 连带影响（删文件前必须知道的副作用）

- **tools/verify_project.py 现在就会失败**：docs/source-baseline-sha256.json 仍是 96 项原始哈希，其中 App/ashare_bsp_scanner_gui.py 已被剃刀改写（changed=1）；删除 .py 后 L24 会 FileNotFoundError。必须按 D10 处理后才可作最终验收工具。  
  证据：tools/verify_project.py:22-27
- **4 个必留回归脚本完全不依赖样本/网络**：已核查：Debug/test_cross_year_infer.py、test_cross_year_e2e.py、test_user_2026_01.py、test_with_year_filter.py 只插入项目根 sys.path，用 tempfile 自建 GBK fixture；无 A111/CUL9/SCL9、无 requests/baostock、无 input()。删除其他 Debug 脚本不影响它们。  
  证据：4 个脚本内 grep：仅 sys.path.insert + open(tempfile) 写入
- **样本文件 A111.txt / CUL9.txt / SCL9.txt 必须留在工作区（gitignored）**：tools/analysis_fingerprint.py:26 遍历三样本；tools/gui_smoke.py:69 用 --samples/CUL9.txt；tools/razor_gui_check.py 同。它们不是 tracked 文件，不在决策表内，但清理工作区时不要删。  
  证据：tools/analysis_fingerprint.py:26、tools/gui_smoke.py:69
- **文档需同步（docs/DEBUG_INDEX.md、docs/VERIFICATION.md、docs/MAINTENANCE.md）**：分别涉及 36 脚本索引、96 文件哈希结论、main.py/Script/requirements.txt 上游说明。不改不影响运行，但会让文档与仓库不一致。  
  证据：docs/DEBUG_INDEX.md:1-23、docs/VERIFICATION.md:21、docs/MAINTENANCE.md:25
- **工作区生成物可清理（非 tracked）**：test.png（182KB，main.py save2img 产物）、_debug_out.txt（3856B，Debug/debug_tdx.py 产物）、__pycache__/、.local-validation/、.local-backups/ 均可删；删除 Debug 脚本后 _debug_out.txt 不再再生。  
  证据：.gitignore 已忽略；git ls-files 中不存在
- **本次审计新增的交付物**：docs/razor-dependency-evidence.md 与 docs/razor-dependency-evidence.json（本文件），以及审计脚本 .local-validation/razor/{audit_refs.py,audit_imports.py,probe_collect_all.py,build_deliverable.py}（gitignored，可重跑）。未改动任何已有源码/文档。  
  证据：本目录
- **工作区还有 Lead 的未跟踪文件**：RAZOR_HANDOFF.md（交接书）与 tools/razor_gui_check.py（Lead 的离屏 Qt 验收脚本，约 40KB，未跟踪）不属于本次决策范围；若保留 razor_gui_check.py，建议正式纳入 tools/ 与文档。  
  证据：git status --porcelain：?? RAZOR_HANDOFF.md、?? tools/razor_gui_check.py

## 6. 审计方法与可复现命令

1. AST 反向引用：.local-validation/razor/audit_refs.py 遍历 99 个 .py（排除 .venv/.local-backups/.local-validation/__pycache__），输出 .local-validation/razor/refs-report.json（importer:line、dynamic_refs、parse_errors=0）。
2. 静态可达子图：.local-validation/razor/audit_imports.py 以 App/ashare_bsp_scanner_gui.py 为根做 import 图搜索（含函数内 import）：47 个可达、52 个从入口不可达（36 Debug + main.py + AnimatePlotDriver + TencentAPI + tools/3 + 各 __init__）。
3. 动态引用扫描：grep `custom:`、`importlib.import_module`、`__import__`；唯一动态数据源入口是 GUI:164/:179 与 Chan.py:193。
4. 运行时实测（只读，不跑 GUI/Debug）：python -B 逐模块 importlib.import_module —— Chan/ChanConfig/Plot.PlotDriver/DataAPI.{BaoStockAPI,TencentAPI,TDX_TXT_API,csvAPI}/Seg.SegList{DYH,Def} 可导入；DataAPI.ccxt（缺 ccxt）、DataAPI.AkshareAPI（缺 akshare）、Plot.AnimatePlotDriver 与 main（缺 IPython）不可导入。
5. 包依赖链：读 .venv site-packages 的 dist-info/METADATA 与 baostock 源码，并用 `import baostock` 实测 pandas 被加载。
6. 行号基线：HEAD 2c2aa75（codex/razor-project），App/ashare_bsp_scanner_gui.py sha256=5a495fca…（1088 行 / 45984 B）。GUI 若继续变动，引用请以符号名（方法/控件名）为准。
7. PyInstaller 6.22.3 只读实测（.local-validation/razor/probe_collect_all.py）：对 spec 中 14 个名字调用 collect_all()，统计 datas/binaries/hiddenimports；结果见 §3.2。
8. 未运行 GUI/Debug/回归脚本，未联网，未装包，未执行 git 写操作。

复现（PowerShell）：

```powershell
.\.venv\Scripts\python.exe -B .\.local-validation\razor\audit_refs.py
.\.venv\Scripts\python.exe -B .\.local-validation\razor\audit_imports.py
.\.venv\Scripts\python.exe -B .\.local-validation\razor\probe_collect_all.py
.\.venv\Scripts\python.exe -B .\.local-validation\razor\build_deliverable.py
```

## 7. 局限与未验证事项

- 本审计未执行 PyInstaller 完整构建：仅对 collect_all 语义做了只读实测（§3.2，PyInstaller 6.22.3 已可用）；hiddenimports 必要性、入口/pathex 等结论为静态推理与实测联合得出。重建后请按 §3.4 冒烟确认。
- 审计期间 Lead 正在改 App/ashare_bsp_scanner_gui.py；本表按 HEAD 2c2aa75 快照（sha256 见 §6）。GUI 后续改动只影响 GUI 行的内部行号，不影响其他文件结论。
- 未运行 4 个回归/三样本 fingerprint（属验收阶段工作，且交接书禁止批量运行 Debug）；因此“删除后行为不变”基于依赖图与引用证据，而非回归实测。
- 未评估打包产物体积/启动时间收益；未统计删除后 .py 行数变化（可复跑 .local-validation/razor 脚本统计）。
- docs/razor-*.{md,json} 为新增文件；未修改任何已有 docs 文件（按任务要求）。

## 8. 附：未跟踪文件与样本（不在 155 个 tracked 文件内）

- RAZOR_HANDOFF.md（Lead 交接书）
- tools/razor_gui_check.py（Lead 的离屏 Qt 验收脚本，未跟踪）
- A111.txt / CUL9.txt / SCL9.txt（gitignored 样本，必须保留在工作区）
- test.png / _debug_out.txt（gitignored 生成物，可清理）
- .local-validation/、.local-backups/、__pycache__/（gitignored）

