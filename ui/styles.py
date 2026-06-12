"""
双主题 QSS 样式表
=================
提供亮色（Light）和暗色（Dark）两套 QSS（Qt Style Sheets）样式，
应用程序启动时根据 Windows 系统主题自动选择。

什么是 QSS？
  QSS 是 Qt 的样式表语言，语法几乎与 CSS 完全相同。
  它允许我们用类似网页的方式为桌面应用控件设置样式:
    - #objectName  → 匹配指定 objectName 的控件（类似 CSS #id）
    - .className    → 匹配 property "class" 为指定值的控件（类似 CSS .class）
    - WidgetType    → 匹配指定类型的控件（类似 CSS 元素选择器）
    - :hover / :pressed / :disabled → 状态伪类（类似 CSS 伪类）

设计原则:
  1. 纯色背景，不使用渐变或图片 —— 简洁、现代、性能好
  2. 亮色主题背景 #e4e8f0（冷灰白），暗色主题背景 #1a1a28（深蓝黑）
  3. 文字在亮色下为纯黑 #000，暗色下为柔白 #e8e8f0
  4. 统一的圆角（10-16px）、统一的间距、统一的配色语言
  5. 按钮、输入框、输出区使用同色系配色，视觉统一

主题切换机制:
  - detect_system_theme() 读取 Windows 注册表 → 'light' 或 'dark'
  - get_stylesheet(theme) 返回对应的 QSS 字符串
  - MainWindow.setStyleSheet() 应用样式（实时生效，无需重启）
"""

# ================================================================
# 亮色主题 (Light Theme)
# ================================================================
# 配色关键词:
#   背景: #e4e8f0 (主), #f4f5fa (卡片), #edf0f6 (拖放区)
#   文字: #000000 (主), #3a3b48 (次要标题), #787a90 (辅助文字)
#   边框: #d0d4de (卡片), #b8bcc8 (拖放区虚线)
#   强调: #7888b0 (按钮悬停 / 进度条)
#   危险: #e81123 (关闭按钮悬停)

