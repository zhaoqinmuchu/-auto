# -*- coding: utf-8 -*-
"""深入调试 find_revert_fx 中反向特征序列的处理"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Chan import CChan
from Common.CEnum import AUTYPE, KL_TYPE, BI_DIR
from ChanConfig import CChanConfig
from Seg.EigenFX import CEigenFX
from Common.func_util import revert_bi_dir

def main():
    file_path = r"C:\Users\q8369\Desktop\999999.txt"
    config = CChanConfig({
        "bi_strict": True,
        "bi_fx_check": "half",
        "trigger_step": False,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": "1,1p,2,2s,3a,3b",
        "print_warning": False,
        "zs_algo": "normal",
        "cal_bi_zs": False,
        "cal_bi_bsp": False,
    })
    chan = CChan(
        code=file_path,
        begin_time="2024-09",
        data_src="custom:TDX_TXT_API.TDX_TXT_API",
        lv_list=[KL_TYPE.K_1M],
        config=config,
        autype=AUTYPE.NONE,
    )
    kl_list = chan[0]
    bi_list = kl_list.bi_list

    # 打印 bi57 到 bi77 的详细信息
    print("=" * 100)
    print("bi57 到 bi77 的详细信息:")
    for bi in bi_list[57:78]:
        b = bi.begin_klc[0].time
        e = bi.end_klc[-1].time
        print(f"bi{bi.idx}: {bi.dir.name} | {b} ({bi.get_begin_val():.2f}) -> {e} ({bi.get_end_val():.2f}) | high={bi._high():.2f} low={bi._low():.2f}")

    # 手动模拟 find_revert_fx 中反向特征序列的处理
    # 顶分型: up_eigen ele=[58] [60,62] [64], 高点=2747.74 (bi59结束点)
    # find_revert_fx(bi_list, begin_idx=61, thred_value=2747.74, break_thred, outer_dir=UP, outer_thred_value=2747.74)
    print("=" * 100)
    print("模拟 find_revert_fx: begin_idx=61, outer_dir=UP, outer_thred_value=2747.74")
    begin_idx = 61
    outer_dir = BI_DIR.UP
    outer_thred_value = 2747.74
    first_bi_dir = bi_list[begin_idx].dir
    egien_fx = CEigenFX(revert_bi_dir(first_bi_dir), exclude_included=True, lv=KL_TYPE.K_1M)
    print(f"first_bi_dir={first_bi_dir.name}, egien_fx.dir={egien_fx.dir.name}")

    for bi in bi_list[begin_idx::2]:
        # 只处理反向分型，不因创新高中断（观察何时形成底分型）
        is_break = (outer_dir == BI_DIR.UP and bi.is_up() and bi._high() > outer_thred_value) or \
                   (outer_dir == BI_DIR.DOWN and bi.is_down() and bi._low() < outer_thred_value)
        print(f"\nbi{bi.idx}: {bi.dir.name} high={bi._high():.2f} low={bi._low():.2f} | 创新高破坏={is_break}")
        result = egien_fx.add(bi)
        ele_str = []
        for e in egien_fx.ele:
            if e is None:
                ele_str.append("None")
            else:
                ele_str.append(f"[{','.join(str(b.idx) for b in e.lst)}](h={e.high:.2f},l={e.low:.2f},fx={e.fx.name},gap={e.gap})")
        print(f"  add(bi{bi.idx}) -> {result} | ele={' '.join(ele_str)}")
        if result:
            print(f"  -> 反向特征序列出现分型!")
            if egien_fx.actual_break_flag:
                print(f"  -> actual_break_flag=True, 返回 True (确认顶分型)")
            else:
                print(f"  -> actual_break_flag=False, 返回 None")
            break

if __name__ == "__main__":
    main()
