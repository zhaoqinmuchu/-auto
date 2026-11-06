# 本程序「画笔」实现规格说明（纯代码事实）

- 仓库：`C:\Users\q8369\Documents\ChatGPT\chan.py-main`（缠论 chan.py 派生版 ChanScanner）
- 代码版本：工作区 `git status` 相对 HEAD 干净（仅未跟踪的 `.probe/ .pylibs/ .tmp/ yuanwen/ sandbox_probe.txt`）；`Bi/BiList.py`、`KLine/KLine.py`、`KLine/KLine_List.py`、`Combiner/KLine_Combiner.py` 均在提交 `33ea607 chore: archive existing ChanScanner source baseline` 中，与 HEAD 无 diff。
- 取证方式：**只做静态阅读（read/grep）**，未运行缠论计算；对比过 `dist/razor-candidate/ChanScanner/_internal/` 下打包副本与源码的 SHA256（`Bi/BiList.py`、`KLine/KLine.py`、`Bi/Bi.py` 三个文件完全一致），故用户运行的候选 EXE 与源码是同一套画笔逻辑。
- 说明：本文只记录**代码实际做了什么**，不判定是否符合缠论原文；最后一节把「代码里有哪些约束 / 没有哪些约束」列全，供 Lead 与原文对照。
- 术语：**KLU** = 原始 K 线（`CKLine_Unit`）；**KLC** = 合并后 K 线（`CKLine`）；**fx** = 分型类型 `FX_TYPE.BOTTOM/TOP/UNKNOWN`；**span** = 两个 KLC 的 `idx` 差。

---

## 1. 问题1：K 线包含合并（合并K线）怎么做的

### 1.1 合并的数据结构

- 每个级别各建一个 `CKLine_List`：`Chan.py:85-88`（`do_init` 按 `lv_list` 逐级别 `CKLine_List(...)`），`KLine/KLine_List.py:35-52`。
- 合并K线 `CKLine` 继承 `CKLine_Combiner[CKLine_Unit]`：`KLine/KLine.py:8-14`；`CKLine_Combiner.__init__` 保存 `time_begin/time_end/high/low/lst/dir/fx/pre/next`，其中 `lst` 是参与合并的原始 KLU 列表：`Combiner/KLine_Combiner.py:13-26`。
- 合并K线在列表中的序号就是 `KLC.idx`（`KLine/KLine.py:12`，`KLine_List.py:127,131`），后文 span 全部按它计算。

### 1.2 合并判定规则（只比较 high/low）

`CCombine_Item` 对原始 K 线只取 `high/low/time`：`Combiner/Combine_Item.py:14-18`；对已合并K线同样是 `high/low`。`CKLine_Combiner.test_combine`（`Combiner/KLine_Combiner.py:64-78`）按上一根KLC `self` 与当前原始K线 `item` 比较：

1. `self.high >= item.high and self.low <= item.low` → `KLINE_DIR.COMBINE`（当前K线被上一根合并K线包含）：`KLine_Combiner.py:65-66`；
2. `self.high <= item.high and self.low >= item.low` → 当前K线包含上一根：普通 K 线路径因 `exclude_included=False` 返回 `KLINE_DIR.COMBINE`（`allow_top_equal` 只用于线段特征序列，普通 K 线调用不传）：`KLine_Combiner.py:67-72`；`try_add` 被 `KLine_List.py:129` 调用时未传 `exclude_included/allow_top_equal`，两个参数取默认 `False/None`：`KLine_Combiner.py:84`；
3. `self.high > item.high and self.low > item.low` → `KLINE_DIR.DOWN`：`KLine_Combiner.py:73-74`；
4. `self.high < item.high and self.low < item.low` → `KLINE_DIR.UP`：`KLine_Combiner.py:75-76`；
5. 其余抛 `CChanException("combine type unknown")`：`KLine_Combiner.py:77-78`。

等号情形全部落入前两分支，因此默认路径下"高点相等/低点相等"也会被合并（不存在高或低恰好相等的两根相邻合并K线；一字K线例外见 1.3 的 `95/99` 行）。

### 1.3 合并后的 high/low 更新方向（重要）

`CKLine_Combiner.try_add`（`Combiner/KLine_Combiner.py:84-107`）：

- 若判定为 `COMBINE`：把原始 K 线追加进 `lst`（`:91`），设 `klu.klc`（`:92-93`），然后按**本合并K线自身的 `dir`** 更新高低点：
  - `dir == UP`：`high = max(high, item.high)`，`low = max(low, item.low)`（`:94-97`）；
  - `dir == DOWN`：`high = min(high, item.high)`，`low = min(low, item.low)`（`:98-101`）；
  - 一字K线特判：`high==low` 且与当前 high/low 相同的极端一字板不参与更新（`:95,99`）；
  - 其他 dir 抛异常（`:102-103`）。
- 更新时间 `time_end`（`:104`），返回 `_dir` 给 `KLine_List` 用于新建 KLC 的 dir（`KLine_List.py:129-131`）。

**关键代码事实**：合并K线的 `high/low` 不是"该组原始 K 线的真实最高/最低"：

- `dir == UP` 的 KLC：`high = 原始最高`，`low = 原始低点中的最大值`（不是最低）；
- `dir == DOWN` 的 KLC：`low = 原始最低`，`high = 原始高点中的最小值`（不是最高）。

若需要原始极值，代码另有 `get_klu_max_high`/`get_klu_min_low`（`KLine/KLine.py:34-38`）。这一区别直接影响第 3.3/6 节"用哪套价格做比较"。

### 1.4 触发方式与边界

- 每根新原始 K 线进入 `CKLine_List.add_single_klu(klu)`：`KLine/KLine_List.py:124-137`。若被合并（`_dir == COMBINE`），**不新增** KLC、不计算分型、不驱动笔（非 step 模式下什么都不做，`:130-137`）。
- 若产生新 KLC：`self.lst.append(CKLine(klu, idx=len(self.lst), _dir=_dir))`（`:131`），随后只对 **`lst[-2]`** 计算分型（`:133`），再驱动笔（`:134`）。
- 合并只与"当前最后一根合并K线"比较、单遍增量，**不回溯修改**已有 KLC；合并与笔/线段无关，不因笔端点而重置，也不跨级别（每级别独立 `CKLine_List`）。
- 第一根 K 线的 KLC 用默认 `dir=UP` 构造（`KLine_List.py:127` + `KLine/KLine.py:10` 默认参数），只有后续合并才会用到它的 dir。

---

## 2. 问题2：顶/底分型的判定（合并K线还是原始K线、何时确认）

### 2.1 先澄清函数名

仓库中**没有** `check_fx` 函数。与"分型"有关的实际是两处：

- 分型的**计算**：`CKLine_Combiner.update_fx(pre, next, ...)`：`Combiner/KLine_Combiner.py:127-145`；
- 分型的**配对校验**（两个分型能否组成一笔，见第 3.3 节）：`CKLine.check_fx_valid(item2, method, for_virtual)`：`KLine/KLine.py:45-97`。

### 2.2 分型用「合并后 K 线」判定

`update_fx` 使用三根**连续合并K线** `pre/self/next`（`KLine_Combiner.py:141-144`），普通 K 线路径（`exclude_included=False`）的条件是四个严格不等式：

