import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE


def to_baostock_code(code):
    code = str(code).strip()
    if code.startswith('sh.') or code.startswith('sz.'):
        return code
    if code.startswith('6'):
        return f"sh.{code}"
    return f"sz.{code}"


config = CChanConfig({
    "bi_strict": True,
    "trigger_step": False,
    "skip_step": 0,
    "divergence_rate": float("inf"),
    "bsp2_follow_1": False,
    "bsp3_follow_1": False,
    "min_zs_cnt": 0,
    "bs1_peak": False,
    "macd_algo": "peak",
    "bs_type": '1,2,3a,1p,2s,3b',
    "print_warning": True,
    "zs_algo": "normal",
})

begin_time = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
end_time = datetime.now().strftime("%Y-%m-%d")

for code in ['000001', '600000']:
    try:
        chan = CChan(
            code=to_baostock_code(code),
            begin_time=begin_time,
            end_time=end_time,
            data_src=DATA_SRC.BAO_STOCK,
            lv_list=[KL_TYPE.K_DAY],
            config=config,
            autype=AUTYPE.QFQ,
        )
        print(f"[OK] {code} -> {to_baostock_code(code)}, kline count: {len(chan[0])}")
    except Exception as e:
        print(f"[FAIL] {code}: {e}")
