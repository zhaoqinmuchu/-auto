# 代码侧定位：大幅向上跳空之后画不出下降线段

> 数据：`C:\Users\q8369\Desktop\AUL9.txt`（AUL9，10 秒 K 线，4203 根 KLU / 2701 根合并 KLC / 341 笔）
> 配置：GUI 默认 + seg 默认（`seg_algo="chan"`，`ChanConfig.py:31-34`）：
> `{"trigger_step": False, "skip_step": 0, "divergence_rate": inf, "bsp2_follow_1": False, "bsp3_follow_1": False, "min_zs_cnt": 0, "bs1_peak": False, "macd_algo": "peak", "bs_type": "1,1p,2,2s,3a,3b", "print_warning": False, "zs_algo": "normal", "cal_bi_zs": False, "cal_bi_bsp": False, "bi_end_is_peak": False, "bi_strict": False, "bi_fx_check": "loss"}`
> 结论只读源码得出，未修改仓库任何 `.py`；复现脚本与原始输出在 `C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\`。

---

## 0. 结论摘要（先看这里）

1. **线段模块里的“缺口”不是 K 线跳空，而是「特征序列两个相邻元素之间无重叠」**（`Seg/Eigen.py:13-17`）。K 线跳空只进入**笔**的判定（`KLine/KLine.py:40-43`，全仓唯一调用点 `Bi/BiList.py:178`），`Seg/` 目录**没有任何** `has_gap_with_next` 调用。所以“向上跳空”本身不会、也不应该让线段模块进入“等确认”的分支。
2. **本例真正的原因是：跳空把最高点放在了上升线段特征序列的第一个元素上**。11/09 21:00 的 3.52 点向上跳空整体落在上涨笔 `bi326`（872.04→876.60）内部，跳空后的第一根下跌笔 `bi327` 起点就是 876.60（全段最高）。上升线段必须由“下跌笔特征序列的顶分型”终结，而顶分型要求中间元素 `ele[1].high > ele[0].high`；`bi327` 之后每一根下跌笔的起点都低于 876.60，于是 `treat_second_ele` 反复 `reset()`（`Seg/EigenFX.py:33-35`），**顶分型永远凑不出来**，`can_be_end` 连调用机会都没有（`Seg/EigenFX.py:83`）。上升线段不结束 ⇒ 后面的下跌走势只能算它的内部回撤 ⇒ 画不出下降线段。
3. **和原文一致**：这是“线段由特征序列分型终结 / 有缺口需第二特征序列分型确认”这条规则的直接推论，不是把跳空判错的 bug。真正需要向上解释的两点是实现口径：**(a)** 缺口口径是合并后特征元素的高低点（`Seg/Eigen.py:15-16`）；**(b)** 一旦特征序列顶/底分型出现，`actual_break_flag` 只置 `False` 从不复位（`Seg/EigenFX.py:22,137,146,155,158`，`clear()` `Seg/EigenFX.py:112-114` 也不复位），会让同一 `CEigenFX` 之后所有“无缺口分型”都返回 `None`（`Seg/EigenFX.py:93-96`），线段被长期判为“不确定”。
4. GUI 上看到的“跳空后一段升 + 一根下降笔”是**补漏虚段**，不是算法确认的线段：`seg43 UP bi326→338` 的 `reason=collectleft_find_high`（`Seg/SegListComm.py:73-89`）、`seg44 DOWN bi339→339` 的 `reason=collect_left_1`（`Seg/SegListComm.py:121-129`），两者 `is_sure=False`。

---

## 1. 复现实例（真实数据，唯一的大幅向上跳空）

### 1.1 跳空本身

扫描合并后 K 线之间/原始 K 线的跳空，全数据共 433 个 KLC 级跳空，最大且**唯一 >1 点**的向上跳空是跨周末那一根：

| 项目 | 值 |
| --- | --- |
| 原始 K 线 | `klu4044`（2026/11/06 15:00，high=872.18）→ `klu4045`（2026/11/09 21:00，low=875.70） |
| 跳空幅度 | **+3.52 点（+0.404%）**，全数据最大 |
| 后续 | 21:00 冲高到 **876.60**，随后一路回落到 874.28/874.36（约 -2.3 点），数据在 21:13 结束 |

第二、第三大跳空都是**向下**的（11/06 13:30 午休 -2.08 点、09:00 夜盘→日盘 -0.90 点），与本题无关。

### 1.2 跳空落在哪根笔里

```
bi326 UP   klu4038->4045   872.04->876.60   t=2026/11/06 14:59~2026/11/09 21:00   ← 跳空在这根笔内部
bi327 DOWN klu4045->4063   876.60->875.48   t=2026/11/09 21:00~21:01
bi328 UP   klu4063->4067   875.48->875.90
...
bi339 DOWN klu4187->4195   874.76->874.36   t=2026/11/09 21:11~21:12
bi340 UP   klu4195->4201   874.36->874.54   sure=False（数据到此为止）
```

### 1.3 跳空之后的线段输出（脚本实测）

```
seg41 dir=UP   bi300->322 870.90->872.46 sure=True  reason=normal
seg42 dir=DOWN bi323->325 872.46->872.04 sure=True  reason=normal   t=11/06 14:57~14:59
seg43 dir=UP   bi326->338 872.04->874.76 sure=False reason=collectleft_find_high
seg44 dir=DOWN bi339->339 874.76->874.36 sure=False reason=collect_left_1
```

* **最后一个 `is_sure=True` 的线段是 seg42（结束于 11/06 14:59）**，跳空之后（11/09 21:00 起）没有任何确定线段。
* seg43 / seg44 是 `collect_left_*` 补漏产生的**虚段**：seg43 的 872.04→874.76 与“跳空后下跌”方向相反，seg44 只有 1 根笔（`CSeg.__init__` 里 `if end_bi.idx - start_bi.idx < 2: self.is_sure = False`，`Seg/Seg.py:40-41`）。这就是用户看到的“跳空后画不出下降线段/线段画得怪”。

---

## 2. 线段模块的“缺口”到底是什么（代码口径）

### 2.1 K 线跳空不参与线段

`KLine/KLine.py:40-43`：

```python
def has_gap_with_next(self) -> bool:
    assert self.next is not None
    # 相同也算重叠，也就是没有gap
    return not has_overlap(self.get_klu_min_low(), self.get_klu_max_high(), self.next.get_klu_min_low(), self.next.get_klu_max_high(), equal=True)
