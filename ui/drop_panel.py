"""
DropPanel — 左侧面板：文件选择区域
====================================
提供两种方式让用户选择一个文件:
  1. 点击拖放区 → 弹出 Windows 资源管理器文件选择对话框
  2. 从资源管理器拖入文件 → 释放后自动识别文件路径

外观设计:
  采用"液态玻璃"风格（glassPanel），虚线边框的拖放区，
  选中文件后显示文件名和大小。

拖放技术细节:
  - Windows 资源管理器拖放的文件以 MIME `text/uri-list` 格式传递
  - 其中包含 file:// 协议的 URL，需要解析并转换成本地路径
  - 中文路径在 URL 中是百分号编码的，需要用 unquote 解码

信号:
  file_selected(str): 用户选好文件后发出，携带文件的绝对路径
"""

import os
from urllib.parse import urlparse, unquote  # 解析 MIME 中的 file:// URL

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFileDialog,  # 系统原生文件选择对话框
    QFrame,
    QLabel,
    QVBoxLayout,
)


def _extract_local_path(mime_url: str) -> str:
    """
    将拖放操作中 MIME `text/uri-list` 格式的 file:// URL 转为本地文件路径。

    处理逻辑:
      1. urlparse 解析 URL 结构，提取 path 部分
      2. unquote 解码百分号编码（例如 %E4%B8%AD → 中）
      3. Windows 下路径可能以 /C:/xxx 开头（多一个前导斜杠），需要去掉

    示例:
      输入:  "file:///C:/Users/me/doc.txt"
      输出:  "C:/Users/me/doc.txt"

      输入:  "file:///C:/Users/me/%E6%96%87%E4%BB%B6.txt"
      输出:  "C:/Users/me/文件.txt"

    Args:
        mime_url: MIME 数据中单个 URL 的字符串表示

    Returns:
        解码后的本地文件路径
    """
    # urlparse 将 URL 拆解为 scheme、netloc、path 等部分
    # 例如 file:///C:/test.txt → scheme='file', path='/C:/test.txt'
    parsed = urlparse(mime_url.strip())

    # 对 path 进行百分号解码（如 %20 → 空格）
    path = unquote(parsed.path)

    # Windows (os.name == 'nt') 的特殊处理:
    # file:// URL 的 path 以 / 开头（如 /C:/Users/...），
    # 需要去掉最前面的 /，得到正确的 Windows 路径。
    if os.name == "nt" and path.startswith("/"):
        path = path[1:]

    return path


