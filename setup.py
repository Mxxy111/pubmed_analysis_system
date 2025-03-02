import os
import sys
import shutil
import subprocess
import platform
import json
import yaml
import nltk
import copy
import Bio
import logging
import time
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent.absolute()

logger = logging.getLogger(__name__)

def setup_logging():
    """配置日志，同时输出到终端和文件，并支持日志文件滚动保存"""
    global logger
    if logger.hasHandlers():
        return
    # 日志格式
    log_format1 = '%(asctime)s - %(levelname)s - %(message)s'
    log_format2 = '%(message)s'
    # 创建文件处理器，支持日志文件滚动保存
    file_handler = RotatingFileHandler(
        SCRIPT_DIR / "setup.log",  # 日志文件路径
        maxBytes=10 * 1024 * 1024,  # 每个日志文件最大 10MB
        backupCount=5,  # 保留 5 个备份日志文件
        encoding='utf-8'  # 设置文件编码
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format1))

    # 创建控制台处理器，将日志输出到终端
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format2))

    # 获取根日志器并配置
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 测试日志输出
    logger.info("日志配置完成，开始记录日志")

def load_version_map(file_path=SCRIPT_DIR /"version_map.json"):
    #加载版本映射文件
    try:
        with open(file_path, "r") as file:
            # 将 JSON 文件内容解析为 Python 字典
            version_map = json.load(file)
        
        # 转换字符串键为元组
        # 例如 "(3, 8)" -> (3, 8)
        version_map = {tuple(map(int, key.strip('()').split(','))): value for key, value in version_map.items()}
        return version_map
    except Exception as e:
        logger.error(f"加载版本映射文件失败: {e}")
        raise RuntimeError("版本映射文件加载失败")

def load_mirrors_from_json(mirrors_file =SCRIPT_DIR /'mirrors.json'):
    """加载镜像源列表从 JSON 文件"""
    try:
        with open(mirrors_file, 'r') as file:
            data = json.load(file)
            return data.get('mirrors', [])
    except Exception as e:
        logger.error(f"加载镜像源文件失败: {e}")
        sys.exit(1)

def check_project_directory():
    #检查是否在正确的项目目录下运行
    required_files = ['requirements.txt', 'config.yaml.template', 'main.py',]
    missing_files = [f for f in required_files if not (SCRIPT_DIR / f).exists()]
    
    if missing_files:
        logger.error("✗... 项目目录文件不完整")
        logger.error(f"脚本目录: {SCRIPT_DIR}")
        logger.error("项目目录应包含以下文件: ")
        for file in required_files:
            status = '✓...' if file not in missing_files else '✗'
            logger.error(f" {status}...{file}")
        return False
    logger.info("✓...项目目录检查通过")
    return True

def get_compatible_version(current_version, version_map):
    #获取当前 Python 版本最匹配的依赖版本配置
    compatible_version = None
    for version in sorted(version_map.keys()):
        if current_version >= version:
            compatible_version = version

    if compatible_version is None:
        return version_map[min(version_map.keys())]  # 返回最低兼容版本的配置
    
    return version_map[compatible_version]

def check_python_version():
    #检查Python版本是否满足要求并返回适配的依赖版本信息
    min_version = (3, 8)
    max_version = (3, 13)
    version_map = load_version_map()
    
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        logger.error(f"✗... 需要Python {min_version[0]}.{min_version[1]} 或更高版本")
        logger.error(f"当前版本: Python {current_version[0]}.{current_version[1]}")
        return False
    elif current_version > max_version:
        logger.warning(f"警告: 当前Python版本 {current_version[0]}.{current_version[1]} 可能不完全兼容")
        logger.warning(f"推荐使用Python {min_version[0]}.{min_version[1]} 到 {max_version[0]}.{max_version[1]} 之间的版本")
        
        # 询问用户是否退出安装
        while True:
            user_input = input("是否退出当前安装 (y/n)？").strip().lower()
            if user_input == 'y':
                logger.info("用户选择退出安装程序")
                return False
            elif user_input == 'n':
                logger.info(f"✓...继续安装")
                return version_map[max_version]
            else:
                logger.error("✗...无效输入，请输入 'y' 或 'n'")
        

    compatible_packages = get_compatible_version(current_version, version_map)
    
    logger.info(f"✓...Python 版本检查通过: {sys.version.split()[0]}")
    logger.info(f"✓...将使用 Python {current_version[0]}.{current_version[1]} 兼容的依赖版本")
    
    return compatible_packages

def construct_cmd(pkg, mirror,extra_args=None):
    """构建 pip 安装命令"""
    cmd = [
            sys.executable, "-m", "pip", "install",
            pkg,
            "-i", mirror,
            "--timeout", "60",
            "--retries", "3"
        ]
    if extra_args == '--upgrade':
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "-i", mirror]
    elif extra_args:
        cmd.extend(extra_args)
    return cmd

def pip_install(packages, extra_args=None, retry_count=5):
    """通用pip安装函数，支持多个镜像源重试"""
    pip_mirrors = load_mirrors_from_json()  # 从 JSON 文件加载镜像源  
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
                    cmd = construct_cmd(pkg, mirror,extra_args)
                    subprocess.check_call(cmd)
                return True  # 如果所有包都成功安装，返回 True
            except subprocess.CalledProcessError as e:
                if attempt < retry_count - 1:
                    logger.warning(f"安装失败，尝试重试当前镜像源...第{attempt+1}/{retry_count-1}次")
                    continue
                logger.error(f"警告: 使用镜像 {mirror} 安装失败")
                break
    logger.error("所有镜像源尝试失败")
    return False    # 如果所有镜像源都尝试失败
    