```

全仓只有 `Bi/BiList.py:178` 调用它（笔的分型/成笔判定），`Seg/` 下无任何调用。

### 2.2 线段缺口 = 特征序列元素之间无重叠

`Seg/Eigen.py:13-17`：

```python
    def update_fx(self, _pre: Self, _next: Self, exclude_included=False, allow_top_equal=None):
        super(CEigen, self).update_fx(_pre, _next, exclude_included, allow_top_equal)
        if (self.fx == FX_TYPE.TOP and _pre.high < self.low) or \
           (self.fx == FX_TYPE.BOTTOM and _pre.low > self.high):
            self.gap = True
```

即：顶分型时“前一个特征元素 high < 中间元素 low”、底分型时“前一个特征元素 low > 中间元素 high”才算有缺口，`gap` 只挂在**特征序列元素**（`CEigen`，包装的是 `CBi`）上，与 K 线/笔之间有没有跳空无关。

### 2.3 只有 `ele[1].gap` 才走“第二种情况”

`Seg/EigenFX.py:82-96`（`can_be_end`）：

```python
    def can_be_end(self, bi_lst: CBiList, outer_dir=None, outer_thred_value=None):
        assert self.ele[1] is not None
        if self.ele[1].gap:
            ...
            return self.find_revert_fx(bi_lst, end_bi_idx+2, thred_value, break_thred, outer_dir, outer_thred_value)
        else:
            if not self.actual_break_flag:
                return None
            return True
```

* 无缺口 ⇒ 分型成立就 `return True`（线段可以结束）。
* 有缺口 ⇒ 交给 `find_revert_fx` 找**反向特征序列分型**确认（`Seg/EigenFX.py:162-194`），里面还有一条“创新高/新低优先”的破坏判定：

```python
            if (outer_dir == BI_DIR.UP and bi.is_up() and bi._high() > outer_thred_value) or \
               (outer_dir == BI_DIR.DOWN and bi.is_down() and bi._low() < outer_thred_value):
                return False
```

（`Seg/EigenFX.py:177-179`；`:184-193` 用 `egien_fx.add(bi)` 找反向分型，成功且 `actual_break_flag` 为真才 `return True`，否则 `None`。）

### 2.4 谁在收特征序列

`Seg/SegListChan.py:36-62`（`cal_seg_sure`）：

```python
        up_eigen = CEigenFX(BI_DIR.UP, lv=self.lv)  # 上升线段下降笔
        down_eigen = CEigenFX(BI_DIR.DOWN, lv=self.lv)  # 下降线段上升笔
        ...
            if bi.is_down() and last_seg_dir != BI_DIR.UP:
                if up_eigen.add(bi):
                    fx_eigen = up_eigen
            elif bi.is_up() and last_seg_dir != BI_DIR.DOWN:
                if down_eigen.add(bi):
                    fx_eigen = down_eigen
