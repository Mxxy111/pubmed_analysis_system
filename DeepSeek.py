import requests
import json
import yaml
import re
from pathlib import Path

def load_config():
    """加载配置文件

    Returns:
        dict: 配置信息
    """
    try:
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}")
        return None

def get_mesh_query(research_area, broad_search=False, retry_count=0):
    """使用AI将研究领域转换为MeSH检索式

    Args:
        research_area (str): 用户输入的研究领域
        broad_search (bool): 是否使用宽泛的检索策略
        retry_count (int): 重试次数

    Returns:
        str: 生成的MeSH检索式
    """
    # 限制最大重试次数
    if retry_count >= 3:
        print("已达到最大重试次数，请尝试修改研究领域描述")
        return None

    # 初始化PubMed爬虫用于验证MeSH术语
    from pubmed_scraper import PubMedScraper
    scraper = PubMedScraper("22301050067@m.fudan.edu.cn")
    try:
        # 加载配置
        config = load_config()
        if not config:
            print("无法加载配置文件，请确保config.yaml文件存在且格式正确")
            return None

        # 获取MeSH查询专用的API配置
        mesh_query_model = config['api']['mesh_query_model']
        api_config = config['api'][mesh_query_model]
        
        # 根据搜索策略调整系统提示
        strategy_desc = "使用更宽泛策略，包含相关MeSH术语" if broad_search else "使用精确策略，侧重[Majr]标签"
        print(f"\n当前使用的搜索策略: {strategy_desc}")

        system_prompt = """你是一个专业的PubMed检索专家。请将输入的研究领域直接转换为标准的MeSH检索式。只需要输出检索式本身，不要包含任何解释、标记或其他内容。请严格按照以下规则处理：

1. **语法格式**：
   - 必须为每个术语使用完整引号包裹后附加字段标签：即 \"Term\"[字段]
   - 切勿嵌套引号或拆分格式：错误示例 \"Carcinoma, Hepatocellular[Majr]（漏闭合引号）
   - 布尔运算符(AND/OR/NOT)和括号外必须保留空格

2. **字段优先级**（根据用户选择）：
   - 精确策略：[MAJR]标签使用频次要 >30%
   - 宽泛策略：优先使用[Mesh]标签

3. **排除规则**：自动追加非研究文献过滤
   - 必须包含：NOT (\"Case Reports\"[PT] OR \"Comment\"[PT] OR \"Editorial\"[PT])

4. **校验功能**：生成时会自动执行以下验证：
   - 每个\"[字段]前必有闭合引号 \"
   - 字段标签只能是[MAJR]/[Mesh]/[PT]等PubMed允许字段
   - 布尔运算符必须全大写且被空格包裹"""

        payload = {
            "model": api_config['model'],
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"请为【{research_area}】生成PubMed检索式，要求：\n{strategy_desc}\n排除病例报告等非研究文献：NOT (\"Case Reports\"[Publication Type])"
                }
            ],
            "stream": False,
            "max_tokens": api_config['max_tokens'],
            "temperature": api_config['temperature'],
            "top_p": api_config['top_p']
        }

        headers = {
            "Authorization": f"Bearer {api_config['api_key']}",
            "Content-Type": "application/json"
        }

        response = requests.post(api_config['endpoint'], json=payload, headers=headers)
        if response.status_code != 200:
            print(f"API请求失败，状态码: {response.status_code}")
            return None

        try:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content'].strip()
                if content:
                    print(f"API响应内容：{content}")
                    # 移除外层引号并修复引号问题
                    content = content.strip('"')
                    # 应用后处理逻辑
                    content = fix_quotes_closing(content)
                    content = validate_field_tags(content)
                    content = normalize_operators(content)
                    
                    # 进行语法校验
                    errors = validate_query_syntax(content)
                    if errors:
                        print(f"语法错误: {errors}")
                        return get_mesh_query(research_area, broad_search=True, retry_count=retry_count + 1)
                    
                    # 验证MeSH术语
                    # 预处理检索式，移除布尔运算符和括号，但保留引号内的内容
                    terms = []
                    current_term = ''
                    in_quotes = False
                    i = 0
                    while i < len(content):
                        char = content[i]
                        if char == '"':
                            in_quotes = not in_quotes
                            if not in_quotes and current_term:
                                # 提取字段标签
                                field_match = re.search(r'\[(MAJR|Mesh|PT)\]$', current_term)
                                if field_match:
                                    # 移除字段标签，只保留术语本身
                                    term = current_term[:field_match.start()].strip()
                                    terms.append(term)
                                current_term = ''
                        elif in_quotes:
                            current_term += char
                        i += 1
                    
                    # 验证每个MeSH术语
                    invalid_terms = []
                    for term in terms:
                        if term and not scraper.validate_mesh_term(term):
                            invalid_terms.append(term)
                    
                    if invalid_terms:
                        print(f"\n警告：以下MeSH术语可能无效：{', '.join(invalid_terms)}")
                        print("正在尝试使用更宽泛的检索策略...")
                        return get_mesh_query(research_area, broad_search=True, retry_count=retry_count + 1)
                                    
                    if '[Majr]' in content:
                        content = f'({content})'
                    return content
                print("API返回了空的检索式")
                return None
            print("API响应格式不正确")
            return None
        except json.JSONDecodeError as e:
            print(f"解析API响应失败：{str(e)}")
            return None
    except Exception as e:
        print(f"Error generating MeSH query: {str(e)}")
        return None

