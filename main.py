"""
HashVerify — Windows 文件哈希校验工具
=========================================
一个打包为单文件 .exe 的桌面应用（基于 PySide6/Qt），
支持 SHA-256 与 SHA-3 两种校验算法。

核心功能:
  1. 点击或拖放选择任意文件
  2. 一键计算 SHA-256 或 SHA-3 哈希值
  3. 自动复制结果到系统剪贴板
  4. 粘贴他人提供的校验值，自动对比是否一致
  5. 纯色双主题 UI，自动跟随 Windows 亮/暗模式

架构概览:
  main.py          — 入口 & 主窗口（窗口管理、信号编排）
  hash_engine.py   — 后台哈希计算线程（不阻塞 UI）
  ui/drop_panel.py — 左侧面板：拖放/点击选文件
  ui/hash_panel.py — 右侧面板：算法按钮、进度条、结果输出、对比输入
  ui/styles.py     — 亮/暗双主题 QSS 样式表

入口: python main.py
打包: build.bat 或 pyinstaller HashVerify.spec
"""

import sys
import os
import winreg  # 读取 Windows 注册表以探测系统主题（亮/暗模式）

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ---- 项目内部模块 ----
from hash_engine import HashEngine       # 后台线程：分块读取文件并计算哈希
from ui.drop_panel import DropPanel      # 左侧 UI 组件：拖放区 + 文件信息
from ui.hash_panel import HashPanel      # 右侧 UI 组件：算法选择 + 结果展示 + 对比
from ui.styles import get_stylesheet     # 根据主题名返回对应的 QSS 样式字符串


# ======================================================================
# 系统主题检测
# ======================================================================

def detect_system_theme() -> str:
    r"""
    通过读取 Windows 注册表，判断当前系统使用的是亮色还是暗色主题。

    Windows 将个性化设置存储在注册表中:
      路径: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize
      键名: AppsUseLightTheme
      值:   1 = 亮色模式, 0 = 暗色模式

    Returns:
        'light' 或 'dark'（读取失败时默认返回 'dark'）
    """
    try:
        # 打开注册表键（只读）
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        # 读取 AppsUseLightTheme 的值
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)  # 及时关闭，释放系统资源
        return "light" if value == 1 else "dark"
    except Exception:
        # 如果注册表键不存在或权限不足，默认使用暗色主题
        return "dark"


# ======================================================================
# 主窗口
# ======================================================================

