import os
import requests
import random
import time
from tqdm import tqdm
from Bio import Entrez
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class AggressivePDFDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.download_stats = {
            'total': 0,
            'success': 0,
            'failed': [],
            'manual_links': []
        }
        
        # 配置重试策略
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=frozenset(['GET', 'POST'])
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        
        # 随机User-Agent
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
        ]

    def _random_delay(self):
        """随机延迟防止封禁"""
        time.sleep(random.uniform(1, 3))

    def _get_pdf_links(self, pmid):
        """暴力获取所有可能的PDF链接"""
        try:
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            record = Entrez.read(handle)
            article = record['PubmedArticle'][0]['MedlineCitation']['Article']
            
            links = []
            # 获取DOI链接
            if 'ELocationID' in article:
                for eid in article['ELocationID']:
                    if eid.attributes['EIdType'] == 'doi':
                        doi = str(eid)
                        links.append(f'https://doi.org/{doi}')
                        # 生成常见出版社PDF链接
                        links.extend([
                            f'https://link.springer.com/content/pdf/{doi}.pdf',
                            f'https://www.nature.com/articles/{doi.split("/")[-1]}.pdf',
                            f'https://journals.plos.org/plosone/article/file?id={doi}&type=printable'
                        ])
            
            # 获取PMC链接
            handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
            link_record = Entrez.read(handle)
            if link_record[0]['LinkSetDb']:
                for link in link_record[0]['LinkSetDb'][0]['Link']:
                    pmc_id = link['Id']
                    links.extend([
                        f'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/',
                        f'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/?report=reader'
                    ])
            
            return list(set(links))
        except Exception as e:
            print(f"获取链接失败: {str(e)}")
            return []

    def _try_download(self, url, output_path):
        """尝试暴力下载"""
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = self.session.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200 and 'pdf' in response.headers.get('Content-Type', ''):
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
            return False
        except Exception:
            return False

    def download_pdf(self, article, output_dir):
        """增强版下载方法"""
        pmid = article.get('pmid', '')
        doi = article.get('doi', '')
        self.download_stats['total'] += 1
        
        # 创建保存目录
        article_dir = os.path.join(output_dir, pmid)
        os.makedirs(article_dir, exist_ok=True)
        
        # 设置PDF文件保存路径
        pdf_path = os.path.join(article_dir, f"{pmid}.pdf")
        output_path = os.path.join(article_dir, "fulltext.pdf")
        
        # 如果已有PDF文件直接返回
        if os.path.exists(output_path):
            self.download_stats['success'] += 1
            return output_path
        
        # 暴力尝试所有可能的链接
        all_links = self._get_pdf_links(pmid)
        scihub_links = [
            f'https://sci-hub.se/{doi}',
            f'https://sci-hub.st/{pmid}',
            f'https://sci-hub.ru/{doi}'
        ]
        all_links.extend(scihub_links)
        
        for idx, url in enumerate(all_links):
            self._random_delay()
            print(f"尝试链接 [{idx+1}/{len(all_links)}]: {url}")
            if self._try_download(url, output_path):
                self.download_stats['success'] += 1
                return output_path
        
        # 记录失败信息
        manual_links = [
            f"PMID {pmid} 手动下载链接:",
            *[f"- {link}" for link in all_links if 'sci-hub' not in link],
            f"- Sci-Hub备用: https://sci-hub.se/{pmid or doi}"
        ]
        self.download_stats['failed'].append(pmid)
        self.download_stats['manual_links'].extend(manual_links)
        
        return None

    def batch_download(self, articles, output_dir):
        """批量下载入口"""
        print("\n=== 开始暴力下载模式（已提示过很暴力） ===")
        for article in tqdm(articles, desc="下载进度"):
            self.download_pdf(article, output_dir)
        self.show_stats()

    def show_stats(self):
        """显示下载统计信息"""
        print(f"\n=== 下载统计 ===")
        print(f"总计: {self.download_stats['total']}")
        print(f"成功: {self.download_stats['success']}")
        print(f"失败: {len(self.download_stats['failed'])}")
        
        if self.download_stats['manual_links']:
            print("\n=== 手动下载链接 ===")
            for link in self.download_stats['manual_links']:
                print(link)