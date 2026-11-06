import os

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


# 通达信导出的夜盘数据有两种完全相反的日期标注约定：
#   1) 期货约定（SCL9/CUL9 等国内期货）：
#        晚上 21:00 之后属于"下一个交易日"，TXT 里的日期是"交易日"日期。
#        例如：真实世界 6/3 晚上 21:01 的K线，在 TXT 里标记为 6/4 21:01。
#        同一交易日内的顺序：夜盘(21:01~23:59) -> 隔夜(00:00~02:00) -> 日盘(09:00~15:00)。
#   2) 美股指数约定（A111 等道琼斯/纳斯达克指数）：
#        日期是"交易时段开始日"，即 21:31 那根K线的真实自然日。
#        例如：真实世界 5/21 晚上 21:31 的K线，在 TXT 里标记为 5/21 21:31（同一天）。
#        同一交易时段内的顺序：夜盘(21:31~23:59) -> 隔夜(00:00~04:00)，没有日盘。
#
# 两种约定的关键区别：期货约定每个"交易日"内包含日盘(09:00~15:00)，
# 而美股指数约定没有日盘。因此可用"文件中是否存在 09:00~15:00 的K线"来自动判断约定。
#
# 另外，通达信导出的时间格式有两种：
#   1) 有年份：YYYY/MM/DD-HH:MM[:SS]（如 2026/06/03-00:25:05），分钟级及以上周期常用。
#   2) 无年份：DD/HH:MM:SS（如 12/10:31:45 = 8月12日 10:31:45），通达信导出秒级K线（如5秒）时
#      只显示"日/时:分:秒"，没有月份和年份。月份年份由通达信 DATE 函数计算，程序不获取
#      （因为数据最大导出长度不会超过一个月）。程序需根据当前日期推断月份年份：
#      若日 > 当前日，则为上个月；否则为当前月。


def _detect_convention(rows):
    """
    根据原始解析行 (y, m, d, h, minute, ...) 判断日期标注约定。
    返回 True 表示"期货约定"，False 表示"美股指数约定"。
    判断依据：是否存在日盘(09:00~15:00)的K线。
    """
    for row in rows:
        h = row[3]  # 第4个字段是小时
        if 9 <= h <= 15:
            return True  # 有日盘 -> 期货约定
    return False  # 无日盘 -> 美股指数约定


def _infer_month_year(day, ref_date=None):
    """
    通达信导出秒级K线时只显示"日/时:分:秒"，没有月份和年份。
    程序需推断月份年份，返回 (year, month)。

    ref_date: 可选，用户手动指定的参考年月（datetime.date 或 (year, month)）。
        当用户指定了数据所属的年月时，用它作为基准，避免跨月/跨年时
        依赖"当前日期"推断出错（例如9月导出8月数据、1月导出12月数据）。
        数据最大导出长度不会超过一个月，因此所有K线都属于参考月。

    未指定 ref_date 时，回退到当前日期推断：
        若日 > 当前日，则为上个月；否则为当前月。
    """
    from datetime import date
    if ref_date is not None:
        # 用户手动指定了参考年月，直接用参考月
        if isinstance(ref_date, tuple):
            return ref_date[0], ref_date[1]
        return ref_date.year, ref_date.month
    today = date.today()
    if day > today.day:
        # 日 > 当前日 -> 上个月
        if today.month == 1:
            return today.year - 1, 12
        return today.year, today.month - 1
    return today.year, today.month


def _is_no_year_format(time_str):
    """判断通达信时间字符串是否为"无年份"格式（日/时:分:秒，如 12/10:31:45）。"""
    import re
    return bool(re.match(r'^\d{1,2}/\d{1,2}:\d{1,2}:\d{1,2}$', time_str.strip()))


