# PubMed文献分析系统 📚

## 项目简介 🚀
这是一个基于Python的PubMed文献分析系统，可以自动检索、下载和分析医学文献，并生成详细的分析报告。系统使用DeepSeek AI进行文献解读，支持多种输出格式。本系统特别适合医学研究人员、学术工作者以及需要进行大规模医学文献分析的机构使用。

## 功能特点 ✨
- **PubMed文献自动检索和下载** 🔍
  - 支持多关键词组合搜索
  - 自定义时间范围筛选
  - 支持按文章类型、语言指标筛选
- **基于DeepSeek AI的文献智能解读** 🤖
  - 自动提取文献关键信息
  - 多维度分析研究方法和结果
  - 生成文献综述和研究趋势分析
- **支持批量处理多篇文献** 📦
  - 并行处理提高效率
  - 自动断点续传
  - 智能任务队列管理
- **多种输出格式（JSON、Markdown、TXT、CSV）** 📄
  - 结构化数据导出
  - 自定义导出模板
  - 支持批量导出
- **文献趋势分析和可视化** 📊
  - 研究热点分析
  - 作者合作网络图（不好用）
  - 关键词共现分析
  - 时间序列趋势图

## 环境要求 💻
- Python 3.8+
- pip包管理器
- 稳定的网络连接
- 至少4GB可用内存
- 建议使用SSD存储

## 安装步骤 🛠️

1. **克隆项目到本地（已手动安装压缩包的跳过）**：
```bash
git clone https://github.com/Mxxy111/pubmed-analysis-system.git
cd pubmed-analysis-system
```

2. **创建并激活虚拟环境（推荐但可跳过）**：
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖包（Windows可直接运行setup.bat）**：
```bash
pip install -r requirements.txt
```

## 配置说明 ⚙️（已添加setup.bat自动引导配置）

1. **首次使用时，将`config.yaml.template`复制并重命名为`config.yaml`**：
- 系统提供了配置模板文件`config.yaml.template`
- 首次运行时会自动将模板复制为 首次运行时会自动将模板复制为`config.yaml`
- 也可以手动复制并重命名模板文件 也可以手动复制并重命名模板文件

2. **修改配置文件 `config.yaml`**：
- 填写您的PubMed API访问邮箱
- 配置api相关参数（具体端口地址、api_key和模型名称请根据需要查阅相关ai平台的api调用文档）
  - API密钥设置
  - 模型参数调整
  - 并发请求限制
  - 模型选择配置
    - active_model：设置literature_analysis.py和advanced_analysis.py使用的默认模型
    - mesh_query_model：设置DeepSeek.py专用的API配置
- 根据需要调整文献筛选和分析参数
  - 搜索范围设置
  - 过滤条件定义
  - 输出格式配置

## 使用说明 📖

1. **运行主程序（Windows建议直接运行start.bat）**：
```bash
python main.py
```

2. **按照提示输入**：
- 搜索关键词（可直接输入搜索词，使用ai生成检索式支持各种语言，支持布尔运算符，如："cancer AND therapy"）
- 筛选条件
- 需要分析的文献数量（建议首次使用先设置较小的数量测试）

3. **等待系统自动完成**：
- 文献检索和下载
- AI解读分析
- 报告生成

## 输出说明 📂
分析结果将保存在 `results` 目录下，包括：
- **CSV格式的原始文献数据**
  - 基本文献信息
  - 引用数据
  - 作者信息
- **JSON格式的分析报告**
  - 详细的文献解读
  - 研究方法分析
  - 结果总结
- **Markdown格式的可读报告**
  - 文献综述
  - 研究趋势
  - 关键发现
- **可选的TXT或CSV格式报告**
- **可视化图表（如适用）**

## 常见问题 ❓

1. **依赖安装失败**
- 确保使用的是Python 3.8+版本
- 尝试更新pip: `python -m pip install --upgrade pip`
- 如果某个包安装失败，可以单独安装：`pip install package_name`
- 检查是否有系统特定的依赖缺失

2. **API访问错误**
- 检查网络连接
- 确认config.yaml中的邮箱配置正确
- 确保AI的API密钥有效
- 检查API访问频率是否超限

3. **内存不足**
- 减少批量处理的文献数量
- 关闭其他占用内存的程序
- 增加系统虚拟内存
- 考虑使用分批处理模式

4. **下载速度慢**
- 检查网络连接状态
- 调整并发下载数量
- 考虑使用镜像源（已默认使用清华源下载）或代理服务器
- 启用断点续传功能

## 注意事项 ⚠️
- 首次使用需要完成配置文件的设置
- 建议在虚拟环境中运行项目
- 处理大量文献时注意API使用限制
- 定期备份重要的分析结果
- 遵守PubMed的使用条款
- 注意保护API密钥安全
- 尽量不要使用直接下载PDF原文功能，尊重版权

## 许可证 📜
本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式 📧
- **项目维护者**：[Mxxy111]
- **GitHub**：[https://github.com/Mxxy111]
- **问题反馈**：请在GitHub Issues中提交

## 更新日志 📅
### v1.0.0
- 初始版本发布
- 支持基本的文献检索和分析功能
- 集成DeepSeek AI进行文献解读
- 实现多种格式的报告输出

## 贡献指南 🤝
我们欢迎所有形式的贡献，包括但不限于：
- 代码改进
- 文档完善
- 问题报告
- 新功能建议 新功能建议

请参阅 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多详情。

---

