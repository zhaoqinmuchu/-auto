# -*- coding: utf-8 -*-
"""用现有 GUI 配置在 AUL9 5 分钟数据上算笔/线段，生成"真实线段折线版"通达信公式。
目的：验证真实线段端点 → 单条 PLOYLINE（变量+分层求和）的格式，贴到 AUL9 5 分钟图应连成折线。
"""
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\q8369\Documents\ChatGPT\chan.py-main")
sys.path.insert(0, r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\pylibs")
sys.dont_write_bytecode = True

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

OUT = Path(r"C:\Users\q8369\Desktop")


def build(vertices, out_name, title):
    lines = [f"{{ {title} }}", "{ 真实线段端点 → 单条 PLOYLINE（变量版） }"]
    for i, (dt, price) in enumerate(vertices, 1):
        y, mo, d, hh, mm = dt
        date = 1000000 + (y % 100) * 10000 + mo * 100 + d
        lines.append(f"V{i}:=IF((DATE={date} AND TIME={hh * 100 + mm}),{price:.2f},0);")
    names = [f"V{i}" for i in range(1, len(vertices) + 1)]
    gnames = []
    for gi in range(0, len(names), 25):
        chunk = names[gi:gi + 25]
        gname = f"GG{len(gnames) + 1}"
        lines.append(f"{gname}:=" + "+".join(chunk) + ";")
        gnames.append(gname)
    lines.append("TOTV:=" + "+".join(gnames) + ";")
    lines.append("PLOYLINE(TOTV>0,TOTV),COLORYELLOW;")
    p = OUT / out_name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def main():
    conf = CChanConfig({
        "bi_strict": False,
        "bi_fx_check": "loss",
        "bi_end_is_peak": False,
        "trigger_step": False,
        "print_warning": False,
        "cal_bi_zs": False,
        "cal_bi_bsp": False,
    })
    chan = CChan(
        code=r"C:\Users\q8369\Desktop\AUL9.txt",
        begin_time="2026-10",
        data_src="custom:TDX_TXT_API.TDX_TXT_API",
        lv_list=[KL_TYPE.K_1M],
        config=conf,
        autype=AUTYPE.NONE,
    )
    kl = chan[0]
    segs = list(kl.seg_list)
    print(f"KLC={len(kl.lst)} BI={len(kl.bi_list)} SEG={len(segs)}")
    verts = []
    for i, seg in enumerate(segs):
        b = seg.start_bi.get_begin_klu()
        e = seg.end_bi.get_end_klu()
        bt, et = b.time, e.time
        bp, ep = seg.start_bi.get_begin_val(), seg.end_bi.get_end_val()
        print(f"seg{i:02d} {'UP' if seg.is_up() else 'DN'} sure={seg.is_sure} "
              f"{bt.to_str()} {bp} -> {et.to_str()} {ep}")
        if not verts:
            verts.append(((bt.year, bt.month, bt.day, bt.hour, bt.minute), bp))
        verts.append(((et.year, et.month, et.day, et.hour, et.minute), ep))
    # 去掉相邻重复顶点
    dedup = []
    for v in verts:
        if not dedup or dedup[-1] != v:
            dedup.append(v)
    print(f"vertices={len(dedup)}")
    p = build(dedup, "tdx_测试P_真实线段折线版_5分钟.txt", f"测试P：AUL9 真实线段折线版（{len(segs)} 段）")
    print("written", p, p.stat().st_size)


if __name__ == "__main__":
    main()
