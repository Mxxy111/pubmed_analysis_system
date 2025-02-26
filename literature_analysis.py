import pandas as pd
import json
import requests
import os
import yaml
from typing import Dict, List
from datetime import datetime
import time

def generate_literature_analysis(literature_info: Dict, retries: int = 3) -> str:
    """使用DeepSeek AI生成文献解读报告

    Args:
        literature_info (Dict): 包含文献信息的字典
        retries (int): 尝试重试次数

    Returns:
        str: 生成的文献解读报告，如果超过重试限制则返回None
    """
    try:
        # 读取配置文件
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 获取API配置
        api_config = config['api']['volces']
        url = api_config['endpoint']

        prompt = f"""请对以下医学文献进行专业的解读分析，生成一份详细的报告。

文献信息：
标题：{literature_info['title']}
摘要：{literature_info['abstract']}
结论：{literature_info.get('conclusion', '')}
作者：{literature_info['authors']}
期刊：{literature_info['journal']}
发表日期：{literature_info['publication_date']}
关键词：{literature_info['keywords']}

请从以下几个方面进行分析：
1. 研究背景和意义
2. 研究方法评述
3. 主要founded发现
4. 创新点和局限性
5. 临床应用价值
6. 对未来研究的启示

要求：
1. 分析要专业、客观、全面
2. 重点突出研究的创新性和临床价值
3. 指出研究的优势和不足
4. 使用专业的学术语言"""

        payload = {
            "model": api_config['model'],
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位经验丰富的医学文献评论专家，擅长对医学研究论文进行深入解读和分析。"
                },
                {
                    "role": "user",
                    "content": prompt
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

        attempt = 0
        while attempt < retries:
            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()  # 抛出HTTP错误以便更好地处理
                
                response_data = response.json()
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    result = response_data['choices'][0]['message']['content'].strip()
                    if result:
                        return result
                    else:
                        raise ValueError("生成的分析报告为空")
                else:
                    raise ValueError("API响应中未找到有效的分析结果")
            except Exception as e:
                attempt += 1
                print(f"尝试 {attempt} 次生成解读报告失败: {e}")
                time.sleep(2)  # 等待2秒后重试
            
        print("达到最大重试次数，生成解读报告失败。")
        return None
            
    except requests.exceptions.RequestException as e:
        print(f"API请求错误: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        return None
    except Exception as e:
        print(f"生成文献分析时发生错误: {str(e)}")
        return None

def analyze_literature_from_csv(csv_file):
    # 确保使用完整的文件路径
    try:
        # 如果传入的是相对路径，转换为绝对路径
        if not os.path.isabs(csv_file):
            csv_file = os.path.abspath(csv_file)
            
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f'找不到CSV文件: {csv_file}')
            
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        required_columns = ['title', 'abstract', 'conclusion', 'authors', 'journal', 'publication_date', 'keywords']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"CSV文件缺少必要的列: {', '.join(missing_columns)}")
            
        total_rows = len(df)
        print(f"\n找到 {total_rows} 篇文献")
        
        # 让用户选择要解读的文献数量
        while True:
            try:
                num_to_analyze = int(input("\n请输入要解读的文献数量（输入0则解读全部文献）（十分消耗token，慎选大数字）（每篇耗时约45s）: "))
                if 0 <= num_to_analyze <= total_rows:
                    break
                print(f"请输入0到{total_rows}之间的数字")
            except ValueError:
                print("请输入有效的数字")
        
        # 如果用户选择解读全部文献
        if num_to_analyze == 0:
            num_to_analyze = total_rows
            selected_indices = range(total_rows)
        else:
            # 显示文献列表供用户选择
            print("\n可选择的文献列表:")
            for i, row in df.iterrows():
                print(f"[{i+1}] {row['title']}")
            
            # 让用户选择具体文献
            selected_indices = []
            while len(selected_indices) < num_to_analyze:
                try:
                    selection = int(input(f"\n请输入第{len(selected_indices)+1}篇要解读的文献编号（1-{total_rows}）: "))
                    if 1 <= selection <= total_rows:
                        if selection-1 not in selected_indices:
                            selected_indices.append(selection-1)
                        else:
                            print("该文献已被选择，请选择其他文献")
                    else:
                        print(f"请输入1到{total_rows}之间的数字")
                except ValueError:
                    print("请输入有效的数字")
        
        analyses = []
        # 仅处理选中的文献
        for i, index in enumerate(selected_indices):
            row = df.iloc[index]
            print(f"\n正在处理第 {i + 1}/{num_to_analyze} 篇文献...")
            print(f"标题: {row['title']}")
            
            literature_info = {
                'title': row['title'],
                'abstract': row['abstract'],
                'conclusion': row['conclusion'],
                'authors': row['authors'],
                'journal': row['journal'],
                'publication_date': row['publication_date'],
                'keywords': row['keywords']
            }

            # 生成解读报告
            analysis = generate_literature_analysis(literature_info)
            if analysis:
                analyses.append({
                    'literature_info': literature_info,
                    'analysis_report': analysis
                })
            else:
                print(f"警告: 该文献的分析报告生成失败")

        return analyses
        
    except pd.errors.EmptyDataError:
        print("错误: CSV文件为空")
        return []
    except Exception as e:
        print(f"处理CSV文件时发生错误: {str(e)}")
        return []