```

上升线段由**下跌笔**组成的特征序列判定，且只有当 `add()` 返回 `True`（已成顶分型）才会进 `treat_fx_eigen` → `can_be_end`（`Seg/SegListChan.py:60-62`、`:64-74`）。

---

## 3. 本例卡在哪一步（实测特征序列状态）

从“最后一个确定线段 seg42（结束笔 bi325）”之后开始，按 `cal_seg_sure` 的真实喂法（`last_seg_dir=DOWN`，只把下跌笔喂给 `up_eigen`，`Seg/SegListChan.py:42-44`）逐笔复算（脚本直接驱动 `CEigenFX(BI_DIR.UP)`，未改源码）：

| 下跌笔 | 起→止 | 喂入后 ele[0] | 是否成顶分型 |
| --- | --- | --- | --- |
| bi327 | 876.60→875.48 | `[bi327]` h=876.60 | 否 |
| bi329 | 875.90→875.14 | `[bi329]` h=875.90（876.60 被 reset 挤掉） | 否 |
| bi331 | 875.42→874.28 | `[bi331]` h=875.42 | 否 |
| bi333 | 875.16→874.66 | `[bi331,bi333]` h=875.42（合并） | 否 |
| bi335 | 874.92→874.50 | `[bi335]` h=874.92 | 否 |
| bi337 | 874.72→874.40 | `[bi337]` h=874.72 | 否 |
| bi339 | 874.76→874.36 | `[bi337]` + **`ele[1]=[bi339]` h=874.76** | 差第三元素，数据结束 |

对应代码 `Seg/EigenFX.py:28-36`（`treat_second_ele`）：

```python
        combine_dir = self.ele[0].try_add(bi, exclude_included=self.exclude_included)
        if combine_dir != KLINE_DIR.COMBINE:  # 不能合并
            self.ele[1] = CEigen(bi, self.kl_dir)
            if (self.is_up() and self.ele[1].high < self.ele[0].high) or \
               (self.is_down() and self.ele[1].low > self.ele[0].low):  # 前两元素不可能成为分形
                return self.reset()