```
TOP   : pre.high < self.high and next.high < self.high
        and pre.low  < self.low  and next.low  < self.low
BOTTOM: pre.high > self.high and next.high > self.high
        and pre.low  > self.low  and next.low  > self.low
```

来源：`KLine_Combiner.py:141-144`。即标准定义"顶分型 = 三根中高点最高且低点最高"，底分型相反；不需要第 4 根 K 线。

注意：这里比较的是合并K线的 `high/low`（1.3 所述调整值），不是原始 K 线极值。

### 2.3 分型确认时机（必须等下一根合并K线）

- `KLine_List.add_single_klu` 在新建 KLC 后只执行 `self.lst[-2].update_fx(self.lst[-3], self.lst[-1])`：`KLine_List.py:132-133`。也就是说，KLC `i` 的分型要等 KLC `i+1` 出现才被计算，且**只计算一次、之后不重算、不撤销**。
- 边界：`lst[0]` 永远没有分型（缺左侧）；最后一根 KLC 也永远没有分型（缺右侧，保持 `FX_TYPE.UNKNOWN`，初值见 `KLine_Combiner.py:24`）。
- 传给笔模块的永远是 `klc = lst[-2]`、`last_klc = lst[-1]`（`KLine_List.py:134`），所以**"确定笔"的右端点最多只能落在倒数第二根合并K线上**；最后一根 KLC 只能用于"虚笔"（第 5 节）。
- 笔模块只读取 `klc.fx`（`Bi/BiList.py:91,95`）以及虚笔路径下的 `klc.dir`（`BiList.py:194-204`）；`check_fx` 一类重算不存在。

---

## 3. 问题3：笔的建立（span、分型校验、结束点极值、缺口、bi_algo）

### 3.1 成笔总入口与判定顺序

`CBiList.can_make_bi(klc, last_end, for_virtual=False)`：`Bi/BiList.py:183-191`，三步**短路**判断：

1. `satisify_span = True if config.bi_algo == 'fx' else satisfy_bi_span(klc, last_end)`，不满足返回 `False`：`BiList.py:184-186`；
2. `last_end.check_fx_valid(klc, config.bi_fx_check, for_virtual)`，不满足返回 `False`：`BiList.py:187-188`；
3. `config.bi_end_is_peak and not end_is_peak(last_end, klc)` → `False`：`BiList.py:189-190`；
4. 全通过才返回 `True`：`BiList.py:191`。

笔的真正维护在 `CBiList.update_bi_sure(klc)`：`BiList.py:86-103`（每来一根新合并K线、且 `klc` 已是"倒数第二根"时调用，见第 8 节）：

- `klc.fx == UNKNOWN` → 不产生确定笔，只返回"虚笔端点是否变化"：`BiList.py:91-92`；
- 还没有任何笔 → `try_create_first_bi(klc)`：`BiList.py:93-94`；
- `klc.fx == last_end.fx`（同向分型）→ `try_update_end(klc)`，即把**末笔的终点**延伸到 `klc`：`BiList.py:95-96,193-215`；
- `klc.fx` 反向且 `can_make_bi` 通过 → `add_new_bi(last_end, klc)`，新笔起点就是上一笔终点（共用同一个 KLC）：`BiList.py:97-100,143-147`；
- 否则尝试 `update_peak(klc)`（仅 `bi_allow_sub_peak=False` 时可能生效，见 3.4）：`BiList.py:101-102`。

顶底交替由以下事实保证：新建笔只在 `klc.fx != last_end.fx` 分支执行（`BiList.py:95-100`）；`check_fx_valid` 对非虚笔断言 `item2.fx` 与 `self.fx` 相反（`KLine/KLine.py:51,74`）；`CBi.set` 由起点 KLC 的分型决定方向，起点不是分型直接抛异常（`Bi/Bi.py:104-109`）。

### 3.2 最少 K 线数：`satisfy_bi_span`（两种口径）

`satisfy_bi_span(klc, last_end)`：`Bi/BiList.py:149-168`；span 由 `get_klc_span` 计算：`BiList.py:170-181`。

`get_klc_span` 基本式：`span = klc.idx - last_end.idx`（`BiList.py:171`）。**`idx` 是合并K线的序号，所以 span 计的是合并K线，不是原始K线**；差值为 `d` 表示两端 KLC 之间夹 `d-1` 根，含两端共 `d+1` 根合并K线。

**(a) `is_strict=True`（代码默认；老笔口径）**

```python
return bi_span >= 4      # BiList.py:151-152
```

- 阈值 4：两个分型中心 KLC 的索引差 ≥4，即含两端至少 **5 根合并K线**。
- 两组三元素分型（顶组 `[i-1,i,i+1]`、底组 `[j-1,j,j+1]`，`j-i>=4`）之间至少夹 **1 根独立合并K线**（`i+2..j-2` 非空）。
- 该口径只数合并K线；但因为 5 根合并K线每根至少含 1 根原始K线，**隐含区间内原始K线 ≥5 根**。
- 若 `gap_as_kl=True`，span 还会按缺口数 +1（见第 6 节，仅此分支生效）。

**(b) `is_strict=False`（GUI 实际使用；新笔口径）**

```python
if klc.idx - last_end.idx < 3: return False          # BiList.py:157-158
uint_kl_cnt = 0
tmp_klc = last_end
while tmp_klc:
    uint_kl_cnt += len(tmp_klc.lst)                  # 原始K线根数
    if tmp_klc.idx >= klc.idx: break
    if not tmp_klc.next: return False
    tmp_klc = tmp_klc.next
return uint_kl_cnt >= 5                              # BiList.py:159-168
```

- 条件一：合并K线索引差 ≥3 → 含两端至少 **4 根合并K线**；两组三元素分型**不共用**合并K线（底组 `[i-1,i,i+1]`、顶组 `[i+2,i+3,i+4]`，恰好相邻、不重叠）。
- 条件二：从 `last_end` 到 `klc`（含两端 KLC 内**全部**原始 K 线，`len(tmp_klc.lst)`）原始 K 线总数 ≥5：`BiList.py:159-168`。注释原文："2. 原始K线 >= 5（含顶分型的顶那根和底分型的底那根）"：`BiList.py:153-156`。
- **因此新笔并非"4 根K线成笔"**：最小形态是 4 根合并K线且其中至少 1 根由 ≥2 根原始K线合并，或合并K线本身 ≥5 根。任何模式下区间内原始 K 线都 ≥5 根。

汇总：本程序两种模式"最少K线"的实际口径是

| 配置 | 合并K线（含两端） | 两组分型是否共用合并K线 | 原始K线（含两端KLC内全部） |
|---|---|---|---|
| `is_strict=True`（默认） | ≥5 根（idx 差≥4） | 不共用，且至少隔 1 根独立合并K线 | ≥5（由合并K线数隐含，不单独检查） |
| `is_strict=False`（GUI） | ≥4 根（idx 差≥3） | 不共用（两组相邻） | ≥5（显式检查） |

### 3.3 分型有效性校验：`check_fx_valid`（程序自加的过滤条件，与"最少K线数"相互独立）