LIGHT_QSS = r"""
/* ============================================================
   全局 — 所有 QWidget 的基础样式
   ============================================================ */
QMainWindow {
    background-color: #e4e8f0;   /* 主窗口背景：冷灰白色 */
}

QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    /* Segoe UI 是 Windows 11 默认 UI 字体，
       Microsoft YaHei（微软雅黑）作为中文字体的 fallback，
       sans-serif 作为最终的通用 fallback */
    font-size: 14px;
    color: #000000;              /* 纯黑文字，在浅色背景上对比度最高 */
}

/* ============================================================
   标题栏 — 自定义窗口标题栏
   ============================================================ */
#titleBar {
    background-color: #d4d8e4;   /* 比主背景稍深，形成层次感 */
    border-bottom: 1px solid #c8ccd8;  /* 底部分隔线 */
}

#titleLabel {
    font-size: 14px;
    font-weight: 700;            /* bold */
    color: #000000;
    padding-left: 14px;          /* 文字与窗口左边缘保持距离 */
}

/* 最小化 & 关闭按钮的默认状态 */
#btnMinimize, #btnClose {
    background: transparent;     /* 透明背景，融入标题栏 */
    border: none;
    border-radius: 6px;          /* 圆角，视觉柔和 */
    color: #4a4c64;
    font-size: 18px;
    font-weight: bold;
    padding: 4px 12px;
}

/* 最小化按钮悬停: 半透明黑色遮罩 */
#btnMinimize:hover {
    background-color: rgba(0, 0, 0, 0.06);
    color: #000000;
}

/* 关闭按钮悬停: Windows 风格的红色背景 */
#btnClose:hover {
    background-color: #e81123;   /* Windows 标准关闭红色 */
    color: #ffffff;
}

/* ============================================================
   中央内容区
   ============================================================ */
#centralWidget {
    background-color: #e4e8f0;   /* 与主窗口保持一致 */
}

/* ============================================================
   左右分栏卡片 — "液态玻璃"风格
   ============================================================ */
.glassPanel {
    background-color: #f4f5fa;   /* 比主背景稍亮，形成卡片浮起效果 */
    border: 1px solid #d0d4de;   /* 细边框增强层次 */
    border-radius: 14px;         /* 大圆角，现代风格 */
    padding: 20px;
}

/* ============================================================
   左侧拖放区 — 虚线边框的可交互区域
   ============================================================ */
#dropZone {
    background-color: #edf0f6;   /* 比卡片背景稍微有色彩差异 */
    border: 2px dashed #b8bcc8;  /* 虚线提示"这里可以拖放" */
    border-radius: 16px;
}

/* 鼠标悬停: 边框颜色变深，提示用户此处可交互 */
#dropZone:hover {
    border-color: #7888b0;
    background-color: #e8ecf6;
}

/* 拖拽激活: 文件正在上方悬停时的高亮状态 */
/* [dragActive="true"] 是 Qt 属性选择器，由代码 setProperty("dragActive", True) 动态设置 */
#dropZone[dragActive="true"] {
    border-color: #5078b8;       /* 更鲜明的蓝色边框 */
    background-color: #dce4f6;   /* 更明显的蓝色底 */
}

#dropIcon {
    font-size: 52px;             /* emoji 图标，大字号显示 */
    color: #989bb0;
}

#dropText {
    font-size: 15px;
    color: #3a3b48;
    font-weight: 600;            /* semi-bold */
}

#dropSubText {
    font-size: 12px;
    color: #787a90;              /* 次要文字用灰色 */
}

#fileNameLabel {
    font-size: 14px;
    font-weight: 700;
    color: #000000;
}

#fileSizeLabel {
    font-size: 12px;
    color: #606278;
}

/* ============================================================
   算法按钮 — SHA-256 / SHA-3 统一样式
   ============================================================ */
#btnSHA256, #btnSHA3 {
    background-color: #e8eaf4;
    border: 1px solid #c4c8d6;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 700;
    color: #000000;
    min-height: 44px;            /* 满足触控友好的最小点击高度 */
}

#btnSHA256:hover, #btnSHA3:hover {
    background-color: #dce0ee;   /* 悬停时稍微加深 */
    border-color: #a8aec4;
}

#btnSHA256:pressed, #btnSHA3:pressed {
    background-color: #d0d4e4;   /* 按下时进一步加深 */
    border-color: #9098b4;
}

/* 禁用状态: 变灰、降低对比度，提示用户按钮不可用 */
#btnSHA256:disabled, #btnSHA3:disabled {
    background-color: #e4e6f0;
    color: #a0a2b4;
    border: 1px solid #d4d6e0;
}

/* ============================================================
   对比输入框 — 等宽字体 + 与输出区统一配色
   ============================================================ */
#compareInput {
    background-color: #eef0f6;
    border: 1px solid #ccd0da;
    border-radius: 10px;
    padding: 10px 14px;
    /* 哈希值是十六进制字符串，等宽字体确保字符对齐 */
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #000000;
}

/* 聚焦状态: 边框高亮，指示用户正在此处输入 */
#compareInput:focus {
    border-color: #7888b0;
}

/* 占位符文字颜色（显示时、未输入时）*/
#compareInput::placeholder {
    color: #9094a8;
}

/* ============================================================
   进度条 — 简约细线风格（无文字，纯色块）
   ============================================================ */
#hashProgress {
    background-color: #e0e2ec;   /* 进度条底色（未完成部分） */
    border: none;
    border-radius: 3px;
    min-height: 4px;
    max-height: 4px;             /* 固定高度 4px，细线风格 */
    text-align: center;
}

/* ::chunk 是 QProgressBar 的进度填充部分 */
#hashProgress::chunk {
    background-color: #7888b0;   /* 已完成部分的颜色 */
    border-radius: 3px;
}

/* ============================================================
   结果输出区 — 只读多行文本框，展示哈希值
   ============================================================ */
#hashTitle {
    font-size: 15px;
    font-weight: 700;
    color: #000000;
    padding-bottom: 4px;
}

#resultOutput {
    background-color: #eef0f6;   /* 与输入框保持一致 */
    border: 1px solid #ccd0da;
    border-radius: 10px;
    padding: 14px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #000000;
    /* 选中文字时的背景色（半透明蓝色） */
    selection-background-color: rgba(60, 100, 200, 0.2);
}

/* ============================================================
   状态标签 — 底部状态行的文字标签
   ============================================================ */
#copyStatusLabel {
    font-size: 13px;
    color: #187838;              /* 绿色，表示"成功复制" */
    font-weight: 600;
}

/* 算法标签（如 [SHA-256] 小徽章） */
#algoTag {
    font-size: 11px;
    color: #505268;
    background: #e0e2ec;
    border-radius: 4px;
    padding: 2px 10px;
}

/* ============================================================
   滚动条 — 自定义窄滚动条样式
   ============================================================ */
QScrollBar:vertical {
    background: transparent;
    width: 6px;                  /* 窄滚动条 */
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #bfc3d0;         /* 滚动条滑块颜色 */
    border-radius: 3px;
    min-height: 20px;            /* 滑块最小高度，防止太扁 */
}

QScrollBar::handle:vertical:hover {
    background: #9a9fb0;         /* 悬停时加深 */
}

/* 隐藏滚动条两端的箭头按钮 */
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* 滚动条轨道背景透明 */
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ============================================================
   工具提示 — 鼠标悬停时的浮动提示框
   ============================================================ */
QToolTip {
    background-color: #f2f3f8;
    color: #000000;
    border: 1px solid #c8ccd8;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""


# ================================================================
# 暗色主题 (Dark Theme)
# ================================================================
# 配色关键词:
#   背景: #1a1a28 (主), #232336 (卡片), #1e1e30 (拖放区)
#   文字: #e8e8f0 (主), #b8b8d0 (次要标题), #808098 (辅助文字)
#   边框: #303048 (卡片), #383858 (拖放区虚线)
#   强调: #5868a0 (按钮悬停 / 进度条)
#   危险: #e81123 (关闭按钮悬停，与亮色一致)
#
# 暗色主题不是简单的颜色反转。黑色背景上的文字需要降低对比度
# 以避免眼睛疲劳，因此用 #e8e8f0（柔白）而非 #ffffff（纯白）。

DARK_QSS = r"""
/* ============================================================
   全局
   ============================================================ */