```

* 机理：顶分型必须 `ele[1].high` 高于 `ele[0]`；而跳空把**最高点 876.60 固定在跳空后的第一根下跌笔 bi327 的起点**，后面所有下跌笔起点（875.90、875.42、875.16、874.92、874.72、874.76）都低于它，于是新元素一进就被判“前两元素不可能成为分型”而 `reset()`。
* 结果：`up_eigen.add(bi)` 一直到 bi339 才第一次出现 `ele[1]`；此时 `ele[1].gap`、`update_fx` 都还没执行（`update_fx` 在 `treat_third_ele` 里，`Seg/EigenFX.py:38-53`），`can_be_end` 的 `assert self.ele[1] is not None`（`:83`）从未被触发。
* 所以：**上升线段没有“结束”，`cal_seg_sure` 到数据末尾也没有 `add_new_seg`**。`CSegListChan.update` 随后调 `self.collect_left_seg(bi_lst)`（`Seg/SegListChan.py:34`）补漏 → `collect_segs`（`Seg/SegListComm.py:91-110`）→ `collect_left_seg_peak_method` 造出 `collectleft_find_high` 虚段（`:73-89`）→ `collect_left_as_seg` 造出 1 笔 `collect_left_1` 虚段（`:121-129`）。
* 反证（何时才画得出来）：只有当后续下跌笔的起点重新高于 874.76（`ele[1]`），再等到下一根下跌笔形成 `ele[2]`，顶分型才成立；按本例数据，需要价格先突破 876.60 附近的跳空高点区域，或特征序列以“更高的下跌笔起点”重新排列。数据止于 21:13，还差一个特征元素，所以下降线段还没到能画出来的时点。

---

## 4. 是否符合原文规则

**判断：本例的程序行为与原文一致（不是实现偏差导致的“漏画”）。**

* 原文规则：线段必须由特征序列分型终结；分型第一、二元素间有缺口时属于“第二种情况”，需第二个（反向）特征序列分型确认。代码正是这样实现的：`Seg/EigenFX.py:82-96` 分流、`:162-194` 做第二种情况确认。
* 本例跳空只是让**最高点出现在特征序列的第一个元素上**，使得“顶分型需要更高的一根下跌笔起点”这一条件迟迟不满足 —— 这是原文规则的直接推论，换成人工按原文划，同样不会在此处结束上升线段。

**但有两处实现口径/隐患应当告诉用户**（它们不会单独造成本例，但会让“跳空之后线段迟迟不定/画得怪”）：

1. **缺口口径是“合并后的特征元素高低点”**（`exclude_included=True` + `allow_top_equal`，`Seg/EigenFX.py:38-53`、`Seg/Eigen.py:13-17`；元素合并见 `Combiner/KLine_Combiner.py:84-107`）。用户直觉里的“K 线向上跳空”与代码里的 `gap` 不是同一件事，两者可能完全不对应：本数据 433 个 KLC 级跳空里，只有少量会在特征序列上形成 `gap=True`。
2. **`actual_break_flag` 只置位不复位**：`Seg/EigenFX.py:22` 初始 `True`，`:137/:146/:155/:158` 置 `False`；`clear()`（`:112-114`）只清 `ele/lst`，**不复位该标志**。后果是同一个 `CEigenFX` 一旦经历过一次“第三元素未实际突破”，之后所有**无缺口**分型都会走 `:93-96` 返回 `None` ⇒ `treat_fx_eigen` 走 `is_true=False` 分支（`Seg/SegListChan.py:67-74`），把线段标成 `is_sure=False` 且不再继续确认。这是“有跳空/未确认之后线段长期画不出来”的一个真实代码隐患（本例的卡点在更前面的 `ele[1]` 都凑不齐，故未触发它，但同类现象需排查这一条）。

---

## 5. 复现方式

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
$env:MPLCONFIGDIR="C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\mplcache"
cd C:\Users\q8369\Documents\ChatGPT\chan.py-main
.\.venv\Scripts\python.exe C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q\seg_last_gap_check.py
```

* `seg_last_gap_check.py`：载入 `CChan(code=AUL9 全路径, begin_time="2026-11", data_src="custom:TDX_TXT_API.TDX_TXT_API", lv_list=[KL_TYPE.K_1M], config=GUI默认, autype=AUTYPE.NONE)`，打印末尾线段 + 从 seg42 之后直接驱动 `CEigenFX(BI_DIR.UP)` 复算特征序列（第 3 节表格即其输出）。
* `seg_gap_probe.py` → `seg_gap_out.txt`：同一配置下导出全部 45 条线段、341 根笔、433 个 KLC 跳空、SEG 构建日志（`can_be_end` / `find_revert_fx` / `CEigen.update_fx` 记录）。

## 6. 关键代码行索引

| 位置 | 内容 |
| --- | --- |
| `Seg/Eigen.py:13-17` | 线段缺口判定（特征序列元素间无重叠才 `gap=True`） |
| `Seg/EigenFX.py:82-96` | `can_be_end`：有缺口走第二种情况，无缺口直接 `True` |
| `Seg/EigenFX.py:28-36` | `treat_second_ele`：`ele[1]` 未创新高/新低即 `reset`（本例的卡点） |
| `Seg/EigenFX.py:162-194` | `find_revert_fx`：第二种情况需反向特征序列分型；创新高/新低优先判 `False` |
| `Seg/EigenFX.py:112-114`, `:137/146/155/158` | `clear()` 不复位 `actual_break_flag` 的隐患 |
| `Seg/SegListChan.py:36-62` | `cal_seg_sure`：`up_eigen` 收下跌笔，`add()` 成顶分型才进 `treat_fx_eigen` |
| `Seg/SegListChan.py:64-74` | `treat_fx_eigen`：`can_be_end` 结果 → `add_new_seg(is_sure=…)` |
| `Seg/SegListChan.py:34` | `update` 末尾 `collect_left_seg` 补漏 |
| `Seg/SegListComm.py:73-89` | `collect_left_seg_peak_method` → `reason="collectleft_find_high"`（seg43 来源） |
| `Seg/SegListComm.py:121-129` | `collect_left_as_seg` → `reason="collect_left_1"`（seg44 来源） |
| `Seg/Seg.py:40-41` | 笔数 <2 强制 `is_sure=False` |
| `KLine/KLine.py:40-43`, `Bi/BiList.py:178` | K 线跳空只进笔判定，不进线段 |