class MainWindow(QMainWindow):
    """
    HashVerify 主窗口。

    设计要点:
      - 无边框窗口（FramelessWindowHint）：我们自己绘制标题栏，实现统一美观的 UI。
      - 自定义标题栏：包含应用名称、最小化按钮、关闭按钮，支持拖拽移动。
      - 左右分栏布局：左侧 DropPanel（选文件），右侧 HashPanel（算哈希）。
      - 信号/槽机制：各组件通过 Qt Signal 通信，松耦合。

    生命周期:
      1. 构造 → _setup_window() 创建无边框窗口
      2.        → _setup_titlebar() 创建自定义标题栏
      3.        → _setup_content() 创建左右面板
      4.        → _connect_signals() 连接信号与槽
      5. 用户操作 → 槽函数响应 → 启动/停止 HashEngine 线程
    """

    # ---- 窗口尺寸常量 ----
    WINDOW_W = 920   # 默认宽度
    WINDOW_H = 580   # 默认高度
    MIN_W = 720      # 最小宽度（防止布局挤压变形）
    MIN_H = 480      # 最小高度

    def __init__(self, theme: str = "dark"):
        """
        Args:
            theme: 主题名，'light' 或 'dark'，由 detect_system_theme() 提供。
        """
        super().__init__()
        self._theme = theme

        # HashEngine 实例（后台线程），None 表示当前没有在计算
        self._engine: HashEngine | None = None

        # 当前用户选择的文件路径（空字符串表示未选择）
        self._current_file: str = ""

        # 用户粘贴的期望哈希值（用于自动对比），空字符串表示不对比
        self._expected_hash: str = ""

        # 窗口拖拽时的起始坐标（用于自定义标题栏的窗口拖动）
        self._drag_pos = None

        # ---- 按顺序初始化各子系统 ----
        self._setup_window()      # 第一步：创建无边框窗口
        self._setup_titlebar()    # 第二步：创建自定义标题栏
        self._setup_content()     # 第三步：创建左右面板内容区
        self._connect_signals()   # 第四步：连接信号与槽

    # ------------------------------------------------------------------
    # 窗口初始化
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        """
        配置主窗口的基本属性。

        关键设置:
          - FramelessWindowHint: 去掉系统默认标题栏，让我们自己绘制。
          - WindowMinimizeButtonHint: 保留任务栏上的最小化能力。
          - setStyleSheet: 加载对应主题的 QSS 样式表，通过 objectName 精确匹配控件。
        """
        self.setWindowTitle("HashVerify — 文件哈希校验")
        self.resize(self.WINDOW_W, self.WINDOW_H)
        # 设置窗口尺寸限制，既防止太小导致布局错乱，也防止无限制放大
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.setMaximumSize(self.WINDOW_W + 200, self.WINDOW_H + 200)

        # 无边框窗口组合标志:
        #   Qt.Window                    — 普通顶层窗口
        #   Qt.FramelessWindowHint       — 隐藏标题栏和边框
        #   Qt.WindowMinimizeButtonHint  — 任务栏右键菜单中保留"最小化"选项
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowMinimizeButtonHint
        )

        # 所有控件都放在 centralWidget 上，这是 QMainWindow 的顶层容器
        central = QWidget()
        central.setObjectName("centralWidget")  # 给一个 objectName，方便 QSS 选择器定位
        self.setCentralWidget(central)

        # 根据系统主题加载对应的样式表字符串
        self.setStyleSheet(get_stylesheet(self._theme))

    # ------------------------------------------------------------------
    # 自定义标题栏
    # ------------------------------------------------------------------

    def _setup_titlebar(self) -> None:
        """
        创建自定义标题栏，替代被隐藏的系统标题栏。

        布局结构:
          [🔒 HashVerify 标签]  ---- 弹性空白 ----  [最小化按钮] [关闭按钮]

        拖拽移动原理:
          重写标题栏的 mousePressEvent 和 mouseMoveEvent，
          记录鼠标按下位置，移动时计算偏移量并更新窗口位置。
        """
        # 标题栏容器
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)  # 固定高度 40px，与 QSS 配合

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(0, 0, 6, 0)  # 左右上下的内边距（右边留 6px 给关闭按钮呼吸空间）
        layout.setSpacing(0)

        # ---- 应用名称标签 ----
        lbl = QLabel("🔒  HashVerify")
        lbl.setObjectName("titleLabel")
        layout.addWidget(lbl)

        # 弹性空白：把按钮推到最右边
        layout.addStretch()

        # ---- 最小化按钮 ----
        btn_min = QPushButton("─")          # 使用 "─" 字符作为最小化图标
        btn_min.setObjectName("btnMinimize")
        btn_min.setFixedSize(36, 28)
        btn_min.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时变成手型
        btn_min.clicked.connect(self.showMinimized)  # 直接调用 QMainWindow 的最小化方法
        layout.addWidget(btn_min)

        # ---- 关闭按钮 ----
        btn_close = QPushButton("✕")        # 使用 "✕" 字符作为关闭图标
        btn_close.setObjectName("btnClose")
        btn_close.setFixedSize(36, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)  # 调用 QMainWindow 的关闭方法
        layout.addWidget(btn_close)

        # ---- 绑定拖拽事件 ----
        # 将自定义方法挂到标题栏的鼠标事件上，实现"拖动标题栏=移动窗口"
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move

        # 将标题栏加入到根布局中
        central = self.centralWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(title_bar)

    def _title_mouse_press(self, event) -> None:
        """
        标题栏鼠标按下事件 —— 记录拖拽起始位置。

        只有当按下的是鼠标左键时才记录，忽略中键和右键。
        globalPosition() 返回的是屏幕绝对坐标（相对于整个显示器）。
        """
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _title_mouse_move(self, event) -> None:
        """
        标题栏鼠标移动事件 —— 根据偏移量移动窗口。

        只有在按下左键并拖动时才生效。
        计算鼠标从按下到现在移动了多少像素（delta），然后移动窗口同样的距离。
        移动后更新 _drag_pos 为新位置，保证下一次 moveEvent 算的是增量偏移。
        """
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    # ------------------------------------------------------------------
    # 内容区
    # ------------------------------------------------------------------

    def _setup_content(self) -> None:
        """
        创建左右分栏的内容区。

        布局结构:
          [contentArea]
            └── QHBoxLayout (左右并排)
                  ├── DropPanel  (左侧，占 1 份弹性空间) — 选择文件
                  └── HashPanel  (右侧，占 1 份弹性空间) — 计算/显示哈希

        两侧面板使用 QFrame 实现，样式由 QSS 中的 .glassPanel 类控制。
        """
        central = self.centralWidget()
        root = central.layout()  # 前面 _setup_titlebar 已经创建了 QVBoxLayout

        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(14, 8, 14, 14)  # 左右 14px 留白
        content_layout.setSpacing(14)                     # 两个面板之间 14px 间距

        # ---- 左侧：拖放选文件面板 ----
        self._drop_panel = DropPanel()
        content_layout.addWidget(self._drop_panel, 1)  # stretch=1，两侧等宽

        # ---- 右侧：哈希计算面板 ----
        self._hash_panel = HashPanel()
        self._hash_panel.set_buttons_enabled(False)  # 初始禁用算法按钮（还没选文件）
        content_layout.addWidget(self._hash_panel, 1)

        root.addWidget(content, 1)  # stretch=1，内容区占据标题栏下方全部剩余空间

    # ------------------------------------------------------------------
    # 信号/槽连接
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """
        将子控件的 Qt Signal 连接到主窗口的槽函数。

        Qt 信号/槽机制说明:
          - Signal（信号）：控件在特定事件发生时 emit 一个信号。
          - Slot（槽）：接收到信号后执行的函数。
          - connect(signal, slot)：建立绑定关系。
          - 这种松耦合设计让子控件不需要知道主窗口的存在，
            只需 emit 信号，由主窗口负责协调。

        三条关键信号链路:
          1. DropPanel.file_selected     → _on_file_selected      （用户选了文件）
          2. HashPanel.algorithm_selected → _on_algorithm_selected （用户点了算法按钮）
          3. HashPanel.compare_requested  → _on_compare_requested  （用户粘贴了校验值）
        """
        self._drop_panel.file_selected.connect(self._on_file_selected)
        self._hash_panel.algorithm_selected.connect(self._on_algorithm_selected)
        self._hash_panel.compare_requested.connect(self._on_compare_requested)

    # ------------------------------------------------------------------
    # 槽函数（响应 UI 事件）
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: str) -> None:
        """
        用户通过点击或拖放选好了文件。

        做的事:
          1. 记录文件路径
          2. 清空上次的对比值（切换文件意味着之前的期望值已无意义）
          3. 启用右侧面板的算法按钮
        """
        self._current_file = path
        self._expected_hash = ""
        self._hash_panel.set_buttons_enabled(True)

    def _on_algorithm_selected(self, algo_key: str) -> None:
        """
        用户点击了右侧面板的算法按钮（SHA-256 或 SHA-3）。

        这是"手动计算模式"——只计算哈希值，不进行对比。

        防御性检查:
          - 文件路径不为空
          - 文件确实存在于磁盘上（用户可能选了文件后又删了它）
        """
        if not self._current_file or not os.path.isfile(self._current_file):
            self._hash_panel.show_error("请先选择一个有效的文件。")
            return

        self._expected_hash = ""  # 手动模式不对比
        self._start_engine(algo_key)

    def _on_compare_requested(self, algo_key: str, expected_hash: str) -> None:
        """
        用户在右侧面板的对比输入框中粘贴了校验值。

        这是"自动对比模式"——HashPanel 根据粘贴内容的长度自动检测算法类型，
        然后请求主窗口进行计算并对比。

        Args:
            algo_key: 检测到的算法 key（'sha256' 或 'sha3_512'）
            expected_hash: 清理后的用户粘贴值（已 strip + lower）
        """
        if not self._current_file or not os.path.isfile(self._current_file):
            return  # 未选文件时不做任何动作，静默忽略

        self._expected_hash = expected_hash
        self._start_engine(algo_key)

    def _start_engine(self, algo_key: str) -> None:
        """
        启动后台哈希计算线程。

        线程管理策略:
          - 如果上一个计算还在跑，先取消它再启动新的。
          - cancel() 是协作式的（设置 _cancelled 标志），线程在下一次读块时检查。
          - wait(500) 给旧线程最多 500 毫秒退出，避免资源泄漏。

        状态变化:
          - 计算期间禁用算法按钮（防止重复启动）
          - 计算期间禁用拖放区（防止切换文件导致状态混乱）
          - 计算完成后由 _on_engine_finished 恢复

        Qt 跨线程通信:
          HashEngine 是 QThread 子类，运行在工作线程中。
          它通过 emit Signal 向主线程发送进度/结果/错误，
          Qt 自动将信号投递到主线程的事件循环中，因此槽函数可以安全地更新 UI。
        """
        if self._engine and self._engine.isRunning():
            self._engine.cancel()       # 设置取消标志
            self._engine.wait(500)      # 等待线程退出（最多等 500ms）

        # 创建新的计算线程
        self._engine = HashEngine(self._current_file, algo_key)

        # 连接线程信号到 UI 更新函数
        self._engine.progress.connect(self._hash_panel.set_progress)  # 更新进度条
        self._engine.result.connect(self._on_hash_result)             # 显示结果
        self._engine.error.connect(self._hash_panel.show_error)       # 显示错误
        self._engine.finished.connect(self._on_engine_finished)       # 恢复 UI 状态

        # 禁用交互控件，防止计算期间用户误操作
        self._hash_panel.set_buttons_enabled(False)
        self._drop_panel.setAcceptDrops(False)

        self._engine.start()  # QThread.start() → 在新线程中调用 run()

    def _on_hash_result(self, hex_digest: str) -> None:
        """
        哈希计算完成，接收十六进制摘要字符串。

        流程:
          1. 将结果展示在右侧面板
          2. 如果用户之前粘贴了期望值（_expected_hash 不为空），自动进行对比

        Args:
            hex_digest: 哈希值的十六进制表示，如 "a1b2c3..."
        """
        algo_key = self._engine.algorithm_key if self._engine else "sha256"
        self._hash_panel.show_result(hex_digest, algo_key)

        if self._expected_hash:
            self._compare_and_show(hex_digest)

    def _compare_and_show(self, computed: str) -> None:
        """
        对比计算出的哈希值与用户粘贴的期望值。

        比较时不区分大小写（lower()），因为十六进制哈希值的大小写没有意义。

        对比结果通过 QMessageBox 弹出:
          - 一致 → information 级别弹窗（蓝色 i 图标），表示文件完整
          - 不一致 → warning 级别弹窗（黄色 ! 图标），提醒文件可能损坏

        对比完成后清空 _expected_hash，避免下一次计算时重复弹出。
        """
        if computed.lower() == self._expected_hash.lower():
            QMessageBox.information(
                self,
                "校验结果",
                "✅  值相同 — 文件完整，校验通过。"
            )
        else:
            QMessageBox.warning(
                self,
                "校验结果",
                "❌  值不相同 — 文件可能损坏，请注意传输方法。"
            )
        self._expected_hash = ""

    def _on_engine_finished(self) -> None:
        """
        哈希计算线程结束后的清理工作。

        恢复 UI 交互能力:
          - 重新启用算法按钮（用户可以再次点击计算）
          - 重新启用拖放区（用户可以换一个文件重新来）

        这个槽连接的是 QThread.finished 信号，它在 run() 返回后自动发射。
        """
        self._hash_panel.set_buttons_enabled(True)
        self._drop_panel.setAcceptDrops(True)