def _infer_month_year_map(days, ref_date):
    """
    根据"最后一个K线"所属年月(ref_date)，倒推每个K线对应的年月。

    通达信导出秒级K线只显示"日/时:分:秒"，没有月份年份。数据可能跨多个月
    （如 12月30日~2月3日），若把所有K线都归为参考月会出错。正确做法：
    用户填写的年月是"最后一个K线"（即最大时间）所属年月，然后从后往前倒推：
    当某个标注日比它后面（更晚）的标注日更大时，说明向前跨了一个月，月份减一；
    月份减到 0 时年份减一、月份回到 12（跨年）。

    注意：days 必须是不去重的完整标注日序列（按时间顺序），因为去重会丢失
    跨月信息。例如跨 3 个月的数据 [30,31,1,2,...,31,1,2,3]（12月30-31、1月1-31、
    2月1-3），若去重成 [30,31,1,2,...,31]，倒推时只发生一次跨月（31>1 从2月到
    1月），12月的 30、31 会被错误归为 1月，导致"月会倒推但年不会"。

    例：标注日序列 [30, 31, 1, 2, 3, 4]，最后一个K线(日4)为8月。
        倒推：4=8月, 3=8月, 2=8月, 1=8月, 31>1→7月, 30=7月。

    days: 无年份K线的标注日序列（不去重，按时间顺序），如 [30, 31, 1, 2, 3, 4]。
    ref_date: (year, month)，最后一个K线（序列末尾）所属年月。
    返回: 与 days 等长的列表，每个元素是该K线对应的 (year, month)。
    """
    if not days:
        return []
    year, month = ref_date
    result = []
    prev_day = None
    for day in reversed(days):
        if prev_day is not None and day > prev_day:
            # 向前跨月：日变大说明进入上一个月
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        result.append((year, month))
        prev_day = day
    result.reverse()
    return result


