from DeepSeek import get_mesh_query
from pubmed_scraper import PubMedScraper
from literature_analysis import analyze_literature_from_csv
import time
import os
import json
import pandas as pd
from advanced_analysis import AdvancedLiteratureAnalysis
import re
import yaml

def preprocess_query(mesh_query):
    """预处理检索式
    
    Args:
        mesh_query (str): 原始MeSH检索式
        
    Returns:
        str: 处理后的检索式
    """
    # 修常见格式错误
    query = mesh_query.replace('"[', '[').replace(']"', ']')  # 修正引号位置
    query = query.replace('"[Majr] OR"', '[Majr] OR')  # 修正错误拼接
    query = re.sub(r'([\[\(])\s*"', r'\1"', query)  # 修正括号内空格
    query = re.sub(r'\s{2,}', ' ', query)  # 移除多余空格
    return query

def ensure_results_dir(research_area):
    # 创建results目录（如果不存在）
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # 为研究领域创建子目录
    safe_dir_name = ''.join(c for c in research_area if c.isalnum() or c.isspace())
    safe_dir_name = safe_dir_name.strip().replace(' ', '_')
    result_dir = os.path.join(base_dir, safe_dir_name)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    return result_dir

def perform_literature_search()::
    # 从配置文件读取邮箱
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    email = config['pubmed']['email']
    scraper = PubMedScraper(email)

    # 选择搜索方式
    print("\n请选择搜索方式:")
    print("1. 直接输入关键词检索")
    print("2. 使用AI辅助生成MeSH检索式进行专业检索")
    search_mode = input("请选择 (1-2): ").strip()

    # 获取用户感兴趣的研究领域
    print("\n请输入您感兴趣的研究领域: ")
    research_area = input().strip()

    if search_mode == '1':
        # 直接使用用户输入的关键词
        mesh_query = research_area
    else:
        # 选择检索策略
        print("\n请选择检索策略:")
        print("1. 精准检索 - 使用更严格的MeSH主题词，可能获得较少但更相关的结果")
        print("2. 宽泛检索 - 使用更广泛的MeSH主题词，可能获得更多但相关性较低的结果")
        search_strategy = input("请选择 (1-2): ").strip()
        
        # 使用DeepSeek AI转换为MeSH检索式
        print("\n正在生成MeSH检索式...")
        broad_search = search_strategy == '2'
        mesh_query = get_mesh_query(research_area, broad_search=broad_search)
        if not mesh_query:
            print("生成MeSH检索式失败，程序退出")
            return None, None

        # 预处理检索式
        mesh_query = preprocess_query(mesh_query)
        # 移除外层引号并添加必要的布尔运算符
        mesh_query = mesh_query.strip('"')
        if '[Majr]' in mesh_query:
            mesh_query = f'({mesh_query})'
        print(f"生成的MeSH检索式: {mesh_query}")

    # 获取最大文献数量
    max_results = int(input("\n请输入需要获取的最大文献数量: "))

    # 获取筛选条件
    filters = scraper.get_filter_options()
    
    # 构建完整查询语句
    full_query = scraper.build_query(mesh_query, filters)

    # 搜索文献
    print("\n开始搜索文献...")
    id_list = scraper.search_pubmed(full_query, max_results)

    if not id_list and search_mode == '2':
        print("\n未找到相关文献，是否尝试使用更宽泛的检索策略？(y/n): ")
        retry_with_broad_search = input().strip().lower()
        
        if retry_with_broad_search == 'y':
            print("\n使用宽泛检索策略重新生成MeSH检索式...")
            mesh_query = get_mesh_query(research_area, broad_search=True)
            if not mesh_query:
                print("生成MeSH检索式失败，程序退出")
                return None, None
            
            # 移除外层引号并添加必要的布尔运算符
            mesh_query = mesh_query.strip('"')
            if '[Majr]' in mesh_query:
                mesh_query = f'({mesh_query})'
            
            # 重新构建查询语句并搜索
            full_query = scraper.build_query(mesh_query, filters)
            print("\n开始使用宽泛检索策略搜索文献...")
            id_list = scraper.search_pubmed(full_query, max_results)
            
            if not id_list:
                print("使用宽泛检索策略仍未找到相关文献")
                return None, None
        else:
            print("已取消使用宽泛检索策略")
            return None, None
    elif not id_list:
        print("未找到相关文献")
        return None, None

    print(f"找到 {len(id_list)} 篇文献")

    # 获取详细信息
    articles = scraper.fetch_details(id_list)

    # 导出结果
    if articles:
        # 确保结果目录存在
        result_dir = ensure_results_dir(research_area)
        
        # 生成输出文件名
        safe_query = ''.join(c for c in research_area if c.isalnum() or c.isspace())
        output_file = os.path.join(result_dir, f"pubmed_results_{safe_query.strip().replace(' ', '_')}_{time.strftime('%Y%m%d')}.csv")
        
        # 导出CSV文件
        scraper.export_to_csv(articles, output_file, research_area)
        
        # 询问是否下载PDF
        if input("\n是否需要尝试获取文献PDF全文？(y/n):（由于优雅性，建议尽量先手动输入doi查找）（需校园网或开代理） ").lower() == 'y':
            # 显示文献列表供用户选择
            print("\n已检索到的文献列表：")
            df = pd.read_csv(output_file)
            for idx, row in df.iterrows():
                print(f"[{idx+1}] PMID: {row['pmid']}")
                print(f"    标题: {row['title']}")
                print()
            
            # 获取用户选择
            print("\n请输入要下载的文献编号（多个编号用逗号分隔，输入'all'下载全部）: ")
            selection = input().strip().lower()
            
            selected_articles = []
            if selection == 'all':
                selected_articles = articles
            else:
                try:
                    # 解析用户输入的编号
                    indices = [int(i.strip())-1 for i in selection.split(',')]
                    # 获取选中的文献
                    selected_articles = [articles[i] for i in indices if 0 <= i < len(articles)]
                except:
                    print("输入格式错误，取消下载")
                    return output_file, research_area
            
            if selected_articles:
                print(f"\n开始下载选中的 {len(selected_articles)} 篇文献...")
                scraper.batch_download(selected_articles, result_dir)
            else:
                print("未选择任何文献进行下载")
            
        return output_file, research_area
    
    return None, None