`CKLine.check_fx_valid(item2, method, for_virtual=False)`：`KLine/KLine.py:45-97`。它拿"本笔起点 KLC（`self`）"和"候选终点 KLC（`item2`）"各自**附近 1~3 根合并K线的价格区间**做比较，判断这两个分型的价格结构是否允许成笔。**这不是笔的最少K线数规则，也不影响 span 判定；它是 span 之外的第二道过滤。**

前置断言：`self.next`、`item2.pre`、`self.pre` 非空，且 `item2.idx > self.idx`：`KLine/KLine.py:47-49`。

#### 3.3.1 四种方法在"上升笔"（起点=底分型 B，终点=顶分型 T）下的条件

BOTTOM 分支：`KLine/KLine.py:73-95`。

| method | 终点侧（顶分型）取价 | 起点侧（底分型）取价 | 通过条件 | 行号 |
|---|---|---|---|---|
| HALF | `item2_low = min(T.pre.low, T.low)` | `cur_high = max(B.high, B.next.high)` | `B.low < item2_low 且 T.high > cur_high` | `KLine.py:77-79,95` |
| LOSS | `item2_low = T.low` | `cur_high = B.high` | 同上 | `KLine.py:80-82,95` |
| STRICT | `item2_low = min(T.pre.low, T.low, T.next.low)`（非虚笔要求 `T.next` 存在） | `cur_high = max(B.pre.high, B.high, B.next.high)` | 同上 | `KLine.py:83-89,95` |
| TOTALLY | `item2_low = min(T.pre.low, T.low, T.next.low)`（同上） | 不使用 `cur_high` | `B.high < item2_low` | `KLine.py:83-89,92-93` |

#### 3.3.2 四种方法在"下降笔"（起点=顶分型 T，终点=底分型 B）下的条件

TOP 分支：`KLine/KLine.py:50-72`。

| method | 终点侧（底分型）取价 | 起点侧（顶分型）取价 | 通过条件 | 行号 |
|---|---|---|---|---|
| HALF | `item2_high = max(B.pre.high, B.high)` | `self_low = min(T.low, T.next.low)` | `T.high > item2_high 且 B.low < self_low` | `KLine.py:54-56,72` |
| LOSS | `item2_high = B.high` | `self_low = T.low` | 同上 | `KLine.py:57-59,72` |
| STRICT | `item2_high = max(B.pre.high, B.high, B.next.high)`（非虚笔要求 `B.next` 存在） | `self_low = min(T.pre.low, T.low, T.next.low)` | 同上 | `KLine.py:60-66,72` |
| TOTALLY | `item2_high = max(B.pre.high, B.high, B.next.high)` | 不使用 `self_low` | `T.low > item2_high` | `KLine.py:60-66,69-70` |

- 其余情况（`self.fx` 既非 TOP 也非 BOTTOM）抛 `CChanException("only top/bottom fx can check_valid_top_button")`：`KLine.py:96-97`；method 非法抛 `"bi_fx_check config error!"`：`KLine.py:67-68,90-91`。
- 虚笔（`for_virtual=True`）时终点 KLC 还没有 fx，用 `item2.dir` 代替：向上笔要求 `item2.dir == DOWN`（`KLine.py:52-53`），向下笔要求 `item2.dir == UP`（`KLine.py:75-76`）；且 `STRICT/TOTALLY` 的终点侧因没有 `item2.next` 而退化为"前两元素"：`KLine.py:61-62,84-85`。

#### 3.3.3 四种方法的关系与 HALF 具体放宽/收紧了什么

由分型性质可得（顶分型满足 `T.next.low < T.low`、底分型满足 `B.pre.high > B.high`）：

- **LOSS ⊆ HALF ⊆ STRICT**（接受集包含关系）。逐项比较：HALF 的终点侧取价与起点侧取价都比 LOSS 更极端（条件更强），而 STRICT 又比 HALF 多纳入了"外侧"那一根：
  - 上升笔：STRICT 比 HALF 多查 `T.next.low`（更低）和 `B.pre.high`（更高）→ 条件更强；
  - 下降笔：STRICT 比 HALF 多查 `B.next.high`（更高）和 `T.pre.low`（更低）→ 条件更强。
- **TOTALLY 不与上述三者构成包含链**，它是另一条判据：不比较两端极值大小，而要求"起点分型 KLC 的（内侧方向）极值 < 终点侧三元素的最低点"（上升笔）或"起点分型 KLC 的极值 > 终点侧三元素的最高点"（下降笔），即两组区间**完全分离、不重叠**：`KLine.py:69-70,92-93`。
- HALF 的取舍：它只查两个分型**朝内**的 2 根合并K线（顶分型取 `{T.pre, T}`、底分型取 `{B, B.next}`），**不查顶分型左侧一根 `T.pre` 之外的外侧 KLC、也不查底分型右侧一根 `B.next` 之外的外侧 KLC**；LOSS 只查分型 KLC 自身 1 根；STRICT 连外侧一根也查。
- **HALF 下"笔与笔之间价格区间重叠"的机制**：因为外侧一根被排除，下面两种结构可以通过 HALF、但会被 STRICT 拒绝：
  1. 下降笔 `T→B` 成立，而终点底分型 KLC 的右侧一根 `B.next` 的高点已经**高于本笔起点 T 的高点**（HALF 只要求 `T.high > max(B.pre.high, B.high)`，不比较 `B.next.high`）→ 紧接着的上升笔从 `B` 起来，价格区间已经"盖过"前一笔的顶；
  2. 上升笔 `B→T` 成立，而起点底分型 KLC 的左侧一根 `B.pre` 的高点**高于本笔终点 T 的高点**（HALF 不把 `B.pre.high` 计入 `cur_high`）→ 本笔的顶低于上一笔尾部区域的高点，相邻两笔区间重叠。
  （这是代码层面的可成立空间；实际行情中是否常见需要数据验证，本报告未跑数据。）
- 这些方法比较的是**合并K线的 `high/low`**（接受合并方向调整后的值），不是原始 K 线极值；与第 6 节缺口判定使用的原始极值不同。
- 与 README 对照：`README.md:468` 的 strict 描述、`:471` 的 half 描述、`:470` 的 loss 描述与代码一致；`README.md:469` 的 totally 描述（"底分型3元素的最高点…"）比代码**多**取了"底分型3元素最高点"——代码上升笔只用起点 KLC 自身 `B.high`（`KLine.py:92-93`），下降笔同理只用 `T.low`（`KLine.py:69-70`）。
- GUI 固定用 HALF（见第 7 节），代码注释称"HALF 更符合缠论原文，避免 strict 过度过滤"：`App/ashare_bsp_scanner_gui.py:431`。

### 3.4 `bi_end_is_peak`（笔的尾部是否是整笔最低/最高）

