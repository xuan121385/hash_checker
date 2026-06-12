"""
HashPanel — 右侧面板：哈希计算与对比
======================================
提供哈希计算的完整交互界面，包括算法选择、进度显示、
结果输出和校验值对比。

交互流程:
  1. 用户点击 SHA-256 或 SHA-3 按钮 → 发射 algorithm_selected 信号
  2. 用户在对比输入框中粘贴校验值 → 自动检测算法 → 发射 compare_requested 信号
  3. 主窗口启动后台计算 → 调用 set_progress() 更新进度条
  4. 计算完成 → 调用 show_result() 显示结果并自动复制到剪贴板
  5. 出错 → 调用 show_error() 显示错误信息

智能对比:
  当用户在"对比校验"输入框中粘贴一个十六进制哈希值时，
  _detect_algo_from_length() 根据字符串长度自动判断算法:
    64 个字符 → SHA-256
    128 个字符 → SHA-3
  检测到算法后自动发射 compare_requested 信号，主窗口立即
  启动计算并与粘贴值对比。

自动复制:
  show_result() 计算出哈希值后自动写入系统剪贴板，
  状态栏显示"✅ 哈希值已自动复制到剪贴板"，2.5 秒后自动消失。
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,   # 用于访问系统剪贴板 QApplication.clipboard()
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,      # 单行文本输入框（对比校验值输入）
    QProgressBar,   # 进度条
    QPushButton,
    QTextEdit,      # 多行文本只读区域（哈希结果输出）
    QVBoxLayout,
    QSizePolicy,
)


class HashPanel(QFrame):
    """
    右侧哈希计算与校验面板。

    内部结构:
      ┌── glassPanel (卡片容器) ────────────┐
      │   "哈希校验值" 标题                   │
      │   [ SHA-256 ] [ SHA-3 ]  算法按钮行   │
      │   ━━━━━━━━━━━━━━━━━━━  进度条      │
      │   ┌──────────────────────┐           │
      │   │ 粘贴校验值以自动对比... │ 对比输入框  │
      │   └──────────────────────┘           │
      │   ┌──────────────────────┐           │
      │   │ SHA-256              │           │
      │   │ ────────────────      │ 结果输出区  │
      │   │ a1b2c3...            │           │
      │   └──────────────────────┘           │
      │   ✅ 已自动复制到剪贴板    [SHA-256]  │ 状态行
      └──────────────────────────────────────┘

    Signals:
        algorithm_selected(str): 用户点击算法按钮，携带算法 key
        compare_requested(str, str): 用户粘贴了校验值，携带 (算法key, 清理后的哈希值)
    """

    # ---- Qt Signal 定义 ----
    algorithm_selected = Signal(str)
    compare_requested = Signal(str, str)

    # ---- 支持的算法列表 ----
    # 与 hash_engine.py 中的 ALGORITHMS 保持同步
    # 每个元素: (内部 key, 用户界面显示的名称)
    ALGORITHMS = [
        ("sha256",   "SHA-256"),
        ("sha3_512", "SHA-3"),
    ]

    # ---- 按钮 objectName 映射 ----
    # 用于在 QSS 中为不同按钮设置不同样式（虽然目前两按钮样式相同）
    BTN_OBJECT_NAMES = {
        "sha256":   "btnSHA256",
        "sha3_512": "btnSHA3",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hashPanel")
        self.setMinimumWidth(300)

        # 当前选中的算法 key（None = 尚未计算过）
        self._current_algo: str | None = None

        # 最近一次计算出的哈希值（缓存，供复制等用途）
        self._result_text: str = ""

        # 对比输入框中已清理的内容
        self._compare_text: str = ""

        # 自动消失定时器：显示"已复制"提示 2.5 秒后自动清空
        self._copy_timer: QTimer | None = None

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """构建 HashPanel 内部的全部控件和布局。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 卡片容器 ----
        card = QFrame(self)
        card.setProperty("class", "glassPanel")  # QSS .glassPanel 匹配
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 20)
        card_layout.setSpacing(14)

        # -- 标题 --
        title = QLabel("哈希校验值")
        title.setObjectName("hashTitle")
        card_layout.addWidget(title)

        # -- 算法按钮行 --
        # 两个按钮并排，等宽，使用 QSizePolicy.Expanding
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._buttons: dict[str, QPushButton] = {}  # key → button 映射

        for algo_key, algo_label in self.ALGORITHMS:
            btn = QPushButton(algo_label)
            obj_name = self.BTN_OBJECT_NAMES.get(algo_key, "")
            btn.setObjectName(obj_name)
            btn.setCursor(Qt.PointingHandCursor)
            # Expanding 策略: 按钮在水平方向均分可用空间
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # 绑定点击事件: 使用闭包捕获 algo_key
            btn.clicked.connect(self._make_click_handler(algo_key))
            self._buttons[algo_key] = btn
            btn_row.addWidget(btn)

        card_layout.addLayout(btn_row)

        # -- 进度条 --
        # 默认隐藏，计算开始时通过 set_progress() 显示
        self._progress = QProgressBar()
        self._progress.setObjectName("hashProgress")
        self._progress.setRange(0, 100)        # 范围 0-100%
        self._progress.setValue(0)
        self._progress.setTextVisible(False)    # 不显示百分比数字（纯色条）
        self._progress.setVisible(False)        # 初始隐藏
        self._progress.setFixedHeight(4)        # 细线风格
        card_layout.addWidget(self._progress)

        # -- 对比校验输入框 --
        # 用户在此粘贴期望的哈希值，触发自动对比
        self._compare_input = QLineEdit()
        self._compare_input.setObjectName("compareInput")
        self._compare_input.setPlaceholderText("粘贴他人提供的校验值以自动对比...")
        self._compare_input.setClearButtonEnabled(True)  # 右侧显示一键清除按钮
        # textChanged 在每次文本变化时触发（包括粘贴、手打、删除）
        self._compare_input.textChanged.connect(self._on_compare_text_changed)
        card_layout.addWidget(self._compare_input)

        # -- 结果输出区 --
        # QTextEdit 支持多行文本展示，设为只读
        self._output = QTextEdit()
        self._output.setObjectName("resultOutput")
        self._output.setReadOnly(True)  # 用户不能编辑
        self._output.setPlaceholderText("选择文件后点击上方按钮开始校验...")
        self._output.setMinimumHeight(120)
        # Expanding 策略: 在垂直方向占据剩余空间
        self._output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout.addWidget(self._output, 1)  # stretch=1

        # -- 底部状态行 --
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 2, 0, 0)

        # 左侧: 状态信息（如 "✅ 哈希值已自动复制到剪贴板"）
        self._status_label = QLabel("")
        self._status_label.setObjectName("copyStatusLabel")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status_row.addWidget(self._status_label, 1)

        # 右侧: 当前算法标签（如 "SHA-256"）
        self._algo_tag = QLabel("")
        self._algo_tag.setObjectName("algoTag")
        status_row.addWidget(self._algo_tag)

        card_layout.addLayout(status_row)
        root.addWidget(card)

        # -- 自动消失定时器 --
        # 单次触发: 2.5 秒后调用 _fade_out_status 清空状态文字
        self._copy_timer = QTimer(self)
        self._copy_timer.setSingleShot(True)  # 只触发一次，不循环
        self._copy_timer.timeout.connect(self._fade_out_status)

    # ------------------------------------------------------------------
    # Public API（主窗口调用）
    # ------------------------------------------------------------------

    def set_progress(self, percent: int) -> None:
        """
        更新进度条显示。

        在进度变化时由主窗口调用（响应 HashEngine.progress 信号）。

        Args:
            percent: 0-100 的整数百分比

        行为:
          - 首次调用时自动显示进度条
          - 到达 100% 时自动隐藏并归零（为下一次计算准备）
        """
        self._progress.setVisible(True)
        self._progress.setValue(percent)
        if percent >= 100:
            self._progress.setVisible(False)
            self._progress.setValue(0)

    def show_result(self, hex_digest: str, algo_key: str) -> None:
        """
        在输出区展示计算结果，并自动复制到系统剪贴板。

        Args:
            hex_digest: 十六进制哈希字符串
            algo_key: 使用的算法 key（用于显示算法名标签）

        输出格式示例:
          SHA-256
          ────────────────────────────────────────────────────────────────
          a1b2c3d4e5f6...
          ────────────────────────────────────────────────────────────────
          长度: 64 位十六进制
        """
        self._result_text = hex_digest
        self._current_algo = algo_key

        # 构建算法名映射（如 sha256 → SHA-256）
        algo_labels = {a[0]: a[1] for a in self.ALGORITHMS}
        algo_name = algo_labels.get(algo_key, algo_key)

        # 格式化输出文本
        display = (
            f"{algo_name}\n"
            f"{'─' * 64}\n"
            f"{hex_digest}\n"
            f"{'─' * 64}\n"
            f"长度: {len(hex_digest)} 位十六进制"
        )
        self._output.setPlainText(display)

        # 更新底部算法标签
        self._algo_tag.setText(algo_name)

        # 自动复制到剪贴板
        self._copy_to_clipboard(hex_digest)

    def show_error(self, message: str) -> None:
        """
        在输出区显示错误信息。

        Args:
            message: 人类可读的错误描述（由 HashEngine 生成）
        """
        self._progress.setVisible(False)
        self._output.setPlainText(f"❌ {message}")
        self._status_label.setText("")
        self._algo_tag.setText("")

    def set_buttons_enabled(self, enabled: bool) -> None:
        """
        批量启用/禁用所有算法按钮。

        计算期间禁用（防止用户重复点击），计算结束后恢复。

        Args:
            enabled: True = 启用按钮, False = 禁用（变灰且不可点击）
        """
        for btn in self._buttons.values():
            btn.setEnabled(enabled)

    @property
    def compare_text(self) -> str:
        """当前对比输入框中已清理的哈希值（只读）。"""
        return self._compare_text

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _on_compare_text_changed(self, text: str) -> None:
        """
        对比输入框文本变化时的回调。

        每当用户在对比输入框中输入、粘贴或删除文字时触发。
        处理逻辑:
          1. 清理输入（去空白、转小写）
          2. 根据长度检测算法类型
          3. 如果检测成功 → 发射 compare_requested 信号

        信号连接:
          MainWindow._on_compare_requested() 接收此信号并启动计算+对比流程。
        """
        # 清理: 去掉首尾空格、转小写（哈希值大小写不敏感）
        cleaned = text.strip().lower()
        self._compare_text = cleaned

        # 尝试从字符串长度推断算法
        algo_key = _detect_algo_from_length(cleaned)
        if algo_key is not None:
            # 发射信号通知主窗口
            self.compare_requested.emit(algo_key, cleaned)

    def _make_click_handler(self, algo_key: str):
        """
        创建一个闭包（closure），用于按钮点击事件。

        为什么需要闭包？
          Qt 的 clicked.connect() 不接受带参数的槽函数（或者说参数由 Qt 提供）。
          这里我们通过闭包捕获 algo_key，使得每个按钮点击时能传递自己的算法标识。

        等价于:
          lambda: self.algorithm_selected.emit(algo_key)

        但显式写 def handler() 比 lambda 更清晰。
        """
        def handler():
            self.algorithm_selected.emit(algo_key)
        return handler

    def _copy_to_clipboard(self, text: str) -> None:
        """
        将文本写入系统剪贴板，并显示"已复制"状态提示。

        状态提示通过 _copy_timer 在 2.5 秒后自动消失。
        """
        # QApplication.clipboard() 返回系统剪贴板对象（单例）
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

        # 显示状态提示
        self._status_label.setText("✅  哈希值已自动复制到剪贴板")

        # 启动定时器，2.5 秒后清空提示
        if self._copy_timer:
            self._copy_timer.start(2500)  # 毫秒

    def _fade_out_status(self) -> None:
        """
        定时器回调：清空状态行文字。

        这不是真正的"渐隐"动画（QSS 动画在 Qt Widgets 中支持有限），
        而是简单的到期清除。
        """
        self._status_label.setText("")


# ------------------------------------------------------------------
# 哈希长度 → 算法检测
# ------------------------------------------------------------------

def _detect_algo_from_length(hex_str: str) -> str | None:
    """
    根据十六进制字符串的长度推断使用的哈希算法。

    推理规则:
      - 64 个字符 → SHA-256（256 bits / 4 = 64 hex chars）
      - 128 个字符 → SHA-3（512 bits / 4 = 128 hex chars）
      - 其他长度 → 无法判断，返回 None

    为什么可以这样推断？
      每种哈希算法生成固定长度的摘要:
        SHA-256 → 256 bits → 32 bytes → 64 hex 字符
        SHA-3-512 → 512 bits → 64 bytes → 128 hex 字符
      因此，只看字符串长度就能确定是哪种算法。

    Args:
        hex_str: 已清理（strip + lower）的十六进制字符串

    Returns:
        算法 key（'sha256' 或 'sha3_512'），若长度不匹配则返回 None
    """
    length = len(hex_str)
    if length == 64:
        return "sha256"
    elif length == 128:
        return "sha3_512"
    return None