def install_dependencies():
    """安装项目依赖（分阶段安装）"""
    requirements_file = SCRIPT_DIR / "requirements.txt"
    try:
        logger.info("=== 开始分阶段安装依赖 ===\n")
        
        # 获取适配的依赖版本
        compatible_versions = check_python_version()
        
        #调用系统命令升级 pip
        logger.info("0.调用系统命令升级 pip...")
        if pip_install(['pip'],"--upgrade"):
            logger.info("✓... pip 升级成功")

        # 基础编译依赖
        logger.info("1. 安装基础编译依赖...")
        if pip_install(["wheel", "setuptools>=69.0.0"]):
            logger.info("✓... 基础编译依赖安装完成")
        
        # 数值计算核心
        logger.info("\n2. 安装数值计算核心包...")
        packages = [
            f"numpy>={compatible_versions['numpy']}",
            f"pandas>={compatible_versions['pandas']}",
            f"scipy>={compatible_versions['scipy']}"
        ]
        
        for package in packages:
            extra_args = []
            if "numpy" in package:
                extra_args.append("--only-binary=:all: ")
            if "pandas" in package:
                extra_args.append("--use-pep517")
            
            if pip_install(package, extra_args):
                logger.info(f"✓... {package} 安装成功")
        
        # 图形相关依赖
        logger.info("\n3. 安装图形相关依赖...")
        if pip_install("matplotlib>=3.7.0"):
            logger.info("✓... matplotlib 安装成功")
        
        if platform.system() == "Windows":
            if pip_install("PyQt5>=5.15.0"):
                logger.info("✓... PyQt5 安装成功")
        
        # 其他依赖
        logger.info("\n4. 安装其他依赖...")
        if pip_install(f"-r {str(requirements_file)}"):
            logger.info("✓... 其他依赖安装完成")
        
        logger.info("=== 依赖安装完成 ===\n")
        return True
    
    except Exception as e:
        logger.error(f"\n✗... 安装过程中出现异常: {str(e)}")
        logger.info("如果某些包安装失败，建议: ")
        logger.info("1. 检查网络连接")
        logger.info("2. 使用管理员权限运行")
        logger.info("3. 尝试手动安装失败的包")
        logger.info("4. 考虑使用其他镜像源")
        return False

def load_yaml(file_path):
    """安全加载 YAML 文件"""
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
    
def save_yaml(config_file,config_data):
    with open(config_file, 'w', encoding='utf-8') as file:
        yaml.safe_dump(config_data, file, default_flow_style=False, allow_unicode=True)

def get_available_models(config):
    available_models = {}
    valid_api_info = {}
    for provider, details in config['api'].items():
        if details['api_key'] and details['api_key'] != "your_api_key_here" and details['endpoint'] and details['endpoint'] != "https://default_endpoint.com":  # 过滤掉无效 API key和Endpoint
            valid_models = [model for model in details['models'].values() if model != "No_default_model"]
            if valid_models:
                available_models[provider] = valid_models
                valid_api_info[provider] = copy.deepcopy(details)  # 深拷贝，彻底隔离
                valid_api_info[provider]["provider"] = "your_provider"
                valid_api_info[provider]["model"] = "No_default_model"
                del valid_api_info[provider]["models"]
    return available_models, valid_api_info

def choose_model(available_models, prompt):
    print(f"\n{prompt}")
    model_choices = []
    for provider, models in available_models.items():
        for model in models:
            model_choices.append((provider, model))
    
    for idx, (provider, model) in enumerate(model_choices):
        print(f"{idx+1}. {provider} - {model}")
    attempts = 0
    while attempts <5:
        try:
            choice = int(input("请输入选择的编号: ")) - 1
            if not 0<choice+1 <= len(model_choices):
                raise ValueError
            else:
                break
        except ValueError:
            logger.error(f"无效输入...请输入有效数字({attempts+1}/4)")
            attempts += 1
    else:
        return None , None
    return model_choices[choice][0] ,model_choices[choice][1]  # 返回模型名称
 
def add_custom_api(config_data):
    # 提示用户输入新 API 的配置
    print("请按照提示输入新的 API 配置: ")
    api_name = '自定义'
    default_endpoint = config_data['api']["自定义"]['endpoint']
    default_api_key = config_data['api']["自定义"]['api_key']
    default_models = config_data['api']["自定义"]['models']
    default_max_tokens = config_data['api'][api_name]['max_tokens']
    default_temperature = config_data['api'][api_name]['temperature']
    default_top_p = config_data['api'][api_name]['top_p']
    try:
        config_data['api'][api_name]['endpoint'] = input_endpoint(api_name,config_data)
        if config_data['api'][api_name]['endpoint'] == default_endpoint:
            raise ValueError
        config_data['api'][api_name]['models'] , flag = input_model(api_name,config_data)
        if not flag:
            raise ValueError
        config_data['api'][api_name]['api_key'] = input_api_key(api_name)
        if config_data['api'][api_name]['api_key'] == default_api_key:
            raise ValueError
        config_data['api'][api_name]['max_tokens'] = input_max_tokens(api_name,config_data)
        if not config_data['api'][api_name]['max_tokens']:
            config_data['api'][api_name]['max_tokens'] = default_max_tokens
            raise ValueError
        config_data['api'][api_name]['temperature'] = input_temperature(api_name,config_data)
        if not config_data['api'][api_name]['temperature']:
            config_data['api'][api_name]['temperature'] = default_temperature
            raise ValueError
        config_data['api'][api_name]['top_p'] = input_top_p(api_name,config_data)
        if not config_data['api'][api_name]['top_p']:
            config_data['api'][api_name]['top_p'] = default_top_p
            raise ValueError
        return config_data , True
    except ValueError:
        return config_data , False

def extract_keys(template):
    """递归提取模板的所有字段（键），忽略值。"""
    if isinstance(template, dict):
        return {key: extract_keys(value) for key, value in template.items()}
    elif isinstance(template, list):
        return [extract_keys(item) for item in template]
    else:
        return None

def compare_yaml_files(file1, file2):
    """判断两个 YAML 文件是否完全相同"""
    try:
        yaml1 = load_yaml(file1)
        yaml2 = load_yaml(file2)
        return yaml1 == yaml2  # 直接比较两个字典是否相等
    except Exception as e:
        logger.error(f"比较 YAML 文件时出错: {e}")
        return False

