# -*- coding: utf-8 -*-
"""
腾讯行情数据源 (CTencent)

使用腾讯财经接口 (ifzq.gtimg.cn) 获取 A 股 K 线数据。
该接口支持 1 分钟、5 分钟、15 分钟、30 分钟、60 分钟、日线等周期。

注意:
    - 分钟级别数据最多只能获取最近约 320 根（约 1.3 个交易日）
    - 日线级别可以获取较长的历史数据
    - 数据为不复权数据

接口说明:
    https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},{period},,{count}
    返回 JSON 中 data.{code}.{period} 为 K 线数组
    每根 K 线格式: [时间(YYYYMMDDHHMM), 开盘, 收盘, 最高, 最低, 成交量, {}, 成交额]
"""
import os

import requests

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi

# 禁用系统代理，避免代理无法访问国内行情接口导致连接失败
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
for _k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(_k, None)

# 腾讯接口地址
TENCENT_KLINE_URL = "https://ifzq.gtimg.cn/appstock/app/kline/mkline"

# 周期映射: KL_TYPE -> 腾讯周期代码
# 注意: 腾讯 mkline 接口仅支持分钟级别，日线请使用 baostock
KL_TYPE_TO_TENCENT = {
    KL_TYPE.K_1M: "m1",
    KL_TYPE.K_5M: "m5",
    KL_TYPE.K_15M: "m15",
    KL_TYPE.K_30M: "m30",
    KL_TYPE.K_60M: "m60",
}

# 分钟级别最大可获取根数（腾讯接口限制）
MAX_MINUTE_COUNT = 320


def to_tencent_code(code):
    """
    将股票代码转换为腾讯格式（无点号）。

    规则:
        - 'sh.600000' -> 'sh600000'
        - 'sz.000001' -> 'sz000001'
        - '600000' -> 'sh600000'（6开头为上海）
        - '000001' -> 'sz000001'（其余为深圳）

    Args:
        code: str, 股票代码

    Returns:
        str: 腾讯格式代码
    """
    code = str(code).strip()
    if code.startswith('sh.') or code.startswith('sz.'):
        return code.replace('.', '')
    if code.startswith('sh') or code.startswith('sz'):
        return code
    if code.startswith('6'):
        return f"sh{code}"
    return f"sz{code}"


def parse_time_column(inp):
    """
    解析腾讯时间格式 YYYYMMDDHHMM。

    Args:
        inp: str, 时间字符串（如 '202607301342'）

    Returns:
        CTime: 时间对象
    """
    year = int(inp[0:4])
    month = int(inp[4:6])
    day = int(inp[6:8])
    hour = int(inp[8:10])
    minute = int(inp[10:12])
    return CTime(year, month, day, hour, minute)


class CTencent(CCommonStockApi):
    """使用腾讯财经接口获取 A 股 K 线数据"""

    def __init__(self, code, k_type=KL_TYPE.K_1M, begin_date=None, end_date=None, autype=AUTYPE.NONE):
        super(CTencent, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self):
        """获取 K 线数据"""
        period = self.__convert_type()
        count = self.__get_count()

        # 构建请求参数
        param = f"{to_tencent_code(self.code)},{period},,{count}"
        url = f"{TENCENT_KLINE_URL}?param={param}"

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise Exception(f"腾讯接口请求失败: {e}")

        # 解析返回数据
        data_dict = data.get('data', {})
        if not isinstance(data_dict, dict):
            raise Exception("腾讯接口返回数据格式错误")

        code_key = to_tencent_code(self.code)
        stock_data = data_dict.get(code_key, {})
        if not isinstance(stock_data, dict):
            raise Exception(f"未找到股票 {code_key} 的数据")

        # 分钟级别数据在 {period} 字段，日线级别在 'data' 字段
        kline_list = stock_data.get(period) or stock_data.get('data') or []
        if not kline_list:
            raise Exception(f"股票 {code_key} 无 {period} 级别K线数据")

        # 逐根生成 K 线单元
        for item in kline_list:
            if not isinstance(item, list) or len(item) < 6:
                continue
            # 格式: [时间, 开盘, 收盘, 最高, 最低, 成交量, {}, 成交额]
            item_dict = {
                DATA_FIELD.FIELD_TIME: parse_time_column(str(item[0])),
                DATA_FIELD.FIELD_OPEN: str2float(item[1]),
                DATA_FIELD.FIELD_CLOSE: str2float(item[2]),
                DATA_FIELD.FIELD_HIGH: str2float(item[3]),
                DATA_FIELD.FIELD_LOW: str2float(item[4]),
                DATA_FIELD.FIELD_VOLUME: str2float(item[5]),
            }
            # 成交额（第8个元素，可能不存在）
            if len(item) > 7:
                item_dict[DATA_FIELD.FIELD_TURNOVER] = str2float(item[7])
            yield CKLine_Unit(item_dict)

    def SetBasciInfo(self):
        """设置基本信息（腾讯接口不提供，使用默认值）"""
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        """初始化（无需额外操作）"""
        pass

    @classmethod
    def do_close(cls):
        """关闭（无需额外操作）"""
        pass

    def __convert_type(self):
        """将 KL_TYPE 转换为腾讯周期代码"""
        if self.k_type not in KL_TYPE_TO_TENCENT:
            raise Exception(f"不支持的K线级别: {self.k_type}")
        return KL_TYPE_TO_TENCENT[self.k_type]

    def __get_count(self):
        """根据周期确定可获取的最大根数（分钟级别统一为 320 根）"""
        return MAX_MINUTE_COUNT