if __name__ == "__main__":
    # 测试函数
    research_area = input("请输入您感兴趣的研究领域: ")
    # 添加搜索策略选择
    while True:
        strategy = input("\n请选择搜索策略 (1: 精准搜索 2: 宽泛搜索): ")
        if strategy in ['1', '2']:
            break
        print("\n无效的选择，请重新输入")
    
    broad_search = strategy == '2'
    mesh_query = get_mesh_query(research_area, broad_search=broad_search)
    if mesh_query:
        print(f"\n生成的MeSH检索式: {mesh_query}")

def fix_quotes_closing(query):
    """更精准的引号闭合修复"""
    # 匹配格式为 "Term[MAJR] 的错误结构
    pattern = re.compile(r'"([^"]+)\[([A-Za-z]+)\](?!")')
    # 使用 \1 \2 正确引用捕获组
    return pattern.sub(r'"\1"[\2]', query)

def validate_field_tags(query):
    """强制字段标签在引号外侧"""
    # 更新正则表达式以更准确地匹配字段标签
    pattern = re.compile(r'"([^"]+)"\s*\[(MAJR|Mesh|PT)\]')
    return pattern.sub(r'"\1"[\2]', query)  # 保持字段标签格式

def validate_query_syntax(query):
    """校验查询式核心语法，返回错误列表"""
    errors = []
    
    # 校验引号闭合
    if query.count('"') % 2 != 0:
        errors.append("检测到未闭合的引号")
    
    # 修正后的字段标签验证
    field_tag_violations = re.findall(r'"([^"]+)"\[(MAJR|Mesh|PT)\]', query)
    if not field_tag_violations:
        errors.append("未找到有效的字段标签")
    elif not all(tag in ['MAJR', 'Mesh', 'PT'] for _, tag in field_tag_violations):
        errors.append("存在无效字段标签，允许的标签为 [MAJR]/[Mesh]/[PT]")
    
    # 核心修正：匹配小写或混合大小写的布尔运算符
    lower_ops = re.findall(r'\b(and|or|not)\b', query, flags=re.IGNORECASE)
    # 过滤出实际包含小写字符的运算符
    invalid_ops = [op for op in lower_ops if op != op.upper()]
    if invalid_ops:
        errors.append(f"布尔运算符必须全大写，但发现: {', '.join(invalid_ops)}")
    
    return errors

def normalize_operators(query):
    """确保运算符大写且被空格包裹"""
    # 先处理布尔运算符，确保大写并添加空格
    query = re.sub(r'\s*(and|or|not)\s*', lambda m: f' {m.group(1).upper()} ', query, flags=re.IGNORECASE)
    # 修复括号周围的空格
    query = re.sub(r'\s*\(\s*', ' (', query)
    query = re.sub(r'\s*\)\s*', ') ', query)
    # 修复多余的空格
    query = re.sub(r'\s+', ' ', query).strip()
    return query