- 配置默认 `True`：`ChanConfig.py:28`（`CBiConfig` 构造器默认也是 `True`：`Bi/BiConfig.py:12`）。GUI 未覆盖 → 生效 `True`。
- 生效点：`can_make_bi` 最后一步 `if self.config.bi_end_is_peak and not end_is_peak(last_end, klc): return False`：`BiList.py:189-190`。
- 实现 `end_is_peak(last_end, cur_end)`：`BiList.py:221-240`。
  - 起点是底分型（上升笔）：阈值 `cmp_thred = cur_end.high`，从 `last_end.next` 一直走到 `cur_end` 之前，任一 KLC `high > cur_end.high` 即 `False`：`BiList.py:222-230`；
  - 起点是顶分型（下降笔）：阈值 `cmp_thred = cur_end.low`，任一 KLC `low < cur_end.low` 即 `False`：`BiList.py:231-239`；
  - 代码注释指出可用更精确的 `get_klu_max_high()` / `get_klu_min_low()`，实际未用（`BiList.py:223,232`）。
- 结论（代码事实）：只校验**笔的终点**在"起点→终点"区间内是极值；**没有校验起点是本笔极值**。起点极值只在上一笔作为终点时被 `end_is_peak` 检查过（只覆盖上一笔区间）。因此从代码看，不存在"笔内任一根K线不得越过起点极值"的硬约束；理论边界未实测。
- 与原文/README："笔的尾部是否是整笔中最低/最高, 默认为 True"：`README.md:466`，与代码语义一致（只讲尾部）。

### 3.5 `bi_allow_sub_peak`（是否允许次高点成笔）

- 配置默认 `True`：`ChanConfig.py:29`、`Bi/BiConfig.py:13`；GUI 未覆盖 → 生效 `True`。
- `can_update_peak(klc)` 第一行：`if self.config.bi_allow_sub_peak or len(self.bi_list) < 2: return False`：`BiList.py:58-60`。所以 **`bi_allow_sub_peak=True` 时 `update_peak` 永远不会执行**，不会"删除末笔、把前一笔端点回退重锚到 klc"。
- `bi_allow_sub_peak=False` 时，在 `klc.fx` 反向但 `can_make_bi` 失败的情况下，满足以下 5 条才会回退修正（`BiList.py:61-70`）：
  1. 末笔向下且 `klc.high < 末笔起点值` → 不修正（`61-62`）；
  2. 末笔向上且 `klc.low > 末笔起点值` → 不修正（`63-64`）；
  3. `end_is_peak(bi_list[-2].begin_klc, klc)` 不成立 → 不修正（`65-66`）；
  4. 末笔向下且末笔终点值 `< 前一笔起点值` → 不修正（`67-68`）；
  5. 末笔向上且末笔终点值 `> 前一笔起点值` → 不修正（`69-70`）。
- `update_peak` 动作：`pop` 掉末笔 → `try_update_end(klc)` 尝试把（此时）末笔延伸到 `klc`，失败则恢复；虚笔路径下还会把被删末笔的终点记入 `sure_end`：`BiList.py:73-84`。
- 语义（按代码推导）：`False` 用于"要求笔端点必须是真极值的严格处理"：如果最后一笔没有走出比前一笔更高的高/更低的低，则删掉它、把前一笔延长到新的极值；`True`（默认/GUI）保留"次高点也成笔"的笔，不做这种回退。
- 说明：`BI_TYPE.SUB_VALUE`（次高低点成笔）枚举虽有定义（`Common/CEnum.py:52`），但全仓**从未被赋值**（见 4.3），所以该开关不会在 `CBi.type` 上留下标记。

### 3.6 `gap_as_kl`（缺口处理）——详见第 6 节

- 配置默认 `False`：`ChanConfig.py:27`；`CBiConfig` 构造器默认 `True`（`Bi/BiConfig.py:11`），但 `CChanConfig` 永远显式传参（`ChanConfig.py:23-30`），所以库层面默认是 `False`。GUI 未覆盖 → 生效 `False`。
- 仅影响 `get_klc_span`（`BiList.py:170-181`），且只对 `is_strict=True` 分支有意义：非 strict 分支在第 150 行算出 `bi_span` 后**并未使用**（`BiList.py:150` 对 `157-168`）。GUI 下 `gap_as_kl=False` 且 `is_strict=False`，**该参数对 GUI 的画笔完全无影响**。

### 3.7 `bi_algo` 对画笔的影响

- 唯一使用点：`BiList.py:184`：`satisify_span = True if self.config.bi_algo == 'fx' else self.satisfy_bi_span(klc, last_end)`。
  - `'fx'`：**跳过最少K线数检查**（span 约束失效），但仍要过 `check_fx_valid` 和 `end_is_peak`：`BiList.py:183-191`；
  - 其它任意字符串（含 `'normal'`、拼写错误）：一律按 `normal` 走 `satisfy_bi_span`。
- `CBiConfig` 对 `bi_algo` 不做合法性校验，直接保存：`Bi/BiConfig.py:15`；README 只声明 `normal/fx`：`README.md:461-463`。
- GUI 未设置 `bi_algo`（`App/ashare_bsp_scanner_gui.py:422-445` 的 15 个键里没有它）→ 生效 `normal`。

---

## 4. 问题4：笔的端点取值、原始K线/合并K线、`BI_TYPE.STRICT`

### 4.1 端点 KLC 与方向

- `CBi` 保存 `begin_klc/end_klc`，两者都是**合并K线**（`Bi/Bi.py:101-103`）。
- 方向由起点 KLC 的分型决定：`begin_klc.fx == BOTTOM → BI_DIR.UP`；`== TOP → BI_DIR.DOWN`；否则抛 `"ERROR DIRECTION when creating bi"`：`Bi/Bi.py:104-109`。
- 一致性断言 `check()`：向下笔要求 `begin_klc.high > end_klc.low`；向上笔要求 `begin_klc.low < end_klc.high`，否则抛 `"...笔的方向和收尾位置不一致!"`：`Bi/Bi.py:92-99`。

### 4.2 端点价格与实际画出的点

- `get_begin_val()`：向上笔 = `begin_klc.low`，向下笔 = `begin_klc.high`；`get_end_val()`：向上笔 = `end_klc.high`，向下笔 = `end_klc.low`：`Bi/Bi.py:113-119`。
- 由于分型 KLC 的合并方向是确定的（顶分型 KLC 是 UP 方向、底分型 KLC 是 DOWN 方向），上述 4 个取值恰好等于该 KLC 内原始 K 线的真实极值（顶=原始最高，底=原始最低）：见 1.3 的合并方向规则。
- 端点原始 K 线：`get_begin_klu()/get_end_klu()` 在端点 KLC 内取极值原始 KLU（`Bi/Bi.py:121-133` → `CKLine_Combiner.get_peak_klu/get_high_peak_klu/get_low_peak_klu`：`Combiner/KLine_Combiner.py:109-125`，倒序遍历 `lst` 找 `high==KLC.high` 或 `low==KLC.low` 的那根）。
- 绘图坐标用**原始 KLU 的 `idx`**：`PlotMeta.py:30-31`（`begin_x = bi.get_begin_klu().idx`，`end_x = bi.get_end_klu().idx`），y 用 `get_begin_val/get_end_val`：`PlotMeta.py:32-33`。所以图上笔端点落在端点 KLC 内那根极值原始 K 线上，而不是合并K线的序号上。
- 原始K线根数/合并K线根数：`get_klu_cnt = end_klu.idx - begin_klu.idx + 1`（`Bi/Bi.py:139-141`）；`get_klc_cnt = end_klc.idx - begin_klc.idx + 1`（`Bi/Bi.py:143-147`）。
- 笔覆盖的 KLC 范围是连续的：`klc_lst` 从 `begin_klc` 沿 `next` 走到 `end_klc`，`klc_lst_re` 反向：`Bi/Bi.py:66-81`。
- 相邻笔共用端点 KLC：`add_new_bi(last_end, klc)`（`BiList.py:98-99,143-147`），即 `bi[i].end_klc is bi[i+1].begin_klc`。虚笔端点更新时也沿用该结构。