def compare_and_update(existing, template):
    """递归比较 YAML 结构，仅保留用户修改过的字段。"""
    if isinstance(template, dict):
        if not isinstance(existing, dict):
            return copy.deepcopy(template), {}  # 直接用模板替换，并返回空的 retained_values

        new_retained_values = {}

        for key in template:
            if key in existing:
                updated_value, retained_sub_values = compare_and_update(existing[key], template[key])
                existing[key] = updated_value

                # 只有当 retained_sub_values 不是空时，才认为这个 key 有用户修改
                if retained_sub_values not in [None, {}, []]:
                    new_retained_values[key] = retained_sub_values
            else:
                existing[key] = copy.deepcopy(template[key])  # 如果 `existing` 里没有，直接补充

        return existing, new_retained_values if new_retained_values else None

    elif isinstance(template, list):
        if not isinstance(existing, list):
            return copy.deepcopy(template), []  # 直接替换，并返回空的 retained_values

        new_retained_values = []
        min_length = min(len(existing), len(template))

        for i in range(min_length):
            updated_value, retained_val = compare_and_update(existing[i], template[i])
            existing[i] = updated_value
            if retained_val not in [None, {}, []]:
                new_retained_values.append(retained_val)

        # 如果 `existing` 比 `template` 长，说明用户增加了内容，需要保留
        if len(existing) > len(template):
            new_retained_values.extend(existing[len(template):])

        # 如果 `template` 比 `existing` 长，说明 `existing` 需要扩展
        if len(existing) < len(template):
            existing.extend(copy.deepcopy(template[len(existing):]))

        return existing, new_retained_values if new_retained_values else None

    else:
        # **改进点: 如果 existing 已有值，且不同于 template，则保留 existing**
        if existing != template and existing is not None:
            return existing, existing  # existing 是用户修改的值，保留它
        return template, None  # 没有修改，则不需要保留

def sync_yaml_with_template(template_file, existing_file):
    """同步 YAML 文件，并仅输出用户修改过的字段。"""
    template = load_yaml(template_file)
    existing = load_yaml(existing_file)

    updated_existing, retained_values = compare_and_update(existing, template)

    excluded_keys = {"active_model", "mesh_query_model"}  # 要排除的字段

    # 生成一个新的字典，去除指定字段
    filtered_existing = {k: v for k, v in updated_existing.items() if k not in excluded_keys}
    with open(existing_file, "w", encoding="utf-8") as file:
        yaml.safe_dump(filtered_existing, file, default_flow_style=False, allow_unicode=True)

    save_yaml(existing_file,updated_existing)

    logger.info("\n✓...YAML 文件已同步。\n")

    # **仅输出真正修改的字段**
    if retained_values not in [None, {}, []]:
        print(yaml.dump(retained_values, allow_unicode=True, default_flow_style=False))
        print("\n📌 以上是原 YAML 中用户除active_model与mesh_query_model外修改的部分（注意:模版预设值如默认的Endpoint和model ID不会显示！！） ")
    else:
        print("\n✓...YAML 文件同步完成，未检测到用户修改的数据。")

    return updated_existing

def check_application_model_info(model_data,template_data):
    if isinstance(template_data, dict):
        for key in template_data:
            if key in model_data and not check_application_model_info(model_data[key], template_data[key]) and key != "models":
                return False
            if key == "models":
                if not model_data["model"] in template_data["models"].values():
                    return False
        return True
    # 如果是其他类型（如字符串、数字等），直接比较值
    else:
        return model_data == template_data

def setup_config():
    """设置配置文件"""
    config_template = Path("config.yaml.template")
    config_file = Path("config.yaml")

    if not config_template.exists():
        logger.error(f"✗... 未找到配置模板 {config_template}")
        return False
    
    if not config_file.exists():
        if not edit_config(config_template, config_file,edit_new_config=True):
            return False
    
    # 判断 YAML 是否完全未修改（即仍然是默认配置）
    if compare_yaml_files(config_file, config_template):
        logger.info("✓... 检测到当前 YAML 文件仍为默认配置，启动引导设置")
        if not edit_config(config_template, config_file):
            return False
    
    # 否则，正常同步 YAML
    attempts = 0
    while attempts < 5:
        for i in range(1, 3):
            message = " 正在同步模板信息" + "." * i
            sys.stdout.write("\r" + message)
            sys.stdout.flush()
            time.sleep(0.5)
        sync_yaml_with_template(config_template, config_file)
        if compare_yaml_files(config_file, config_template):
            logger.info("✓... 检测到当前 YAML 文件仍为默认配置，启动引导设置")
            if not edit_config(config_template, config_file):
                return False
            continue
            
        print("请选择以下功能:")
        print("1、确认先有文件基本信息无误，继续下一步以确认mesh query model & active model")
        print("2、(手动逐条修改，较复杂)在现有配置文件基础上补充或删除信息（若少量配置信息需要修改，可选择此项）")
        print("3、(自动引导修改，较快捷)在现有配置文件基础上补充或删除信息（若较多配置信息需要修改，可选择此项）")
        print("4、直接删除现有配置文件并重新配置")
        print("5、不做修改，退出程序")
        user_choice = input('请选择（输入1-5）: ').strip()
        if user_choice == "1":
            active_model_flag = False
            while True:
                config_data = load_yaml(config_file)
                template_data = load_yaml(config_template)
                active_model_provider = config_data["active_model"]["provider"]
                mesh_query_model_provider = config_data["mesh_query_model"]["provider"]
                if active_model_provider == "your_provider" or not check_application_model_info(config_data["active_model"],config_data["api"][active_model_provider])or active_model_flag:
                    logger.info("正在查找active model可用的API相关设置")

                    available_models , available_api_infos = get_available_models(config_data)

                    if not available_models:
                        logger.error(f"\n\n✗...未找到可用模型(模型ID，API-KEY，Endpoint不完整)，请检查配置文件({attempts+1}/4)\n\n")
                        break
                    provider , active_model = choose_model(available_models, "请选择 active_model:")
                    if not active_model:
                        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
                        return False
                    else:
                        available_api_infos[provider]['model'] = active_model
                        available_api_infos[provider]["provider"] = provider
                        for key in available_api_infos[provider].keys():
                            config_data['active_model'][key] = available_api_infos[provider][key]
                        save_yaml(config_file,config_data)
                        active_model_flag = False

                if mesh_query_model_provider == "your_provider" or not check_application_model_info(config_data["mesh_query_model"],config_data["api"][mesh_query_model_provider]):
                    logger.info("正在查找mesh query model可用的API相关设置")
                    available_models , available_api_infos = get_available_models(config_data)
                    if not available_models:
                        logger.error(f"\n\n✗...未找到可用模型(模型ID，API-KEY，Endpoint不完整)，请检查配置文件({attempts+1}/4)\n\n")
                        break
                    provider , mesh_query_model = choose_model(available_models, "请选择 mesh_query_model:")
                    if not mesh_query_model:
                        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
                        return False
                    else:
                        available_api_infos[provider]['model'] = mesh_query_model
                        available_api_infos[provider]["provider"] = provider
                        for key in available_api_infos[provider].keys():
                            config_data['mesh_query_model'][key] = available_api_infos[provider][key]
                        save_yaml(config_file,config_data)

                if not active_model_flag:
                    print(f"\n您选择的 active_model 配置信息:\n")
                    print(yaml.dump(config_data['active_model'], allow_unicode=True, default_flow_style=False))
                    if input("回车Enter以继续，若要修改请输入其他任意字符:").strip():
                        config_data['active_model'] = template_data['active_model']
                        save_yaml(config_file,config_data)
                        active_model_flag = True
                        continue
                    else:
                        active_model_flag = False

                print(f"您选择的 mesh_query_model 配置信息:\n ")
                print(yaml.dump(config_data['mesh_query_model'], allow_unicode=True, default_flow_style=False))
                user_input = input("回车Enter以继续，若要修改请输入其他任意字符,输入b返回上一步(选择active modoel):")

                if user_input == "b":
                    active_model_flag = True
                    config_data['active_model'] = template_data['active_model']
                    save_yaml(config_file,config_data)
                    continue
                elif user_input:
                    config_data['mesh_query_model'] = template_data['mesh_query_model']
                    save_yaml(config_file,config_data)
                    active_model_flag = False
                    continue

                save_yaml(config_file,config_data)
                print("\n-------------配置已成功保存！-------------\n")
                time.sleep(2)
                logger.info("✓... 配置文件检查完毕")
                return True
        elif user_choice == "2":
            result = edit_old_config(config_file,config_template)
            if result== "quit":
                continue
            else:
                return result
        elif user_choice == "3":
            if not edit_config(config_template, config_file):
                return False
            continue
        elif user_choice == '4':
            config_file.unlink()
            logger.info(f"\n✓... 文件 {config_file} 已删除")
            if not edit_config(config_template, config_file,edit_new_config=True):
                return False
        elif user_choice == '5':
            return False
        else:
            logger.error(f'无效输入，请输入正确数字({attempts+1}/4)')       
            attempts += 1
    else:
        logger.error("✗... 超过最大重试次数")
        return False

