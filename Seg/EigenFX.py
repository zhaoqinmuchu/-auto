from typing import List, Optional

from Bi.Bi import CBi
from Bi.BiList import CBiList
from Common.CEnum import BI_DIR, FX_TYPE, KLINE_DIR, SEG_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import revert_bi_dir

from .Eigen import CEigen


class CEigenFX:
    def __init__(self, _dir: BI_DIR, exclude_included=True, lv=SEG_TYPE.BI):
        self.lv = lv
        self.dir = _dir  # 线段方向
        self.ele: List[Optional[CEigen]] = [None, None, None]
        self.lst: List[CBi] = []
        self.exclude_included = exclude_included
        self.kl_dir = KLINE_DIR.UP if _dir == BI_DIR.UP else KLINE_DIR.DOWN
        self.last_evidence_bi: Optional[CBi] = None
        self.last_evidence_bi_is_sure: bool = False
        self.actual_break_flag = True

    def treat_first_ele(self, bi: CBi) -> bool:
        self.ele[0] = CEigen(bi, self.kl_dir)
        return False

    def treat_second_ele(self, bi: CBi) -> bool:
        assert self.ele[0] is not None
        combine_dir = self.ele[0].try_add(bi, exclude_included=self.exclude_included)
        if combine_dir != KLINE_DIR.COMBINE:  # 不能合并
            self.ele[1] = CEigen(bi, self.kl_dir)
            if (self.is_up() and self.ele[1].high < self.ele[0].high) or \
               (self.is_down() and self.ele[1].low > self.ele[0].low):  # 前两元素不可能成为分形
                return self.reset()
        return False

    def treat_third_ele(self, bi: CBi) -> bool:
        assert self.ele[0] is not None
        assert self.ele[1] is not None
        self.last_evidence_bi = bi
        self.last_evidence_bi_is_sure = bi.is_used_to_be_sure
        allow_top_equal = (1 if bi.is_down() else -1) if self.exclude_included else None
        combine_dir = self.ele[1].try_add(bi, allow_top_equal=allow_top_equal)
        if combine_dir == KLINE_DIR.COMBINE:
            return False
        self.ele[2] = CEigen(bi, combine_dir)
        if not self.actual_break():
            return self.reset()
        self.ele[1].update_fx(self.ele[0], self.ele[2], exclude_included=self.exclude_included, allow_top_equal=allow_top_equal)  # type: ignore
        fx = self.ele[1].fx
        is_fx = (self.is_up() and fx == FX_TYPE.TOP) or (self.is_down() and fx == FX_TYPE.BOTTOM)
        return True if is_fx else self.reset()

    def add(self, bi: CBi) -> bool:  # 返回是否出现分形
        assert bi.dir != self.dir
        self.lst.append(bi)
        if self.ele[0] is None:  # 第一元素
            return self.treat_first_ele(bi)
        elif self.ele[1] is None:  # 第二元素
            return self.treat_second_ele(bi)
        elif self.ele[2] is None:  # 第三元素
            return self.treat_third_ele(bi)
        else:
            raise CChanException(f"特征序列3个都找齐了还没处理!! 当前笔:{bi.idx},当前:{str(self)}", ErrCode.SEG_EIGEN_ERR)

    def reset(self):
        bi_tmp_list = list(self.lst[1:])
        if self.exclude_included:
            self.clear()
            for bi in bi_tmp_list:
                if self.add(bi):
                    return True
        else:
            assert self.ele[1] is not None
            ele2_begin_idx = self.ele[1].lst[0].idx
            self.ele[0], self.ele[1], self.ele[2] = self.ele[1], self.ele[2], None
            self.lst = [bi for bi in bi_tmp_list if bi.idx >= ele2_begin_idx]  # 从第二元素开始

        return False

    def can_be_end(self, bi_lst: CBiList, outer_dir=None, outer_thred_value=None):
        assert self.ele[1] is not None
        if self.ele[1].gap:
            assert self.ele[0] is not None
            end_bi_idx = self.GetPeakBiIdx()
            thred_value = bi_lst[end_bi_idx].get_end_val()
            break_thred = self.ele[0].low if self.is_up() else self.ele[0].high
            if outer_dir is None:  # 最外层（原线段）的方向与顶分型高点/底分型低点
                outer_dir = self.dir
                outer_thred_value = thred_value
            return self.find_revert_fx(bi_lst, end_bi_idx+2, thred_value, break_thred, outer_dir, outer_thred_value)
        else:
            if not self.actual_break_flag:
                return None
            return True

    def is_down(self):
        return self.dir == BI_DIR.DOWN

    def is_up(self):
        return self.dir == BI_DIR.UP

    def GetPeakBiIdx(self):
        assert self.ele[1] is not None
        return self.ele[1].GetPeakBiIdx()

    def all_bi_is_sure(self):
        assert self.last_evidence_bi is not None
        return next((False for bi in self.lst if not bi.is_used_to_be_sure), True) and self.last_evidence_bi_is_sure

    def clear(self):
        self.ele = [None, None, None]
        self.lst = []

    def __str__(self):
        _t = [f"{[] if ele is None else ','.join([str(b.idx) for b in ele.lst])}" for ele in self.ele]
        return " | ".join(_t)

    def actual_break(self):
        if not self.exclude_included:
            return True
        assert self.ele[2] and self.ele[1]
        if (self.is_up() and self.ele[2].low < self.ele[1][-1]._low()) or \
           (self.is_down() and self.ele[2].high > self.ele[1][-1]._high()):  # 防止第二元素因为合并导致后面没有实际突破
            return True
        assert len(self.ele[2]) == 1
        ele2_bi = self.ele[2][0]
        if ele2_bi.next and ele2_bi.next.next:
            if ele2_bi.is_down():
                if ele2_bi.next.next._low() < ele2_bi._low():
                    self.last_evidence_bi = ele2_bi.next.next
                    self.last_evidence_bi_is_sure = ele2_bi.next.next.is_used_to_be_sure
                    return True
                else:
                    if not ele2_bi.next.next.is_used_to_be_sure or ele2_bi.next.next.next is None:
                        self.actual_break_flag = False
                        return True
            elif ele2_bi.is_up():
                if ele2_bi.next.next._high() > ele2_bi._high():
                    self.last_evidence_bi = ele2_bi.next.next
                    self.last_evidence_bi_is_sure = ele2_bi.next.next.is_used_to_be_sure
                    return True
                else:
                    if not ele2_bi.next.next.is_used_to_be_sure or ele2_bi.next.next.next is None:
                        self.actual_break_flag = False
                        return True
        else:
            if ele2_bi.next:
                if self.is_up() and ele2_bi.next._high() > self.ele[1].high:
                    ...
                elif self.is_down() and ele2_bi.next._low() < self.ele[1].low:
                    ...
                else:
                    self.actual_break_flag = False
                    return True
            else:
                self.actual_break_flag = False
                return True
        return False

    def find_revert_fx(self, bi_list: CBiList, begin_idx: int, thred_value: float, break_thred: float, outer_dir=None, outer_thred_value=None):
        COMMON_COMBINE = False  # 是否用普通分形合并规则处理
        # 如果返回None，表示找到最后了
        if outer_dir is None:  # 最外层（原线段）的方向与顶分型高点/底分型低点
            outer_dir = self.dir
            outer_thred_value = thred_value
        first_bi_dir = bi_list[begin_idx].dir  # down则是要找顶分型
        egien_fx = CEigenFX(revert_bi_dir(first_bi_dir), exclude_included=not COMMON_COMBINE, lv=self.lv)  # 顶分型的话要找上升线段
        for bi in bi_list[begin_idx::2]:
            # 先进行创新高/新低破坏检测（缠论第二种情况）：
            # 反向特征序列中出现与最外层同向的笔突破最外层顶分型高点/底分型低点，
            # 说明原线段延续，待定顶分型/底分型作废。
            # 注意：必须先于反向分型检测。因为同一根笔既可能确认反向分型、又同时创新高/新低
            # （如本例：bi39 既作为反向底分型的第三元素确认底分型，又突破顶分型高点创新高）。
            # 此时创新高/新低优先——一旦突破，原线段延续，待定分型作废，走势按原线段方向处理。
            if (outer_dir == BI_DIR.UP and bi.is_up() and bi._high() > outer_thred_value) or \
               (outer_dir == BI_DIR.DOWN and bi.is_down() and bi._low() < outer_thred_value):
                return False
            # 反向特征序列尚未被创新高/新低破坏时，才检查反向特征序列是否出现分型：
            # 一旦反向标准特征序列出现分型（无论该分型第一、第二元素间是否有缺口），
            # 即确认原线段在先前顶分型/底分型处结束（缠论第二种情况）。
            # 反向分型自身的缺口不影响对原线段的确认。
            if egien_fx.add(bi):
                if COMMON_COMBINE:
                    return True
                assert egien_fx.ele[2]
                self.last_evidence_bi = egien_fx.ele[2].lst[-1]
                if egien_fx.actual_break_flag:
                    self.last_evidence_bi_is_sure = self.last_evidence_bi.is_used_to_be_sure and egien_fx.last_evidence_bi_is_sure
                    return True
                else:
                    return None
        return None