### 4.3 `BI_TYPE.STRICT`

- `CBi.__init__` 里 `self.__type = BI_TYPE.STRICT`：`Bi/Bi.py:16`；全仓对 `BI_TYPE` 的赋值只有这一处（grep 结果），`CBi.type` 无 setter。
- 因此**无论 `is_strict` 配置是 True 还是 False，所有笔的 `type` 都是 `BI_TYPE.STRICT`**；`BI_TYPE` 里其余枚举值（`SUB_VALUE/TIAOKONG_THRED/DAHENG/TUIBI/UNSTRICT/TIAOKONG_VALUE`，`Common/CEnum.py:49-57`）从未被赋值。`type` 字段只被绘图/标签使用（`Plot/PlotMeta.py:29`），不参与成笔判定。
- 不能把 `CBi.type` 当作"老笔/新笔"的运行时标记。

---

## 5. 问题5：笔的确认状态机（`is_sure` / 虚拟笔 / `update_bi` / `restore_from_virtual_end`）与最后一笔

### 5.1 `CBi` 的状态字段

- `__is_sure`、`__used_to_be_sure`（初值 = 构造时的 `is_sure`）、`__sure_end: List[CKLine]`：`Bi/Bi.py:20-22`；只读属性：`Bi/Bi.py:53-63`。
- 新笔创建入口 `CBiList.add_new_bi(pre_klc, cur_klc, is_sure=True)`：默认 `is_sure=True`（`BiList.py:143-147`）；虚笔用 `is_sure=False`（`BiList.py:136`）。

### 5.2 虚拟笔端点变化

`CBi.update_virtual_end(new_klc)`：`Bi/Bi.py:169-173`：

1. `append_sure_end(self.end_klc)` 把当前（曾确定的）终点 KLC 压入 `sure_end`：`Bi.py:170,181-182`；
2. `update_new_end(new_klc)`：改 `end_klc`、重新 `check()`、清缓存：`Bi.py:184-187`；
3. `used_to_be_sure = is_sure`；`is_sure = False`：`Bi.py:172-173`。

`CBi.restore_from_virtual_end(sure_end)`：`Bi/Bi.py:175-179`：`is_sure=True`、`used_to_be_sure=True`、终点改回某个保存的 KLC、清空 `sure_end`。

### 5.3 删除/恢复虚拟笔

`CBiList.delete_virtual_bi()`：`BiList.py:105-118`：

- 若末笔不是确定笔（`not bi_list[-1].is_sure`）：
  - `sure_end` 非空 → `restore_from_virtual_end(sure_end[0])` 恢复成确定笔，并把 `sure_end[1:]` 里保存的旧端点逐个补成新的确定笔：`BiList.py:108-113`；
  - `sure_end` 为空 → 直接删除末笔：`BiList.py:114-115`。
- 之后 `last_end = 末笔.end_klc` 或 `None`，末笔的 `next` 置空：`BiList.py:116-118`。

### 5.4 每次真实更新的流程

`CBiList.update_bi(klc, last_klc, cal_virtual)`：`BiList.py:48-56`：

- `flag1 = update_bi_sure(klc)`：`BiList.py:51`；
- 若 `cal_virtual`（等于 `config.trigger_step`）再 `flag2 = try_add_virtual_bi(last_klc)`：`BiList.py:52-53`；否则只返回 `flag1`：`BiList.py:55-56`。

`update_bi_sure(klc)` 开头先记录旧端点 KLU idx、再 `delete_virtual_bi()` 撤销虚笔，然后按 3.1 的分支处理确定笔；返回值表示"末笔原始端点 KLU 的 idx 是否变化"（`BiList.py:86-103`，比较用 `get_last_klu_of_last_bi`：`BiList.py:217-218`）。

### 5.5 虚拟笔的生成（`try_add_virtual_bi`）

`BiList.py:120-141`：

1. `need_del_end=True` 时先 `delete_virtual_bi()`：`BiList.py:121-122`；
2. 没有笔、或当前 KLC 就是末笔终点 → 返回 `False`：`BiList.py:123-126`；
3. 若末笔方向创新高/新低（末笔向上且 `klc.high >= 末笔终点 high`；末笔向下且 `klc.low <= 末笔终点 low`）→ `update_virtual_end(klc)`，即把末笔端点虚移到该 KLC：`BiList.py:127-130`；
4. 否则从 `klc` 沿 `pre` 往回找，`_tmp_klc.idx > 末笔.end_klc.idx` 期间：
   - `can_make_bi(_tmp_klc, 末笔.end_klc, for_virtual=True)` 通过 → 新建 `is_sure=False` 的笔：`BiList.py:131-137`；
   - 否则 `update_peak(_tmp_klc, for_virtual=True)` 通过 → `True`：`BiList.py:138-139`；
   - 继续回退：`BiList.py:140`。
- 虚笔路径用 `klc.dir` 代替 `fx`（最后一根 KLC 没有 fx）：`try_update_end` 内部 `check_top/check_bottom`：`BiList.py:194-204`；`check_fx_valid` 中 `for_virtual` 分支：`KLine/KLine.py:52-53,61-62,75-76,84-85`。

### 5.6 最后一笔与非 step 模式（GUI）

- GUI 固定 `trigger_step=False`（第 7 节）；`KLine_List.step_calculation = config.trigger_step`：`KLine_List.py:52,121-122`。
- `add_single_klu` 调 `bi_list.update_bi(lst[-2], lst[-1], self.step_calculation)`：`KLine_List.py:134` → 非 step 模式 `cal_virtual=False` → **只维护确定笔，不产生虚笔**：`BiList.py:51-56`。
- 全量数据加载完成后，`KLine_List.cal_seg_and_zs()` 开头执行 `if not step_calculation: self.bi_list.try_add_virtual_bi(self.lst[-1])`：`KLine_List.py:104-106` → 补出"最后一笔"的虚笔（`is_sure=False`）。之后才用 `bi_list` 计算线段/中枢/买卖点：`KLine_List.py:107-119`。
- 因此 GUI 最终 `bi_list` 的末笔通常是 `is_sure=False` 的虚拟笔（除非无法形成）；其余为确定笔 `is_sure=True`。
- step 模式（`trigger_step=True`，非 GUI）下，每来一根新合并K线都会维护虚笔（`BiList.py:52-53`），合并K线时也会 `try_add_virtual_bi(lst[-1], need_del_end=True)`：`KLine_List.py:136`；虚笔每次被 `delete_virtual_bi` 撤销后重算。
- 首笔特殊：第一笔成立前所有候选 KLC 存在 `free_klc_lst` 中（`BiList.py:16`）；每根新 KLC 调 `try_create_first_bi`，从旧到新找第一根"分型相反且 `can_make_bi` 通过"的候选 KLC 成笔，否则把当前 KLC 存入缓存、`last_end=klc`：`BiList.py:36-46`。注意首笔起点是"最早能通过的候选"，代码不保证它是全局极值。