def edit_old_config(yaml_file,template_file):
    data = load_yaml(yaml_file)
    template = load_yaml(template_file)

    updated_data = update_yaml_interactively(data,template,config_data=data,template_data=template)

    print("\n📁 配置文件已保存")
    if updated_data:
        # 保存修改后的 YAML
        save_yaml(yaml_file,updated_data)
        return "quit"
    else:
        return False

def get_value_from_path(template, path):
    """根据路径提取template中的值，并格式化为yaml字符串"""
    target = template
    for p in path:
        target = target[p]
    return yaml.dump(target, default_flow_style=False, allow_unicode=True)

def get_user_choice(options, current_data, template, path=None, allow_reset=False):
    """获取用户选择，并根据用户选择恢复或修改字段"""
    if path is None:
        path = []
    attempt = 0
    while attempt < 5:
        print("\n请选择要修改的字段 (输入序号):")
        for i, key in enumerate(options):
            print(f"{i + 1}. {key}")

        if allow_reset:
            print("0. 🔄 恢复以上所有字段为默认值")
        
        if path:  # 只有在子目录时才显示返回上一级
            print("b. ⬅ 返回上一级")

        choice = input("\n输入序号 (或输入 'q' 退出): ").strip()
    
        if choice.lower() == 'q':
            return "quit_all"
        elif choice.lower() == 'b' and path:
            return "back"
        elif allow_reset and choice == "0":
            default_value_str = get_value_from_path(template, path)
            print(f"\n当前字段的默认值为: \n{default_value_str}")
            restore_default = input("\n确认恢复为默认值吗？ (y/n): ").strip().lower()
            atmpt = 0
            while atmpt <5:
                if restore_default == "y":
                    return "reset"  # 用户确认恢复默认值
                elif restore_default == "n":
                    print("\n操作已取消")
                    return "quit"
                else:
                    print(f"✗...请输入 'y' 或 'n'({atmpt+1}/4)")
                    atmpt +=1
            else:
                return "quit"

        elif choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        else:
            logger.info(f"✗...无效选择，请重新输入({attempt+1}/4)")
            attempt += 1
    else:
        logger.error("✗... 超过最大重试次数，请检查输入!!!")
        return None
    
