# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 (x64 架构，带图标)
=============================================
与 HashVerify.spec 的区别:
  1. target_arch=None → 跟随当前 Python 架构（通常 x64）
  2. icon=['icon.ico'] → 使用自定义图标文件 icon.ico

建议使用此 spec 进行最终发布构建，因为它包含了应用程序图标。

构建命令:
  pyinstaller HashVerify_x64.spec
"""

# ---- Analysis: 分析依赖 ----
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 将 ui 文件夹作为数据目录打包进去
    datas=[('ui', 'ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ---- PYZ: 将纯 Python 模块打包成压缩包 ----
pyz = PYZ(a.pure)

# ---- EXE: 生成最终的可执行文件 ----
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HashVerify_x64',       # 输出文件名为 HashVerify_x64.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # 使用 UPX 压缩以减小文件体积
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # 窗口模式（不显示命令行黑框）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,            # None = 跟随当前 Python 架构
    codesign_identity=None,
    entitlements_file=None,

    # ---- 自定义图标 ----
    # icon.ico 位于项目根目录，打包后 exe 将使用此图标
    # 而不是 PyInstaller 的默认图标
    icon=['icon.ico'],
)
