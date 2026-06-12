# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 (x86 / 通用架构)
==========================================
该文件由 PyInstaller 自动生成后手动调整，用于将 Python 脚本打包成
Windows 独立可执行文件 (.exe)。

PyInstaller 工作原理:
  1. Analysis 阶段: 分析 main.py，追踪所有 import 依赖，收集需要的文件
  2. PYZ 阶段: 将纯 Python 模块编译并打包成 .pyz 压缩包
  3. EXE 阶段: 将所有内容打包成单个 .exe 文件

构建命令（等效于 build.bat）:
  pyinstaller --onefile --windowed --name "HashVerify" --add-data "ui;ui" main.py

与 HashVerify_x64.spec 的区别:
  该 spec 没有设置 icon 参数，且 target_arch 为 None（跟随当前 Python 架构）。
"""

# ---- Analysis: 分析依赖 ----
a = Analysis(
    # 入口脚本列表（可以多个，这里只有 main.py）
    ['main.py'],

    # pathex: 额外的模块搜索路径（空 = 仅用默认路径）
    pathex=[],

    # binaries: 需要打包的外部二进制文件（.dll / .pyd 等）
    binaries=[],

    # datas: 需要打包的非 Python 数据文件
    # ('ui', 'ui') 表示将 ui/ 文件夹复制到打包后的 ui/ 目录
    # 这确保了 ui/__init__.py 等模块在运行时能被正确导入
    datas=[('ui', 'ui')],

    # hiddenimports: 隐式导入 — 某些模块通过 importlib / __import__ 动态导入，
    # PyInstaller 无法自动检测到，需要手动声明
    hiddenimports=[],

    # hookspath: 自定义 hook 文件目录（hook 文件告诉 PyInstaller 如何处理特定包）
    hookspath=[],

    # hooksconfig: 传递给 hook 文件的配置参数
    hooksconfig={},

    # runtime_hooks: 运行时 hook 脚本列表
    runtime_hooks=[],

    # excludes: 排除不需要的模块（减小打包体积）
    excludes=[],

    # noarchive: False = 将 Python 代码打包进压缩包（推荐）
    noarchive=False,

    # optimize: 0 = 不优化, 1 = -O（去掉 assert）, 2 = -OO（去掉 assert + docstring）
    optimize=0,
)

# ---- PYZ: 将纯 Python 模块打包成压缩包 ----
pyz = PYZ(a.pure)

# ---- EXE: 生成最终的可执行文件 ----
exe = EXE(
    # pyz: Python 压缩包
    pyz,

    # a.scripts: 入口脚本
    # a.binaries: 二进制依赖
    # a.datas: 数据文件
    a.scripts,
    a.binaries,
    a.datas,

    # 额外的二进制文件列表（空）
    [],

    # name: 输出 .exe 文件的名称（不含 .exe 后缀）
    name='HashVerify',

    # debug: True = 开启调试模式（输出更多信息）
    debug=False,

    # bootloader_ignore_signals: 是否忽略启动加载器发出的信号
    bootloader_ignore_signals=False,

    # strip: True = 移除符号表（减小体积）
    strip=False,

    # upx: True = 使用 UPX 压缩可执行文件（大幅减小体积，可能引发杀软误报）
    upx=True,
    upx_exclude=[],

    # runtime_tmpdir: 运行时的临时目录（None = 系统默认）
    runtime_tmpdir=None,

    # console: False = 窗口模式（无命令行黑窗口），True = 控制台模式
    console=False,

    # disable_windowed_traceback: 是否禁用窗口模式下的错误追踪
    disable_windowed_traceback=False,

    # argv_emulation: macOS 专用，Windows 下无效
    argv_emulation=False,

    # target_arch: 目标架构（None = 跟随当前 Python，可选 'x86', 'x64'）
    target_arch=None,

    # codesign_identity: macOS 代码签名，Windows 下无效
    codesign_identity=None,

    # entitlements_file: macOS 授权文件，Windows 下无效
    entitlements_file=None,

    # icon: exe 图标文件（此 spec 未设置，使用默认图标）
    # 对比 HashVerify_x64.spec 中有 icon=['icon.ico']
)
