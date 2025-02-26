import sys
import os
import time
from Bio import Entrez
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from aggressive_downloader import AggressivePDFDownloader

class PubMedScraper(AggressivePDFDownloader):
    def __init__(self, email):
        """初始化PubMed爬虫

        Args:
            email (str): 用于访问NCBI的邮箱地址
        """
        super().__init__()
        Entrez.email = email
        self.results_per_page = 100

    def validate_mesh_term(self, term):
        """验证MeSH术语是否存在

        Args:
            term (str): 要验证的MeSH术语

        Returns:
            bool: 术语是否有效
        """
        try:
            # 移除[Majr]标签进行验证
            clean_term = term.replace('[Majr]', '').strip()
            handle = Entrez.esearch(db="mesh", term=f'"{clean_term}"[MeSH Terms]', retmax=1)
            record = Entrez.read(handle)
            handle.close()
            return int(record['Count']) > 0
        except Exception as e:
            print(f"术语验证失败: {str(e)}")
            return False

    def get_filter_options(self):
        """获取用户的筛选选项

        Returns:
            dict: 筛选条件字典
        """
        filters = {}
        
        print("\n是否需要设置筛选条件？(y/n)")
        print("提示：设置合适的筛选条件可以帮助您更精确地找到所需文献")
        if input().lower() != 'y':
            return filters
        
        # 日期范围筛选
        print("\n是否需要设置日期范围筛选？(y/n)")
        print("提示：PubMed支持精确到天的日期筛选，可以帮助您找到特定时间段发表的文献")
        if input().lower() == 'y':
            while True:
                print("请输入起始日期 (格式：YYYY/MM/DD，例如：2020/01/01，直接回车跳过): ")
                print("说明：日期格式必须是YYYY/MM/DD，年份范围为1800至今")
                start_date = input().strip()
                if not start_date:
                    break
                try:
                    date = datetime.strptime(start_date, '%Y/%m/%d')
                    if 1800 <= date.year <= datetime.now().year:
                        filters['start_date'] = start_date
                        break
                    else:
                        print(f"年份必须在1800至{datetime.now().year}之间！")
                except ValueError:
                    print("日期格式错误！请使用YYYY/MM/DD格式，例如：2020/01/01")
            
            while True:
                print("请输入结束日期 (格式：YYYY/MM/DD，例如：2023/12/31，直接回车跳过): ")
                print("说明：结束日期必须晚于或等于起始日期")
                end_date = input().strip()
                if not end_date:
                    break
                try:
                    date = datetime.strptime(end_date, '%Y/%m/%d')
                    if 'start_date' in filters and end_date < filters['start_date']:
                        print("结束日期不能早于起始日期！")
                        continue
                    if 1800 <= date.year <= datetime.now().year:
                        filters['end_date'] = end_date
                        break
                    else:
                        print(f"年份必须在1800至{datetime.now().year}之间！")
                except ValueError:
                    print("日期格式错误！请使用YYYY/MM/DD格式，例如：2023/12/31")
        
        # 文章类型筛选
        print("\n是否需要设置文章类型筛选？(y/n)")
        print("提示：选择特定类型的文章可以帮助您找到更相关的研究成果")
        if input().lower() == 'y':
            print("请选择文章类型（多个类型用逗号分隔）：")
            print("1. Clinical Trial（临床试验：评估治疗、干预或诊断方法的研究）")
            print("2. Review（综述：对特定主题的现有研究进行总结和评价）")
            print("3. Meta-Analysis（荟萃分析：对多个相关研究结果进行统计分析）")
            print("4. Randomized Controlled Trial（随机对照试验：最高级别的临床研究设计）")
            print("5. Systematic Review（系统综述：系统性地收集和评价相关研究）")
            print("6. Case Reports（病例报告：详细描述单个或少量病例）")
            print("7. Observational Study（观察性研究：观察特定人群的健康结果）")
            types = input().strip()
            if types:
                type_map = {
                    '1': 'Clinical Trial',
                    '2': 'Review',
                    '3': 'Meta-Analysis',
                    '4': 'Randomized Controlled Trial',
                    '5': 'Systematic Review',
                    '6': 'Case Reports',
                    '7': 'Observational Study'
                }
                selected_types = [type_map[t.strip()] for t in types.split(',') if t.strip() in type_map]
                if selected_types:
                    filters['article_types'] = selected_types
        
        # 语言筛选
        print("\n是否需要设置语言筛选？(y/n)")
        print("提示：PubMed收录了多种语言的文献，选择特定语言可以帮助您更好地理解文献内容")
        if input().lower() == 'y':
            print("请选择语言（多个语言用逗号分隔）：")
            print("1. English（英语：最主要的科技文献语言）")
            print("2. Chinese（中文：包括中国大陆、港澳台地区发表的文献）")
            print("3. Japanese（日语：来自日本的研究文献）")
            print("4. German（德语：来自德语国家的研究文献）")
            print("5. French（法语：来自法语国家的研究文献）")
            langs = input().strip()
            if langs:
                lang_map = {
                    '1': 'English',
                    '2': 'Chinese',
                    '3': 'Japanese',
                    '4': 'German',
                    '5': 'French'
                }
                selected_langs = [lang_map[l.strip()] for l in langs.split(',') if l.strip() in lang_map]
                if selected_langs:
                    filters['languages'] = selected_langs
        
        return filters

    def build_query(self, base_query, filters):
        """根据筛选条件构建PubMed查询语句

        Args:
            base_query (str): 基础查询语句
            filters (dict): 筛选条件

        Returns:
            str: 完整的查询语句
        """
        # 移除外层引号
        base_query = base_query.strip('"')
        query_parts = [base_query]
        
        # 日期筛选
        if 'start_date' in filters or 'end_date' in filters:
            start_date = filters.get('start_date', '1900/01/01')
            end_date = filters.get('end_date', datetime.now().strftime('%Y/%m/%d'))
            
            # 添加日期格式验证
            try:
                datetime.strptime(start_date, '%Y/%m/%d')
                datetime.strptime(end_date, '%Y/%m/%d')
            except ValueError:
                raise ValueError("日期格式必须为YYYY/MM/DD")
            
            # 使用PubMed要求的正确格式
            date_query = f'("{start_date}"[Date - Publication] : "{end_date}"[Date - Publication])'
            query_parts.append(date_query)
        
        # 文章类型筛选
        if 'article_types' in filters and filters['article_types']:
            type_parts = [f'"{t}"[Publication Type]' for t in filters['article_types']]
            if len(type_parts) > 1:
                query_parts.append(f'({" OR ".join(type_parts)})')
            else:
                query_parts.append(type_parts[0])
        
        # 语言筛选
        if 'languages' in filters and filters['languages']:
            lang_parts = [f'"{l}"[Language]' for l in filters['languages']]
            if len(lang_parts) > 1:
                query_parts.append(f'({" OR ".join(lang_parts)})')
            else:
                query_parts.append(lang_parts[0])
        
        return ' AND '.join(query_parts)

    def get_search_query(self):
        """获取用户的搜索查询

        Returns:
            str: 搜索查询语句
        """
        print("\n请选择搜索方式：")
        print("1. 直接输入搜索词（简单检索）")
        print("2. 使用AI辅助生成MeSH检索式（专业检索）")
        choice = input("请输入选择（1或2）：").strip()

        if choice == "1":
            print("\n请输入搜索词：")
            return input().strip()
        elif choice == "2":
            from DeepSeek import get_mesh_query
            print("\n请输入研究领域描述：")
            research_area = input().strip()
            mesh_query = get_mesh_query(research_area)
            if not mesh_query:
                print("\nAI生成MeSH检索式失败，请直接输入搜索词：")
                return input().strip()
            return mesh_query
        else:
            print("\n无效选择，请直接输入搜索词：")
            return input().strip()

    def search_pubmed(self, query, max_results=100):
        """搜索PubMed文献

        Args:
            query (str): 搜索关键词
            max_results (int, optional): 最大结果数量. Defaults to 100.

        Returns:
            list: PubMed ID列表
        """
        try:
            # 打印完整的查询语句用于调试
            print(f"\n完整的PubMed查询语句: {query}")
            
            # 执行搜索
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
                usehistory="y",  # 使用历史功能以提高可靠性
                retmode="xml"
            )
            
            # 读取结果
            record = Entrez.read(handle)
            handle.close()
            
            # 打印调试信息
            print("\nPubMed API响应信息:")
            print(f"查询计数: {record.get('Count', '未知')}")
            print(f"查询转换: {record.get('QueryTranslation', '未知')}")
            
            # 检查搜索结果
            if "IdList" in record and record["IdList"]:
                print(f"\n成功找到 {len(record['IdList'])} 篇文献")
                return record["IdList"]
            else:
                print("\n未找到符合条件的文献，请尝试调整搜索条件")
                if "ErrorList" in record:
                    print(f"搜索错误信息: {record['ErrorList']}")
                if "WarningList" in record:
                    print(f"搜索警告信息: {record['WarningList']}")
                return []
                
        except Exception as e:
            print(f"\n搜索过程中出现错误: {str(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return []

    def fetch_details(self, id_list):
        """获取文献详细信息

        Args:
            id_list (list): PubMed ID列表

        Returns:
            list: 文献信息字典列表
        """
        articles = []
        for pmid in tqdm(id_list, desc="获取文献信息"):
            try:
                handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="text")
                record = Entrez.read(handle)["PubmedArticle"][0]["MedlineCitation"]
                handle.close()
    
                article = {'pmid': pmid}
                # 获取标题
                article['title'] = str(record['Article'].get('ArticleTitle', ''))
    
                # 获取摘要和结论
                if 'Abstract' in record['Article'] and 'AbstractText' in record['Article']['Abstract']:
                    abstract_text = record['Article']['Abstract']['AbstractText']
                    if isinstance(abstract_text, list):
                        article['abstract'] = str(abstract_text[0])
                        article['conclusion'] = ''
                        for section in abstract_text:
                            # 针对可能为字典的情况进行判断
                            if isinstance(section, dict) and section.get('Label', '').lower() in ['conclusion', 'conclusions']:
                                article['conclusion'] = str(section.get('#text', ''))
                                break
                            # 如果是对象，则用 hasattr 判断
                            elif hasattr(section, 'attributes') and 'Label' in section.attributes:
                                if section.attributes['Label'].lower() in ['conclusion', 'conclusions']:
                                    article['conclusion'] = str(section)
                                    break
                    else:
                        article['abstract'] = str(abstract_text)
                        article['conclusion'] = ''
                else:
                    article['abstract'] = ''
                    article['conclusion'] = ''
    
                # 获取作者
                if 'AuthorList' in record['Article']:
                    authors = []
                    for author in record['Article']['AuthorList']:
                        last_name = str(author.get('LastName', ''))
                        fore_name = str(author.get('ForeName', ''))
                        authors.append(f"{last_name} {fore_name}".strip())
                    article['authors'] = '; '.join(authors)
                else:
                    article['authors'] = ''
    
                # 获取期刊名
                article['journal'] = str(record['Article'].get('Journal', {}).get('Title', ''))
    
                # 获取出版日期（年月）
                if 'Journal' in record['Article'] and 'JournalIssue' in record['Article']['Journal'] and \
                   'PubDate' in record['Article']['Journal']['JournalIssue']:
                    pub_date = record['Article']['Journal']['JournalIssue']['PubDate']
                    year = str(pub_date.get('Year', ''))
                    month = str(pub_date.get('Month', ''))
                    if year:
                        if month:
                            try:
                                if month.isdigit():
                                    month_num = int(month)
                                else:
                                    try:
                                        # 先尝试缩写格式
                                        month_num = datetime.strptime(month, '%b').month
                                    except ValueError:
                                        month_num = datetime.strptime(month, '%B').month
                                article['publication_date'] = f"{year}/{month_num:02d}"
                            except ValueError:
                                article['publication_date'] = f"{year}"
                        else:
                            article['publication_date'] = f"{year}"
                    else:
                        article['publication_date'] = ''
                else:
                    article['publication_date'] = ''
    
                # 获取文章类型
                if 'PublicationTypeList' in record['Article']:
                    pub_types = [str(pt) for pt in record['Article']['PublicationTypeList']]
                    article['article_type'] = '; '.join(pub_types)
                else:
                    article['article_type'] = ''
    
                # 获取期刊影响因子（IF）
                try:
                    if article['journal']:
                        journal_if_map = {
                            'Nature': '49.962',
                            'Science': '47.728',
                            'Cell': '41.582',
                            'The Lancet': '202.731',
                            'The New England Journal of Medicine': '91.245'
                        }
                        article['impact_factor'] = journal_if_map.get(article['journal'], '')
                    else:
                        article['impact_factor'] = ''
                except Exception as e:
                    print(f"获取影响因子出错: {str(e)}")
                    article['impact_factor'] = ''
    
                # 获取DOI
                article['doi'] = ''
                if 'ELocationID' in record['Article']:
                    # ELocationID 可能为字典或列表
                    elocation = record['Article']['ELocationID']
                    if not isinstance(elocation, list):
                        elocation = [elocation]
                    for id_info in elocation:
                        # 针对字典格式处理
                        if isinstance(id_info, dict):
                            if id_info.get('@EIdType') == 'doi':
                                article['doi'] = id_info.get('#text', '')
                                break
                        # 如果是对象（例如Biopython内部的对象），则用 attributes 判断
                        elif hasattr(id_info, 'attributes') and 'EIdType' in id_info.attributes:
                            if id_info.attributes['EIdType'] == 'doi':
                                article['doi'] = str(id_info)
                                break
    
                # 获取MeSH主题词
                if 'MeshHeadingList' in record:
                    mesh_terms = []
                    for mesh in record['MeshHeadingList']:
                        # 针对字典格式
                        if isinstance(mesh, dict):
                            mesh_terms.append(str(mesh.get('DescriptorName', '')))
                        else:
                            mesh_terms.append(str(mesh))
                    article['keywords'] = '; '.join(mesh_terms)
                else:
                    article['keywords'] = ''
    
                articles.append(article)
                time.sleep(0.5)  # 避免请求过于频繁
            except Exception as e:
                print(f"处理PMID {pmid}时出错: {str(e)}")
                # 可以选择记录错误或继续处理下一篇
                continue
        return articles

    def export_to_csv(self, articles, output_file, query):
        """将结果导出为CSV文件

        Args:
            articles (list): 文献信息字典列表
            output_file (str): 输出文件名
            query (str): 搜索关键词
        """
        try:
            # 创建results目录（如果不存在）
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
            os.makedirs(results_dir, exist_ok=True)
            
            # 根据查询关键词创建子文件夹
            safe_query_folder = ''.join(c for c in query if c.isalnum() or c.isspace()).strip().replace(' ', '_')
            query_dir = os.path.join(results_dir, safe_query_folder)
            os.makedirs(query_dir, exist_ok=True)
            
            # 构建完整的输出文件路径
            full_output_path = os.path.join(query_dir, output_file)
            
            # 创建新的DataFrame
            new_df = pd.DataFrame(articles)
            
            # 如果目标文件已存在，读取并合并数据
            if os.path.exists(full_output_path):
                try:
                    existing_df = pd.read_csv(full_output_path, encoding='utf-8-sig')
                    # 合并数据框并去重
                    merged_df = pd.concat([existing_df, new_df], ignore_index=True)
                    merged_df = merged_df.drop_duplicates(subset=['pmid'], keep='first')
                    df = merged_df
                except Exception as e:
                    print(f"读取现有文件时出错: {str(e)}")
                    df = new_df
            else:
                df = new_df
            
            # 格式化日期列
            if 'publication_date' in df.columns:
                def format_date(date_str):
                    if not date_str:
                        return ''
                    try:
                        if '/' in date_str:
                            year, month = date_str.split('/')
                            if month.isdigit():
                                return f"{year}/{int(month):02d}"
                        return date_str
                    except:
                        return date_str
                
                df['publication_date'] = df['publication_date'].apply(format_date)
            
            # 规范化作者列表格式
            if 'authors' in df.columns:
                df['authors'] = df['authors'].str.strip().str.replace('\s+', ' ')
            
            # 清理和规范化其他列
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip()
            
            # 保存到指定的子文件夹中
            df.to_csv(full_output_path, 
                      index=False, 
                      encoding='utf-8-sig',
                      quoting=1,
                      quotechar='"',
                      escapechar='\\')
            
            print(f"结果已保存到: {full_output_path}")
            print(f"总共保存了 {len(df)} 条记录，其中新增 {len(new_df)} 条记录")
            
        except Exception as e:
            print(f"导出CSV文件出错: {str(e)}")
            print("建议：\n1. 确保目标文件未被其他程序打开\n2. 检查文件夹的写入权限\n3. 尝试指定其他位置保存文件")

def main():
    # 从配置文件读取邮箱
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    email = config['pubmed']['email']
    scraper = PubMedScraper(email)

    # 设置搜索参数
    query = input("请输入搜索关键词: ")
    max_results = int(input("请输入需要获取的最大文献数量: "))

    # 获取筛选条件
    filters = scraper.get_filter_options()
    
    # 构建完整查询语句
    full_query = scraper.build_query(query, filters)

    # 搜索文献
    print("\n开始搜索文献...")
    id_list = scraper.search_pubmed(full_query, max_results)

    if not id_list:
        print("未找到相关文献")
        return

    print(f"找到 {len(id_list)} 篇文献")

    # 获取详细信息
    articles = scraper.fetch_details(id_list)

    # 导出结果
    if articles:
        # 生成输出文件名
        output_file = f"pubmed_results_{time.strftime('%Y%m%d')}.csv"
        scraper.export_to_csv(articles, output_file, query)

if __name__ == "__main__":
    main()