def update_yaml_interactively(data, template, config_data,template_data,path=None,model= None):
    """递归地引导用户修改 YAML 数据"""
    if path is None:
        path = []

    while isinstance(data, (dict, list)):
        print("\n📂 当前字段已保存信息:")
        print(yaml.dump(data, allow_unicode=True, default_flow_style=False))
        if isinstance(data, dict):
            choice = get_user_choice(list(data.keys()), data, template_data, path, allow_reset=True)

            if choice is None:
                return data
            elif choice == "quit_all":
                if path:
                    return "quit_all"
                else:
                    return data
            elif choice == "back":
                return "back"
            elif choice == "quit":
                continue
            elif choice == "reset" and not path:
                restore_all = input("\n是否要恢复所有内容为模板的默认值？(yes/no): ").strip().lower()
                attempts = 0
                while attempts < 5:
                    if restore_all == "yes":
                        logger.info("\n✓...所有字段已恢复为默认值！")
                        return template  # 返回整个模板（恢复所有内容）
                    elif restore_all == "no":
                        break
                    else:
                        logger.error("✗...请输入 'yes' 或 'no'")
                        attempts += 1
                else:
                    logger.error("✗... 超过最大重试次数，请检查输入")
                    return data
                continue
            elif choice == "reset":
                template_target = template
                print("\n✓...以上所有字段已恢复为默认值！")
                return template_target  # 直接返回
            else:
                path.append(choice)
                pattern = r"^model_[1-5]$"
                if choice == "username":
                    result = input_username(config_data,template_data)
                elif choice == "email":
                    result = input_email(config_data,template_data)
                elif choice == "endpoint":
                    result = input_endpoint(path[-2],config_data,template_data)
                elif choice == "api_key":
                    result = input_api_key(path[-2],config_data,template_data)
                elif choice == "max_tokens":
                    result = input_max_tokens(path[-2],config_data,template_data)
                elif choice == "temperature":
                    result = input_temperature(path[-2],config_data,template_data)
                elif choice == "top_p":
                    result = input_top_p(path[-2],config_data,template_data)
                elif choice == "active_model" or choice =="mesh_query_model":
                    print(f"\n{choice}配置禁止在此功能中修改!!!!\n")
                    result = "back"
                elif re.match(pattern, choice):
                    result = update_yaml_interactively(data[choice], template[choice],config_data,template_data, path,model=path[-3])
                else:
                    result = update_yaml_interactively(data[choice], template[choice],config_data,template_data, path)

            if result == "back":
                if path:
                    path.pop()
                continue
            elif result == "quit":
                return "quit"
            elif result == "quit_all":
                path.pop()
                if path:
                    return "quit_all"
                else:
                    return data
            else:
                if path:
                    path.pop()
                data[choice] = result  # 更新数据

        elif isinstance(data, list):
            attempts = 0
            while attempts < 5:
                print("\n当前字段是一个列表，请选择要修改的索引:")
                for i, item in enumerate(data):
                    print(f"{i + 1}. {item}")

                if path:
                    print("b. ⬅ 返回上一级")
                index_choice = input("\n输入索引 (1 ~ {}，或输入 'q' 退出): ".format(len(data))).strip()

                if index_choice.lower() == 'q':
                    return "quit_all"
                elif index_choice.lower() == 'b':
                    return "back"

                if index_choice.isdigit() and 1 <= int(index_choice) <= len(data):
                    index = int(index_choice) - 1
                    path.append(index)
                    result = update_yaml_interactively(data[index], template[index], config_data,template_data,path)
                    if result == "back":
                        if path:
                            path.pop()
                        continue
                    elif result == "quit":
                        return "quit"
                    elif result == "quit_all":
                        path.pop()
                        if path:
                            return "quit_all"
                        else:
                            return data
                    else:
                        if path:
                            path.pop()
                        data[index] = result  # 更新数据
                else:
                    logger.error(f"✗...无效索引，请重新输入{attempts+1}/4")
                    attempts +=1
            else:
                logger.error("✗... 超过最大重试次数，请检查输入")
                continue

    # 处理叶子节点
    current_value = data
    default_value = template

    # 判断是否和默认值相同，并加上（默认）标记
    default_label = "（默认）" if current_value == default_value else ""

    print(f"\n当前字段的值: {current_value} {default_label}")
    print(f"默认值: {default_value}")

    attempts = 0
    while attempts < 5:
        restore_default = input("\n恢复默认值 (y) 或输入新值 (n)，输入 'b' 返回上一级: ").strip().lower()
        if restore_default in ["y", "n"]:
            break
        if restore_default == "b":
            return "back"
        
        print(f"✗...请输入 'y' 、'n'或'b'({attempts+1}/4)")
        attempts += 1
    else:
        logger.error("✗... 超过最大重试次数，自动返回上一级")
        return "back"

    # 关键修复:直接替换整个字段的值，不再通过路径索引操作
    if restore_default == "y":
        # 直接返回模板的默认值
        print("\n✓...该字段已恢复为默认值！")
        return template
    else:
        attempts = 0
        while attempts <5:
            new_value = input("\n请输入新的值: ").strip()
            try:
                if isinstance(template, int):
                    new_value = int(new_value)
                elif isinstance(template,float):
                    new_value = float(new_value)
            except ValueError:
                logger.error(f"无效输入...请输入格式一致的有效信息{attempts+1}/4")
                attempts += 1
                continue
            if new_value:
                if model:
                    if new_value == "No_default_model":
                        logger.error(f"无效输入...请输入有效信息{attempts+1}/4")
                        attempts += 1
                        continue
                    elif new_value in config_data["api"][model]["models"].values():
                        for repeat_model_index,repeat_model in enumerate(config_data["api"][model]["models"].values()):
                            if new_value == repeat_model:
                                logger.error(f"\n重复输入...已保存的model{repeat_model_index+1}ID:{repeat_model}\n请输入有效模型接入点ID({attempts+1}/4)")
                                attempts += 1
                                break
                        continue
                print("\n✓...修改成功！")
                return new_value  # 直接返回用户输入的新值
            else:
                logger.error(f"空白输入...请输入有效信息{attempts+1}/4")
                attempts += 1
        else:
            logger.error("✗... 超过最大重试次数，自动返回上一级")
            return "back"