# ======================================================================
# 程序入口
# ======================================================================

def main():
    """
    应用程序入口函数。

    启动流程:
      1. 设置高 DPI 缩放策略（PassThrough 让 Qt 直接使用系统缩放比例，避免模糊）
      2. 创建 QApplication 实例（PySide6 应用的核心，管理事件循环）
      3. 设置默认字体（Segoe UI，Windows 11 系统字体）
      4. 探测系统主题
      5. 创建并显示主窗口
      6. 进入 Qt 事件循环（app.exec()），程序在此处阻塞直到窗口关闭

    app.exec() 返回值是退出码，传给 sys.exit() 让进程正确退出。
    """
    # 高 DPI 适配：
    # PassThrough 策略让 Qt 不做额外缩放，直接使用操作系统的 DPI 设置。
    # 这样在高分屏（如 4K 显示器 200% 缩放）上文字和控件仍然清晰。
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # QApplication 管理全局状态（剪贴板、字体、样式等），必须在任何 QWidget 之前创建
    app = QApplication(sys.argv)
    app.setApplicationName("HashVerify")
    app.setApplicationVersion("1.0.0")

    # 默认字体设置：
    # Segoe UI 是 Windows Vista 起的系统 UI 字体，中文环境下通常 fallback 到 Microsoft YaHei。
    # PreferAntialias 确保文字渲染平滑。
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # 探测 Windows 系统主题（亮/暗），传给 MainWindow 以加载对应 QSS
    theme = detect_system_theme()
    print(f"[HashVerify] 系统主题: {theme}")

    # 创建主窗口并显示
    window = MainWindow(theme=theme)
    window.show()

    # app.exec() 进入 Qt 事件循环，程序在此处阻塞。
    # 事件循环不断从消息队列中取出事件（鼠标点击、键盘输入、信号等）并分发处理。
    # 当最后一个窗口关闭时，事件循环退出，exec() 返回退出码。
    sys.exit(app.exec())


# Python 脚本直接运行时执行 main()，
# 如果是被 import 则什么都不做（例如 PyInstaller 打包时）。
if __name__ == "__main__":
    main()
