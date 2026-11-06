from datetime import datetime


class CTime:
    def __init__(self, year, month, day, hour, minute, second=0, auto=True, real_ts_date=None):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.auto = auto  # 自适应对天的理解
        # real_ts_date: (ry, rm, rd) 真实世界日期，用于计算时间戳 ts。
        # 通达信期货夜盘(21:00之后)标记为"下一个交易日"，但真实世界时间是前一天晚上。
        # 因此显示字段(year/month/day)保留"交易日"日期，而 ts 用真实世界日期计算，
        # 保证K线时间戳单调递增，满足缠论框架的单调性检查。
        self.real_ts_date = real_ts_date
        self.set_timestamp()  # set self.ts

    def __str__(self):
        if self.hour == 0 and self.minute == 0:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        else:
            return f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}"

    def to_str(self):
        if self.hour == 0 and self.minute == 0:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        else:
            return f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}"

    def toDateStr(self, splt=''):
        return f"{self.year:04}{splt}{self.month:02}{splt}{self.day:02}"

    def toDate(self):
        return CTime(self.year, self.month, self.day, 0, 0, auto=False)

    def set_timestamp(self):
        if self.real_ts_date is not None:
            # 使用真实世界日期计算时间戳（用于夜盘等跨日场景）
            ry, rm, rd = self.real_ts_date
            if self.hour == 0 and self.minute == 0 and self.auto:
                date = datetime(ry, rm, rd, 23, 59, self.second)
            else:
                date = datetime(ry, rm, rd, self.hour, self.minute, self.second)
        elif self.hour == 0 and self.minute == 0 and self.auto:
            date = datetime(self.year, self.month, self.day, 23, 59, self.second)
        else:
            date = datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)
        self.ts = date.timestamp()

    def __gt__(self, t2):
        return self.ts > t2.ts

    def __ge__(self, t2):
        return self.ts >= t2.ts