def edit_config(config_template, config_file, edit_new_config = False, simple_mode = False):
    """引导用户填写 YAML 配置"""
    if edit_new_config:
        shutil.copy2(config_template, config_file)
        logger.info(f"✓... 已创建新配置文件: {config_file}")
    attempts = 0
    while attempts <5 :
        print("请选择配置模式:")
        print(*[f"{i+1}.{choice}" for i,choice in enumerate(["快捷配置模式（模型的参数配置将使用默认值，如max_tokens、temperature、top_p；且无法自定义新API）","高级配置模式(可修改所有配置)"])], sep = "\n")
        simple_mode_choice = input("请输入对应序号(输入q以退出程序):").strip()
        if simple_mode_choice == "1":
            simple_mode = True
            break
        elif simple_mode_choice == "2":
            break
        elif simple_mode_choice == "q":
            return False
        else:
            attempts += 1
            logger.error(f'无效输入，请输入正确数字({attempts}/4)')
    else:
        logger.error("✗... 超过最大重试次数")
        return False
        
    config_data = load_yaml(config_file)
    template_data = load_yaml(config_template)
    attempts = 0
    while attempts <5:
        try:
            print("请按照提示输入以下信息: ")

            username = input_username(config_data,template_data)
            if not username:
                raise ValueError
            else:
                config_data['username'] = username
            
            email = input_email(config_data,template_data)
            if not email:
                raise ValueError
            else:
                config_data['pubmed']['email'] = email

            api_list = list(config_data.get("api", {}).keys())
            api_list.append("保存并退出")

            atmpt = 0
            while atmpt <5:
                print(*[f"{i+1}. {name}" for i, name in enumerate(api_list)], sep="\n")
                provider_choice = input(f"本程序设置了几个默认API访问地址(provider)，请选择: ").strip()
                try:
                    provider_choice_number = int(provider_choice)
                    if not (provider_choice_number < len(api_list)+1 and provider_choice_number>0):
                        raise ValueError
                except ValueError:
                    atmpt +=1
                    logger.error(f"无效输入...请重新输入正确的数字({atmpt}/4)")
                    continue
                
                api_name = api_list[provider_choice_number - 1]

                if api_name == "自定义" and simple_mode:
                    logger.error("\n快捷配置模式不能自定义API！！！\n")
                    continue
                elif api_name == "保存并退出":
                    save_yaml(config_file,config_data)
                    return False 
                else:
                    try:
                        endpoint = input_endpoint(api_name,config_data,template_data)
                        if not endpoint:
                            raise ValueError
                        else:
                            config_data["api"][api_name]["endpoint"] = endpoint

                        models , flag= input_model(api_name,config_data,template_data)
                        if not flag:
                            config_data["api"][api_name]["models"] = models
                            raise ValueError
                        else:
                            config_data["api"][api_name]["models"] = models

                        api_key = input_api_key(api_name,config_data,template_data)
                        if not api_key:
                            raise ValueError
                        else:
                            config_data['api'][api_name]['api_key'] = api_key
                        
                        if not simple_mode:
                            max_tokens = input_max_tokens(api_name,config_data,template_data)
                            if not max_tokens:
                                raise ValueError
                            else:
                                config_data['api'][api_name]['max_tokens'] = max_tokens
                            
                            temperature = input_temperature(api_name,config_data,template_data)
                            if not temperature:
                                raise ValueError
                            else:
                                config_data['api'][api_name]['temperature'] = temperature
                
                            top_p = input_top_p(api_name,config_data,template_data)
                            if not top_p:
                                raise ValueError
                            else:
                                config_data['api'][api_name]['top_p'] = top_p
                    except ValueError:
                        save_yaml(config_file,config_data)
                        return False
                print("\n您的信息如下: ")
                print(f"您的用户名: {config_data['username']}")
                print(f"您的Pubmed邮箱地址: {config_data['pubmed']['email']}")
                print(f"您的API名称: {api_name}")
                print(f"您的API端点: {config_data['api'][api_name]['endpoint']}")
                print(f"您的模型IDs: ")
                for model_index_number,model_ID in enumerate(config_data['api'][api_name]['models'].values()):
                    if model_ID != 'No_default_model':
                        print(f"   {model_index_number+1}:{model_ID}")
                print(f"您的API密钥:{config_data['api'][api_name]['api_key']}")
                if not simple_mode:
                    print(f"max_tokens:{config_data['api'][api_name]['max_tokens']}")
                    print(f"temperature:{config_data['api'][api_name]['temperature']}")
                    print(f"top_p:{config_data['api'][api_name]['top_p']}")

                apt = 0
                while apt <5:
                    user_input = input("这些信息正确吗？ (y/n): ").strip().lower()
                    if  user_input== 'y':
                        save_yaml(config_file,config_data)
                        return True
                    elif user_input== 'n':
                        logger.error(f"\n重新输入{attempts+1}/4\n")
                        attempts +=1
                        break
                    else:
                        apt+=1
                        logger.error(f"无效输入...请重新输入正确的数字或字母({apt}/4)")
                else:
                    logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
                    save_yaml(config_file,config_data)
                    return False
                break
            else:
                logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
                save_yaml(config_file,config_data)
                return False
        except ValueError or IndexError:
            logger.error(f"请检查输入!!!")
            save_yaml(config_file,config_data)
            return False 
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    
def input_username(config_data,template_data):
    old_username = config_data['username']
    default_username = template_data["username"]
    attempts = 0
    while attempts <5:
        if old_username == default_username:
            username = input(f"请输入您的用户名: ").strip()
        else:
            username = input(f"已保存的用户名(回车Enter保存并继续，或直接输入新用户名):{old_username}\n")
        if not username :
            if old_username == default_username:
                logger.error(f"无效输入...请输入有效用戶名({attempts+1}/4)")
                attempts += 1
                continue
            else:
                return old_username
        else:
            return username
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    
def input_email(config_data,template_data):
    old_email = config_data['pubmed']["email"]
    default_email = template_data['pubmed']["email"]
    attempts = 0
    while attempts <5:
        if old_email == default_email:
            email = input(f"请输入您的Pubmed邮箱地址: ").strip()
        else:
            email = input(f"已保存的邮箱地址(回车Enter保存并继续，或直接输入新用户名):{old_email}\n")
        if not email:
            if old_email == default_email:
                logger.error(f"无效输入...请输入有效邮箱地址({attempts+1}/4)")
                attempts += 1
                continue
            else:
                return old_email
        else:
            return email
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False

def input_endpoint(api_name,config_data,template_data):
    old_endpoint = config_data['api'][api_name]['endpoint']
    default_endpoint = template_data['api'][api_name]['endpoint']
    attempts = 0
    while attempts <5:
        if default_endpoint == old_endpoint and default_endpoint != "https://default_endpoint.com":
            endpoint = input(f"已保存的Endpoint为默认地址{default_endpoint}(回车Enter保存并继续，或直接输入新地址)\n")
            if not endpoint:
                endpoint = default_endpoint
        elif default_endpoint == old_endpoint and default_endpoint == "https://default_endpoint.com":
            endpoint = input(f"请输入您想使用的API地址（无默认端点，需手动添加！！）: ").strip()
        else:
            endpoint = input(f"已保存API地址(回车Enter保存并继续，或直接输入新地址):{old_endpoint}\n").strip()
            if not endpoint:
                endpoint = old_endpoint

        if not endpoint or endpoint == "https://default_endpoint.com":
            logger.error(f"无效输入...请输入有效API端点({attempts+1}/4)")
            attempts += 1
        else:
            break
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    return endpoint