QMainWindow {
    background-color: #1a1a28;   /* 深蓝黑背景，不是纯黑 */
}

QWidget {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    color: #e8e8f0;              /* 柔白文字，暗色背景下不刺眼 */
}

/* ============================================================
   标题栏
   ============================================================ */
#titleBar {
    background-color: #1e1e30;   /* 比主背景稍亮，形成层次 */
    border-bottom: 1px solid #2a2a40;
}

#titleLabel {
    font-size: 14px;
    font-weight: 700;
    color: #e8e8f0;
    padding-left: 14px;
}

#btnMinimize, #btnClose {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #8080a0;
    font-size: 18px;
    font-weight: bold;
    padding: 4px 12px;
}

#btnMinimize:hover {
    background-color: rgba(255, 255, 255, 0.07);  /* 半透明白色遮罩 */
    color: #e8e8f0;
}

#btnClose:hover {
    background-color: #e81123;   /* 统一的关闭红色 */
    color: #ffffff;
}

/* ============================================================
   中央内容区
   ============================================================ */
#centralWidget {
    background-color: #1a1a28;
}

/* ============================================================
   左右分栏卡片
   ============================================================ */
.glassPanel {
    background-color: #232336;   /* 卡片稍亮于背景 */
    border: 1px solid #303048;
    border-radius: 14px;
    padding: 20px;
}