---

## 6. 问题6：缺口处理

- 缺口定义：`CKLine.has_gap_with_next()`：`KLine/KLine.py:40-43`。它用相邻两根合并K线的**原始极值区间** `[get_klu_min_low, get_klu_max_high]`（`KLine.py:34-38`）做重叠判断：`return not has_overlap(..., equal=True)`。
- `has_overlap(l1,h1,l2,h2,equal=True)`：`Common/func_util.py:23-24`；`equal=True` 表示"相等也算重叠"。所以：**两段区间只要有重叠（含边界相等）就没有缺口；完全无重叠才算缺口**。
- 缺口唯一用途：`CBiList.get_klc_span` 中，当 `gap_as_kl=True` 时，把 `last_end → klc` 之间每个缺口让 `span += 1`：`BiList.py:170-181`（`:172-173` 为 False 时直接返回 `klc.idx - last_end.idx`；`:174-175` 当 span 已 ≥4 提前返回；`:176-180` 遍历补 span）。
- 生效范围：**只在 `satisfy_bi_span` 的 `is_strict=True` 分支被使用**（`BiList.py:150-152`）。`is_strict=False` 分支在 `:150` 算出 `bi_span` 却没有使用它（`:157-168` 用的是 `klc.idx - last_end.idx` 和原始 KLU 计数）→ **GUI（is_strict=False）下 `gap_as_kl` 对画笔没有任何影响**。
- 是否可能"绕过最少K线"：`gap_as_kl=True` 时缺口只会让 span **增大**（每个缺口 +1），不会减小；`span >= 4` 分支已满足阈值直接返回（`:174-175`），精确值即使更大也只影响"已通过"的判定。因此它是"缺口当成一根合并K线"的放宽规则，**不会绕过 `>=4` 门槛之外再放宽**。
- GUI 实际组合：`gap_as_kl=False`（`ChanConfig.py:27` 默认，GUI 未覆盖）+ `is_strict=False` → 缺口完全不参与画笔。
- 文档不一致：`README.md:465` 写"gap_as_kl：缺口是否处理成一根K线，默认为 True"，与代码默认 `False`（`ChanConfig.py:27`）不符。

---

## 7. 问题7：默认参数 vs GUI 实际生效参数

### 7.1 三套默认值（容易混淆，逐条核对）

| 参数 | `CChanConfig()` 默认 | 直接构造 `CBiConfig()` 默认 | GUI `get_chan_config()` 实际 | 证据 |
|---|---|---|---|---|
| `bi_algo` | `"normal"` | `"normal"` | `"normal"`（未传入） | `ChanConfig.py:24`；`Bi/BiConfig.py:8`；GUI 15 键无此项 `App/ashare_bsp_scanner_gui.py:429-445` |
| `bi_strict`（→`is_strict`） | `True` | `True` | **`False`** | `ChanConfig.py:25`；`BiConfig.py:9`；`GUI:430` |
| `bi_fx_check` | `"strict"`（→STRICT） | `"half"`（→HALF） | **`"half"`（→HALF）** | `ChanConfig.py:26`；`BiConfig.py:10,17-26`；`GUI:431` |
| `gap_as_kl` | `False` | `True` | `False` | `ChanConfig.py:27`；`BiConfig.py:11`；GUI 未设置 |
| `bi_end_is_peak` | `True` | `True` | `True` | `ChanConfig.py:28`；`BiConfig.py:12`；GUI 未设置 |
| `bi_allow_sub_peak` | `True` | `True` | `True` | `ChanConfig.py:29`；`BiConfig.py:13`；GUI 未设置 |
| `trigger_step` | `False` | — | `False` | `ChanConfig.py:42`；`GUI:432` |
| `cal_bi_zs` | `True` | — | `False`（不影响成笔） | `ChanConfig.py:52`；`GUI:443` |
| `cal_bi_bsp` | `True` | — | `False`（不影响成笔） | `ChanConfig.py:53`；`GUI:444` |

要点：

- `CBiConfig` 构造器默认的 `bi_fx_check="half"`、`gap_as_kl=True` 这两个值**不会被 `CChanConfig` 使用**，因为 `CChanConfig.__init__` 对 6 个笔参数全部显式调用 `conf.get(..., 默认值)`：`ChanConfig.py:23-30`。所以框架层"什么都不传"时的实际默认是 **normal / 严格笔 / STRICT / 缺口不算K线 / 尾部极值 / 允许次高点**。
- GUI 固定的是 `bi_strict=False` 与 `bi_fx_check="half"`（`App/ashare_bsp_scanner_gui.py:430-431`），其余笔参数落到 `CChanConfig` 默认：`bi_algo="normal"`、`gap_as_kl=False`、`bi_end_is_peak=True`、`bi_allow_sub_peak=True`。
- GUI 注释（`GUI:431`）原文："half 更符合缠论原文，避免 strict 过度过滤"；界面文案"固定使用新笔(bi_strict=False)"（`GUI:18,316`）；项目文档同样表述（`PROJECT_GUIDE.md:47,56-67`、`docs/RAZOR_ACCEPTANCE.md:97-98,113`，后者明确"内核旧笔严格分支保留，只是 GUI 固定默认"）。
- README 文档默认值与代码不一致两处：`bi_strict` 写默认 True（`README.md:464`，与 `CChanConfig` 一致，但 GUI 固定 False）；`gap_as_kl` 写默认 True（`README.md:465`，代码 `ChanConfig.py:27` 默认 False）。README 配置 demo 里显式写 `"bi_strict": True`：`README.md:588`。
- 用户实际跑 GUI 时的参数链路：`get_chan_config()` 构造 `CChanConfig`（`GUI:429-445`）→ 传入 `SingleAnalysisThread`（`GUI:480-481,514-516`）→ `CChan(config=...)` 直接使用该对象（`Chan.py:40-42`）→ `do_init` 每级别 `CKLine_List` 使用 `conf.bi_conf`（`Chan.py:85-88`；`KLine_List.py:40`）。GUI 的 `lv_list` 只有一个级别（`GUI:161-196`），因此不存在多级别递归对画笔的干扰。
- 打包核对：`dist/razor-candidate/ChanScanner/_internal/Bi/BiList.py`、`.../KLine/KLine.py`、`.../Bi/Bi.py` 的 SHA256 与源码对应文件逐一相同（`BiList.py` 7AE089BD…、`KLine.py` FF2BE1D0…、`Bi.py` 9E7231C7…），即候选 EXE 用的是同一套画笔代码。

### 7.2 「GUI 实际生效的画笔参数组合」一句话

> `bi_algo="normal"`、`is_strict=False`（新笔）、`bi_fx_check=HALF`、`gap_as_kl=False`、`bi_end_is_peak=True`、`bi_allow_sub_peak=True`、`trigger_step=False`。

即：**按新笔规则数最少K线（合并K线 idx 差≥3 且原始K线≥5）+ HALF 分型区间过滤 + 要求笔尾是整笔极值 + 不用缺口补K线 + 不做次高点回退**。