def input_model(api_name,config_data,template_data):
    model_counter = 1
    models = config_data['api'][api_name]['models']
    old_model = config_data['api'][api_name]['models']
    default_model = template_data['api'][api_name]['models']
    attempts = 0
    while attempts < 5 and model_counter < 6:
        model_index = f"model_{model_counter}"
        print(f"\n默认模型{model_counter}接入点ID:{default_model[model_index]}")
        if old_model[model_index] == default_model[model_index] and default_model[model_index] != "No_default_model":
            model_choice = input(f"请输入您想使用的模型{model_counter}接入点ID(最多输入5个)（回车Enter选择默认,或直接输入新ID）: ").strip()
            if model_choice == "No_default_model":
                logger.error(f"\n请勿输入默认值！！！\n请输入有效模型接入点ID({attempts+1}/4)")
                attempts += 1
                continue
            elif model_choice in models.values():
                for repeat_model_index,repeat_model in enumerate(models.values()):
                    if model_choice == repeat_model:
                        logger.error(f"\n重复输入...已保存的model{repeat_model_index+1}ID:{repeat_model}\n请输入有效模型接入点ID({attempts+1}/4)")
                        attempts += 1
                        break
                continue
            elif not model_choice in models.values():
                if model_choice:
                    models[model_index] = model_choice
                else:
                    models[model_index] = default_model[model_index]
        elif old_model[model_index] == default_model[model_index] and default_model[model_index] == "No_default_model":
            if old_model[model_index] == "No_default_model":
                if model_counter == 1:
                    model_choice = input(f"请输入您想使用的模型{model_counter}接入点ID(最多输入5个)（无默认模型，请手动添加）: ").strip()
                    if model_choice == "No_default_model":
                        logger.error(f"\n请勿输入默认值！！！\n请输入有效模型接入点ID({attempts+1}/4)")
                        attempts += 1
                        continue
                    if not model_choice :
                        logger.error(f"\n空白输入...请输入有效模型接入点ID({attempts+1}/4)")
                        attempts += 1
                        continue
                    elif model_choice in models.values():
                        for repeat_model_index,repeat_model in enumerate(models.values()):
                            if model_choice == repeat_model:
                                logger.error(f"\n重复输入...已保存的model{repeat_model_index+1}ID:{repeat_model}\n请输入有效模型接入点ID({attempts+1}/4)")
                                attempts += 1
                                break
                        continue
                    else:
                        models[model_index]= model_choice
                elif 1< model_counter <= 5:
                    model_choice = input(f"请输入您想使用的模型{model_counter}接入点ID(最多输入5个)（无默认模型）,回车Enter进行下一步: ").strip()
                    if model_choice == "No_default_model":
                        logger.error(f"\n请勿输入默认值！！！\n请输入有效模型接入点ID({attempts+1}/4)")
                        attempts += 1
                        continue
                    if model_choice in models.values():
                        for repeat_model_index,repeat_model in enumerate(models.values()):
                            if model_choice == repeat_model:
                                logger.error(f"\n重复输入...已保存的model{repeat_model_index+1}ID:{repeat_model}\n请输入有效模型接入点ID({attempts+1}/4)")
                                attempts += 1
                                break
                        continue
                    elif model_choice != '':
                        models[model_index] = model_choice  
                    else:
                        break
        else:
            model_choice = input(f"已保存的模型{model_counter}接入点ID：{old_model[model_index]}\n（回车Enter保存并继续,或直接输入新ID）: ").strip()
            if model_choice == "No_default_model":
                logger.error(f"\n请勿输入默认值！！！\n请输入有效模型接入点ID({attempts+1}/4)")
                attempts += 1
                continue
            if model_choice in models.values():
                for repeat_model_index,repeat_model in enumerate(models.values()):
                    if model_choice == repeat_model:
                        logger.error(f"\n重复输入...已保存的model{repeat_model_index+1}ID:{repeat_model}\n请输入有效模型接入点ID({attempts+1}/4)")
                        attempts += 1
                        continue
            if not model_choice:
                models[model_index] = old_model[model_index]
            else:
                models[model_index] = model_choice
        model_counter += 1  # 增加模型索引
    else:
        if attempts >=5:
            logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
            return models , False
    return models , True
     
def input_api_key(api_name,config_data,template_data):
    old_api_key = config_data['api'][api_name]["api_key"]
    default_api_key = template_data['api'][api_name]["api_key"]
    attempts = 0
    while attempts <5:
        if old_api_key == default_api_key:
            api_key = input(f"请输入您的 {api_name} API 密钥: ").strip()
        else:
            api_key = input(f"已保存的{api_name} API 密钥(回车Enter保存并继续，或直接输入API密钥):{old_api_key}\n")
            if not api_key:
                api_key = old_api_key
        if not api_key:
            logger.error(f"无效输入...请输入有效API_KEY({attempts+1}/4)")
            attempts += 1
        else:
            return api_key
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    
def input_max_tokens(api_name,config_data,template_data):
    old_max_tokens = config_data['api'][api_name]['max_tokens']
    default_max_tokens = template_data['api'][api_name]['max_tokens']
    attempts = 0
    while attempts<5:
        if old_max_tokens == default_max_tokens:
            max_tokens = input(f"请输入您的 {api_name} max_tokens（默认 {default_max_tokens}）,按回车Enter保存并继续: ").strip()
            if not max_tokens:
                max_tokens = default_max_tokens
        else:
            max_tokens = input(f"已保存的{api_name} max_tokens(回车Enter保存并继续，或直接输入max_tokens):{old_max_tokens}\n")
            if not max_tokens:
                max_tokens = old_max_tokens
        try:
            max_tokens = int(max_tokens)
            break
        except ValueError:
            logger.error(f"无效输入...请输入有效数字({attempts+1}/4)")
            attempts+=1
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    return max_tokens

