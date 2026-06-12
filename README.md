# HashVerify — Windows 文件哈希校验工具

一款基于 PySide6/Qt 的 Windows 桌面应用，支持 **SHA-256** 和 **SHA-3** 两种哈希算法，提供文件完整性校验功能。打包为单个 `.exe` 文件，支持亮/暗双主题，自动跟随系统设置。

## 功能特性

- **拖放选文件** — 从资源管理器直接拖入文件，或点击选择
- **双算法支持** — SHA-256（64 位 hex）和 SHA-3（128 位 hex）
- **自动对比** — 粘贴他人提供的校验值，自动检测算法类型并对比结果
- **自动复制** — 计算结果自动写入系统剪贴板
- **双主题** — 自动检测 Windows 亮/暗模式并切换配色
- **无边框窗口** — 自定义标题栏，视觉效果统一
- **大文件友好** — 分块读取（64KB/chunk），不占用大量内存

## 运行截图

> 运行后会自动跟随 Windows 系统主题

## 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.10 | 运行环境 |
| PySide6 | ≥ 6.5.0 | Qt for Python GUI 框架 |
| PyInstaller | ≥ 5.13.0 | 打包为 exe（仅构建时需要） |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行

```bash
python main.py
```

### 3. 打包为 exe（可选）

```bash
# 方式一：双击 build.bat
# 方式二：命令行
pyinstaller --onefile --windowed --name "HashVerify" --add-data "ui;ui" main.py
```

输出文件在 `dist/HashVerify.exe`。

## 项目结构

```
hash/
├── main.py              # 程序入口 & 主窗口（信号编排）
├── hash_engine.py       # 后台哈希计算线程
├── ui/
│   ├── __init__.py      # UI 包
│   ├── drop_panel.py    # 左侧面板：拖放/点击选文件
│   ├── hash_panel.py    # 右侧面板：算法选择、进度条、结果输出、对比
│   └── styles.py        # 亮/暗双主题 QSS 样式表
├── icon.ico             # 应用图标
├── requirements.txt     # Python 依赖
├── build.bat            # 一键打包脚本
├── HashVerify.spec      # PyInstaller 配置（通用架构）
└── HashVerify_x64.spec  # PyInstaller 配置（x64 + 图标）
```

## 使用说明

1. 打开 `HashVerify.exe`
2. 点击左侧虚线框选择文件，或从资源管理器拖入文件
3. 点击 **SHA-256** 或 **SHA-3** 按钮开始计算
4. 计算结果自动复制到剪贴板
5. 如需校验：将他人提供的哈希值粘贴到"对比校验"输入框中，工具会自动识别算法并对比

## 架构说明

| 模块 | 职责 |
|------|------|
| `main.py` | 主窗口管理、信号/槽编排、Windows 主题检测 |
| `hash_engine.py` | `QThread` 子类，后台分块计算哈希，emit 进度/结果/错误信号 |
| `ui/drop_panel.py` | 文件拖放接收、MIME `file://` URL 解析、点击选文件 |
| `ui/hash_panel.py` | 算法按钮、进度条、结果展示、校验值输入、自动复制 |
| `ui/styles.py` | 亮色/暗色 QSS 样式表，通过 objectName/class 精准匹配控件 |
