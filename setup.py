import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = Path(__file__).parent.absolute()

def check_project_directory():
    """检查是否在正确的项目目录下运行"""
    required_files = ['requirements.txt', 'config.yaml.template', 'main.py']
    missing_files = [f for f in required_files if not (SCRIPT_DIR / f).exists()]
    
    if missing_files:
        print("错误: 项目目录文件不完整")
        print(f"脚本目录: {SCRIPT_DIR}")
        print("项目目录应包含以下文件:")
        for file in required_files:
            status = '✓' if file not in missing_files else '✗'
            print(f"  {status} {file}")
        sys.exit(1)
    print("✓ 项目目录检查通过")

def check_python_version():
    """检查Python版本是否满足要求并返回适配的依赖版本信息"""
    min_version = (3, 8)
    max_version = (3, 13)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print(f"错误: 需要Python {min_version[0]}.{min_version[1]} 或更高版本")
        print(f"当前版本: Python {current_version[0]}.{current_version[1]}")
        sys.exit(1)
    elif current_version > max_version:
        print(f"警告: 当前Python版本 {current_version[0]}.{current_version[1]} 可能不完全兼容")
        print(f"推荐使用Python {min_version[0]}.{min_version[1]} 到 {max_version[0]}.{max_version[1]} 之间的版本")
    
    # 根据Python版本返回适配的依赖版本
    version_map = {
        (3, 8): {
            'numpy': '1.24.3',
            'pandas': '2.0.3',
            'scipy': '1.10.1'
        },
        (3, 9): {
            'numpy': '1.24.3',
            'pandas': '2.0.3',
            'scipy': '1.11.3'
        },
        (3, 10): {
            'numpy': '1.26.3',
            'pandas': '2.1.4',
            'scipy': '1.11.4'
        },
        (3, 11): {
            'numpy': '1.26.3',
            'pandas': '2.2.0',
            'scipy': '1.12.0'
        },
        (3, 12): {
            'numpy': '1.26.4',
            'pandas': '2.2.3',
            'scipy': '1.13.0'
        },
        (3, 13): {
            'numpy': '2.1.3',
            'pandas': '2.2.3',
            'scipy': '1.13.0'
        }
    }
    
    # 获取最接近的版本配置
    compatible_version = None
    for version in sorted(version_map.keys()):
        if current_version >= version:
            compatible_version = version
    
    if compatible_version:
        print(f"✓ Python版本检查通过: {sys.version.split()[0]}")
        print(f"✓ 将使用Python {compatible_version[0]}.{compatible_version[1]} 兼容的依赖版本")
        return version_map[compatible_version]
    else:
        print(f"警告: 未找到完全匹配的依赖版本配置，将使用默认版本")
        return version_map[max(version_map.keys())]

def install_dependencies():
    """安装项目依赖（分阶段安装）"""
    # 定义pip镜像源列表，按优先级排序
    pip_mirrors = [
        "https://pypi.tuna.tsinghua.edu.cn/simple",  # 清华源
        "https://mirrors.aliyun.com/pypi/simple",    # 阿里源
        "https://pypi.mirrors.ustc.edu.cn/simple",   # 中科大源
        "https://pypi.douban.com/simple",           # 豆瓣源
        "https://pypi.org/simple"                    # 官方源
    ]
    
    def pip_install(packages, extra_args=None, retry_count=5):
        """通用pip安装函数，支持多个镜像源重试"""
        if isinstance(packages, str):
            # 处理requirements.txt文件路径
            if packages.startswith('-r'):
                req_file = packages.split(' ', 1)[1].strip()
                packages = [f"-r{req_file}"]  # 移除多余的空格
            else:
                packages = [packages]
        
        for mirror in pip_mirrors:
            for attempt in range(retry_count):
                try:
                    for pkg in packages:
                        cmd = [
                            sys.executable, "-m", "pip", "install",
                            pkg,
                            "-i", mirror,
                            "--timeout", "60",
                            "--retries", "3"
                        ]
                        if extra_args:
                            cmd.extend(extra_args)
                        subprocess.check_call(cmd)
                    return True
                except subprocess.CalledProcessError as e:
                    if attempt < retry_count - 1:
                        print(f"安装失败，尝试使用其他镜像源重试...")
                        continue
                    print(f"警告：使用镜像 {mirror} 安装失败")
                    break
        return False
    
    try:
        print("\n=== 开始分阶段安装依赖 ===\n")
        
        # 获取适配的依赖版本
        compatible_versions = check_python_version()
        
        # 基础编译依赖
        print("1. 安装基础编译依赖...")
        if pip_install(["wheel", "setuptools>=69.0.0"]):
            print("✓ 基础编译依赖安装完成")
        
        # 数值计算核心
        print("\n2. 安装数值计算核心包...")
        packages = [
            f"numpy>={compatible_versions['numpy']}",
            f"pandas>={compatible_versions['pandas']}",
            f"scipy>={compatible_versions['scipy']}"
        ]
        
        for package in packages:
            extra_args = []
            if "numpy" in package:
                extra_args.append("--only-binary=:all:")
            if "pandas" in package:
                extra_args.append("--use-pep517")
            
            if pip_install(package, extra_args):
                print(f"✓ {package} 安装成功")
        
        # 图形相关依赖
        print("\n3. 安装图形相关依赖...")
        if pip_install("matplotlib>=3.7.0"):
            print("✓ matplotlib 安装成功")
        
        if platform.system() == "Windows":
            if pip_install("PyQt5>=5.15.0"):
                print("✓ PyQt5 安装成功")
        
        # 其他依赖
        print("\n4. 安装其他依赖...")
        requirements_file = SCRIPT_DIR / "requirements.txt"
        if pip_install(f"-r {str(requirements_file)}"):
            print("✓ 其他依赖安装完成")
        
        print("\n=== 依赖安装完成 ===\n")
        print("如果某些包安装失败，建议：")
        print("1. 检查网络连接")
        print("2. 使用管理员权限运行")
        print("3. 尝试手动安装失败的包")
        print("4. 考虑使用其他镜像源：")
        for mirror in pip_mirrors:
            print(f"   - {mirror}")
        
    except Exception as e:
        print(f"\n错误: 安装过程中出现异常: {str(e)}")
        print("请尝试手动安装依赖，或者使用其他镜像源重试")
        sys.exit(1)

