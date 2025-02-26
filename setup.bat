@echo off
chcp 65001 > nul
echo 正在配置PubMed文献分析系统...

REM ----------------------------
REM 检查Python是否正确安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python，请确保Python已正确安装并添加到系统环境变量PATH中
    pause
    exit /b 1
)

REM 可选：创建虚拟环境
set /p checkVenv=是否创建虚拟环境？ (Y/n): 
if /I "%checkVenv%"=="n" (
    echo 跳过虚拟环境创建.
) else (
    if not exist venv (
        echo 正在创建虚拟环境...
        python -m venv venv
        if errorlevel 1 (
            echo 创建虚拟环境失败，请确保：
            echo 1. Python已正确安装（版本3.8或更高）
            echo 2. Python已添加到系统环境变量PATH中
            echo 3. 当前用户具有足够的执行权限
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

REM 运行 setup.py
python setup.py
if errorlevel 1 (
    echo set.up 脚本运行出错.
    pause
    exit /b 1
)


REM 在虚拟环境中检测必要的模块
REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python，请安装Python 3.8或更高版本
    pause
    exit /b 1
)


REM 检查requirements.txt中列出的所有模块是否已安装
echo 正在检查requirements.txt中列出的所有模块是否已安装...
python -c "import Bio, pandas, tqdm, requests, numpy, scipy, matplotlib, seaborn, networkx, nltk, wordcloud, yaml, dotenv, colorama, PyQt5, psutil, openpyxl" > nul 2>&1
if errorlevel 1 (
    echo 检查失败：部分模块可能未安装，正在尝试自动安装...
    pip install -r requirements.txt
    REM 再次检查
    python -c "import Bio, pandas, tqdm, requests, numpy, scipy, matplotlib, seaborn, networkx, nltk, wordcloud, yaml, dotenv, colorama, PyQt5, psutil, openpyxl" > nul 2>&1
    if errorlevel 1 (
        echo 自动安装后仍有模块未安装，请手动检查配置.
        pause
        exit /b 1
    ) else (
        echo 自动安装后所有 requirements.txt 中的模块均已安装.
    )
) else (
    echo 所有 requirements.txt 中的模块均已安装.
)

echo 安装完成！开始使用吧~
pause