class DropPanel(QFrame):
    """
    可拖放 / 点击选文件的"液态玻璃"风格面板。

    内部结构:
      ┌── glassPanel (卡片容器) ──────────┐
      │  ┌── dropZone (虚线框) ─────────┐ │
      │  │   📂 图标                     │ │
      │  │   点击或拖放文件到此处          │ │
      │  │   支持任意文件类型              │ │
      │  └─────────────────────────────┘ │
      │  ┌── info_frame (默认隐藏) ─────┐ │
      │  │   文件名 + 文件大小            │ │
      │  └─────────────────────────────┘ │
      └──────────────────────────────────┘

    交互状态:
      默认 → 显示引导图标 + 提示文字
      选中文件后 → 隐藏 info_frame → 显示文件名和大小，图标变为 ✅
      拖拽悬停 → dropZone 边框和背景变色（通过动态属性 dragActive 触发 QSS）

    Signals:
        file_selected(str): 用户选中（拖入或点击）文件后发出
    """

    # 定义一个 Qt Signal，携带文件路径字符串
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropPanel")  # QSS 中通过 #dropPanel 定位

        # 开启拖放接收（必须调用，否则 dragEnterEvent 不会被触发）
        self.setAcceptDrops(True)

        # 最小宽度防止窗口缩太小时布局被挤扁
        self.setMinimumWidth(300)

        # 当前选中的文件路径（内部状态）
        self._selected_path: str = ""

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """构建 DropPanel 内部的全部控件和布局。"""
        # 根布局
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 玻璃卡片容器 ----
        # QFrame 作为卡片背景，QSS 通过 property "class" = "glassPanel" 设置样式
        card = QFrame(self)
        card.setProperty("class", "glassPanel")  # 相当于 CSS class，在 QSS 中用 .glassPanel 匹配
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        # ---- 拖放区（虚线框） ----
        # 这是一个嵌套的 QFrame，作为实际的拖放热区
        self._drop_zone = QFrame(card)
        self._drop_zone.setObjectName("dropZone")  # QSS 中用 #dropZone 匹配
        self._drop_zone.setAcceptDrops(True)        # 拖放事件会冒泡到这里
        self._drop_zone.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手型

        # 安装事件过滤器（这里其实未使用 eventFilter，保留以备扩展）
        self._drop_zone.installEventFilter(self)

        drop_layout = QVBoxLayout(self._drop_zone)
        drop_layout.setContentsMargins(16, 40, 16, 40)
        drop_layout.setSpacing(8)
        drop_layout.setAlignment(Qt.AlignCenter)  # 子控件垂直居中

        # 文件夹图标（emoji 大字号显示）
        self._icon_label = QLabel("\U0001F4C2")  # 📂 = U+1F4C2
        self._icon_label.setObjectName("dropIcon")
        self._icon_label.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(self._icon_label)

        # 主导提示文字
        self._hint_label = QLabel("点击或拖放文件到此处")
        self._hint_label.setObjectName("dropText")
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._hint_label.setWordWrap(True)  # 允许换行，防止窄窗口时文字被截断
        drop_layout.addWidget(self._hint_label)

        # 辅助提示文字
        self._sub_hint = QLabel("支持任意文件类型")
        self._sub_hint.setObjectName("dropSubText")
        self._sub_hint.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(self._sub_hint)

        card_layout.addWidget(self._drop_zone, 1)  # stretch=1，占据卡片主要空间

        # ---- 文件信息区（选中文件后才显示） ----
        self._info_frame = QFrame(card)
        self._info_frame.setVisible(False)  # 默认隐藏
        info_layout = QVBoxLayout(self._info_frame)
        info_layout.setContentsMargins(4, 8, 4, 0)
        info_layout.setSpacing(2)

        # 文件名标签
        self._file_name_label = QLabel("")
        self._file_name_label.setObjectName("fileNameLabel")
        self._file_name_label.setAlignment(Qt.AlignCenter)
        self._file_name_label.setWordWrap(True)  # 长文件名自动换行
        info_layout.addWidget(self._file_name_label)

        # 文件大小标签
        self._file_size_label = QLabel("")
        self._file_size_label.setObjectName("fileSizeLabel")
        self._file_size_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self._file_size_label)

        card_layout.addWidget(self._info_frame)
        root.addWidget(card)

        # ---- 点击事件 ----
        # 绑定额外的 mousePressEvent，点击 drop_zone 时打开文件选择对话框
        # 注意：dragEnterEvent / dropEvent 等通过重写类方法实现，
        #       而 mousePressEvent 直接赋值绑定，因为 drop_zone 是子控件。
        self._drop_zone.mousePressEvent = self._on_drop_zone_click

    # ------------------------------------------------------------------
    # 点击 → 文件选择对话框
    # ------------------------------------------------------------------

    def _on_drop_zone_click(self, event: QMouseEvent) -> None:
        """
        点击拖放区 → 打开 Windows 资源管理器的"打开文件"对话框。

        QFileDialog.getOpenFileName 是模态对话框，会阻塞直到用户选择或取消。
        选择文件后调用 _on_file() 统一处理。

        过滤器设置为 "所有文件 (*.*)"，即不限制文件类型。
        """
        if event.button() == Qt.LeftButton:
            # getOpenFileName 返回 (文件路径, 过滤器)
            # 如果用户点击取消，返回 ("", "")
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择要校验的文件",   # 对话框标题
                "",                  # 初始目录（空 = 默认目录）
                "所有文件 (*.*)",     # 文件类型过滤器
            )
            if path and os.path.isfile(path):
                self._on_file(path)

    # ------------------------------------------------------------------
    # 拖放事件处理
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        拖拽进入事件 —— 当用户拖着一个文件进入控件区域时触发。

        这里做了严格的验证:
          1. 只接受恰好 1 个文件的拖放（不处理多文件、文件夹）
          2. 验证拖入的确实是一个文件（不是快捷方式或无效路径）

        验证通过后:
          - 设置 drop_zone 的动态属性 dragActive=true，触发 QSS 高亮样式
          - 调用 acceptProposedAction() 表示接受这个拖放

        验证失败:
          - 调用 ignore() 表示不接受，鼠标光标会显示"禁止"图标
        """
        mime = event.mimeData()
        # hasUrls() 检查是否为文件 URL 列表（资源管理器拖放的标准格式）
        # 只接受恰好 1 个文件
        if mime.hasUrls() and len(mime.urls()) == 1:
            path = _extract_local_path(mime.urls()[0].toString())
            if os.path.isfile(path):
                # 设置动态属性 → QSS 中通过 #dropZone[dragActive="true"] 匹配高亮样式
                self._drop_zone.setProperty("dragActive", True)
                # 刷新样式：unpolish + polish 强制 Qt 重新计算 QSS
                self._drop_zone.style().unpolish(self._drop_zone)
                self._drop_zone.style().polish(self._drop_zone)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """
        拖拽离开事件 —— 用户把文件拖出了控件区域。

        恢复 dragActive=false，去掉高亮样式。
        """
        self._drop_zone.setProperty("dragActive", False)
        self._drop_zone.style().unpolish(self._drop_zone)
        self._drop_zone.style().polish(self._drop_zone)

    def dropEvent(self, event: QDropEvent) -> None:
        """
        拖放事件 —— 用户松开了鼠标，文件被放下。

        先恢复正常样式（dragActive=false）。
        然后解析文件路径，调用 _on_file() 统一处理。

        这里允许 >= 1 个 URL（比 dragEnterEvent 更宽松），但只取第一个。
        """
        # 恢复样式
        self._drop_zone.setProperty("dragActive", False)
        self._drop_zone.style().unpolish(self._drop_zone)
        self._drop_zone.style().polish(self._drop_zone)

        mime = event.mimeData()
        if mime.hasUrls() and len(mime.urls()) >= 1:
            path = _extract_local_path(mime.urls()[0].toString())
            if os.path.isfile(path):
                self._on_file(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ------------------------------------------------------------------
    # 文件选择统一入口
    # ------------------------------------------------------------------

    def _on_file(self, path: str) -> None:
        """
        文件选好后的统一处理入口（无论来自点击还是拖放）。

        做的事:
          1. 记录路径
          2. 提取文件名和大小
          3. 更新 UI（显示文件信息、改变图标）
          4. emit file_selected 信号，通知主窗口
        """
        self._selected_path = path

        # os.path.basename 提取文件名（去掉目录部分）
        file_name = os.path.basename(path)
        # os.path.getsize 获取文件大小（字节数）
        file_size = os.path.getsize(path)

        # 更新 UI
        self._file_name_label.setText(file_name)
        self._file_size_label.setText(_format_size(file_size))
        self._info_frame.setVisible(True)  # 显示出文件信息区域

        # 图标切换为"对勾"，提示用户文件已就绪
        self._icon_label.setText("✅")
        self._hint_label.setText("文件已就绪")
        self._sub_hint.setText("点击右侧按钮开始校验")

        # 通知主窗口：文件已就绪
        self.file_selected.emit(path)


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _format_size(size_bytes: int) -> str:
    """
    将字节数转换为人类可读的带单位字符串。

    采用 1024 进制（与操作系统一致）:
      B  → KB → MB → GB → TB → PB

    示例:
      0          → "0.0 B"
      1024       → "1.0 KB"
      1048576    → "1.0 MB"
      1073741824 → "1.0 GB"

    循环实现: 每轮除以 1024，直到数值小于 1024 或单位耗尽。
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    # 理论上不会到这里（PB 级别的文件几乎不存在），但保留兜底
    return f"{size_bytes:.1f} PB"