---

## 8. 问题8：完整链路伪代码（合并→分型→笔）

```python
# 入口：CChan.__init__ → do_init 每级别建 CKLine_List (Chan.py:49,85-88)
#      非 step 模式一次性 load() (Chan.py:51-53,196-199)，每根 KLU → add_new_kl (Chan.py:213-219)

CKLine_List.add_single_klu(klu):                          # KLine_List.py:124-137
    if len(lst) == 0: lst.append(CKLine(klu, idx=0))      # :126-127
    else:
        _dir = lst[-1].try_add(klu)                       # :129  合并判定(仅 high/low, KLine_Combiner.py:64-107)
        if _dir != COMBINE:                               # :130  产生新合并K线
            lst.append(CKLine(klu, idx=len(lst), _dir=_dir))          # :131
            if len(lst) >= 3: lst[-2].update_fx(lst[-3], lst[-1])     # :132-133 只给"中间那根"算分型
            bi_list.update_bi(lst[-2], lst[-1], step_calculation)     # :134  klc=倒数第2根, last=最后一根
            if 返回值 and step_calculation: cal_seg_and_zs()          # :134-135
        elif step_calculation: try_add_virtual_bi(lst[-1], need_del_end=True)  # :136

CBiList.update_bi(klc, last_klc, cal_virtual):            # BiList.py:48-56
    flag1 = update_bi_sure(klc)                           # 确定笔维护
    if cal_virtual: flag2 = try_add_virtual_bi(last_klc)  # 虚笔(仅 step 模式/结束后补一笔)
    return flag1 or flag2

update_bi_sure(klc):                                      # BiList.py:86-103
    delete_virtual_bi()                                   # :89  先撤销虚笔
    if klc.fx == UNKNOWN: return 端点未变                # :91-92
    if 没有笔: return try_create_first_bi(klc)            # :93-94  free_klc_lst 缓存 :36-46
    if klc.fx == last_end.fx: return try_update_end(klc)  # :95-96  延伸末笔终点(要求创新高/新低 :209-210)
    if can_make_bi(klc, last_end): add_new_bi(last_end, klc); return True   # :97-100 共用端点
    if update_peak(klc): return True                      # :101-102 仅 bi_allow_sub_peak=False 才可能生效 :58-60

can_make_bi(klc, last_end, for_virtual=False):            # BiList.py:183-191
    if bi_algo != 'fx' and not satisfy_bi_span(klc, last_end): return False  # :184  span 口径见 3.2
    if not last_end.check_fx_valid(klc, bi_fx_check, for_virtual): return False  # :187-188 四种方法见 3.3
    if bi_end_is_peak and not end_is_peak(last_end, klc): return False         # :189-190
    return True

# 全量加载结束(非 step)：cal_seg_and_zs 先补最后一根虚笔，再算线段/中枢/买卖点
if not step_calculation: bi_list.try_add_virtual_bi(lst[-1])              # KLine_List.py:104-106
```

---

## 9. 问题9：关键细节核对清单（逐条给代码事实）

1. **最少K线数怎么算/阈值/含不含端点**
   - `is_strict=True`：`KLC.idx` 差 ≥4 → 含两端至少 5 根**合并**K线（`BiList.py:151-152,171`）；两组分型之间至少 1 根独立合并K线；端点包含（idx 差 = 终点 idx − 起点 idx，含两端）。
   - `is_strict=False`：`KLC.idx` 差 ≥3 → 含两端至少 4 根**合并**K线（`BiList.py:157-158`）；另外要求 `last_end` 至 `klc`（含两端 KLC 内全部原始 K 线）原始 K 线数 ≥5（`BiList.py:159-168`）。
   - 阈值是硬编码常量 4 / 3 / 5，无配置项。
2. **计合并K线还是原始K线**：严格笔只数合并K线（不数原始）；新笔两者都数（合并 idx 差 + 原始 KLU 总数）。两种模式最终都保证"两端之间原始K线 ≥5 根"（严格笔由"≥5 根合并K线 × 每根≥1"隐含，新笔显式检查）。
3. **顶/底分型能否共用K线**：两种模式都**不允许**两组三元素分型共用合并K线——严格笔要求两组间至少隔 1 根独立合并K线（idx 差≥4），新笔要求两组相邻但不重叠（idx 差≥3）。相邻两笔**共用端点KLC**是设计使然（`BiList.py:98-99,143-147`），不属于"分型共用K线"。
4. **端点极值是否严格**：`bi_end_is_peak=True` 只检查笔**终点**在整笔范围内是最高（上升笔）/最低（下降笔）（`BiList.py:189-190,221-240`），用合并KLC 的 `high/low`；允许相等（`try_update_end` 用 `>=`/`<=` 延伸端点，`BiList.py:209-210`）。**未找到"起点必须是整笔极值"或"笔内K线不得越过起点极值"的检查**（起点极值只在上一笔作为终点时被检查过）。此理论边界未实测。
5. **顶底交替**：强制。确定笔只在 `klc.fx != last_end.fx` 时才可能新建（`BiList.py:95-100`），`check_fx_valid` 对非虚笔断言反向分型（`KLine/KLine.py:51,74`）；虚笔用 KLC `dir` 保证反向（`KLine.py:52-53,75-76`）。
6. **端点价格取哪根K线**：端点 KLC 是合并K线（分型中心）；实际价格 `get_begin_val/get_end_val` 等于该 KLC 内原始极值（顶=原始最高/底=原始最低，由合并方向保证：`Bi/Bi.py:113-119` + `KLine_Combiner.py:94-101`）；更精确的原始K线由 `get_begin_klu/get_end_klu` 返回（`Bi/Bi.py:121-133`）；绘图 x 坐标用原始 KLU 的 `idx`（`Plot/PlotMeta.py:30-31`）。
7. **`BI_TYPE.STRICT`**：`CBi.type` 恒为 `BI_TYPE.STRICT`（`Bi/Bi.py:16`，全仓唯一赋值），与 `is_strict` 配置无关；其余 `BI_TYPE` 枚举从未使用。不能用作"老笔/新笔"标记。
8. **最后一笔**：GUI 非 step 模式下，全量加载结束时由 `cal_seg_and_zs` 添加一根 `is_sure=False` 的虚拟末笔（`KLine_List.py:104-106`），因此最终 `bi_list[-1]` 通常不确定；确定笔由 `update_bi_sure` 增量产生（`BiList.py:86-103`）。`used_to_be_sure` 记录"曾经确定过"（`Bi/Bi.py:172-173,176-177`）。
9. **HALF 与原文对照点（只列代码事实）**：HALF 只比较两端分型**内侧** 2 根合并K线的区间：上升笔要求 `底KLC.low < min(顶KLC左侧一根.low, 顶KLC.low)` 且 `顶KLC.high > max(底KLC.high, 底KLC右侧一根.high)`（`KLine/KLine.py:77-79,95`）；不比较顶分型外侧（左侧一根之外）与底分型外侧（右侧一根之外）的 KLC。相比 STRICT 少了两个外侧极值检查；相比 LOSS 多了内侧相邻一根的检查。GUI 固定 HALF（`GUI:431`）。它与"最少K线数"是两套独立约束。
10. **分型确认时机**：需要右侧一根合并K线；`lst[-1]` 永远没有 fx；确定笔右端点最多到 `lst[-2]`（`KLine_List.py:132-134`）。
11. **首笔**：`free_klc_lst` 缓存第一笔成立前的 W 根 KLC，取"最早可通过 `can_make_bi` 的相反分型 KLC"作为起点（`BiList.py:36-46`）；不保证首笔起点是全局极值。
12. **缺口**：缺口不造 K 线、不影响分型，只在 `is_strict=True` 且 `gap_as_kl=True` 时让 span 每个缺口 +1（`BiList.py:170-181`）；GUI 两项配置都不满足 → 无影响（见第 6 节）。
13. **`bi_algo='fx'`**：完全跳过最少K线数（`BiList.py:184`），其余不变；GUI 不设置 → `normal`。
14. **代码里没有的东西**（与"原文要求"对照时可直接检查）：没有 `check_fx` 函数；没有统一的"一笔至少 N 根K线"单一实现（是两套口径）；没有用原始K线计 span（严格笔）；没有"笔的起点/内部极值不得越过起点"的检查；没有把 `BI_TYPE` 其他值用于笔；没有把缺口单列成笔的规则（只补 span）；没有 `is_strict=False` 下使用 `gap_as_kl` 的路径。

