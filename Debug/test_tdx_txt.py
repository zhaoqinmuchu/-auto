# -*- coding: utf-8 -*-
"""测试通达信 TXT 数据源 + CChan 缠论分析"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, KL_TYPE

# 使用项目根目录的 SCL9.txt 作为测试数据
file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SCL9.txt")
print(f"数据文件: {file_path}")

config = CChanConfig({
    "bi_strict": True,
    "trigger_step": False,
})

chan = CChan(
    code=file_path,  # code 传入 TXT 文件路径
    data_src="custom:TDX_TXT_API.TDX_TXT_API",
    lv_list=[KL_TYPE.K_1M],
    config=config,
    autype=AUTYPE.NONE,
)

print(f"分析完成! K线数量: {len(chan[0])}")
print("前5根K线:")
for i in range(min(5, len(chan[0]))):
    kl = chan[0][i]
    print(f"  {kl.time_begin}  open={kl.lst[0].open} high={kl.lst[0].high} low={kl.lst[0].low} close={kl.lst[0].close}")
