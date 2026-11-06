# -*- coding: utf-8 -*-
"""从通达信客户端进程内存只读提取当前图表 K 线（免手工导出）。

原理
----
通达信客户端把当前图表的 K 线放在进程内存里，每条记录 32 字节：

    偏移  类型     含义
    +0    float32  开盘
    +4    float32  最高
    +8    float32  最低
    +12   float32  收盘
    +16   int32    持仓量（股票为 0 或其他）
    +20   int32    成交量
    +24   int32    恒为 0
    +28   int32    时间键 D = 交易日序号 * 86400 + 秒数

正常 K 线的 D 中"秒数"= 该 K 线标签时间 + 周期步长（5 秒线步长=5，10 秒线=10）；
时段收尾/开盘等边界 K 线会存成下一时段开盘时间，解码时需要特殊处理。

本模块：
1. 找到通达信进程（默认路径含 ``new_tdxqh`` 的期货通）；
2. 遍历已提交内存区，按 8 个相位（0,4,...,28）把字节视作 32B 记录，
   向量化找出连续有效的记录段；
3. 选"最新更新时间最新、K 线数最多"的一段作为当前图表数据；
4. 解码时间标签 + 用系统时间推出交易日，输出 K 线列表，可写成通达信 TXT。

该模块只读进程内存，不修改通达信任何文件/数据；不联网。

命令行用法（开发期）：:

    python -m TdxBridge.mem_reader --out D:\\tmp\\out.txt --chan

@author: chan.py TdxBridge
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# Windows API 封装
# ---------------------------------------------------------------------------

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]


kernel32.VirtualQueryEx.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.ReadProcessMemory.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = wt.BOOL
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wt.HANDLE,
    wt.DWORD,
    wt.LPWSTR,
    ctypes.POINTER(wt.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
psapi.EnumProcesses.argtypes = [
    ctypes.POINTER(wt.DWORD),
    wt.DWORD,
    ctypes.POINTER(wt.DWORD),
]
psapi.EnumProcesses.restype = wt.BOOL

EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wt.LPARAM]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wt.HWND


# ---------------------------------------------------------------------------
# 进程定位
# ---------------------------------------------------------------------------


def list_process_ids() -> list[int]:
    arr = (wt.DWORD * 4096)()
    needed = wt.DWORD()
    if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(needed)):
        raise OSError(ctypes.get_last_error(), "EnumProcesses failed")
    n = int(needed.value) // ctypes.sizeof(wt.DWORD)
    return [int(arr[i]) for i in range(n)]


def process_image_path(pid: int) -> str | None:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(2048)
        size = wt.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return None
    finally:
        kernel32.CloseHandle(h)


def find_tdx_process(install_key: str = "new_tdxqh") -> tuple[int, str]:
    """找通达信进程；install_key 为路径必须包含的关键字（空串=不筛选）。"""
    hits: list[tuple[int, str]] = []
    for pid in list_process_ids():
        path = process_image_path(pid)
        if not path:
            continue
        low = path.lower()
        if low.endswith("tdxw.exe") or low.endswith("tdx.exe"):
            hits.append((pid, path))
    if not hits:
        raise RuntimeError("没找到通达信进程（tdxw.exe / tdx.exe），请先打开通达信")
    if install_key:
        sel = [(p, x) for (p, x) in hits if install_key.lower() in x.lower()]
        if sel:
            return sel[0]
    return hits[0]


def _enum_windows() -> list[tuple[int, int, str]]:
    """枚举可见且带标题的窗口，返回 [(hwnd, pid, title)]。"""
    out: list[tuple[int, int, str]] = []

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        # 注意：必须先取长度再取文本（GetWindowTextW 传 nMaxCount=0 在部分系统上返回 0）
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        if user32.GetWindowTextW(hwnd, buf, length + 1) <= 0:
            return True
        title = buf.value
        if not title:
            return True
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((int(hwnd or 0), int(pid.value), title))
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)
    return out


def tdx_window_titles() -> list[tuple[int, str]]:
    """当前可见的通达信窗口标题（用于识别品种名）。"""
    return [(pid, title) for (_hwnd, pid, title) in _enum_windows()]


def tdx_chart_symbol(pid: int) -> str:
    """从窗口标题里取当前图表品种名，如 '原油加权'；失败返回空串。

    标题形如：``通达信期货通V1.75 - [分析图表-原油加权]`` 或
    ``... - [技术图形-黄金加权]``；多窗口时优先取前台窗口。
    """
    fg = int(user32.GetForegroundWindow() or 0)
    best = ""
    for hwnd, p, title in _enum_windows():
        if p != pid:
            continue
        m = re.search(r"\[[^\]]*?-([^\]]+)\]", title)
        if not m:
            continue
        name = m.group(1).strip()
        if hwnd == fg:
            return name
        if not best:
            best = name
    return best


# ---------------------------------------------------------------------------
# 内存读取
# ---------------------------------------------------------------------------


def iter_regions(h) -> "list[tuple[int, int, int]]":
    """返回 [(base, size, protect)]，仅 MEM_COMMIT 且可读的区域。"""
    regions: list[tuple[int, int, int]] = []
    addr = 0
    while True:
        mbi = MEMORY_BASIC_INFORMATION()
        ret = kernel32.VirtualQueryEx(
            h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if not ret:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        if size <= 0:
            break
        if mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD) and mbi.Protect != PAGE_NOACCESS:
            regions.append((base, size, int(mbi.Protect)))
        addr = base + size
        if addr <= 0:
            break
    return regions


def read_mem(h, addr: int, size: int) -> bytes:
    """读进程内存；整段失败时按块降级读取（读不到的部分填 0）。"""
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(
        h, ctypes.c_void_p(addr), buf, ctypes.c_size_t(size), ctypes.byref(got)
    )
    if ok and int(got.value) == size:
        return buf.raw
    out = bytearray(size)
    pos = 0
    chunk = 1 << 18
    while pos < size:
        n = min(chunk, size - pos)
        tmp = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            h, ctypes.c_void_p(addr + pos), tmp, ctypes.c_size_t(n), ctypes.byref(g)
        )
        if ok and int(g.value) == n:
            out[pos:pos + n] = tmp.raw
            pos += n
        elif chunk > 4096:
            chunk //= 4
        else:
            pos += 4096
    return bytes(out)


# ---------------------------------------------------------------------------
# 32 字节 K 线记录结构
# ---------------------------------------------------------------------------

REC_DTYPE = np.dtype(
    {
        "names": ["O", "H", "L", "C", "OI", "V", "Z", "D"],
        "formats": ["<f4", "<f4", "<f4", "<f4", "<i4", "<i4", "<i4", "<i4"],
        "offsets": [0, 4, 8, 12, 16, 20, 24, 28],
        "itemsize": 32,
    }
)

# 日线记录（证券终端/日线周期）的布局与日内不同：
#   [date int32][O,H,L,C float32][amount float32][volume int32][X int32] = 32 字节
# 即日期在最前面。因为 REC_DTYPE 以 float 段对齐时 D(+28) 读到的其实是
# "下一根记录的日期"，所以扫描日线时仍用 REC_DTYPE 找连续段，再把起始地址
# 往前挪 4 字节、多读一根，用 DAILY_DTYPE 真正解析。
DAILY_DTYPE = np.dtype(
    {
        "names": ["D", "O", "H", "L", "C", "A", "V", "X"],
        "formats": ["<i4", "<f4", "<f4", "<f4", "<f4", "<f4", "<i4", "<i4"],
        "offsets": [0, 4, 8, 12, 16, 20, 24, 28],
        "itemsize": 32,
    }
)

# 已知通达信周期步长（秒）
KNOWN_STEPS = {1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 180, 300, 600, 900, 1800, 3600}


def valid_mask(rec: np.ndarray) -> np.ndarray:
    o = rec["O"]
    hgh = rec["H"]
    low = rec["L"]
    close = rec["C"]
    m = (o > 0.5) & (hgh > 0.5) & (low > 0.5) & (close > 0.5)
    m &= (o < 2.0e5) & (hgh < 2.0e5) & (low < 2.0e5) & (close < 2.0e5)
    m &= (low <= np.minimum(o, close)) & (np.maximum(o, close) <= hgh)
    d = rec["D"].astype(np.int64)
    m &= (d > 1_000_000) & (d < 2_100_000_000)
    m &= (rec["V"] >= 0) & (rec["OI"] >= 0) & (rec["Z"] == 0)
    return m


@dataclass
class Candidate:
    addr: int
    count: int
    step: int
    firstD: int
    lastD: int
    firstC: float
    lastC: float
    protect: int = 0
    kind: str = "intraday"  # "intraday"（秒/分钟）或 "daily"（日线）
    ptr_hits: int = 0  # 内存里有多少个指针引用该数组（当前图表的数组通常被结构引用）

    def __str__(self) -> str:
        return (
            f"addr=0x{self.addr:x} kind={self.kind} count={self.count} step={self.step} "
            f"lastD={self.lastD} price {self.firstC:.2f}->{self.lastC:.2f} refs={self.ptr_hits}"
        )


def _runs(mask: np.ndarray, min_count: int) -> list[tuple[int, int]]:
    """把布尔掩码里的连续 True 段找出来，返回 [(start, end_exclusive)]。"""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    starts = edges[0::2]
    ends = edges[1::2]
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e - s >= min_count]


def _is_date_int(v: int) -> bool:
    """判断一个 int 是否像 YYYYMMDD 日期。"""
    if not (19900101 <= v <= 21001231):
        return False
    md = v % 10000
    return 101 <= md <= 1231


def _daily_mask(rec: np.ndarray) -> np.ndarray:
    """日线候选掩码：float 段合法 + D(+28) 是"下一根日期"。"""
    o, hgh, low, close = rec["O"], rec["H"], rec["L"], rec["C"]
    m = (o > 0.5) & (hgh > 0.5) & (low > 0.5) & (close > 0.5)
    m &= (hgh < 2.0e5) & (low <= np.minimum(o, close)) & (np.maximum(o, close) <= hgh)
    d = rec["D"].astype(np.int64)
    m &= (d >= 19900101) & (d <= 21001231)
    md = d % 10000
    m &= (md >= 101) & (md <= 1231)
    m &= (rec["V"] >= 0) & (rec["V"] < 2_000_000_000)
    return m



def scan_candidates(
    h,
    min_count: int = 200,
    min_region: int = 64 * 1024,
    phases: tuple[int, ...] = (0, 4, 8, 12, 16, 20, 24, 28),
    log=None,
) -> tuple[list[Candidate], dict]:
    """扫描全部已提交内存，返回 32B K 线记录段候选。"""
    cands: list[Candidate] = []
    regions = iter_regions(h)
    scanned = 0
    t0 = time.time()
    for base, size, protect in regions:
        if size < min_region:
            continue
        data = read_mem(h, base, size)
        if len(data) < min_region:
            continue
        scanned += len(data)
        for phase in phases:
            n = (len(data) - phase) // 32
            if n < min_count:
                continue
            rec = np.frombuffer(data, dtype=REC_DTYPE, count=n, offset=phase)

            # ① 秒/分钟级：D(+28) = 交易日序号*86400 + 秒
            m = valid_mask(rec)
            if int(m.sum()) >= min_count:
                for s, e in _runs(m, min_count):
                    sub = rec[s:e]
                    ds = sub["D"].astype(np.int64)
                    dd = np.diff(ds)
                    pos = dd[(dd > 0) & (dd <= 90000)]
                    if pos.size == 0:
                        continue
                    vals, cnts = np.unique(pos, return_counts=True)
                    step = int(vals[int(np.argmax(cnts))])
                    cands.append(
                        Candidate(
                            addr=base + phase + s * 32,
                            count=int(e - s),
                            step=step,
                            firstD=int(ds[0]),
                            lastD=int(ds[-1]),
                            firstC=float(sub["C"][0]),
                            lastC=float(sub["C"][-1]),
                            protect=protect,
                        )
                    )
    stats = {
        "regions": len(regions),
        "scanned_bytes": scanned,
        "seconds": round(time.time() - t0, 2),
        "candidates": len(cands),
    }
    if log:
        log(f"扫描完成：{stats['regions']} 个内存区、{scanned/1e6:.0f}MB、"
            f"{stats['seconds']}s、候选段 {len(cands)} 个")
    return cands, stats


def _cand_time_key(c: Candidate) -> int:
    """把候选"最后一根时间"归一成秒（日线按 15:00 折算成 交易日序号*86400+54000）。"""
    if c.kind != "daily":
        return c.lastD
    try:
        y, md = divmod(int(c.lastD), 10000)
        mo, dd = divmod(md, 100)
        days = (dt.date(y, mo, dd) - TDX_DAY_EPOCH).days
    except ValueError:
        return -1
    return days * 86400 + 54000


def count_ptr_refs(h, addrs: list[int], max_hits_per_addr: int = 50) -> dict[int, int]:
    """统计内存里有多少个 8 字节指针指向这些数组地址。

    通达信会把"当前正在看的图表"的 K 线数组挂在内部结构上（存在指针引用），
    而之前看过、仍残留在内存里的其它品种数组通常没有引用。
    """
    counts = {a: 0 for a in addrs}
    want = set(addrs)
    for base, size, protect in iter_regions(h):
        data = read_mem(h, base, size)
        if len(data) < 8:
            continue
        u32 = np.frombuffer(data[: len(data) // 4 * 4], dtype="<u4")
        for a in want:
            if counts[a] >= max_hits_per_addr:
                continue
            idx = np.flatnonzero(u32 == np.uint32(a & 0xFFFFFFFF))
            for i in idx.tolist():
                if i + 1 < len(u32) and int(u32[i + 1]) == (a >> 32):
                    counts[a] += 1
                    if counts[a] >= max_hits_per_addr:
                        break
    return counts


def select_candidates(
    cands: list[Candidate], prefer_step: int | None = None, fresh_margin: int = 180
) -> list[Candidate]:
    """挑选"当前图表"候选：时间最新 + 记录最多（去重拷贝）。

    秒/分钟级按 180 秒容差取最新；日线按 3 天容差取最新。
    """
    known = [c for c in cands if c.kind == "daily" or c.step in KNOWN_STEPS]
    if not known:
        raise RuntimeError("内存里没找到像样的 K 线记录段（通达信是否打开了图表？）")
    intra = [c for c in known if c.kind != "daily"]
    daily = [c for c in known if c.kind == "daily"]
    fresh: list[Candidate] = []
    if intra:
        mx = max(c.lastD for c in intra)
        fresh.extend(c for c in intra if c.lastD >= mx - fresh_margin)
    if daily:
        mxk = max(_cand_time_key(c) for c in daily)
        fresh.extend(c for c in daily if _cand_time_key(c) >= mxk - 3 * 86400)
    if prefer_step:
        pref = [c for c in fresh if c.step == prefer_step]
        if pref:
            fresh = pref
    # 若内存里存在"比日线明显更新"的日内数据（例如刚看过 5 秒/10 秒图），
    # 说明当前图表多半是分钟/秒级，此时丢掉日线候选，避免把历史日线缓存
    # 误当成"当前图表"（证券终端的日线数组通常会一直留在内存里）。
    if intra and daily and fresh:
        mx_daily = max(_cand_time_key(c) for c in daily)
        if any(
            _cand_time_key(c) > mx_daily + 86400
            for c in fresh
            if c.kind != "daily"
        ):
            fresh = [c for c in fresh if c.kind != "daily"]
    uniq: dict[tuple, Candidate] = {}
    for c in fresh:
        # 去重键要带价格：不同品种的日线数组可能根数完全相同（如都是 700 根、到同一天），
        # 只按键值去重会把不同品种误当成同一份拷贝。
        uniq.setdefault(
            (c.kind, c.count, c.step, c.firstD, c.lastD, round(c.firstC, 2), round(c.lastC, 2)),
            c,
        )
    out = sorted(uniq.values(), key=lambda c: (-int(c.ptr_hits > 0), -c.count, -_cand_time_key(c)))
    return out



# ---------------------------------------------------------------------------
# KN 线解码
# ---------------------------------------------------------------------------


@dataclass
class Bar:
    date: dt.date
    hour: int
    minute: int
    second: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    dn: int = 0  # 交易日序号（内部用）
    flagged: bool = False  # 是否时段收尾/开盘边界 bar

    def label(self) -> str:
        return "%02d/%02d:%02d:%02d" % (
            self.date.day,
            self.hour,
            self.minute,
            self.second,
        )


# 通达信内部日期序号（K 线记录 +28 的 D 除以 86400）的零点：
# dn=8339 对应 2026-10-30（黄金/原油 5 秒数据校准）；对期货，夜盘 bar 的 dn
# 是"下一交易日"，对股票就是日历日；两者都与 TDX 显示/公式里的 DATE 一致。
TDX_DAY_EPOCH = dt.date(2003, 12, 31)


def decode_labels(ds: list[int] | np.ndarray, step: int) -> tuple[list[int], list[bool]]:
    """把时间键 D 解码成"当日秒数"标签；返回 (labels, flagged)。

    规则（已在黄金 5 秒导出数据上逐根验证）：
      cs[i] = (D%86400 - step) % 86400
      labels[0] = cs[0]
      i>0: A=cs[i], B=(labels[i-1]+step)%86400
           若 A==B 或 (A-cs[i-1])%86400==step  -> label=A
           否则 -> label=B，并标记为"边界 bar"
    """
    n = len(ds)
    cs = [((int(d) % 86400) - step) % 86400 for d in ds]
    labels = [cs[0]]
    flagged = [False]
    for i in range(1, n):
        a = cs[i]
        b = (labels[-1] + step) % 86400
        if a == b or (a - cs[i - 1]) % 86400 == step:
            labels.append(a)
            flagged.append(False)
        else:
            labels.append(b)
            flagged.append(True)
    return labels, flagged


def _trading_day_on_or_before(d: dt.date) -> dt.date:
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _trading_day_after(d: dt.date) -> dt.date:
    d += dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def infer_anchor_date(now: dt.datetime | None = None) -> dt.date:
    """按"当前时刻最后一根 K 线属于哪个交易日"推断锚点日期。

    期货交易日规则：夜盘（21:00 起）属于下一交易日；凌晨 00:00–02:30
    属于前一晚夜盘，即"下一交易日"；日盘属于当日。
    """
    now = now or dt.datetime.now()
    t = now.time()
    if dt.time(9, 0) <= t < dt.time(21, 0):
        # 日盘/收盘后：最后一个交易时段是当天（或最近一个交易日）
        return _trading_day_on_or_before(now.date())
    if t >= dt.time(21, 0):
        # 夜盘中：属于下一交易日
        return _trading_day_after(now.date())
    # 00:00 - 09:00：属于前一晚夜盘 -> 下一交易日（相对昨天）
    return _trading_day_after(now.date() - dt.timedelta(days=1))


def read_candidate_bars(
    h, cand: Candidate, now: dt.datetime | None = None
) -> tuple[list[Bar], dict]:
    """按候选段地址读出全部 K 线并解码。"""
    raw = read_mem(h, cand.addr, cand.count * 32)
    cnt = len(raw) // 32
    if cnt <= 0:
        raise RuntimeError("读取 K 线数组失败")
    rec = np.frombuffer(raw, dtype=REC_DTYPE, count=cnt)
    ds = rec["D"].astype(np.int64)
    labels, flagged = decode_labels(ds, cand.step)

    date_dn = (ds // 86400).astype(np.int64)
    for i in range(1, cnt):
        if flagged[i]:
            date_dn[i] = date_dn[i - 1]
    dn_last = int(date_dn[-1])

    # 日期直接用通达信内部"日期序号"换算：这样
    #   期货：夜盘 bar 的 dn = 下一交易日（与 TDX 显示一致）；
    #   股票：dn = 日历日；
    # 都不再依赖"读取时刻"去猜交易日（旧逻辑在凌晨读取股票时会整体偏 3 天，
    # 导出的公式 DATE 对不上图上 K 线 -> 贴到通达信里严重错位）。
    dates = [TDX_DAY_EPOCH + dt.timedelta(days=int(dn)) for dn in date_dn]
    now_dt = now or dt.datetime.now()
    if not dates or not (
        dt.date(2005, 1, 1) <= dates[-1] <= now_dt.date() + dt.timedelta(days=7)
    ):
        # 兜底：日期序号异常时退回"按读取时刻推断最后一个交易日"的老办法
        anchor = infer_anchor_date(now)
        days_delta = date_dn - dn_last
        dates = [
            anchor + dt.timedelta(days=int(days_delta[i])) for i in range(cnt)
        ]
    anchor = dates[-1]

    o = rec["O"]
    hgh = rec["H"]
    low = rec["L"]
    close = rec["C"]
    vol = rec["V"]
    bars: list[Bar] = []
    for i in range(cnt):
        sec = labels[i]
        bars.append(
            Bar(
                date=dates[i],
                hour=sec // 3600,
                minute=(sec % 3600) // 60,
                second=sec % 60,
                open=float(o[i]),
                high=float(hgh[i]),
                low=float(low[i]),
                close=float(close[i]),
                volume=int(vol[i]),
                dn=int(date_dn[i]),
                flagged=bool(flagged[i]),
            )
        )
    meta = {
        "step": cand.step,
        "count": len(bars),
        "anchor": anchor,
        "addr": cand.addr,
        "dn_last": dn_last,
        "first": bars[0],
        "last": bars[-1],
    }
    return bars, meta


# ---------------------------------------------------------------------------
# 输出 TXT / 读取入口
# ---------------------------------------------------------------------------


def write_tdx_txt(path: str, bars: list[Bar], title: str = "") -> str:
    """按通达信导出格式写 TXT（GBK，行首空格，制表符分隔）。

    日线（全部 bar 的时分秒都是 0，或 meta['kind']=='daily'）写成纯日期 YYYY/MM/DD，
    与通达信导出的日线格式一致（TDX_TXT_API 会识别为日线）。
    """
    daily = bool(bars) and all(
        b.hour == 0 and b.minute == 0 and b.second == 0 for b in bars[:5]
    )
    with open(path, "w", encoding="gbk", newline="") as f:
        if title:
            f.write(title + "\r\n")
            f.write("\r\n")
        f.write("时间\t开盘\t最高\t最低\t收盘\t成交量\r\n")
        for b in bars:
            if daily:
                f.write(
                    " %04d/%02d/%02d\t%.2f\t%.2f\t%.2f\t%.2f\t%d\r\n"
                    % (b.date.year, b.date.month, b.date.day, b.open, b.high, b.low, b.close, b.volume)
                )
            else:
                f.write(
                    " %02d/%02d:%02d:%02d\t%.2f\t%.2f\t%.2f\t%.2f\t%d\r\n"
                    % (b.date.day, b.hour, b.minute, b.second, b.open, b.high, b.low, b.close, b.volume)
                )
    return path


def read_current_bars(
    install_key: str = "new_tdxqh",
    prefer_step: int | None = None,
    now: dt.datetime | None = None,
    log=None,
) -> tuple[list[Bar], dict]:
    """读取通达信当前图表 K 线（主入口）。"""
    pid, exe = find_tdx_process(install_key)
    if log:
        log(f"通达信进程 pid={pid} {exe}")
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        h = kernel32.OpenProcess(PROCESS_VM_READ, False, pid)
    if not h:
        raise RuntimeError(f"打开通达信进程失败（err={ctypes.get_last_error()}），可能需要同权限启动")
    try:
        cands, stats = scan_candidates(h, log=log)
        fresh = select_candidates(cands, prefer_step=prefer_step)
        # "当前图表"判据：通达信会把正在看的图表的 K 线数组挂在内部结构上（有指针引用），
        # 而之前看过、仍残留在内存里的其它品种/周期数组引用通常更少或没有。
        # 日线数组的引用常指向数组起点，秒级数组的引用有时指向起点前 4/36 字节，故偏移都算。
        # 排序规则：先"有引用"优先，再按根数（同品种多份拷贝取最长的那份），最后按时间。
        if len(fresh) > 1:
            try:
                offsets = (-36, -4, 0, 4)
                ref_addrs = []
                for c in fresh:
                    ref_addrs.extend(c.addr + d for d in offsets)
                refs = count_ptr_refs(h, sorted(set(ref_addrs)))
                for c in fresh:
                    c.ptr_hits = int(sum(refs.get(c.addr + d, 0) for d in offsets))
                fresh.sort(
                    key=lambda c: (-int(c.ptr_hits > 0), -c.count, -_cand_time_key(c))
                )
            except Exception as e:  # 指针统计失败不影响主流程
                if log:
                    log(f"指针引用统计失败（忽略）：{e}")
        chosen = fresh[0]
        if log:
            log(f"选中数据段：{chosen}")
            for c in fresh[1:6]:
                log(f"  其他候选：{c}")
        bars, meta = read_candidate_bars(h, chosen, now=now)
    finally:
        kernel32.CloseHandle(h)
    title = tdx_chart_symbol(pid)
    meta.update(
        {
            "pid": pid,
            "exe": exe,
            "symbol": title,
            "stats": stats,
            "candidates": fresh[:8],
        }
    )
    return bars, meta


def ref_begin_time(bars: list[Bar]) -> str:
    """给 TDX_TXT_API 用的 begin_time：最后一根 K 线的年月（解析器把 begin_date 当 ref_date）。"""
    last = bars[-1]
    return "%04d-%02d" % (last.date.year, last.date.month)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_chan(txt_path: str, begin_time: str) -> dict:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from Chan import CChan
    from ChanConfig import CChanConfig
    from Common.CEnum import KL_TYPE, AUTYPE

    conf = CChanConfig(
        {
            "bi_strict": False,
            "bi_fx_check": "loss",
            "bi_end_is_peak": False,
            "gap_as_kl": False,
            "bi_allow_sub_peak": True,
            "bi_algo": "normal",
            "trigger_step": False,
            "print_warning": False,
            "cal_bi_zs": False,
            "cal_bi_bsp": False,
        }
    )
    chan = CChan(
        code=txt_path,
        begin_time=begin_time,
        data_src="custom:TDX_TXT_API.TDX_TXT_API",
        lv_list=[KL_TYPE.K_1M],
        config=conf,
        autype=AUTYPE.NONE,
    )
    lv = chan[0]
    return {
        "KLC": len(lv.lst),
        "KLU": sum(len(k.lst) for k in lv.lst),
        "BI": len(lv.bi_list),
        "SEG": len(lv.seg_list),
        "first_time": lv.lst[0].lst[0].time.to_str(),
        "last_time": lv.lst[-1].lst[-1].time.to_str(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从通达信进程内存读取当前图表 K 线")
    ap.add_argument("--install", default="new_tdxqh", help="通达信安装路径关键字（默认期货通 new_tdxqh）")
    ap.add_argument("--step", type=int, default=None, help="期望周期步长（5=5秒, 10=10秒）；默认自动")
    ap.add_argument("--out", default="", help="输出 TXT 路径（默认写到临时目录）")
    ap.add_argument("--chan", action="store_true", help="读完后顺带跑一遍 chan.py 并打印结果")
    args = ap.parse_args(argv)

    def log(msg: str) -> None:
        print(msg, flush=True)

    bars, meta = read_current_bars(install_key=args.install, prefer_step=args.step, log=log)
    first, last = meta["first"], meta["last"]
    log(
        "解码完成：%d 根，step=%ds，时间 %s → %s，价格 %.2f~%.2f"
        % (
            len(bars),
            meta["step"],
            "%04d-%02d-%02d %02d:%02d:%02d"
            % (first.date.year, first.date.month, first.date.day, first.hour, first.minute, first.second),
            "%04d-%02d-%02d %02d:%02d:%02d"
            % (last.date.year, last.date.month, last.date.day, last.hour, last.minute, last.second),
            min(b.low for b in bars),
            max(b.high for b in bars),
        )
    )
    log("品种（窗口标题）：%s" % (meta["symbol"] or "未知"))

    if args.out:
        out = args.out
    else:
        out = os.path.join(os.environ.get("TEMP", "."), "tdx_mem_read.txt")
    write_tdx_txt(out, bars, title=meta["symbol"] or "")
    log("已写出 TXT：%s" % out)

    if args.chan:
        begin_time = ref_begin_time(bars)
        log("chan.py 解析 begin_time=%s ..." % begin_time)
        res = _run_chan(out, begin_time)
        log("chan.py 结果：KLC=%d KLU=%d BI=%d SEG=%d 时间 %s → %s" % (
            res["KLC"], res["KLU"], res["BI"], res["SEG"], res["first_time"], res["last_time"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
