@echo off
REM ============================================================
REM   HashVerify — PyInstaller 一键打包脚本
REM ============================================================
REM
REM 使用方法:
REM   双击 build.bat 或在命令行中运行
REM
REM 前提条件:
REM   - 已安装 Python 3.10+
REM   - pip 可用
REM
REM 脚本做什么:
REM   1. 安装 requirements.txt 中的依赖（PySide6、PyInstaller）
REM   2. 清理上次构建的临时文件（build/、dist/）
REM   3. 调用 PyInstaller 将 main.py 打包成单个 .exe
REM   4. 输出结果到 dist\HashVerify.exe
REM
REM PyInstaller 参数说明:
REM   --onefile  : 打包成单个 .exe 文件（用户友好）
REM   --windowed : 窗口模式（运行时不弹出命令行黑框）
REM   --name     : 输出文件名
REM   --add-data : 额外打包的数据文件/目录（格式: 源;目标）
REM   --clean    : 清理 PyInstaller 缓存
REM   --noconfirm: 覆盖输出目录时不询问确认
REM ============================================================

chcp 65001 >nul
REM ^ 将控制台编码切换到 UTF-8，确保中文字符正常显示

echo ============================================
echo   HashVerify — PyInstaller 打包脚本
echo ============================================
echo.

REM ---- 确保 Python 依赖已安装 ----
REM >nul 2>&1 表示隐藏 pip install 的输出（除非出错）
pip install -r requirements.txt >nul 2>&1

echo [1/2] 清理旧的构建产物...
REM 删除上次构建的临时目录和产物（保证干净构建）
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
REM 删除可能残留的 spec 文件备份
if exist "*.spec" del /q *.spec 2>nul

echo [2/2] 开始构建单文件 exe...
echo.

REM ---- 调用 PyInstaller ----
REM ^ 是 Windows cmd 的续行符（相当于 Linux 的 \）
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "HashVerify" ^
    --add-data "ui;ui" ^
    --clean ^
    --noconfirm ^
    main.py

REM ---- 检查构建结果 ----
REM %ERRORLEVEL% 是上一条命令的退出码，0 表示成功
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   构建成功！
    echo   输出: dist\HashVerify.exe
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   构建失败，请检查错误信息。
    echo ============================================
)

REM 暂停，让用户看到结果（双击运行时不会闪退）
pause
