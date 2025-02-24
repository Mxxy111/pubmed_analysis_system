
@echo off
echo 正在配置PubMed文献分析系统...

REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python，请安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 运行setup.py
python setup.py
if errorlevel 1 (
    echo 安装过程中出现错误，请查看上述错误信息
    pause
    exit /b 1
)

echo 安装完成！
pause
