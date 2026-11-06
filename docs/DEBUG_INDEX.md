# 历史调试脚本索引

这些脚本原样保留，有的在导入时就运行。不要直接批量运行 `pytest Debug`，以免意外联网、读取个人文件或生成输出。

| 类别 | 脚本 | 条件及用途 |
| --- | --- | --- |
| 默认离线回归 | `test_cross_year_infer.py` | 无年份日期跨月、跨年倒推 |
| 默认离线回归 | `test_cross_year_e2e.py` | 临时构造跨三个月的秒级 TXT 并完整读取 |
| 默认离线回归 | `test_user_2026_01.py` | 有年份历史数据不被参考年月误过滤 |
| 默认离线回归 | `test_with_year_filter.py` | 另一参考年月下保留有年份历史数据 |
| 项目内行情样本 | `test_tdx_txt.py` | 依赖项目根目录的 SCL9.txt；不是可移植的内置测试样本 |
| 项目内行情样本 | `test_seg_0723.py`、`test_seg_0723b.py` 到 `test_seg_0723i.py`、`test_seg_9310.py` | SCL9 特定区间的笔、分型、线段诊断；部分脚本有临时追踪逻辑，只在单独进程使用 |
| 项目内行情样本及输出 | `debug_tdx.py` | 使用相对路径读取 SCL9.txt，写入根目录 `_debug_out.txt`；从项目根目录运行 |
| 桌面个人文件 | `test_000688_fix.py` | 硬编码桌面 000688.txt，验证脏 OHLC 数据修正 |
| 桌面个人文件 | `test_seg_diag.py`、`test_seg_diag2.py`、`test_seg_diag3.py`、`test_seg_diag4.py`、`test_seg_revert_fx_debug.py`、`test_seg_second_case.py` | 硬编码桌面 999999.txt，针对个人报告区间诊断 |
| 桌面个人文件 | `test_tdx_daily.py` | 硬编码桌面 600570.txt；检查时此文件不存在。默认自动检查不执行它，Qt 检查另构造日线数据 |
| 联网诊断 | `test_baostock_chan.py`、`test_baostock_enc.py`、`test_baostock_enc2.py`、`test_baostock_list.py` | 登录 baostock、查询数据或计算 |
| 联网诊断 | `test_get_stocks.py` | 调用 GUI 内的股票列表查询 |
| 联网诊断 | `test_tencent_kline.py` | 请求腾讯行情接口并检查各周期数据深度 |
| 上游策略演示 | `strategy_demo.py`、`strategy_demo2.py`、`strategy_demo3.py`、`strategy_demo4.py` | 依赖行情服务及特定策略条件，可能绘图，不属于本次离线回归 |
| 上游机器学习演示 | `strategy_demo5.py`、`strategy_demo6.py` | 还需 xgboost 等额外依赖，可能联网、训练和输出文件；不等同于 GUI 内置交易功能 |

默认验证入口为项目的 `tools/verify_project.py`，只选取表中明确标记的四个离线回归。脚本名称中的 test 不表示它已被整理成标准测试框架用例。