def input_temperature(api_name,config_data,template_data):
    old_temperature = config_data['api'][api_name]['temperature']
    default_temperature = template_data['api'][api_name]['temperature'] 
    attempts = 0
    while attempts<5:
        if old_temperature == default_temperature:
            temperature = input(f"请输入您的 {api_name} temperature（默认{default_temperature}）,按回车Enter保存并继续: ").strip()
            if not temperature:
                temperature = default_temperature
        else:
            temperature = input(f"已保存的{api_name} temperture(回车Enter保存并继续，或直接输入自定义temperature):{old_temperature}\n")
            if not temperature:
                temperature = old_temperature
        try:
            temperature = float(temperature)
            break
        except ValueError:
            logger.error(f"无效输入...请输入有效数字({attempts+1}/4)")
            attempts+=1
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    return temperature

def input_top_p(api_name,config_data,template_data):
    old_top_p = config_data['api'][api_name]['top_p']  
    default_top_p = template_data['api'][api_name]['top_p'] 
    attempts = 0
    while attempts<5:
        if old_top_p == default_top_p:
            top_p = input(f"请输入您的 {api_name} top_p（默认{default_top_p}），回车Enter保存并继续: ").strip()
            if not top_p:
                top_p = default_top_p
        else:
            top_p = input(f"已保存的{api_name} top_p(回车Enter保存并继续，或直接输入自定义top_p):{old_top_p}\n")
            if not top_p:
                top_p = old_top_p
        try:
            top_p = float(top_p)
            break
        except ValueError:
            logger.error(f"无效输入...请输入有效数字({attempts+1}/4)")
            attempts+=1
    else:
        logger.error("✗... 超过最大重试次数，请检查输入并重新运行程序")
        return False
    return top_p

def create_directories():
    """创建必要的目录结构"""
    directories = [
        "results",
        "cache"
    ]
    for directory in directories:
        (SCRIPT_DIR / directory).mkdir(exist_ok=True)
        logger.info(f"✓... 确保目录存在: {directory}")

def check_environment():
    """检查运行环境"""
    print("=== 环境检查 ===")
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    logger.info(f"Python路径: {sys.executable}")
    logger.info(f"脚本目录: {SCRIPT_DIR}")
    return True

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
            print(f"✓... 找到可用的中文字体: {', '.join(available_fonts)}")
        return bool(available_fonts)
    except Exception as e:
        print(f"警告: 检查中文字体时出错: {e}")
        return False

def test_environment():
    """测试环境配置"""
    try:
        logger.info("=== 环境测试 ===\n")
        # 测试必要的Python包
        logger.info("测试Python包导入...")
        required_packages = [
            'pandas', 'numpy', 'scipy', 'matplotlib', 
            'networkx', 'nltk', 'yaml', 'Bio', 'wordcloud', 
            'tqdm', 'seaborn'
        ]
        Failed_pkgs = []
        for pkg in required_packages:
            try:
                __import__(pkg)
                logger.info(f"✓... {pkg} 导入成功")
            except ImportError:
                logger.error(f"✗... {pkg} 导入失败，缺少该包！")
                # 选择是否自动安装缺失的包
                install_pkg = input(f"是否尝试重新安装 {pkg}? (y/n): ").strip().lower()
                attempts = 0
                while attempts <5:
                    if install_pkg == 'y':
                        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                        logger.info(f"✓... {pkg} 安装成功")
                        break
                    elif install_pkg == 'n':
                        logger.error(f"{pkg} 安装跳过，请手动检查")
                        Failed_pkgs.append(pkg)
                        break
                    else:
                        logger.error(f'无效输入，请输入 y 或 n ！（{attempts+1}/4）')
                        attempts +=1
                else:
                    logger.error("无效输入...请重新输入正确的数字或字母")
        if Failed_pkgs:
            raise ImportError(Failed_pkgs)

        # 测试NLTK数据
        logger.info("\n下载并验证NLTK数据...")
        required_nltk_data = ['punkt', 'stopwords', 'averaged_perceptron_tagger']
        for data in required_nltk_data:
            try:
                nltk.data.find(f'tokenizers/{data}')
            except LookupError:
                logger.warning(f"下载NLTK数据: {data}...")
                nltk.download(data, quiet=True)
        logger.info("✓... NLTK数据验证完成")

        # 验证Bio库功能
        logger.info("\n验证Bio库功能...")
        if not hasattr(Bio, '__version__'):
            raise ImportError("Bio库安装不完整")
        logger.info(f"✓... Bio库版本: {Bio.__version__}")

        # 检查中文字体
        logger.info("\n检查中文字体配置...")
        check_chinese_font()

        # 测试matplotlib后端
        logger.info("\n验证matplotlib配置...")
        plt.figure()
        plt.close()
        logger.info("✓... Matplotlib配置正常")
        logger.info("\n✓... 环境测试全部通过！")
        return True
    except ImportError as e:
        if isinstance(e,list):
            for pkg in e:
                logger.warning(f"\n✗... 缺少必要的Python包: {e}")
        else:
            logger.warning(f"\n✗... 缺少必要的Python包: {e}")
        logger.info("请手动运行 'pip install -r requirements.txt' 安装所有依赖")
        return False
    except Exception as e:
        logger.warning(f"\n✗... 环境测试失败: {e}")
        return False

def main():
    print("=== 开始配置PubMed文献分析系统 ===\n")
    
    # 切换到脚本所在目录
    os.chdir(SCRIPT_DIR)

    # 初始化日志配置
    setup_logging()

    # 检查Python版本
    check_python_version()
    
    # 创建必要的目录
    create_directories()

    # 检查项目目录
    if not check_project_directory():
        logger.error("环境检查失败，请确保项目目录完整后重试！")
        return False

    # 检查环境
    if not check_environment():
        return False   

    # 安装依赖
    if not install_dependencies():
        return False
    
    # 设置配置文件
    if not setup_config():
        return False
    
    # 测试环境配置
    if test_environment():
        logger.info("=== 配置完成 ===")
        logger.info(" 您现在可以运行 'python main.py' 来启动系统")
    else:
        logger.error("=== 配置未完全成功,请检查日志===")

if __name__ == "__main__":
    main()