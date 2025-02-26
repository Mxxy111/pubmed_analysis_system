@echo off
chcp 65001 > nul
echo 正在配置PubMed文献分析系统...

REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python，请安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查是否安装requests模块
python -c "import requests" > nul 2>&1
if errorlevel 1 (
    echo 未检测到requests模块，正在安装...
    pip install requests
    if errorlevel 1 (
        echo 安装requests模块时出现错误，请检查网络连接或pip配置
        pause
        exit /b 1
    )
) else (
    echo 检测到requests模块.
)

REM 检测yaml是否安装
python -c "import yaml" > nul 2>&1
if errorlevel 1 (
    echo 未检测到yaml模块，正在安装...
    pip install pyyaml
    if errorlevel 1 (
        echo 安装yaml模块时出现错误，请检查网络连接或pip配置
        pause
        exit /b 1
    )
) else (
    echo 检测到yaml模块.
)



REM ----------------------------
REM 可选：创建虚拟环境
set /p checkVenv=是否创建虚拟环境？ (Y/n): 
if /I "%checkVenv%"=="n" (
    echo 跳过虚拟环境创建.
) else (
    if not exist venv (
        echo 正在创建虚拟环境...
        python -m venv venv
        if errorlevel 1 (
            echo 创建虚拟环境失败
            pause
            exit /b 1
        )
    ) else (
        echo 检测到venv虚拟环境.
    )
)

REM ----------------------------
REM 可选：激活虚拟环境
set /p activateVenv=是否激活虚拟环境？ (Y/n): 
if /I "%activateVenv%"=="n" (
    echo 跳过激活虚拟环境.
) else (
    if not exist "venv\Scripts\activate" (
        echo 虚拟环境未创建或未找到激活脚本，跳过激活虚拟环境.
    ) else (
        call venv\Scripts\activate
        if errorlevel 1 (
            echo 激活虚拟环境失败
            pause
            exit /b 1
        )
    )
)

REM 运行setup.py进行其他安装操作
python setup.py
if errorlevel 1 (
    echo 安装过程中出现错误，请查看上述错误信息
    pause
    exit /b 1
)

echo 安装完成！
pause