def _parse_tdx_time_str(inp, ref_date=None, defer_month=False):
    """
    解析通达信导出的时间字符串，返回 (year, month, day, hour, minute, second, is_daily)。

    支持三种格式：
      1) 有年份带时间：YYYY/MM/DD-HH:MM[:SS]（如 2026/06/03-00:25:05），分钟级及以上周期。
      2) 无年份：DD/HH:MM:SS（如 12/10:31:45 = 8月12日 10:31:45），通达信导出秒级K线
         （如5秒）时只显示"日/时:分:秒"，没有月份和年份。月份年份由程序推断
         （_infer_month_year），因为数据最大导出长度不会超过一个月。
      3) 纯日期（日线）：YYYY/MM/DD（如 2017/12/29），通达信导出日线数据时只有日期，
         没有时间部分。此时 hour=minute=second=0，is_daily=True。

    ref_date: 可选，用户手动指定的参考年月（datetime.date 或 (year, month)）。
        无年份时用它推断月份年份；未指定则用当前日期推断。

    返回: (year, month, day, hour, minute, second, is_daily)
        is_daily=True 表示纯日期格式（日线数据，无时间部分）。
    """
    import re
    inp = inp.strip()
    # 情况1：有年份带时间，YYYY/MM/DD-HH:MM[:SS]
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})-(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$', inp)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hour, minute = int(m.group(4)), int(m.group(5))
        second = int(m.group(6)) if m.group(6) else 0
        return year, month, day, hour, minute, second, False
    # 情况2：无年份，DD/HH:MM:SS（如 12/10:31:45 = 8月12日 10:31:45）
    # 通达信导出秒级K线时，只显示"日/时:分:秒"，没有月份和年份。
    m = re.match(r'^(\d{1,2})/(\d{1,2}):(\d{1,2}):(\d{1,2})$', inp)
    if m:
        day = int(m.group(1))
        hour, minute, second = int(m.group(2)), int(m.group(3)), int(m.group(4))
        if defer_month:
            # 占位：年月稍后由 get_kl_data 基于"最后一个K线"统一倒推（跨月数据）
            year, month = 0, 0
        else:
            year, month = _infer_month_year(day, ref_date)
        return year, month, day, hour, minute, second, False
    # 情况3：纯日期（日线），YYYY/MM/DD（如 2017/12/29），无时间部分
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', inp)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return year, month, day, 0, 0, 0, True
    # 兜底：尝试按 YYYY/MM/DD-HH:MM[:SS] 解析
    raise ValueError(f"无法解析通达信时间格式: {inp!r}")


def parse_tdx_time(inp, is_futures=True, ref_date=None):
    """
    解析通达信导出的时间格式，返回 CTime 对象。

    支持三种格式：
      1) 有年份带时间：YYYY/MM/DD-HH:MM[:SS]（如 2026/06/03-00:25:05），分钟级及以上周期。
      2) 无年份：DD/HH:MM:SS（如 12/10:31:45 = 8月12日 10:31:45），通达信导出秒级K线
         （如5秒）时只显示"日/时:分:秒"，没有月份和年份。月份年份由程序推断
         （_infer_month_year），因为数据最大导出长度不会超过一个月。
      3) 纯日期（日线）：YYYY/MM/DD（如 2017/12/29），通达信导出日线数据时只有日期，
         没有时间部分。日线数据没有夜盘/隔夜概念，直接使用标注日期，不做日期调整。

    ref_date: 可选，用户手动指定的参考年月（datetime.date 或 (year, month)）。
        无年份时用它推断月份年份；未指定则用当前日期推断。

    is_futures=True  -> 期货约定：夜盘(21:00之后)属于"下一个交易日"，
                        因此夜盘的真实世界日期 = 交易日日期 - 1天。
    is_futures=False -> 美股指数约定：日期是"交易时段开始日"，
                        夜盘(21:00之后)的真实世界日期 = 标注日期（同一天），
                        隔夜(00:00~04:00)的真实世界日期 = 标注日期 + 1天。
    """
    year, month, day, hour, minute, second, is_daily = _parse_tdx_time_str(inp, ref_date)
    # auto=False: 保持原始时间，避免 0:00 被自动改成 23:59
    from datetime import date, timedelta
    if is_daily:
        # 日线数据（纯日期格式）：没有夜盘/隔夜概念，直接使用标注日期。
        # 注意：CTime 在 hour==0 且 auto=True 时会把 0:00 自动改成 23:59，
        # 因此这里必须用 auto=False 保持 0:00，使 ts 落在当天 00:00。
        return CTime(year, month, day, 0, 0, 0, auto=False)
    if is_futures:
        if hour >= 21:
            # 期货夜盘：真实世界日期 = 交易日日期 - 1天
            real_date = date(year, month, day) - timedelta(days=1)
            return CTime(year, month, day, hour, minute, second, auto=False,
                         real_ts_date=(real_date.year, real_date.month, real_date.day))
        return CTime(year, month, day, hour, minute, second, auto=False)
    else:
        if hour >= 21:
            # 美股夜盘：真实世界日期 = 标注日期（同一天）
            return CTime(year, month, day, hour, minute, second, auto=False)
        # 美股隔夜(00:00~04:00)：真实世界日期 = 标注日期 + 1天
        real_date = date(year, month, day) + timedelta(days=1)
        return CTime(year, month, day, hour, minute, second, auto=False,
                     real_ts_date=(real_date.year, real_date.month, real_date.day))


def tdx_trading_sort_key(klu, is_futures=True):
    """
    计算通达信K线的"交易日排序键"。

    期货约定：同一个交易日内的数据顺序固定为：
        夜盘(21:01~23:59) -> 隔夜(00:00~02:00) -> 日盘(09:00~15:00)
    美股指数约定：同一个交易时段内的数据顺序固定为：
        夜盘(21:31~23:59) -> 隔夜(00:00~04:00)

    注意：这里的时间戳 ts 是"真实时间"，不能直接用来排序，
    否则夜盘(21:01, ts大)会被排到隔夜(00:00, ts小)之后，导致顺序错乱。

    正确做法：按 (标注日期, 交易时段序号, 时分) 排序。
    时段序号：夜盘=0, 隔夜=1, 日盘=2。
    """
    t = klu.time
    # 标注日期（txt 里的日期）
    date_key = (t.year, t.month, t.day)
    # 交易时段序号
    if t.hour >= 21:          # 夜盘 21:01~23:59
        session = 0
    elif t.hour < 9:          # 隔夜 00:00~08:59
        session = 1
    else:                     # 日盘 09:00~20:59（仅期货约定存在）
        session = 2
    # 时段内的时间（时分秒，秒级K线如5秒需要秒来保证同一分钟内顺序正确）
    time_key = t.hour * 10000 + t.minute * 100 + t.second
    return (date_key, session, time_key)


class TDX_TXT_API(CCommonStockApi):
    """
    通达信导出的 TXT 数据源。

    通达信软件"数据导出"生成的 TXT 文件格式:
        - 前两行为标题（GBK 编码中文，需跳过）
        - 数据行用 Tab 分隔: 时间  开盘  最高  最低  收盘  成交量
        - 时间格式有两种:
            * 有年份: 2026/06/03-00:25（分钟级及以上）
            * 无年份: 12/10-10:31:45（秒级K线，如5秒，省略年份）

    支持两种夜盘日期标注约定（自动检测）：
        - 期货约定（SCL9/CUL9 等）：夜盘 21:00 之后属于下一个交易日
        - 美股指数约定（A111 等）：日期为交易时段开始日，夜盘 21:31~04:00

    用法:
        chan = CChan(
            code="600000",
            data_src="custom:TDX_TXT_API.TDX_TXT_API",
            lv_list=[KL_TYPE.K_1M],
            config=config,
            autype=AUTYPE.NONE,
        )
        其中 code 需传入 TXT 文件的完整路径。
    """

    def __init__(self, code, k_type=KL_TYPE.K_1M, begin_date=None, end_date=None, autype=None):
        # code 参数传入 TXT 文件的完整路径
        self.file_path = code
        super(TDX_TXT_API, self).__init__(code, k_type, begin_date, end_date, autype)
        # 解析参考年月：当用户手动指定了数据所属年月（如 "2026-08"）时，
        # 用它作为推断无年份格式(日/时:分:秒)的基准，避免跨月/跨年时依赖
        # "当前日期"推断出错。begin_date 支持 "YYYY-MM" 或 "YYYY-MM-DD"。
        self.ref_date = None
        if begin_date:
            import re as _re
            m = _re.match(r'^(\d{4})-(\d{1,2})', str(begin_date))
            if m:
                self.ref_date = (int(m.group(1)), int(m.group(2)))

    def get_kl_data(self):
        if not os.path.exists(self.file_path):
            raise CChanException(f"file not exist: {self.file_path}", ErrCode.SRC_DATA_NOT_FOUND)

        # 通达信导出的夜盘数据，每个交易日/交易时段内部顺序为：
        #   夜盘(21:xx~23:59) -> 隔夜(00:00~04:00) -> [日盘(09:00~15:00)，仅期货]
        # 全部用同一个日期标记，导致时间戳并非单调递增（23:59 后紧跟 00:00）。
        # 因此不能按文件顺序直接喂给缠论框架，否则会丢失大量K线或顺序错乱。
        # 正确做法：先把所有行读入并按"交易日排序键"排序，再按顺序输出。

        # 第一遍：读取所有原始行，用于自动判断日期标注约定
        raw_rows = []  # (y, m, d, h, minute, second, open, high, low, close, volume, is_daily)
        no_year_days = []  # 无年份格式(日/时:分:秒)的标注日序列（不去重，按时间顺序），用于跨月倒推
        no_year_indices = []  # 无年份K线在 raw_rows 中的索引
        with open(self.file_path, 'r', encoding='gbk', errors='ignore') as f:
            for line_number, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                # 用 Tab 分隔
                parts = line.split('\t')
                # 过滤空字段
                parts = [p.strip() for p in parts if p.strip() != '']
                if len(parts) < 5:
                    continue
                # 通达信导出列顺序: 时间 开盘 最高 最低 收盘 成交量
                time_str = parts[0]
                # 跳过标题行（时间列无法解析为日期格式）
                if '/' not in time_str:
                    continue
                # 无年份格式(日/时:分:秒)先不推断年月，收集标注日，稍后统一倒推
                is_no_year = _is_no_year_format(time_str)
                try:
                    y, m, d, hh, mm, ss, is_daily = _parse_tdx_time_str(time_str, self.ref_date, defer_month=is_no_year)
                except Exception:
                    continue  # 跳过无法解析的行（标题行等）

                # 时间过滤：仅对"有年份"格式(YYYY/MM/DD-HH:MM[:SS])做字符串比较。
                # 无年份格式(日/时:分:秒)没有月份年份，字符串比较无意义，
                # 且此时 begin_date 用于承载参考年月(ref_date)，不做过滤。
                if '/' in time_str and time_str[0].isdigit() and len(time_str) >= 10 and time_str[4] == '/':
                    # 有年份格式：YYYY/MM/DD...
                    # 注意：begin_date 可能是"参考年月"(YYYY-MM，如 2026-02)而非完整日期。
                    # 此时它仅用于无年份格式的跨月/跨年倒推基准，不应作为过滤截止，
                    # 否则会把早于该年月的所有数据(如 2025 全年)误删。
                    # 只有当 begin_date/end_date 是完整日期(YYYY-MM-DD)时才做字符串过滤。
                    if self.begin_date is not None and len(str(self.begin_date)) > 7 and time_str < self.begin_date:
                        continue
                    if self.end_date is not None and len(str(self.end_date)) > 7 and time_str > self.end_date:
                        continue

                open_p = str2float(parts[1])
                high = str2float(parts[2])
                low = str2float(parts[3])
                close = str2float(parts[4])
                volume = str2float(parts[5]) if len(parts) > 5 else 0.0

                if is_no_year:
                    no_year_days.append(d)  # 不去重，保留每个K线的标注日（时间顺序）
                    no_year_indices.append(len(raw_rows))
                raw_rows.append((y, m, d, hh, mm, ss, open_p, high, low, close, volume, is_daily))

        # 无年份格式：基于"最后一个K线"所属年月倒推每个K线的年月。
        # 用户填写的年月(ref_date)是最后一个K线（最大时间）所属年月；
        # 未填写时按当前日期推断最后一个K线的年月。
        # 注意：no_year_days 不去重（保留每个K线的标注日），否则跨多个月时
        # 会丢失跨月信息，导致"月会倒推但年不会"（如 2025-12 被误归为 2026-01）。
        if no_year_days:
            last_day = no_year_days[-1]  # 最后一个K线（最大时间）的标注日
            if self.ref_date is not None:
                last_ym = self.ref_date
            else:
                last_ym = _infer_month_year(last_day, None)
            month_list = _infer_month_year_map(no_year_days, last_ym)
            # 为每个无年份K线把占位(0,0)替换为真实年月
            for idx, ym in zip(no_year_indices, month_list):
                y, m, d, hh, mm, ss, o, h, l, c, v, is_daily = raw_rows[idx]
                raw_rows[idx] = (ym[0], ym[1], d, hh, mm, ss, o, h, l, c, v, is_daily)

        # 自动判断日期标注约定
        is_futures = _detect_convention(raw_rows)

        # 第二遍：构造 K 线单元
        kl_units = []
        for y, m, d, hh, mm, ss, open_p, high, low, close, volume, is_daily in raw_rows:
            if is_daily:
                # 日线数据（纯日期格式）：直接传 YYYY/MM/DD，parse_tdx_time 会识别为日线，
                # 不进行夜盘/隔夜日期调整，hour=minute=second=0。
                time_str = f"{y:04}/{m:02}/{d:02}"
            else:
                time_str = f"{y:04}/{m:02}/{d:02}-{hh:02}:{mm:02}:{ss:02}"
            time_obj = parse_tdx_time(time_str, is_futures=is_futures)
            kl_dict = {
                DATA_FIELD.FIELD_TIME: time_obj,
                DATA_FIELD.FIELD_OPEN: open_p,
                DATA_FIELD.FIELD_HIGH: high,
                DATA_FIELD.FIELD_LOW: low,
                DATA_FIELD.FIELD_CLOSE: close,
                DATA_FIELD.FIELD_VOLUME: volume,
            }
            # autofix=True：通达信导出的原始数据偶发 OHLC 不合法（如收盘价略高于最高价），
            # 此时自动修正 high/low 而非抛异常中断整个导入。
            kl_units.append(CKLine_Unit(kl_dict, autofix=True))

        # 按"交易日排序键"排序，保证K线顺序正确。
        # 注意：不能用真实时间戳 ts 排序！夜盘(21:xx起)与隔夜(00:00起)共用同一日期标记，
        # 若按 ts 排序，夜盘(21:xx, ts大)会被排到隔夜(00:00, ts小)之后，导致顺序错乱。
        kl_units.sort(key=lambda klu: tdx_trading_sort_key(klu, is_futures=is_futures))
        # 去重：通达信导出偶发"同一时间戳出现两次"的脏数据（如 31/13:00:50 出现两行）。
        # 缠论框架要求K线时间严格递增，重复时间戳会触发 kline time err。
        # 这里保留每个时间戳的第一根K线，跳过后续重复项。
        last_key = None
        for klu in kl_units:
            key = (klu.time.year, klu.time.month, klu.time.day,
                   klu.time.hour, klu.time.minute, klu.time.second)
            if key == last_key:
                continue  # 跳过重复时间戳
            last_key = key
            yield klu

    def is_daily_data(self):
        """
        判断当前 TXT 文件是否为"日线"数据（纯日期格式 YYYY/MM/DD，无时间部分）。

        通达信导出日线数据时，时间列只有日期（如 2017/12/29），没有 -HH:MM 时间部分；
        而分钟/秒级数据的时间列带时间（如 2026/06/03-00:25 或 25/23:59:30）。

        返回:
            bool: True 表示日线数据，False 表示分钟/秒级数据。
        """
        import re
        if not os.path.exists(self.file_path):
            return False
        with open(self.file_path, 'r', encoding='gbk', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split('\t') if p.strip() != '']
                if len(parts) < 5:
                    continue
                time_str = parts[0]
                if '/' not in time_str:
                    continue  # 标题行
                # 纯日期格式 YYYY/MM/DD（日线）
                if re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', time_str):
                    return True
                # 带时间的格式（分钟/秒级）
                if re.match(r'^\d{4}/\d{1,2}/\d{1,2}-', time_str) or _is_no_year_format(time_str):
                    return False
        return False

    def SetBasciInfo(self):
        pass

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass
