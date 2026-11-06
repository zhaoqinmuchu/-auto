"""
ChanScanner - 缠论图表分析工具 - Powered by chan.py

功能说明:
    - 导入通达信导出的本地TXT K线数据（日线/分钟/秒级，支持跨月跨年日期推断）
    - 联网分析单只A股（腾讯分钟线 / baostock 日线）
    - 可视化显示K线、笔、线段、中枢、买卖点、MACD等
    - 图表交互: 滚轮缩放、拖拽平移、右键框选、双击恢复视图、十字光标
    - 导出通达信线段公式文件(.tni)

数据来源:
    - 分钟级别(1/5/15/30/60分钟): 使用腾讯财经接口 (ifzq.gtimg.cn)
      注意: 分钟数据最多获取最近约320根(约1.3个交易日)
    - 日线级别: 使用 baostock 获取A股历史K线数据
    - 本地数据: 通达信导出的TXT文件

笔划分规则（界面可切换）:
    - 笔类型: 新笔（默认，bi_strict=False）/ 旧笔（严格，bi_strict=True）
    - 分型校验: loss（默认，最贴原文第77课价格条款）/ half（原程序默认）/ strict
    - 笔尾极值约束: 关闭（原文无此条款，开启会导致跳空/急跌后笔链停摆）

依赖:
    - PyQt6: GUI框架
    - matplotlib: 图表绑定
    - requests: 腾讯接口请求
    - baostock: 日线数据接口
    - chan.py: 缠论分析核心库

使用方法:
    python App/ashare_bsp_scanner_gui.py
"""
import os
import re
import sys
import tempfile
from pathlib import Path

# 禁用系统代理，避免代理无法访问国内行情接口（如东方财富）导致连接失败
# 程序直接连接行情服务器，不走系统代理（Clash/V2Ray 等）
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)

# 将项目根目录加入路径，以便导入 chan.py 核心模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox,
    QMessageBox, QStatusBar, QSplitter, QFileDialog, QInputDialog
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

try:  # 通达信内存直读模块（可选依赖 numpy；缺失时 GUI 其余功能仍可用）
    from TdxBridge.mem_reader import (
        read_current_bars as tdx_read_current_bars,
        ref_begin_time as tdx_ref_begin_time,
        write_tdx_txt as tdx_write_txt,
    )
    TDX_LIVE_AVAILABLE = True
except Exception:  # pragma: no cover - 缺省降级
    tdx_read_current_bars = None
    tdx_ref_begin_time = None
    tdx_write_txt = None
    TDX_LIVE_AVAILABLE = False


def to_baostock_code(code):
    """
    将纯数字股票代码转换为 baostock 格式（带 sh./sz. 前缀）。

    规则:
        - 6开头（600/601/603/605等）: 上海 -> sh.xxxxxx
        - 0/3开头（000/001/002/003/300等）: 深圳 -> sz.xxxxxx
        - 已带 sh./sz. 前缀则原样返回

    Args:
        code: str, 股票代码（如 '000001' 或 'sh.600000'）

    Returns:
        str: baostock 格式代码（如 'sz.000001'）
    """
    code = str(code).strip()
    if code.startswith('sh.') or code.startswith('sz.'):
        return code
    if code.startswith('6'):
        return f"sh.{code}"
    return f"sz.{code}"


# 周期选项: 显示文本 -> (KL_TYPE, 数据源)
PERIOD_OPTIONS = [
    ("1分钟", KL_TYPE.K_1M, "tencent"),
    ("5分钟", KL_TYPE.K_5M, "tencent"),
    ("15分钟", KL_TYPE.K_15M, "tencent"),
    ("30分钟", KL_TYPE.K_30M, "tencent"),
    ("60分钟", KL_TYPE.K_60M, "tencent"),
    ("日线", KL_TYPE.K_DAY, "baostock"),
]


def get_period_config(period_text):
    """
    根据周期文本返回对应的 (KL_TYPE, 数据源标识)。

    Args:
        period_text: str, 周期显示文本（如 '1分钟'）

    Returns:
        tuple: (KL_TYPE, str) 数据源标识为 'tencent' 或 'baostock'
    """
    for text, kl_type, src in PERIOD_OPTIONS:
        if text == period_text:
            return kl_type, src
    return KL_TYPE.K_DAY, "baostock"