def save_analysis_results(analyses: List[Dict], csv_file: str) -> str:
    """保存分析结果到JSON文件

    Args:
        analyses (List[Dict]): 分析结果列表
        csv_file (str): 原始CSV文件路径

    Returns:
        str: 输出文件路径
    """
    try:
        if not analyses:
            raise ValueError("没有可保存的分析结果")

        # 生成输出文件路径，使用CSV文件所在目录下的analysis_results子目录
        csv_dir = os.path.dirname(csv_file)
        analysis_dir = os.path.join(csv_dir, "analysis_results")
        os.makedirs(analysis_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{os.path.splitext(os.path.basename(csv_file))[0]}_analysis_{timestamp}.json"
        output_file = os.path.join(analysis_dir, output_filename)

        # 保存分析结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)

        print(f"分析结果成功保存至: {output_file}")
        return output_file

    except Exception as e:
        print(f"保存分析结果时发生错误: {str(e)}")
        return None

def convert_analysis_format(json_file: str, output_format: str = 'json') -> str:
    """将JSON格式的文献分析结果转换为指定格式

    Args:
        json_file (str): JSON文件路径
        output_format (str): 输出格式，可选 'json'、'md'、'txt'、'csv'

    Returns:
        str: 输出文件路径
    """
    try:
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            analyses = json.load(f)

        if not analyses:
            raise ValueError("JSON文件中没有分析结果")

        # 生成输出文件路径
        output_dir = os.path.dirname(json_file)
        base_name = os.path.splitext(os.path.basename(json_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}.{output_format}")

        if output_format == 'json':
            # 直接复制JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analyses, f, ensure_ascii=False, indent=2)

        elif output_format == 'md':
            # 生成Markdown格式报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 文献分析报告\n\n")
                for i, analysis in enumerate(analyses, 1):
                    info = analysis['literature_info']
                    f.write(f"## {i}. {info['title']}\n\n")
                    f.write(f"**作者**: {info['authors']}\n\n")
                    f.write(f"**期刊**: {info['journal']}\n\n")
                    f.write(f"**发表日期**: {info['publication_date']}\n\n")
                    f.write(f"**关键词**: {info['keywords']}\n\n")
                    f.write("### 摘要\n\n")
                    f.write(f"{info['abstract']}\n\n")
                    f.write("### 分析报告\n\n")
                    f.write(f"{analysis['analysis_report']}\n\n")
                    f.write("---\n\n")

        elif output_format == 'txt':
            # 生成纯文本格式报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("文献分析报告\n\n")
                for i, analysis in enumerate(analyses, 1):
                    info = analysis['literature_info']
                    f.write(f"{i}. {info['title']}\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"作者: {info['authors']}\n")
                    f.write(f"期刊: {info['journal']}\n")
                    f.write(f"发表日期: {info['publication_date']}\n")
                    f.write(f"关键词: {info['keywords']}\n\n")
                    f.write("摘要:\n")
                    f.write(f"{info['abstract']}\n\n")
                    f.write("分析报告:\n")
                    f.write(f"{analysis['analysis_report']}\n\n")
                    f.write("-" * 80 + "\n\n")

        elif output_format == 'csv':
            # 生成CSV格式报告
            df_rows = []
            for analysis in analyses:
                info = analysis['literature_info']
                df_rows.append({
                    '标题': info['title'],
                    '作者': info['authors'],
                    '期刊': info['journal'],
                    '发表日期': info['publication_date'],
                    '关键词': info['keywords'],
                    '摘要': info['abstract'],
                    '分析报告': analysis['analysis_report']
                })
            pd.DataFrame(df_rows).to_csv(output_file, index=False, encoding='utf-8-sig')

        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

        return output_file

    except Exception as e:
        print(f"转换格式时发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    print("请使用main.py运行完整的文献分析程序")
    # 测试函数
    csv_file = input("请输入文献CSV文件路径: ")
    analyses = analyze_literature_from_csv(csv_file)
    
    if analyses:
        # 保存JSON格式结果
        json_file = save_analysis_results(analyses, csv_file)
        if json_file:
            print(f"\nJSON格式的分析报告已保存至: {json_file}")
            
            # 自动生成Markdown格式报告
            md_file = convert_analysis_format(json_file, 'md')
            if md_file:
                print(f"\nMarkdown格式的分析报告已保存至: {md_file}")
            
            # 让用户选择其他输出格式
            print("\n可选的其他输出格式: txt, csv")
            output_format = input("请选择其他输出格式 (直接回车跳过): ").lower()
            
            if output_format in ['txt', 'csv']:
                # 转换为选定格式
                output_file = convert_analysis_format(json_file, output_format)
                if output_file:
                    print(f"\n{output_format.upper()}格式的分析报告已保存至: {output_file}")
                else:
                    print("\n格式转换失败")
        else:
            print("\n保存分析结果失败")
    else:
        print("\n没有生成任何分析结果")