---

## 10. 供 Lead 与原文对照用的「代码事实清单」

### 10.1 实际生效参数组合（用户跑 GUI）

| 项 | 值 | 证据 |
|---|---|---|
| 入口 | `App/ashare_bsp_scanner_gui.py`（PyQt6，单级别 CChan） | `GUI:151-196` |
| `bi_algo` | `normal` | `ChanConfig.py:24`（GUI 未传） |
| `bi_strict` | `False`（新笔） | `GUI:430` |
| `bi_fx_check` | `half`（HALF） | `GUI:431` |
| `gap_as_kl` | `False` | `ChanConfig.py:27`（GUI 未传） |
| `bi_end_is_peak` | `True` | `ChanConfig.py:28`（GUI 未传） |
| `bi_allow_sub_peak` | `True` | `ChanConfig.py:29`（GUI 未传） |
| `trigger_step` | `False` | `GUI:432`；`ChanConfig.py:42` |
| 计算完成后末笔 | 一根 `is_sure=False` 的虚拟笔 | `KLine_List.py:104-106` |
| 打包一致性 | `dist/razor-candidate/.../_internal` 的 `Bi/BiList.py`、`KLine/KLine.py`、`Bi/Bi.py` 与源码 SHA256 相同 | 见 7.1 |

### 10.2 代码里实现了的规则（客观列举）

- 包含合并：只用相邻 KLC 的 `high/low`，上升合并取 `high=max, low=max`、下降合并取 `high=min, low=min`，一字K线特判（`KLine_Combiner.py:64-107`）。
- 分型：3 根连续**合并K线**的严格高低点关系（顶=高点最高且低点最高；底相反）；需要左邻+右邻；只算一次（`KLine_Combiner.py:127-145`；`KLine_List.py:132-133`）。
- 笔：顶底交替、相邻笔共用端点KLC、笔覆盖连续 KLC 区间（`BiList.py:97-100,143-147`；`Bi/Bi.py:66-81`）。
- 最少K线：严格笔"合并K线 idx 差≥4"；新笔"合并K线 idx 差≥3 且原始K线≥5"（`BiList.py:149-168`）。
- 结束点极值：`bi_end_is_peak=True` 要求终点是整笔最高/最低（`BiList.py:189-190,221-240`）。
- 分型价格区间过滤：四种可选方法 STRICT/LOSS/HALF/TOTALLY，默认 STRICT，GUI 用 HALF（`KLine.py:45-97`；`ChanConfig.py:26`；`GUI:431`）。
- 缺口可配置为"一根K线"：`gap_as_kl=True` 时每个缺口 span+1，只作用于严格笔分支（`BiList.py:170-181`）。
- 虚拟末笔与确认状态：`is_sure/used_to_be_sure/sure_end`、`update_virtual_end`、`restore_from_virtual_end`、`delete_virtual_bi`（`Bi/Bi.py:20-22,169-187`；`BiList.py:105-141`）。
- 次高点成笔开关：`bi_allow_sub_peak=True` 时**禁用**端点回退修正；`False` 时允许 pop 末笔并把前一笔延伸到新极值（`BiList.py:58-84`）。
- `bi_algo='fx'`：无最少K线数，仅 fx + 尾部极值（`BiList.py:184`）。

### 10.3 代码里没有/需要原文对照时注意的点（代码事实，不下结论）

1. `CBi.type` 恒为 `BI_TYPE.STRICT`，无法区分老笔/新笔（`Bi/Bi.py:16`）。
2. 严格笔的最少K线只按**合并K线**计数（`BiList.py:151-152`）。
3. 新笔除了"分型不共用"外，还额外要求原始K线≥5（`BiList.py:159-168`）；若 4 根合并K线全部由单根原始K线构成，则不成笔。
4. **只检查笔尾极值**，不检查笔起点极值、也不检查笔内K线是否越过起点（`BiList.py:221-240`；`BiList.py:189-190`）。
5. `HALF` 不检查两端分型的外侧邻根（顶分型左侧一根之外、底分型右侧一根之外），因此相邻笔的价格区间可以重叠（第 3.3.3 节）。
6. `TOTALLY` 的实现与 README 描述不完全一致：代码上升笔只用起点底分型KLC自身 `high`（不是底分型3元素的最高点）与终点顶分型3元素最低点比较；下降笔对称（`KLine.py:69-70,92-93` vs `README.md:469`）。
7. `gap_as_kl` 文档默认 True，代码默认 False（`README.md:465` vs `ChanConfig.py:27`）。
8. `CBiConfig()` 构造器默认值（`bi_fx_check="half"`、`gap_as_kl=True`）与 `CChanConfig()` 默认值（`"strict"`、`False`）不同；经 `CChanConfig` 构造时以后者为准（`Bi/BiConfig.py:8-13`；`ChanConfig.py:23-30`）。
9. 首笔起点来自 `free_klc_lst` 中"最早可通过 `can_make_bi`"的候选，不保证首笔起点是全局极值（`BiList.py:36-46`）。
10. GUI 用单级别、`trigger_step=False`，全部数据加载完才补一根虚拟末笔并计算线段/中枢/买卖点（`KLine_List.py:104-119`）；`cal_bi_zs/cal_bi_bsp` 关闭只影响笔级别中枢/买卖点，不影响成笔（`GUI:443-444`）。
11. 代码注释中唯一直接拿"原文"作比较的地方：GUI 注释称 `half` 更符合缠论原文、`strict` 过度过滤（`App/ashare_bsp_scanner_gui.py:431`）；这是注释主张，不是代码约束。
12. 框架层保留严格笔分支，GUI 只是固定默认（`PROJECT_GUIDE.md:47,67`；`docs/RAZOR_ACCEPTANCE.md:78,113`），因此"本程序画笔"存在两套口径，GUI 用户实际只走新笔+HALF 这一套。