/* ============================================================
   左侧拖放区
   ============================================================ */
#dropZone {
    background-color: #1e1e30;
    border: 2px dashed #383858;
    border-radius: 16px;
}

#dropZone:hover {
    border-color: #6070a0;
    background-color: #212138;
}

#dropZone[dragActive="true"] {
    border-color: #5880c8;
    background-color: #242440;
}

#dropIcon {
    font-size: 52px;
    color: #606080;
}

#dropText {
    font-size: 15px;
    color: #b8b8d0;
    font-weight: 600;
}

#dropSubText {
    font-size: 12px;
    color: #808098;
}

#fileNameLabel {
    font-size: 14px;
    font-weight: 700;
    color: #e8e8f0;
}

#fileSizeLabel {
    font-size: 12px;
    color: #9898b0;
}

/* ============================================================
   算法按钮 — 与亮色主题对应，暗色版本
   ============================================================ */
#btnSHA256, #btnSHA3 {
    background-color: #1e1e32;
    border: 1px solid #30304c;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 700;
    color: #e8e8f0;
    min-height: 44px;
}

#btnSHA256:hover, #btnSHA3:hover {
    background-color: #262640;
    border-color: #404060;
}

#btnSHA256:pressed, #btnSHA3:pressed {
    background-color: #2c2c4c;
    border-color: #484870;
}

#btnSHA256:disabled, #btnSHA3:disabled {
    background-color: #1c1c2e;
    color: #585870;
    border: 1px solid #282840;
}

/* ============================================================
   对比输入框
   ============================================================ */
#compareInput {
    background-color: #181828;   /* 比卡片背景深，区分输入区 */
    border: 1px solid #2a2a42;
    border-radius: 10px;
    padding: 10px 14px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #e8e8f0;
}

#compareInput:focus {
    border-color: #5868a0;
}

#compareInput::placeholder {
    color: #686888;
}

/* ============================================================
   进度条
   ============================================================ */
#hashProgress {
    background-color: #242438;
    border: none;
    border-radius: 3px;
    min-height: 4px;
    max-height: 4px;
    text-align: center;
}

#hashProgress::chunk {
    background-color: #5868a0;
    border-radius: 3px;
}

/* ============================================================
   结果输出
   ============================================================ */
#hashTitle {
    font-size: 15px;
    font-weight: 700;
    color: #e8e8f0;
    padding-bottom: 4px;
}

#resultOutput {
    background-color: #181828;
    border: 1px solid #2a2a42;
    border-radius: 10px;
    padding: 14px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    color: #e8e8f0;
    selection-background-color: rgba(80, 120, 210, 0.3);
}

/* ============================================================
   状态标签
   ============================================================ */
#copyStatusLabel {
    font-size: 13px;
    color: #48c870;              /* 暗色下的绿色（比亮色的 #187838 更亮） */
    font-weight: 600;
}

#algoTag {
    font-size: 11px;
    color: #9090b0;
    background: #2a2a42;
    border-radius: 4px;
    padding: 2px 10px;
}

/* ============================================================
   滚动条
   ============================================================ */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #3a3a55;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #585878;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ============================================================
   提示框
   ============================================================ */
QToolTip {
    background-color: #282840;
    color: #e8e8f0;
    border: 1px solid #383858;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""


# ================================================================
# 主题获取函数
# ================================================================

def get_stylesheet(theme: str) -> str:
    """
    根据主题名返回对应的 QSS 样式表字符串。

    Args:
        theme: 'light' 或 'dark'（其他值默认返回暗色）

    Returns:
        对应主题的完整 QSS 字符串，可直接传给 QApplication.setStyleSheet()

    使用方式:
        app.setStyleSheet(get_stylesheet(detect_system_theme()))
    """
    if theme == "light":
        return LIGHT_QSS
    # 默认返回暗色主题（未知主题名时的安全回退）
    return DARK_QSS