def setup_config():
    """设置配置文件"""
    config_template = SCRIPT_DIR / "config.yaml.template"
    config_file = SCRIPT_DIR / "config.yaml"
    
    if not config_template.exists():
        print(f"错误: 未找到配置模板文件 {config_template}")
        sys.exit(1)
    
    if not config_file.exists():
        shutil.copy2(config_template, config_file)
        print(f"✓ 已创建配置文件: {config_file}")
        print("请修改配置文件中的以下内容:")
        print("  1. api.deepseek.api_key - 替换为您的DeepSeek API密钥")
        print("  2. pubmed.email - 替换为您的邮箱地址")
    else:
        print(f"提示: 配置文件 {config_file} 已存在，跳过创建")

def create_directories():
    """创建必要的目录结构"""
    directories = [
        "results",
        "cache"
    ]
    
    for directory in directories:
        (SCRIPT_DIR / directory).mkdir(exist_ok=True)
        print(f"✓ 确保目录存在: {directory}")

def check_environment():
    """检查运行环境"""
    print("\n=== 环境检查 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python路径: {sys.executable}")
    print(f"脚本目录: {SCRIPT_DIR}")

def check_chinese_font():
    """检查中文字体配置"""
    try:
        import matplotlib.font_manager as fm
        fonts = [f.name for f in fm.fontManager.ttflist]
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'FangSong']
        available_fonts = [f for f in chinese_fonts if f in fonts]
        
        if not available_fonts:
            print("警告: 未找到中文字体，可能影响中文显示")
            if platform.system() == 'Windows':
                print("建议安装 SimHei 或 Microsoft YaHei 字体")
            else:
                print("建议安装相应的中文字体包")
        else:
            print(f"✓ 找到可用的中文字体: {', '.join(available_fonts)}")
        return bool(available_fonts)
    except Exception as e:
        print(f"警告: 检查中文字体时出错: {e}")
        return False

def test_environment():
    """测试环境配置"""
    try:
        print("\n=== 环境测试 ===\n")
        
        # 测试必要的Python包
        print("测试Python包导入...")
        import pandas
        import numpy
        import scipy
        import matplotlib
        import networkx
        import nltk
        import yaml
        import Bio
        from Bio import Entrez
        from Bio import Medline
        import wordcloud
        import tqdm
        import seaborn
        print("✓ 所有必要的Python包导入成功")
        
        # 测试NLTK数据
        print("\n下载并验证NLTK数据...")
        required_nltk_data = ['punkt', 'stopwords', 'averaged_perceptron_tagger']
        for data in required_nltk_data:
            try:
                nltk.data.find(f'tokenizers/{data}')
            except LookupError:
                print(f"下载NLTK数据: {data}...")
                nltk.download(data, quiet=True)
        print("✓ NLTK数据验证完成")
        
        # 验证Bio库功能
        print("\n验证Bio库功能...")
        if not hasattr(Bio, '__version__'):
            raise ImportError("Bio库安装不完整")
        print(f"✓ Bio库版本: {Bio.__version__}")
        
        # 检查中文字体
        print("\n检查中文字体配置...")
        check_chinese_font()
        
        # 测试matplotlib后端
        print("\n验证matplotlib配置...")
        matplotlib.pyplot.figure()
        matplotlib.pyplot.close()
        print("✓ Matplotlib配置正常")
        
        # 测试配置文件读取和模板完整性
        print("\n验证配置文件...")
        config_file = SCRIPT_DIR / "config.yaml"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 验证配置文件的完整性
            required_sections = ['api', 'pubmed', 'filters', 'visualization', 'analysis', 'output']
            missing_sections = [section for section in required_sections if section not in config]
            if missing_sections:
                print(f"警告: 配置文件缺少以下部分: {', '.join(missing_sections)}")
            else:
                print("✓ 配置文件结构验证通过")
        
        print("\n✓ 环境测试全部通过！")
        return True
    except ImportError as e:
        print(f"\n错误: 缺少必要的Python包: {e}")
        print("请运行 'pip install -r requirements.txt' 安装所有依赖")
        return False
    except Exception as e:
        print(f"\n错误: 环境测试失败: {e}")
        return False

def main():
    print("=== 开始配置PubMed文献分析系统 ===\n")
    
    # 切换到脚本所在目录
    os.chdir(SCRIPT_DIR)
    
    # 检查项目目录
    check_project_directory()
    
    # 检查Python版本
    check_python_version()
    
    # 检查环境
    check_environment()
    
    # 创建必要的目录
    create_directories()
    
    # 安装依赖
    install_dependencies()
    
    # 设置配置文件
    setup_config()
    
    # 测试环境配置
    if test_environment():
        print("\n=== 配置完成 ===")
        print("1. 请确保已在config.yaml中设置了正确的API密钥和邮箱地址")
        print("2. 您现在可以运行 'python main.py' 来启动系统")
    else:
        print("\n=== 配置未完全成功 ===")
        print("请检查上述错误信息并解决问题后重新运行setup.py")

if __name__ == "__main__":
    main()