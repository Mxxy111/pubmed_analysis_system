import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
from typing import Dict, List, Optional
from datetime import datetime
import requests
import json
import yaml  # 添加yaml模块导入
from pathlib import Path

class AdvancedLiteratureAnalysis:
    def __init__(self):
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    def filter_literature(self, df: pd.DataFrame, filters: Dict = None) -> pd.DataFrame:
        filtered_df = df.copy()
        
        if not filters:
            return filtered_df
            
        # 日期范围筛选
        if 'date_range' in filters:
            # 首先尝试标准格式转换
            filtered_df['publication_date'] = pd.to_datetime(filtered_df['publication_date'], format='%Y-%m-%d', errors='coerce')
            # 如果存在空值，尝试其他常见格式
            mask = filtered_df['publication_date'].isna()
            if mask.any():
                filtered_df.loc[mask, 'publication_date'] = pd.to_datetime(filtered_df.loc[mask, 'publication_date'], errors='coerce')
            
            if 'start' in filters['date_range']:
                start_date = pd.to_datetime(filters['date_range']['start'], format='%Y-%m')
                filtered_df = filtered_df[filtered_df['publication_date'].notna() & (filtered_df['publication_date'] >= start_date)]
            if 'end' in filters['date_range']:
                end_date = pd.to_datetime(filters['date_range']['end'], format='%Y-%m')
                filtered_df = filtered_df[filtered_df['publication_date'].notna() & (filtered_df['publication_date'] <= end_date)]
        
        return filtered_df
    
    def analyze_from_csv(self, csv_file: str) -> None:
        """从CSV文件读取并分析文献数据
        
        Args:
            csv_file (str): CSV文件路径
        """
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        
        # 生成可视化结果
        output_dir = Path(csv_file).parent / 'visualization_results'
        output_paths = self.save_visualization_results(df, str(output_dir))
        
        print("\n可视化结果已保存:")
        for name, path in output_paths.items():
            print(f"{name}: {path}")
    
    def generate_wordcloud(self, text_data: List[str], title: str, output_path: str) -> None:
        """生成词云图
        
        Args:
            text_data (List[str]): 文本数据列表
            title (str): 图表标题
            output_path (str): 输出文件路径
        """
        text = ' '.join(text_data)
        wordcloud = WordCloud(width=1200, height=800,
                            background_color='white',
                            font_path='simhei.ttf',  # 使用中文字体
                            max_words=100).generate(text)
        
        plt.figure(figsize=(15, 10))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(title, fontsize=16)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_author_network(self, df: pd.DataFrame, output_path: str) -> None:
        """创建作者合作网络图
        
        Args:
            df (pd.DataFrame): 文献数据
            output_path (str): 输出文件路径
        """
        G = nx.Graph()
        
        # 构建作者合作网络
        for authors in df['authors']:
            author_list = [a.strip() for a in authors.split(',')]
            for i in range(len(author_list)):
                for j in range(i + 1, len(author_list)):
                    if G.has_edge(author_list[i], author_list[j]):
                        G[author_list[i]][author_list[j]]['weight'] += 1
                    else:
                        G.add_edge(author_list[i], author_list[j], weight=1)
        
        # 设置节点大小和边的粗细
        node_size = [G.degree(node) * 100 for node in G.nodes()]
        edge_width = [G[u][v]['weight'] for u, v in G.edges()]
        
        plt.figure(figsize=(20, 20))
        pos = nx.spring_layout(G)
        nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color='lightblue')
        nx.draw_networkx_edges(G, pos, width=edge_width, alpha=0.5)
        nx.draw_networkx_labels(G, pos, font_size=8)
        
        plt.title('作者合作网络图', fontsize=16)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def analyze_research_trends(self, df: pd.DataFrame, output_path: str) -> None:
        """分析研究趋势并生成可视化图表
        
        Args:
            df (pd.DataFrame): 文献数据
            output_path (str): 输出文件路径
        """
        # 按年份统计文献数量
        df['year'] = pd.to_datetime(df['publication_date']).dt.year
        yearly_counts = df['year'].value_counts().sort_index()
        
        plt.figure(figsize=(12, 6))
        yearly_counts.plot(kind='line', marker='o')
        plt.title('研究趋势分析', fontsize=14)
        plt.xlabel('年份', fontsize=12)
        plt.ylabel('文献数量', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def compare_literature(self, literature_list: List[Dict]) -> str:
        """使用AI对多篇文献进行对比分析
        
        Args:
            literature_list (List[Dict]): 文献信息列表
        
        Returns:
            str: 对比分析报告
        """
        try:
            # 读取配置文件
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 获取API配置
            api_config = config['active_model']
            url = api_config['endpoint']
            
            # 构建文献对比提示词
            literature_texts = []
            for i, lit in enumerate(literature_list, 1):
                literature_texts.append(f"文献{i}:\n标题：{lit['title']}\n摘要：{lit['abstract']}\n结论：{lit.get('conclusion', '')}\n")
            
            prompt = f"""请对以下{len(literature_list)}篇文献进行对比分析，生成一份详细的报告：

{''.join(literature_texts)}

请从以下几个方面进行分析：
1. 各篇文献的研究重点和方法对比
2. 研究结果的异同点
3. 各自的优势和局限性
4. 研究结论的互补性
5. 对该研究领域的整体贡献
6. 未来研究方向的建议

要求：
1. 分析要客观、系统、全面
2. 突出各篇文献的特色和创新点
3. 指出研究结果的一致性和差异性
4. 总结该领域的研究趋势"""
            
            payload = {
                "model": api_config['model'],
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的医学文献评论专家，擅长对多篇医学研究论文进行对比分析。"
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
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content'].strip()
            else:
                raise ValueError("API响应中未找到有效的分析结果")
                
        except Exception as e:
            print(f"生成文献对比分析时发生错误: {str(e)}")
            return None
    
    def handle_literature_comparison(self, df: pd.DataFrame, output_dir: str) -> Optional[str]:
        """处理文献对比分析的交互流程
        
        Args:
            df (pd.DataFrame): 文献数据
            output_dir (str): 输出目录
        
        Returns:
            Optional[str]: 对比分析报告的文件路径
        """
        need_comparison = input("\n是否需要进行文献对比分析？(y/n): ").lower().strip() == 'y'
        if not need_comparison:
            return None
            
        print("\n请选择要对比分析的文献:")
        for i, (_, row) in enumerate(df.iterrows(), 1):
            print(f"[{i}] {row['title']}")
        
        selected_indices = input("\n请输入要对比的文献编号（用逗号分隔）（建议不要太多，除非token很足）（共计耗时约2min）: ").split(',')
        selected_literature = []
        
        for idx in selected_indices:
            try:
                i = int(idx.strip()) - 1
                if 0 <= i < len(df):
                    row = df.iloc[i]
                    selected_literature.append({
                        'title': row['title'],
                        'abstract': row['abstract']
                    })
            except ValueError:
                continue
        
        if selected_literature:
            print("\n正在生成对比分析报告...")
            comparison_report = self.compare_literature(selected_literature)
            if comparison_report:
                report_path = Path(output_dir) / 'comparison_report.txt'
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(comparison_report)
                print(f"\n对比分析报告已保存至: {report_path}")
                return str(report_path)
        
        return None

    def save_visualization_results(self, df: pd.DataFrame, output_dir: str) -> Dict[str, str]:
        """
        Args:
            df (pd.DataFrame): 文献数据
            output_dir (str): 输出目录
        
        Returns:
            Dict[str, str]: 各个可视化文件的路径
        """
        if df.empty:
            print("警告：没有找到符合条件的文献数据，无法生成可视化结果。")
            return {}
            
        output_paths = {}
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成词云图
        wordcloud_path = f"{output_dir}/wordcloud.png"
        combined_text = df.apply(lambda row: f"{row['title']} {row['abstract'] if pd.notna(row['abstract']) else ''}", axis=1)
        text_data = [' '.join(combined_text.tolist())]
        self.generate_wordcloud(
            text_data,
            '研究热点词云图',
            wordcloud_path
        )
        output_paths['wordcloud'] = wordcloud_path
        
        # 生成作者合作网络图
        network_path = f"{output_dir}/author_network.png"
        self.create_author_network(df, network_path)
        output_paths['author_network'] = network_path
        
        # 生成研究趋势图
        trends_path = f"{output_dir}/research_trends.png"
        self.analyze_research_trends(df, trends_path)
        output_paths['research_trends'] = trends_path
        
        # 处理文献对比分析
        comparison_report_path = self.handle_literature_comparison(df, output_dir)
        if comparison_report_path:
            output_paths['comparison_report'] = comparison_report_path
        
        return output_paths

if __name__ == "__main__":
    # 测试代码
    analyzer = AdvancedLiteratureAnalysis()
    
    # 读取示例数据
    csv_file = input("请输入文献CSV文件路径: ")
    df = pd.read_csv(csv_file)
    
    # 询问是否需要筛选
    need_filter = input("是否需要按日期范围筛选文献？(y/n): ").lower().strip() == 'y'
    filters = None
    
    if need_filter:
        start_date = input("请输入起始日期 (格式: YYYY-MM，例如 2010-01): ")
        end_date = input("请输入结束日期 (格式: YYYY-MM，例如 2024-12): ")
        filters = {
            'date_range': {'start': start_date, 'end': end_date}
        }
    
    # 筛选文献
    filtered_df = analyzer.filter_literature(df, filters)
    print(f"\n筛选后的文献数量: {len(filtered_df)}")
    
    # 生成可视化结果
    output_dir = Path(csv_file).parent / 'visualization_results'
    output_paths = analyzer.save_visualization_results(filtered_df, str(output_dir))
    
    print("\n可视化结果已保存:")
    for name, path in output_paths.items():
        print(f"{name}: {path}")
