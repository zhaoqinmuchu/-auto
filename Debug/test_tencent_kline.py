# -*- coding: utf-8 -*-
"""测试腾讯mkline接口各周期的历史数据深度"""
import os
import sys

os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(k, None)

import requests

def fetch(url, label):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        print(f"[{label}] 状态码: {r.status_code}")
    except Exception as e:
        print(f"[{label}] 失败: {type(e).__name__}: {str(e)[:60]}")
    return None

# 测试各周期能获取多少历史数据
periods = [("m1", "1分钟"), ("m5", "5分钟"), ("m15", "15分钟"), ("m30", "30分钟"), ("m60", "60分钟"), ("day", "日线")]
for period, label in periods:
    # 尝试大数量
    url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param=sz000001,{period},,10000"
    d = fetch(url, label)
    if d:
        data = d.get('data', {})
        if isinstance(data, dict):
            for code, v in data.items():
                if isinstance(v, dict):
                    k = v.get(period) or v.get('data')
                    if k:
                        print(f"  {label}: 返回 {len(k)} 根, 最早: {k[0][0]}, 最晚: {k[-1][0]}")
                    else:
                        print(f"  {label}: 无K线数据")
