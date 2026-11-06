"""Fingerprint local analyses without changing application code or contacting data services."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    sys.path.insert(0, str(root))
    from Chan import CChan
    from ChanConfig import CChanConfig
    from Common.CEnum import AUTYPE, KL_TYPE
    from DataAPI.TDX_TXT_API import TDX_TXT_API

    results = []
    for name in ("A111.txt", "CUL9.txt", "SCL9.txt"):
        sample = root / name
        if not sample.is_file():
            raise FileNotFoundError(f"Local sample missing: {sample}; restore it from the full snapshot")
        for strict in (False, True):
            config = CChanConfig({
                "bi_strict": strict, "bi_fx_check": "half", "trigger_step": False,
                "skip_step": 0, "divergence_rate": float("inf"), "bsp2_follow_1": False,
                "bsp3_follow_1": False, "min_zs_cnt": 0, "bs1_peak": False,
                "macd_algo": "peak", "bs_type": "1,1p,2,2s,3a,3b", "print_warning": False,
                "zs_algo": "normal", "cal_bi_zs": False, "cal_bi_bsp": False,
            })
            level = KL_TYPE.K_DAY if TDX_TXT_API(str(sample)).is_daily_data() else KL_TYPE.K_1M
            chan = CChan(code=str(sample), begin_time="2026-08", data_src="custom:TDX_TXT_API.TDX_TXT_API",
                         lv_list=[level], config=config, autype=AUTYPE.NONE)
            kl = chan[0]
            raw = list(kl.klu_iter())
            line = lambda item: [item.get_begin_klu().idx, item.get_end_klu().idx,
                                 item.get_begin_val(), item.get_end_val(), item.dir.name, item.is_sure]
            zone = lambda item: [item.begin.idx, item.end.idx, item.low, item.high, item.is_sure]
            point = lambda item: [item.klu.idx, item.is_buy, item.type2str(), item.bi.idx]
            payloads = {
                "raw_kline": [[k.idx, k.time.to_str(), k.open, k.high, k.low, k.close, k.trade_info.metric] for k in raw],
                "combined_kline": [[k.idx, k.high, k.low, k.dir.name, k.fx.name, [u.idx for u in k.lst]] for k in kl.lst],
                "bi": [line(b) for b in kl.bi_list], "seg": [line(s) for s in kl.seg_list],
                "zs": [zone(z) for z in kl.zs_list], "segzs": [zone(z) for z in kl.segzs_list],
                "bsp": [point(p) for p in kl.bs_point_lst.getSortedBspList()],
                "seg_bsp": [point(p) for p in kl.seg_bs_point_lst.getSortedBspList()],
            }
            results.append({"sample": name, "bi_strict": strict, "first_time": raw[0].time.to_str(),
                            "last_time": raw[-1].time.to_str(),
                            "elements": {key: {"count": len(value), "sha256": digest(value)} for key, value in payloads.items()}})
            print(f"PASS {name} strict={strict}: raw={len(raw)} bi={len(kl.bi_list)} seg={len(kl.seg_list)}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