class SingleAnalysisThread(QThread):
    """
    单只股票分析的后台线程

    用于分析用户手动输入的股票代码，避免阻塞 UI。

    Signals:
        finished: (CChan) 分析完成，返回 CChan 对象
        error: (str) 分析出错时返回错误信息
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code, config, period_text="日线", days=365, file_path=None, begin_time=None):
        """
        初始化分析线程

        Args:
            code: str, 股票代码（如 '000001'）
            config: CChanConfig, 缠论配置
            period_text: str, 周期文本（如 '1分钟'、'日线'）
            days: int, 获取多少天的历史数据
            file_path: str or None, 本地通达信TXT文件路径（导入本地数据时使用）
            begin_time: str or None, 本地TXT数据所属年月（如 "2026-08"），
                用于推断通达信秒级K线无年份格式(日/时:分:秒)的月份年份。
        """
        super().__init__()
        self.code = code
        self.config = config
        self.period_text = period_text
        self.days = days
        self.file_path = file_path
        self.begin_time = begin_time

    def run(self):
        """执行缠论分析，完成后通过信号返回结果"""
        try:
            if self.file_path:
                # 导入本地通达信TXT数据
                # 使用 custom: 数据源格式加载 TDX_TXT_API，code 传入文件路径
                # 自动判断数据级别：日线数据(纯日期格式)用 K_DAY，分钟/秒级用 K_1M
                from DataAPI.TDX_TXT_API import TDX_TXT_API
                _detect = TDX_TXT_API(code=self.file_path)
                _lv = KL_TYPE.K_DAY if _detect.is_daily_data() else KL_TYPE.K_1M
                chan = CChan(
                    code=self.file_path,
                    begin_time=self.begin_time,
                    data_src="custom:TDX_TXT_API.TDX_TXT_API",
                    lv_list=[_lv],
                    config=self.config,
                    autype=AUTYPE.NONE,
                )
                self.finished.emit(chan)
                return

            kl_type, src = get_period_config(self.period_text)

            if src == "tencent":
                # 腾讯接口：分钟级别数据（最多320根，约1.3个交易日）
                # 使用 custom: 数据源格式加载 CTencent
                chan = CChan(
                    code=to_baostock_code(self.code),
                    data_src="custom:TencentAPI.CTencent",
                    lv_list=[kl_type],
                    config=self.config,
                    autype=AUTYPE.NONE,
                )
            else:
                # baostock：日线级别数据
                begin_time = (datetime.now() - timedelta(days=self.days)).strftime("%Y-%m-%d")
                end_time = datetime.now().strftime("%Y-%m-%d")
                chan = CChan(
                    code=to_baostock_code(self.code),
                    begin_time=begin_time,
                    end_time=end_time,
                    data_src=DATA_SRC.BAO_STOCK,
                    lv_list=[KL_TYPE.K_DAY],
                    config=self.config,
                    autype=AUTYPE.QFQ,
                )
            self.finished.emit(chan)
        except Exception as e:
            self.error.emit(str(e))


class ChanPlotCanvas(FigureCanvas):
    """
    嵌入 PyQt 的 Matplotlib 画布

    用于在 GUI 中显示缠论分析图表，包括K线、笔、线段、中枢等。

    Args:
        parent: 父控件
        width: 图表宽度（英寸）
        height: 图表高度（英寸）
    """

    def __init__(self, parent=None, width=12, height=8):
        self.fig = Figure(figsize=(width, height), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(400)

    def clear(self):
        """清空画布内容"""
        self.fig.clear()
        self.draw()


class AkshareGUI(QMainWindow):
    """
    ChanScanner 缠论图表分析主窗口

    主要功能:
        - 本地导入: 选择通达信导出的TXT文件进行缠论分析
        - 单股分析: 手动输入股票代码进行在线缠论分析
        - 图表显示: 可视化展示K线、笔、线段、中枢、买卖点、MACD
        - 公式导出: 把当前线段划分导出为通达信公式文件

    界面布局:
        - 左侧面板: 股票代码/周期选择、本地TXT导入、公式导出
        - 右侧面板: 图表显示区域，支持缩放、拖拽、框选和十字光标
    """

    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.chan = None  # 当前分析的 CChan 对象
        self.analysis_thread = None  # 单股分析/本地导入线程
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('ChanScanner 缠论图表分析 - Powered by chan.py')
        self.setGeometry(100, 100, 1600, 900)

        # 创建中央 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 左侧分析控制面板
        left_panel = self.create_left_panel()

        # 右侧图表区域
        right_panel = self.create_chart_panel()

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 1150])

        main_layout.addWidget(splitter)

        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪 - 可导入本地TXT数据或输入股票代码分析')

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 单只股票分析
        single_group = QGroupBox("单只股票分析")
        single_layout = QVBoxLayout(single_group)

        code_row = QHBoxLayout()
        code_row.addWidget(QLabel("股票代码:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("如: 000001")
        code_row.addWidget(self.code_input)

        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.clicked.connect(self.analyze_single)
        code_row.addWidget(self.analyze_btn)
        single_layout.addLayout(code_row)

        # 周期选择
        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("K线周期:"))
        self.period_combo = QComboBox()
        for text, _, _ in PERIOD_OPTIONS:
            self.period_combo.addItem(text)
        self.period_combo.setCurrentText("1分钟")
        period_row.addWidget(self.period_combo)
        single_layout.addLayout(period_row)

        # 周期说明
        period_hint = QLabel("提示: 分钟级别数据来自腾讯接口(最近约1.3天)，日线来自baostock")
        period_hint.setWordWrap(True)
        period_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(period_hint)

        # 笔类型选择（新笔/旧笔）
        bi_type_row = QHBoxLayout()
        bi_type_row.addWidget(QLabel("笔类型:"))
        self.bi_type_combo = QComboBox()
        self.bi_type_combo.addItem("新笔（默认）", "new")
        self.bi_type_combo.addItem("旧笔（严格）", "old")
        bi_type_row.addWidget(self.bi_type_combo)
        single_layout.addLayout(bi_type_row)

        # 分型校验方式选择（原文价格条款只有 loss 一档）
        bi_fx_row = QHBoxLayout()
        bi_fx_row.addWidget(QLabel("分型校验:"))
        self.bi_fx_combo = QComboBox()
        self.bi_fx_combo.addItem("loss（原文，默认）", "loss")
        self.bi_fx_combo.addItem("half（原程序默认）", "half")
        self.bi_fx_combo.addItem("strict（更严）", "strict")
        bi_fx_row.addWidget(self.bi_fx_combo)
        single_layout.addLayout(bi_fx_row)

        # 笔划分规则说明（随下拉框动态更新）
        self.rule_hint = QLabel("")
        self.rule_hint.setWordWrap(True)
        self.rule_hint.setStyleSheet("color: #666666; font-size: 11px;")
        single_layout.addWidget(self.rule_hint)
        self.bi_type_combo.currentIndexChanged.connect(self._update_rule_hint)
        self.bi_fx_combo.currentIndexChanged.connect(self._update_rule_hint)
        self._update_rule_hint()

        # 导入本地通达信TXT数据
        import_row = QHBoxLayout()
        self.import_btn = QPushButton("导入本地TXT数据")
        self.import_btn.clicked.connect(self.import_local_txt)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        import_row.addWidget(self.import_btn)
        single_layout.addLayout(import_row)

        import_hint = QLabel("导入通达信导出的TXT文件(支持日线/分钟/秒级)，可查看完整历史数据")
        import_hint.setWordWrap(True)
        import_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(import_hint)

        # 从通达信内存直接读取当前图表（免手工导出）
        live_row = QHBoxLayout()
        self.live_read_btn = QPushButton("读取当前图(通达信)")
        self.live_read_btn.clicked.connect(self.read_from_tdx_live)
        self.live_read_btn.setStyleSheet("""
            QPushButton {
                background-color: #00897B;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #00695C; }
        """)
        live_row.addWidget(self.live_read_btn)
        single_layout.addLayout(live_row)

        live_hint = QLabel("直接从通达信内存读取当前图表的K线（不用先导出文件）；需期货通已打开目标品种，自动识别5秒/10秒周期")
        live_hint.setWordWrap(True)
        live_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(live_hint)

        # 导出通达信线段公式
        export_row = QHBoxLayout()
        self.export_btn = QPushButton("导出通达信线段公式")
        self.export_btn.clicked.connect(self.export_tdx_seg_formula)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        export_row.addWidget(self.export_btn)
        single_layout.addLayout(export_row)

        export_hint = QLabel("将当前线段划分导出为通达信公式文件(.tni)，导入后可直接画在通达信图上")
        export_hint.setWordWrap(True)
        export_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(export_hint)

        # 按目标周期映射导出（如 10 秒级别画出来的线段，映射到 5 分钟 K 线上）
        map_period_row = QHBoxLayout()
        map_period_row.addWidget(QLabel("映射周期:"))
        self.map_period_combo = QComboBox()
        for minutes in (5, 1, 15, 30, 60):
            self.map_period_combo.addItem(f"{minutes}分钟", minutes)
        map_period_row.addWidget(self.map_period_combo)
        single_layout.addLayout(map_period_row)

        map_export_row = QHBoxLayout()
        self.map_export_btn = QPushButton("导出5分钟映射公式")
        self.map_export_btn.clicked.connect(self.export_tdx_seg_formula_mapped)
        self.map_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #8E24AA;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #6A1B9A; }
        """)
        map_export_row.addWidget(self.map_export_btn)
        single_layout.addLayout(map_export_row)

        map_hint = QLabel(
            "把当前级别画出的线段，按时间映射到大周期K线上（如10秒线段→5分钟图）；"
            "坐标按目标周期的K线定位，价格不变"
        )
        map_hint.setWordWrap(True)
        map_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(map_hint)

        # 折线版导出：整条链路只用一条 PLOYLINE 画出
        # 通达信限制：公式最多 100 个输出；每条 PLOYLINE 的"最后一折"会变成射线向后延伸。
        # 所以把全部线段端点写进一条折线，射线只出现在最新K线之后，不可见。
        poly_export_row = QHBoxLayout()
        self.poly_export_btn = QPushButton("导出5分钟折线版")
        self.poly_export_btn.clicked.connect(self.export_tdx_polyline_formula)
        self.poly_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-size: 13px;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1B5E20; }
        """)
        poly_export_row.addWidget(self.poly_export_btn)
        single_layout.addLayout(poly_export_row)

        poly_hint = QLabel(
            "折线版：用一条折线(PLOYLINE)连起全部线段，绕开通达信"
            "「最多100个输出」和「每条折线末尾会飞出一条射线」的限制；未确定末段用红色覆盖"
        )
        poly_hint.setWordWrap(True)
        poly_hint.setStyleSheet("color: #888888; font-size: 11px;")
        single_layout.addWidget(poly_hint)

        self.map_period_combo.currentIndexChanged.connect(self._update_map_period_hint)
        self._update_map_period_hint()

        layout.addWidget(single_group)

        layout.addStretch()

        return panel

    def create_chart_panel(self):
        """创建右侧图表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 绘图配置
        config_layout = QHBoxLayout()

        self.plot_kline_cb = QCheckBox("K线")
        self.plot_kline_cb.setChecked(True)
        config_layout.addWidget(self.plot_kline_cb)

        self.plot_bi_cb = QCheckBox("笔")
        self.plot_bi_cb.setChecked(True)
        config_layout.addWidget(self.plot_bi_cb)

        self.plot_seg_cb = QCheckBox("线段")
        self.plot_seg_cb.setChecked(True)
        config_layout.addWidget(self.plot_seg_cb)

        self.plot_zs_cb = QCheckBox("线段中枢")
        self.plot_zs_cb.setChecked(True)
        config_layout.addWidget(self.plot_zs_cb)

        self.plot_bsp_cb = QCheckBox("线段买卖点")
        self.plot_bsp_cb.setChecked(True)
        config_layout.addWidget(self.plot_bsp_cb)

        self.plot_macd_cb = QCheckBox("MACD")
        # 默认不显示MACD，让K线视图铺满整个窗口的剩余面积
        self.plot_macd_cb.setChecked(False)
        config_layout.addWidget(self.plot_macd_cb)

        config_layout.addStretch()

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新图表")
        self.refresh_btn.clicked.connect(self.refresh_chart)
        config_layout.addWidget(self.refresh_btn)

        layout.addLayout(config_layout)

        # matplotlib 画布
        self.canvas = ChanPlotCanvas(panel, width=12, height=8)
        self.toolbar = NavigationToolbar(self.canvas, panel)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        return panel

    def _update_rule_hint(self):
        """刷新"笔划分规则"说明文字，并提示需要重新分析"""
        bi_type = self.bi_type_combo.currentData()
        bi_fx = self.bi_fx_combo.currentData()
        if bi_type == "old":
            type_text = "旧笔（严格：分型不共用K线 + 顶底之间≥1根独立K线）"
        else:
            type_text = "新笔（分型不共用K线 + 顶底之间≥3根原始K线）"
        fx_text_map = {
            "loss": "loss（原文第77课：顶分型最高K线区间需部分高于底分型最低K线区间）",
            "half": "half（额外要求顶/底分型相邻K线也拉开，比原文严）",
            "strict": "strict（两分型两侧各3根K线全部纳入比较，最严）",
        }
        self.rule_hint.setText(
            f"笔划分规则: {type_text}\n"
            f"分型校验: {fx_text_map.get(bi_fx, bi_fx)}\n"
            "笔尾极值约束: 关（原文无此条款）"
        )
        status_bar = getattr(self, "statusBar", None)
        if status_bar is not None and hasattr(status_bar, "showMessage"):
            status_bar.showMessage("笔划分参数已修改，请重新点击「分析」或「导入本地TXT数据」生效")

    def get_chan_config(self):
        """
        获取缠论分析配置

        Returns:
            CChanConfig: 包含笔划分、买卖点类型等配置的对象
        """
        bi_type = self.bi_type_combo.currentData() if hasattr(self, "bi_type_combo") else "new"
        bi_fx = self.bi_fx_combo.currentData() if hasattr(self, "bi_fx_combo") else "loss"
        return CChanConfig({
            "bi_strict": (bi_type == "old"),  # 笔类型: 新笔(False)/旧笔(True)，由界面下拉框决定
            "bi_fx_check": bi_fx,  # 分型有效性校验: loss(默认,原文)/half(原程序默认)/strict
            # 笔尾极值约束（原文没有这条）：开启时若笔内出现过"无法成笔的分型极值"（如跳空/急跌造成的
            # 顶底过近极值），后续所有合格分型都会被判 False，笔链会永久停止推进（AUL9 2026-11-06 午休后即如此）。
            "bi_end_is_peak": False,
            "trigger_step": False,  # 不启用逐步触发模式
            "skip_step": 0,
            "divergence_rate": float("inf"),  # 背驰比率
            "bsp2_follow_1": False,  # 二类买卖点不跟随一类
            "bsp3_follow_1": False,  # 三类买卖点不跟随一类
            "min_zs_cnt": 0,  # 最小中枢数量
            "bs1_peak": False,
            "macd_algo": "peak",  # MACD 算法
            "bs_type": "1,1p,2,2s,3a,3b",  # 启用的买卖点类型
            "print_warning": False,
            "zs_algo": "normal",  # 中枢算法
            "cal_bi_zs": False,  # 不计算笔级别中枢（未绘制，省算力）
            "cal_bi_bsp": False,  # 不计算笔级别买卖点（未绘制，省算力）
        })

    def get_plot_config(self):
        """
        获取图表绑定配置

        Returns:
            dict: 包含各图层显示开关的配置字典
        """
        return {
            "plot_kline": self.plot_kline_cb.isChecked(),  # 显示K线
            "plot_kline_combine": True,  # 显示合并K线
            "plot_bi": self.plot_bi_cb.isChecked(),  # 显示笔
            "plot_seg": self.plot_seg_cb.isChecked(),  # 显示线段
            "plot_zs": False,  # 不显示笔级别中枢
            "plot_segzs": self.plot_zs_cb.isChecked(),  # 显示线段级别中枢
            "plot_macd": self.plot_macd_cb.isChecked(),  # 显示MACD
            "plot_bsp": False,  # 不显示笔级别买卖点
            "plot_segbsp": self.plot_bsp_cb.isChecked(),  # 显示线段级别买卖点
        }

    def analyze_single(self):
        """分析单只股票"""
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return
        self.analyze_stock(code)

    def analyze_stock(self, code):
        """分析指定股票"""
        self.analyze_btn.setEnabled(False)
        period_text = self.period_combo.currentText()
        self.statusBar.showMessage(f'正在分析 {code} ({period_text})...')

        config = self.get_chan_config()
        self.analysis_thread = SingleAnalysisThread(code, config, period_text=period_text, days=365)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()

    def import_local_txt(self):
        """
        导入本地通达信导出的 TXT 数据文件（1分钟线）并进行分析。

        通过文件对话框选择 TXT 文件，然后使用 TDX_TXT_API 数据源进行缠论分析。
        可查看完整的本地历史数据（不受腾讯接口320根限制）。

        通达信导出的秒级K线（如5秒）时间格式为"日/时:分:秒"（如 12/10:31:45），
        没有月份和年份。程序默认按当前日期推断，但跨月/跨年时可能推断不准。
        因此导入时弹窗让用户可选填写数据所属年月，用于精确定位。
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择通达信导出的TXT数据文件",
            "",
            "通达信TXT文件 (*.txt);;所有文件 (*.*)",
        )
        if not file_path:
            return

        # 弹窗让用户可选填写数据所属年月（用于推断秒级K线无年份格式的月份年份）
        begin_time = self._ask_ref_year_month()
        if begin_time is None:
            return  # 用户取消

        self.analyze_btn.setEnabled(False)
        self.statusBar.showMessage(f'正在导入并分析本地数据: {os.path.basename(file_path)}...')

        config = self.get_chan_config()
        # 本地TXT文件使用 TDX_TXT_API 数据源，code 参数传入文件路径
        self.analysis_thread = SingleAnalysisThread(
            os.path.basename(file_path),
            config,
            period_text="1分钟",
            days=365,
            file_path=file_path,
            begin_time=begin_time,
        )
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()

    def read_from_tdx_live(self):
        """从通达信进程内存直接读取当前图表的K线并分析（免手工导出）。"""
        if not TDX_LIVE_AVAILABLE:
            QMessageBox.warning(
                self,
                "不可用",
                "未找到通达信内存直读模块 TdxBridge/mem_reader.py（或缺少 numpy）。\n"
                "请确认程序目录下有 TdxBridge 文件夹。",
            )
            return

        self.live_read_btn.setEnabled(False)
        self.statusBar.showMessage("正在从通达信内存读取当前图表K线（约5~15秒）...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            bars, meta = tdx_read_current_bars(install_key="new_tdxqh")
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.live_read_btn.setEnabled(True)
            QMessageBox.warning(
                self,
                "读取失败",
                "从通达信读取数据失败：\n%s\n\n请确认：\n"
                "1) 通达信期货通已打开，并已显示目标品种的K线图；\n"
                "2) 本程序与通达信以相同权限运行（不要只把其中一个用管理员运行）；\n"
                "3) 暂只支持期货通（new_tdxqh），证券端暂不支持。" % e,
            )
            self.statusBar.showMessage("读取通达信失败")
            return
        QApplication.restoreOverrideCursor()
        self.live_read_btn.setEnabled(True)

        step = int(meta.get("step") or 0)
        period_text = {1: "1秒", 5: "5秒", 10: "10秒", 15: "15秒", 30: "30秒", 60: "1分钟"}.get(
            step, "%d秒" % step
        )
        symbol = (meta.get("symbol") or "").strip() or "当前图"
        safe_symbol = re.sub(r'[\\/:*?"<>|]', "_", symbol)

        tmp_dir = os.path.join(tempfile.gettempdir(), "tdx_live")
        os.makedirs(tmp_dir, exist_ok=True)
        txt_path = os.path.join(tmp_dir, "%s_%ss.txt" % (safe_symbol, step))
        try:
            tdx_write_txt(txt_path, bars, title="%s (%s)" % (symbol, period_text))
            begin_time = tdx_ref_begin_time(bars)
        except Exception as e:
            QMessageBox.warning(self, "读取失败", "写出临时TXT失败：\n%s" % e)
            return

        first, last = meta["first"], meta["last"]
        self.code_input.setText(symbol)
        self.statusBar.showMessage(
            "已从通达信读取 %d 根 %s K线（%s，%04d-%02d-%02d %02d:%02d → %04d-%02d-%02d %02d:%02d），开始分析..."
            % (
                len(bars),
                period_text,
                symbol,
                first.date.year, first.date.month, first.date.day, first.hour, first.minute,
                last.date.year, last.date.month, last.date.day, last.hour, last.minute,
            )
        )

        self.analyze_btn.setEnabled(False)
        config = self.get_chan_config()
        self.analysis_thread = SingleAnalysisThread(
            safe_symbol,
            config,
            period_text=period_text,
            days=365,
            file_path=txt_path,
            begin_time=begin_time,
        )
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()

    def _ask_ref_year_month(self):
        """
        弹窗让用户可选填写数据所属年月（如 2026-08），用于推断通达信秒级K线
        无年份格式(日/时:分:秒)的月份年份，避免跨月/跨年时按当前日期推断不准。

        注意：填写的年月是"最后一个K线"（数据中最晚的那根）所属年月。
        程序会以它为基准，从后往前倒推前面K线的月份（跨月数据也能正确区分，
        如 7月30日-8月4日，填 8月 时 7月30-31日会自动归为7月）。

        返回:
            str or None: 用户填写的年月字符串（如 "2026-08"），
            用户留空则返回当前年月（自动推断），取消则返回 None。
        """
        from datetime import date
        today = date.today()
        default_text = f"{today.year}-{today.month:02d}"

        text, ok = QInputDialog.getText(
            self,
            "数据所属年月（可选）",
            "通达信秒级K线(如5秒)时间格式为 日/时:分:秒，没有月份年份。\n"
            "请填写数据中【最后一个K线】所属的年月（如 2026-08）。\n"
            "程序会以它为基准倒推前面K线的月份，跨月数据也能正确区分\n"
            "（如 7月30日-8月4日，填 8月 时 7月30-31日会自动归为7月）。\n"
            "若数据是最近一个月内的，可留空使用当前年月自动推断：",
            QLineEdit.EchoMode.Normal,
            default_text,
        )
        if not ok:
            return None  # 用户取消
        text = text.strip()
        if not text:
            return default_text  # 留空 -> 当前年月
        # 校验格式 YYYY-MM
        import re
        if re.match(r'^\d{4}-\d{1,2}$', text):
            return text
        QMessageBox.warning(self, "格式错误", "年月格式应为 YYYY-MM（如 2026-08），请重新填写。")
        return self._ask_ref_year_month()  # 重新询问

    def on_analysis_finished(self, chan):
        """单只股票分析完成"""
        self.chan = chan
        self.analyze_btn.setEnabled(True)
        self.plot_chart()
        self.statusBar.showMessage(f'分析完成: {chan.code}')

    def on_analysis_error(self, error_msg):
        """分析出错"""
        self.analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "分析错误", error_msg)
        self.statusBar.showMessage('分析失败')

    def export_tdx_seg_formula(self):
        """导出与当前数据周期一致的线段公式（原有按钮，行为不变）。"""
        self._export_tdx_seg_formula_impl(None)

    def export_tdx_seg_formula_mapped(self):
        """把当前线段按时间映射到目标周期（默认 5 分钟）后导出。"""
        period = 5
        if hasattr(self, "map_period_combo"):
            data = self.map_period_combo.currentData()
            if data:
                period = int(data)
        self._export_tdx_seg_formula_impl(period)

    def _update_map_period_hint(self):
        """映射周期下拉变化时，同步更新按钮文字。"""
        period = 5
        if hasattr(self, "map_period_combo"):
            data = self.map_period_combo.currentData()
            if data:
                period = int(data)
        if hasattr(self, "map_export_btn"):
            self.map_export_btn.setText(f"导出{period}分钟映射公式")
        if hasattr(self, "poly_export_btn"):
            self.poly_export_btn.setText(f"导出{period}分钟折线版")

    def _tdx_poly_cond(self, klu, map_period):
        """折线版定位条件：返回 (date_val, hour, minute)。

        把 K 线时间按"结束时刻"向上取整到目标周期的整点（与 DRAWLINE 映射版口径一致）。
        """
        t = klu.time
        date_val = 1000000 + (t.year % 100) * 10000 + t.month * 100 + t.day
        sec = t.hour * 3600 + t.minute * 60 + (getattr(t, 'second', 0) or 0)
        period_sec = max(int(map_period), 1) * 60
        label_sec = sec if sec % period_sec == 0 else ((sec // period_sec) + 1) * period_sec
        if label_sec >= 86400:
            label_sec -= 86400
        return date_val, label_sec // 3600, (label_sec % 3600) // 60

    @staticmethod
    def _tdx_poly_cond_str(cond):
        """把 (date_val, hour, minute) 拼成通达信定位条件字符串。"""
        date_val, hour, minute = cond
        if hour == 0 and minute == 0:
            return f"DATE={date_val} AND TIME=0"
        return f"DATE={date_val} AND TIME={hour * 100 + minute}"

    def export_tdx_polyline_formula(self):
        """折线版导出：用一条 PLOYLINE 画出全部线段（可选叠加红色未确定末段）。

        背景（已在通达信里实测确认）：
          - 公式最多 100 个输出，每条 PLOYLINE 只算 1 个输出；
          - 单条折线的顶点数不受限，但每句最多 800 个单词；
          - **每条 PLOYLINE 的"最后一折"会变成一条射线向后无限延伸**，
            所以把线拆成很多条时，每条末尾都会飞出一条射线（画面混乱）。
        因此：每个线段端点写一句 `Vn:=IF(条件,价格,0)`，再分层求和成一条序列，
        最后只画一条 PLOYLINE。整条线只有一个末尾射线，且最后一个顶点就在
        最新K线上，射线看不见。未确定的末段再叠一条红色短线（其终点同样在
        最右端，也不会乱飞）。
        """
        if not self.chan:
            QMessageBox.warning(self, "警告", "请先分析一只股票，再导出折线版公式")
            return

        try:
            period = 5
            if hasattr(self, "map_period_combo"):
                data = self.map_period_combo.currentData()
                if data:
                    period = int(data)

            kl_list = self.chan[0]
            seg_list = kl_list.seg_list
            if len(seg_list) == 0:
                QMessageBox.warning(self, "警告", "当前没有划分出线段，无法导出")
                return

            # 1) 收集线段端点（起点、终点交替）
            raw_pts = []  # (cond, price)
            for seg in seg_list:
                raw_pts.append((
                    self._tdx_poly_cond(seg.start_bi.get_begin_klu(), period),
                    seg.start_bi.get_begin_val(),
                ))
                raw_pts.append((
                    self._tdx_poly_cond(seg.end_bi.get_end_klu(), period),
                    seg.end_bi.get_end_val(),
                ))

            # 2) 相邻同一根目标周期K线的点合并（线段可能被压缩到同一根K线内），保留靠后的点
            vertices = []
            for cond, price in raw_pts:
                if vertices and vertices[-1][0] == cond:
                    vertices[-1] = (cond, price)
                else:
                    vertices.append((cond, price))

            # 3) 找出末尾连续的"未确定"线段，单独生成红色覆盖短线
            tail_start = len(seg_list)
            for i in range(len(seg_list) - 1, -1, -1):
                if seg_list[i].is_sure:
                    break
                tail_start = i
            tail_pts = []
            if tail_start < len(seg_list):
                tail_pts.append((
                    self._tdx_poly_cond(seg_list[tail_start].start_bi.get_begin_klu(), period),
                    seg_list[tail_start].start_bi.get_begin_val(),
                ))
                for seg in seg_list[tail_start:]:
                    tail_pts.append((
                        self._tdx_poly_cond(seg.end_bi.get_end_klu(), period),
                        seg.end_bi.get_end_val(),
                    ))
                dedup = []
                for cond, price in tail_pts:
                    if dedup and dedup[-1][0] == cond:
                        dedup[-1] = (cond, price)
                    else:
                        dedup.append((cond, price))
                tail_pts = dedup

            if len(vertices) > 600:
                reply = QMessageBox.question(
                    self,
                    "顶点较多",
                    (
                        f"当前线段端点映射后有 {len(vertices)} 个顶点，对应的公式语句数量较多，\n"
                        "通达信可能提示「语句数超过上限」。是否继续导出？\n\n"
                        "（若报错，可缩短导入的历史数据范围后重试）"
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            lines = []
            lines.append("{缠论线段折线版 - 由 chan.py 自动生成}")
            lines.append(
                f"{{股票: {self.chan.code}  线段数: {len(seg_list)}  "
                f"顶点数: {len(vertices)}  映射周期: {int(period)}分钟}}"
            )
            lines.append("{导入方法: 通达信 -> 功能 -> 公式系统 -> 公式管理器 -> 新建 -> 技术指标公式}")
            lines.append(
                f"{{重要: 本文件是 {int(period)} 分钟映射版本，"
                f"请贴在 {int(period)} 分钟K线图上，不要贴在当前级别图上}}"
            )
            lines.append("{说明: 全部线段用一条 PLOYLINE 折线画出（黄色）；末尾的未确定线段用红色短线覆盖}")
            lines.append("{说明: 通达信每条折线的最后一折会向后延伸成射线；本文件只有1~2条折线，最后顶点在最新K线上，故看不到射线}")
            lines.append("{说明: 期货夜盘K线的日期用交易日标注，与通达信一致，无需改动}")
            lines.append("")

            def _emit_var_block(pts, prefix, out_lines):
                """为一条折线生成变量语句，返回汇总变量名。"""
                names = []
                for i, (cond, price) in enumerate(pts, 1):
                    name = f"{prefix}{i}"
                    names.append(name)
                    out_lines.append(f"{name}:=IF({self._tdx_poly_cond_str(cond)},{price:.2f},0);")
                group_names = []
                for gi in range(0, len(names), 25):
                    gname = f"{prefix}G{len(group_names) + 1}"
                    out_lines.append(f"{gname}:=" + "+".join(names[gi:gi + 25]) + ";")
                    group_names.append(gname)
                total_name = f"{prefix}TOTAL"
                out_lines.append(f"{total_name}:=" + "+".join(group_names) + ";")
                return total_name

            yellow_total = _emit_var_block(vertices, "V", lines)
            lines.append(f"PLOYLINE({yellow_total}>0,{yellow_total}),COLORYELLOW,LINETHICK1;")

            if len(tail_pts) >= 2:
                lines.append("")
                lines.append("{===== 未确定线段（红色覆盖，末尾连续未确定段）=====}")
                red_total = _emit_var_block(tail_pts, "W", lines)
                lines.append(f"PLOYLINE({red_total}>0,{red_total}),COLORRED,LINETHICK1;")

            content = "\n".join(lines) + "\n"

            default_name = f"chan_seg_{self.chan.code}_{int(period)}m_polyline.tni"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"保存通达信折线版公式({int(period)}分钟映射)",
                default_name,
                "通达信公式文件 (*.tni);;文本文件 (*.txt);;所有文件 (*.*)",
            )
            if not file_path:
                return

            with open(file_path, 'w', encoding='gbk', errors='ignore') as f:
                f.write(content)

            self.statusBar.showMessage(
                f'已导出通达信折线版公式({int(period)}分钟映射): {file_path} '
                f'({len(seg_list)}条线段/{len(vertices)}个顶点，请贴在{int(period)}分钟图上)'
            )

            reply = QMessageBox.question(
                self,
                "导出成功",
                (
                    f"已导出 {len(seg_list)} 条线段（{len(vertices)} 个顶点）到:\n{file_path}\n\n"
                    f"这是 {int(period)} 分钟折线版，请把公式贴到 {int(period)} 分钟K线图上。\n"
                    f"黄色=全部线段，红色=末尾未确定线段。\n\n"
                    "是否立即打开该通达信公式文件？"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.startfile(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "打开失败", f"无法打开文件:\n{file_path}\n\n错误: {e}")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))

    def _export_tdx_seg_formula_impl(self, map_period=None):
        """
        将当前分析的线段划分导出为通达信公式文件(.tni)。

        参数 map_period：为 None 时按当前数据周期导出（原行为）；
        传入目标周期（分钟）时，把每个端点按时间映射到目标周期的K线上，
        例如 10 秒数据算出的线段，映射到 5 分钟后可以贴在 5 分钟K线图上。
        映射口径（已与通达信实际数据核对）：
          - 通达信分钟K线以"结束时刻"标注：21:00:10 属于 21:05 那根；
          - 期货夜盘的K线日期用"交易日"标注（如 11/06 21:05 那根，DATE=11/09），
            与从通达信导出的 TXT 中的日期口径一致，因此映射时保留原 K 线日期不变；
          - 端点时间正好落在目标周期整点上（秒=0、分能被周期整除）时，就取该整点。

        通达信公式使用 DRAWLINE 函数在K线图上画线段：
            DRAWLINE(COND1, PRICE1, COND2, PRICE2, EXPAND)
        其中 COND 为条件，PRICE 为价格。

        定位K线用时间(DATE/TIME)而非序号(BARSCOUNT)：
        用户从通达信导出的TXT数据是"当前视图区间"的K线，不是全部历史数据。
        若用 BARSCOUNT(CLOSE)=N 按序号定位，当用户在通达信中缩放K线图时，
        通达信加载的K线数量会变化，序号 N 对应的实际K线就变了，导致划线偏移。

        正确做法是用时间定位：通达信公式的 DATE 返回当前K线日期(1YYMMDD，
        如 1260803 = 2026-08-03)，TIME 返回当前K线时间(HHMMSS，如 218 = 02:18:00)。
        线段端点所在的K线有确定的时间，用 DATE=xxx AND TIME=xxx 就能唯一、
        准确地定位到那根K线，无论通达信加载了多少K线、如何缩放，都不会偏移。

        每个线段用一条 DRAWLINE 从起点K线(价格)画到终点K线(价格)。
        起点=线段起始笔的起点K线，终点=线段结束笔的落点K线。
        不追求线段内部最高/最低点的精确画法（那需要遍历线段内所有笔，
        算力消耗大，线段多时会导致导出卡死），直接用线段起始笔起点和
        结束笔落点即可，简单高效。
        确定线段(is_sure=True)用实线，未确定线段(is_sure=False)用虚线。
        """
        if not self.chan:
            QMessageBox.warning(self, "警告", "请先分析一只股票，再导出线段公式")
            return

        try:
            kl_list = self.chan[0]  # 当前级别 CKLine_List
            seg_list = kl_list.seg_list  # CSegListComm，可迭代

            if len(seg_list) == 0:
                QMessageBox.warning(self, "警告", "当前没有划分出线段，无法导出")
                return

            # 判断当前数据是否为秒级K线（如5秒）。
            # 秒级K线的秒字段非零（如 00:00:05），分钟级K线秒恒为0。
            # 秒级K线同一分钟内有多根，通达信 TIME 只精确到分钟无法唯一定位，
            # 必须改用 TIME0（返回从0点起的秒数，精确到秒）才能唯一锁定K线。
            is_second_level = any(
                getattr(klc.lst[0].time, 'second', 0) != 0
                for klc in kl_list.lst
                if klc.lst
            )

            def _ceil_to_period_label(t, period_min):
                """把时刻向上取整到目标周期的整点（以结束时刻标注）。

                例：10 秒数据 11:03:30 → 5 分钟周期的 11:05 那根K线；
                正好落在整点（秒=0 且分能被周期整除）时就用该整点本身，
                因为通达信分钟K线标注的是结束时刻（21:00:10 属于 21:05 那根）。

                返回 (hour, minute)；若跨过 24:00，则时间回到 00:00，
                日期保持原交易日不变（期货夜盘K线的日期用交易日标注）。
                """
                sec = t.hour * 3600 + t.minute * 60 + (getattr(t, 'second', 0) or 0)
                period_sec = period_min * 60
                label_sec = sec if sec % period_sec == 0 else ((sec // period_sec) + 1) * period_sec
                if label_sec >= 86400:
                    label_sec -= 86400
                return label_sec // 3600, (label_sec % 3600) // 60

            def _make_time_cond(klu):
                """根据K线时间生成通达信定位条件

                通达信 DATE 函数返回 1YYMMDD 格式（7位，如 1260812 = 2026-08-12），
                即"1" + 年份后两位 + 月 + 日。注意：不是 YYYYMMDD！
                通达信 TIME 函数返回 HHMM 格式（如 218 = 02:18，前导零省略）。
                通达信 TIME2 函数返回 HHMMSS 格式（6位，如 103145 = 10:31:45），
                精确到秒，适用于日线以下周期，用于秒级K线（如5秒）唯一锁定
                同一分钟内的某一根K线。
                """
                t = klu.time
                # 通达信 DATE 返回 1YYMMDD（7位）：1000000 + (年份后两位)*10000 + 月*100 + 日
                date_val = 1000000 + (t.year % 100) * 10000 + t.month * 100 + t.day  # 1YYMMDD
                if map_period:
                    # 映射模式：把端点时间映射到目标周期K线的"结束时刻"上。
                    # 日期保持不变：通达信期货夜盘K线的日期本身就是交易日口径
                    # （如 11/06 21:05 的夜盘K线，DATE 是 11/09），与导出的 TXT 一致。
                    hour, minute = _ceil_to_period_label(t, int(map_period))
                    if hour == 0 and minute == 0:
                        return f"DATE={date_val} AND TIME=0"
                    return f"DATE={date_val} AND TIME={hour * 100 + minute}"
                # 注意：必须先判断秒级K线，再判断"时=0分=0"的日线分支。
                # 因为秒级K线在 00:00:50（时=0、分=0）时也会满足 hour==0 and minute==0，
                # 若先走日线分支会漏掉 TIME2，导致通达信定位到错误K线。
                if is_second_level:
                    # 秒级K线：用 TIME2（返回 HHMMSS，精确到秒）唯一定位到某一根秒K线
                    time2_val = t.hour * 10000 + t.minute * 100 + t.second  # HHMMSS
                    return f"DATE={date_val} AND TIME2={time2_val}"
                elif t.hour == 0 and t.minute == 0:
                    # 00:00 的K线（日线 或 期货夜盘/隔夜的 00:00 bar）。
                    # 注意：不能只用 DATE=xxx！因为期货分钟级数据同一日期有多根K线
                    # （00:00, 00:05, ..., 09:00, ..., 15:00），DATE=xxx 会匹配该日期
                    # 所有K线，导致通达信把线画到错误位置（画到该日期第一根或最后一根）。
                    # 必须加上 TIME=0 唯一定位到 00:00 这根K线。
                    # 对日线同样适用：日线K线在 00:00，TIME=0 也能唯一定位。
                    return f"DATE={date_val} AND TIME=0"
                else:
                    # 分钟线：通达信 TIME 返回 HHMM（4位）：时*100 + 分（前导零省略）
                    time_val = t.hour * 100 + t.minute  # HHMM
                    return f"DATE={date_val} AND TIME={time_val}"

            # 生成通达信公式内容
            # 注意：通达信公式注释使用大括号 {}，不能用 // 或 # 注释
            lines = []
            lines.append("{缠论线段划分 - 由 chan.py 自动生成}")
            if map_period:
                lines.append(
                    f"{{股票: {self.chan.code}  线段数: {len(seg_list)}  "
                    f"映射周期: {int(map_period)}分钟}}"
                )
            else:
                lines.append(f"{{股票: {self.chan.code}  线段数: {len(seg_list)}}}")
            lines.append("{导入方法: 通达信 -> 功能 -> 公式系统 -> 公式管理器 -> 新建 -> 技术指标公式}")
            if map_period:
                lines.append(
                    f"{{重要: 本文件是 {int(map_period)} 分钟映射版本，"
                    f"请贴在 {int(map_period)} 分钟K线图上，不要贴在当前级别图上}}"
                )
                lines.append(
                    f"{{说明: 线段来自更小级别数据的笔/线段，端点时间按"
                    f"\"结束时刻\"映射到 {int(map_period)} 分钟K线，价格不变}}"
                )
                lines.append("{说明: 期货夜盘K线的日期用交易日标注，与通达信一致，无需改动}")
            else:
                lines.append("{将以下内容粘贴到公式编辑器中，然后应用到对应K线周期即可}")
            lines.append("")
            lines.append("{说明: 用时间(DATE/TIME)定位K线，不用序号，缩放不偏移}")
            lines.append("{DATE 返回当前K线日期(1YYMMDD)，TIME 返回当前K线时间(HHMM)}")
            lines.append("{线段端点K线有确定时间，用时间可唯一定位，不受缩放影响}")
            lines.append("")

            # 每条线段用一条 DRAWLINE 画线，起点=线段起始笔的起点K线(价格)，
            # 终点=线段结束笔的落点K线(价格)。
            # 说明：不追求线段内部最高/最低点的精确画法（那需要遍历线段内所有笔，
            # 算力消耗大，线段多时会导致导出卡死），直接用线段起始笔的起点和
            # 结束笔的落点即可，简单高效。
            #   DRAWLINE(COND1, PRICE1, COND2, PRICE2, EXPAND)
            # 每条语句很短，不会产生超长嵌套表达式，导出快速不卡死。
            sure_lines = []
            unsure_lines = []
            for seg in seg_list:
                begin_klu = seg.start_bi.get_begin_klu()
                begin_price = seg.start_bi.get_begin_val()
                end_klu = seg.end_bi.get_end_klu()
                end_price = seg.end_bi.get_end_val()
                begin_cond = _make_time_cond(begin_klu)
                end_cond = _make_time_cond(end_klu)
                # 所有线段统一：粗细=1，颜色=黄色
                # 通达信绘图函数后可用 ,COLORxxx 和 ,LINETHICKn 指定颜色与粗细
                drawline = (
                    f"DRAWLINE({begin_cond}, {begin_price:.2f}, "
                    f"{end_cond}, {end_price:.2f}, 0),COLORYELLOW,LINETHICK1;"
                )
                if seg.is_sure:
                    sure_lines.append(drawline)
                else:
                    unsure_lines.append(drawline)

            # 通达信公式：所有线段统一黄色、粗细1
            lines.append("{===== 线段（黄色，粗细1）=====}")
            for dl in sure_lines:
                lines.append(dl)

            if unsure_lines:
                lines.append("")
                lines.append("{===== 未确定线段（黄色，粗细1）=====}")
                for dl in unsure_lines:
                    lines.append(dl)

            content = "\n".join(lines) + "\n"

            # 选择保存路径
            if map_period:
                default_name = f"chan_seg_{self.chan.code}_{int(map_period)}m.tni"
                dlg_title = f"保存通达信线段公式({int(map_period)}分钟映射)"
            else:
                default_name = f"chan_seg_{self.chan.code}.tni"
                dlg_title = "保存通达信线段公式"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                dlg_title,
                default_name,
                "通达信公式文件 (*.tni);;文本文件 (*.txt);;所有文件 (*.*)",
            )
            if not file_path:
                return

            # 通达信公式文件通常使用 GBK 编码
            with open(file_path, 'w', encoding='gbk', errors='ignore') as f:
                f.write(content)

            if map_period:
                self.statusBar.showMessage(
                    f'已导出通达信线段公式({int(map_period)}分钟映射): {file_path} '
                    f'({len(seg_list)}条线段，请贴在{int(map_period)}分钟图上)'
                )
            else:
                self.statusBar.showMessage(f'已导出通达信线段公式: {file_path} ({len(seg_list)}条线段)')

            # 询问是否打开导出的公式文件
            reply = QMessageBox.question(
                self,
                "导出成功",
                (
                    f"已导出 {len(seg_list)} 条线段到:\n{file_path}\n\n"
                    + (
                        f"这是 {int(map_period)} 分钟映射版本，请把公式贴到 {int(map_period)} 分钟K线图上。\n\n"
                        if map_period else ""
                    )
                    + "是否立即打开该通达信公式文件？"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # 用系统默认程序打开文件（Windows 下通达信公式文件通常关联到记事本）
                    os.startfile(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "打开失败", f"无法打开文件:\n{file_path}\n\n错误: {e}")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", str(e))

    def plot_chart(self):
        """
        绑定当前股票的缠论分析图表

        使用 CPlotDriver 生成图表，显示K线、笔、线段、中枢等元素。
        图表大小会根据画布宽度自动调整。

        交互功能:
            - 鼠标滚轮: 以鼠标位置为中心缩放K线
            - 按住左键拖动: 平移查看K线
            - 双击: 恢复全部K线视图
        """
        if not self.chan:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            # 关闭旧的 figure 释放内存
            plt.close('all')

            plot_config = self.get_plot_config()

            # 获取控件宽度，计算合适的图表尺寸
            canvas_width = self.canvas.width()
            dpi = 100
            fig_width = canvas_width / dpi
            fig_height = fig_width * 0.5  # 宽高比 2:1

            # 初始显示最近的一批K线（约500根），避免一次性绘制全部数千根K线导致卡顿。
            # 用户可通过滚轮缩放查看更早的历史数据。
            plot_para = {
                "figure": {
                    "x_range": 500,  # 初始显示最近500根K线，0表示全部
                    "w": fig_width,
                    "h": fig_height,
                }
            }

            plot_driver = CPlotDriver(self.chan, plot_config=plot_config, plot_para=plot_para)

            # 保存 plot_driver 引用，供滚轮缩放时重新绘制更多K线使用
            self._plot_driver = plot_driver

            self.canvas.fig = plot_driver.figure
            self.canvas.figure = plot_driver.figure

            # 绑定交互事件（滚轮缩放 + 拖动平移）
            self._bind_chart_interaction()

            self.canvas.draw()
            self.toolbar.update()
        except Exception as e:
            QMessageBox.critical(self, "绑定错误", str(e))

    def _build_idx_time_map(self):
        """
        构建 K线索引 -> 时间字符串 的映射，用于十字光标显示精确时间。
        遍历当前级别所有K线单元，记录每个 idx 对应的时间。
        """
        self._idx_time_map = {}
        try:
            if not self.chan:
                return
            kl_list = self.chan[0]  # 当前级别 CKLine_List
            for klc in kl_list.lst:  # 遍历合并K线 CKLine
                for klu in klc.lst:  # 遍历K线单元 CKLine_Unit
                    self._idx_time_map[klu.idx] = klu.time.to_str()
        except Exception:
            self._idx_time_map = {}

    def _update_y_range_for_view(self, ax):
        """
        根据当前 x 轴视图范围，重新计算 y 轴范围（顶格缩放）。

        遍历当前视图内的合并K线，取最高点和最低点，并留出少量上下边距，
        使K线在缩放后能顶格显示在图表中。
        """
        try:
            if not self.chan:
                return
            x_min, x_max = ax.get_xlim()
            kl_list = self.chan[0]  # 当前级别 CKLine_List
            y_min = float('inf')
            y_max = float('-inf')
            # 注意：x轴坐标使用的是K线单元(CKLine_Unit)的idx，
            # 因此必须遍历K线单元而不是合并K线(CKLine)，否则y轴范围会计算错误
            for klc in kl_list.lst:  # 遍历合并K线 CKLine
                for klu in klc.lst:  # 遍历K线单元 CKLine_Unit
                    if klu.idx < x_min - 1:
                        continue
                    if klu.idx > x_max + 1:
                        break
                    if klu.high > y_max:
                        y_max = klu.high
                    if klu.low < y_min:
                        y_min = klu.low
            if y_min == float('inf') or y_max == float('-inf'):
                return
            # 留出上下边距（约5%），避免K线贴边
            pad = (y_max - y_min) * 0.05
            if pad <= 0:
                pad = 1.0
            ax.set_ylim(y_min - pad, y_max + pad)
        except Exception:
            pass

    def _bind_chart_interaction(self):
        """
        绑定图表的鼠标交互事件:
            - 滚轮: 以鼠标位置为中心缩放（顶格缩放，y轴自动适配当前视图最高最低点）
            - 左键拖动: 平移视图
            - 右键拖动框选: 框选缩放（x轴缩放到框选的时间区间，y轴按K线上下顶格缩放）
            - 双击: 恢复全部视图
            - 十字光标: 鼠标移动时显示十字线 + 精确时间
        """
        # 断开旧的连接，避免重复绑定
        for cid in getattr(self, '_chart_cids', []):
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._chart_cids = []

        # 拖动平移状态
        self._drag_start_x = None
        self._drag_start_xlim = None

        # 框选缩放状态（右键拖动）
        self._box_select_start = None
        self._box_rect = None

        # 构建 K线索引 -> 时间 映射
        self._build_idx_time_map()

        # 十字光标相关状态
        self._cross_vline = None
        self._cross_hline = None
        self._cross_text = None

        # 滚轮缩放（顶格缩放：缩放后y轴自动适配当前视图最高最低点）
        def on_scroll(event):
            if event.inaxes is None:
                return
            ax = event.inaxes
            x_min, x_max = ax.get_xlim()
            x_range = x_max - x_min
            if x_range <= 0:
                return
            # 缩放比例
            scale = 0.8 if event.button == 'up' else 1.25
            new_range = x_range * scale
            # 以鼠标位置为中心缩放
            mouse_x = event.xdata
            if mouse_x is None:
                return
            # 鼠标位置在视图中的比例
            ratio = (mouse_x - x_min) / x_range
            new_min = mouse_x - new_range * ratio
            new_max = new_min + new_range
            # 限制最小显示范围（至少显示 10 根K线）
            if new_range < 10:
                return
            ax.set_xlim(new_min, new_max)
            # 滚轮向下（缩小，显示更多K线）时，需要重新绘制更多K线，
            # 因为初始只绘制了最近500根K线的图形对象，缩小后需要补充绘制更早的历史K线
            if event.button == 'down':
                try:
                    if getattr(self, '_plot_driver', None) is not None:
                        self._plot_driver.redraw(ax)
                except Exception:
                    pass
            # 顶格缩放：根据当前视图内的K线最高最低点重新计算y轴范围
            self._update_y_range_for_view(ax)
            self.canvas.draw_idle()

        # 按下鼠标（记录起点，用于平移或框选缩放）
        def on_press(event):
            if event.inaxes is None:
                return
            if event.button == 1:  # 左键：平移
                self._drag_start_x = event.xdata
                self._drag_start_xlim = event.inaxes.get_xlim()
            elif event.button == 3:  # 右键：框选缩放
                self._box_select_start = (event.xdata, event.ydata)
                self._box_rect = None

        # 鼠标移动：绘制十字光标 + 拖动平移 + 框选矩形
        def on_motion(event):
            if event.inaxes is None:
                return
            ax = event.inaxes

            # 框选缩放：右键拖动时绘制选择矩形
            if self._box_select_start is not None and event.xdata is not None and event.ydata is not None:
                # 移除旧的矩形
                if self._box_rect is not None:
                    try:
                        self._box_rect.remove()
                    except Exception:
                        pass
                x0, y0 = self._box_select_start
                x1, y1 = event.xdata, event.ydata
                x_left, x_right = min(x0, x1), max(x0, x1)
                y_bottom, y_top = min(y0, y1), max(y0, y1)
                self._box_rect = ax.add_patch(plt.Rectangle(
                    (x_left, y_bottom), x_right - x_left, y_top - y_bottom,
                    fill=True, facecolor='blue', alpha=0.2, edgecolor='blue', linewidth=1
                ))
                try:
                    self.canvas.draw_artist(ax)
                    self.canvas.blit(ax.bbox)
                except Exception:
                    self.canvas.draw_idle()
                return

            # 十字光标：找到最近的K线索引并显示时间
            if event.xdata is not None and event.ydata is not None:
                nearest_idx = int(round(event.xdata))
                # 移除旧的十字线
                for line in (self._cross_vline, self._cross_hline):
                    if line is not None:
                        try:
                            line.remove()
                        except Exception:
                            pass
                if self._cross_text is not None:
                    try:
                        self._cross_text.remove()
                    except Exception:
                        pass
                self._cross_vline = self._cross_hline = self._cross_text = None

                # 画十字线
                self._cross_vline = ax.axvline(nearest_idx, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
                self._cross_hline = ax.axhline(event.ydata, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)

                # 显示时间文本（在轴顶部）
                time_str = self._idx_time_map.get(nearest_idx, '')
                if time_str:
                    x_min, x_max = ax.get_xlim()
                    self._cross_text = ax.text(
                        nearest_idx, ax.get_ylim()[1],
                        f'  {time_str}  ',
                        va='top', ha='left',
                        fontsize=9, color='white',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='#333333', alpha=0.85)
                    )
                # 性能优化：只重绘十字光标相关元素，避免每次鼠标移动都重绘整个画布（数千根K线）
                try:
                    self.canvas.draw_artist(ax)
                    self.canvas.blit(ax.bbox)
                except Exception:
                    self.canvas.draw_idle()

            # 拖动平移
            if self._drag_start_x is not None and event.xdata is not None:
                x_min, x_max = self._drag_start_xlim
                x_range = x_max - x_min
                # 计算拖动偏移量
                dx = self._drag_start_x - event.xdata
                ax.set_xlim(x_min + dx, x_max + dx)
                # 平移后同样顶格缩放y轴
                self._update_y_range_for_view(ax)
                self.canvas.draw_idle()

        # 松开鼠标
        def on_release(event):
            # 右键松开：应用框选缩放
            if event.button == 3 and self._box_select_start is not None and event.inaxes is not None:
                ax = event.inaxes
                x0 = self._box_select_start[0]
                x1 = event.xdata
                # 移除选择矩形
                if self._box_rect is not None:
                    try:
                        self._box_rect.remove()
                    except Exception:
                        pass
                    self._box_rect = None
                if x0 is not None and x1 is not None:
                    x_left, x_right = min(x0, x1), max(x0, x1)
                    # 至少框选1根K线才生效
                    if x_right - x_left > 1:
                        cur_min, cur_max = ax.get_xlim()
                        # (a) X轴：缩放到框选的时间区间
                        ax.set_xlim(x_left, x_right)
                        # 如果框选范围比当前视图大（缩小显示更多K线），需要重新绘制更多K线
                        if (x_right - x_left) > (cur_max - cur_min):
                            try:
                                if getattr(self, '_plot_driver', None) is not None:
                                    self._plot_driver.redraw(ax)
                            except Exception:
                                pass
                        # (b) Y轴：按照K线上下顶格缩放
                        self._update_y_range_for_view(ax)
                        self.canvas.draw_idle()
                self._box_select_start = None
                return
            self._drag_start_x = None
            self._drag_start_xlim = None

        # 双击恢复全部视图
        def on_double_click(event):
            if event.dblclick and event.inaxes is not None:
                ax = event.inaxes
                # 获取该轴对应的全部数据范围
                all_x = [line.get_xdata() for line in ax.lines if len(line.get_xdata()) > 0]
                if all_x:
                    x_min = min(min(xs) for xs in all_x)
                    x_max = max(max(xs) for xs in all_x)
                    ax.set_xlim(x_min, x_max)
                    # 恢复全部视图后，y轴也适配全部K线的最高最低点
                    self._update_y_range_for_view(ax)
                    self.canvas.draw_idle()

        self._chart_cids.append(self.canvas.mpl_connect('scroll_event', on_scroll))
        self._chart_cids.append(self.canvas.mpl_connect('button_press_event', on_press))
        self._chart_cids.append(self.canvas.mpl_connect('motion_notify_event', on_motion))
        self._chart_cids.append(self.canvas.mpl_connect('button_release_event', on_release))
        self._chart_cids.append(self.canvas.mpl_connect('button_press_event', on_double_click))

    def refresh_chart(self):
        """刷新图表"""
        self.plot_chart()


def main():
    """程序入口函数，创建并运行 GUI 应用"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 风格，跨平台一致性好

    window = AkshareGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
