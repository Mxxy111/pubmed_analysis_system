import schedule
import time
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from DeepSeek import get_mesh_query
from pubmed_scraper import PubMedScraper

class LiteratureUpdater:
    def __init__(self, config_path='config.yaml'):
        self.config = self.load_config(config_path)
        self.last_update = None
        
    def load_config(self, config_path):
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def check_new_publications(self, research_area):
        """检查新发表的文献
        
        Args:
            research_area (str): 研究领域
        Returns:
            list: 新发表的文献列表
        """
        mesh_query = get_mesh_query(research_area)
        
        # 初始化PubMed爬虫
        email = self.config['pubmed']['email']
        scraper = PubMedScraper(email)
        
        # 设置筛选条件，只获取最近一周的文献
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        filters = {
            'start_date': start_date.strftime('%Y/%m/%d'),
            'end_date': end_date.strftime('%Y/%m/%d')
        }
        
        # 构建完整查询语句
        full_query = scraper.build_query(mesh_query, filters)
        
        # 搜索文献
        max_results = self.config['auto_update'].get('max_results', 100)
        id_list = scraper.search_pubmed(full_query, max_results)
        
        if not id_list:
            return []
            
        # 获取文献详细信息
        new_publications = scraper.fetch_details(id_list)
        return new_publications
    
    def generate_update_report(self, new_publications):
        """生成文献更新报告
        
        Args:
            new_publications (list): 新发表的文献列表
        Returns:
            str: 更新报告内容
        """
        if not new_publications:
            return "本次未发现新发表的相关文献。"
            
        report = ["# 文献更新报告"]
        report.append(f"\n## 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\n## 新增文献数量：{len(new_publications)}")
        
        for i, pub in enumerate(new_publications, 1):
            report.append(f"\n### {i}. {pub['title']}")
            report.append(f"作者：{pub['authors']}")
            report.append(f"期刊：{pub['journal']}")
            report.append(f"发表日期：{pub['date']}")
            report.append(f"摘要：{pub['abstract']}\n")
            
        return '\n'.join(report)
    
    def send_email_notification(self, report):
        """发送邮件通知
        
        Args:
            report (str): 更新报告内容
        """
        if not self.config['auto_update']['notification']['email']:
            return
            
        # TODO: 添加邮件服务器配置
        sender = 'your-email@example.com'
        password = 'your-password'
        receiver = 'receiver@example.com'
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = f'文献更新通知 - {datetime.now().strftime("%Y-%m-%d")}'
        
        msg.attach(MIMEText(report, 'plain', 'utf-8'))
        
        try:
            with smtplib.SMTP_SSL('smtp.example.com', 465) as server:
                server.login(sender, password)
                server.send_message(msg)
        except Exception as e:
            print(f'发送邮件失败：{str(e)}')
    
    def save_report(self, report, research_area):
        """保存更新报告
        
        Args:
            report (str): 更新报告内容
            research_area (str): 研究领域
        """
        output_dir = Path(self.config['output']['save_path'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = self.config['output']['file_naming'].format(
            research_area=research_area,
            date=datetime.now().strftime('%Y%m%d')
        )
        
        report_path = output_dir / f'{filename}_update.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def check_updates(self, research_area):
        """执行一次性的更新检查
        
        Args:
            research_area (str): 研究领域
        """
        print(f'开始检查文献更新：{research_area}')
        new_publications = self.check_new_publications(research_area)
        
        if len(new_publications) >= self.config['auto_update']['update_threshold']:
            report = self.generate_update_report(new_publications)
            
            if self.config['auto_update']['notification']['report']:
                self.save_report(report, research_area)
                
            if self.config['auto_update']['notification']['email']:
                self.send_email_notification(report)
                
        self.last_update = datetime.now()
        return new_publications

if __name__ == '__main__':
    updater = LiteratureUpdater()
    research_area = input('请输入要检查的研究领域：')
    new_publications = updater.check_updates(research_area)
    if new_publications:
        print(f'发现{len(new_publications)}篇新文献')
    else:
        print('未发现新文献')