def perform_literature_analysis(csv_file=None):
    if not csv_file:
        print("\n请输入要分析的CSV文件路径: ")
        csv_file = input().strip()
    
    if not os.path.exists(csv_file):
        print(f"\n错误：文件 {csv_file} 不存在")
        return
    
    print("\n开始生成文献解读报告...")
    analyze_literature_from_csv(csv_file)

def perform_literature_comparison(csv_file=None):
    if not csv_file:
        print("\n请输入要分析的CSV文件路径: ")
        csv_file = input().strip()
    
    if not os.path.exists(csv_file):
        print(f"\n错误：文件 {csv_file} 不存在")
        return
    
    print("\n开始进行文献对比分析...")
    analyzer = AdvancedLiteratureAnalysis()
    analyzer.analyze_from_csv(csv_file)

def main():
    while True:
        print("\n=== PubMed文献分析系统 ===")
        print("1. 文献查询")
        print("2. 文献解读")
        print("3. 文献对比分析")
        print("4. 退出")
        print("\n请选择功能 (1-4): ")
        
        choice = input().strip()
        
        if choice == '1':
            # 执行文献查询
            csv_file, research_area = perform_literature_search()
            if csv_file:
                # 询问是否需要进行后续分析
                print("\n是否需要生成文献解读报告？(y/n): ")
                if input().strip().lower() == 'y':
                    perform_literature_analysis(csv_file)
                
                print("\n是否需要进行文献对比分析？(y/n): ")
                if input().strip().lower() == 'y':
                    perform_literature_comparison(csv_file)
        
        elif choice == '2':
            # 直接执行文献解读
            perform_literature_analysis()
        
        elif choice == '3':
            # 直接执行文献对比分析
            perform_literature_comparison()
        
        elif choice == '4':
            print("\n感谢使用！再见！")
            break
        
        else:
            print("\n无效的选择，请重新输入")
    
    # 在完成基本数据抓取后，添加PDF下载功能
    # if input("是否需要尝试获取文献PDF全文？(y/n): ").lower() == 'y':
    #     email = input("请输入您的邮箱地址（用于PubMed API）: ")
    #     scraper = PubMedScraper(email=email)
    #     print("\n开始暴力下载PDF全文...")
    #     scraper.batch_download(articles, result_dir)

if __name__ == "__main__":
    main()
