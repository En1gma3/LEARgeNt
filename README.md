# LearnMate 智能学习助手

基于苏格拉底式引导的智能学习系统，帮助用户从论文、新闻、公司、问题等多种兴趣点提取知识并进行深度学习。

## 功能特性

### 兴趣点学习
- **PDF论文** - 从学术论文提取专业术语
- **新闻文章** - 从新闻报道提取关键概念
- **公司/行业** - 深入了解公司或行业相关知识
- **问题/疑问** - 从问题拆解知识点

### 苏格拉底式引导
- 不直接给答案，通过提问引导思考
- 六类核心问题：澄清、假设、证据、反例、推论，元认知
- 七步对话流程：诊断 → 拆解 → 推理 → 识别 → 提示 → 总结

### 核心模块
- **知识库** - SQLite本地存储，名词/标签/关联管理，全文检索
- **记忆系统** - 短期记忆（会话上下文）+ 长期记忆（用户偏好）
- **复习系统** - 艾宾浩斯遗忘曲线算法，智能复习计划
- **信息搜集** - 网页抓取，搜索，结果整合
- **扩展功能** - 学习路径，提醒系统，统计分析，学习总结，思维导图

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- requests - HTTP请求
- beautifulsoup4 - HTML解析
- jieba - 中文分词

### 启动服务

```bash
# 进入项目目录
cd /Users/wzw3/LEARGENT

# 启动交互模式
python -m cli

# 或直接学习指定概念
python -m cli learn 区块链
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `/learn <概念>` | 学习指定概念 |
| `/learn paper <路径>` | 从PDF提取术语学习 |
| `/learn news <URL>` | 从新闻提取概念学习 |
| `/learn company <公司>` | 了解公司相关知识 |
| `/learn whatis <问题>` | 什么是...问题 |
| `/list` | 显示已学习内容 |
| `/help` | 显示帮助 |
| `/exit` | 退出 |

## 项目结构

```
LEARGENT/
├── agent/                      # 学习代理
│   └── socratic/               # 苏格拉底引导
│       ├── types.py            # 类型定义
│       ├── prompt.py           # 提示词
│       └── core.py             # 核心逻辑
├── parser/                     # 内容解析器
│   ├── base.py                 # 解析器基类
│   ├── pdf_parser.py           # PDF解析
│   ├── news_parser.py          # 新闻解析
│   ├── company_parser.py       # 公司解析
│   ├── industry_parser.py      # 行业解析
│   ├── question_parser.py      # 问题解析
│   └── factory.py              # 解析器工厂
├── extractor/                   # 术语提取器
│   ├── base.py                 # 提取器基类
│   ├── nlp_extractor.py       # NLP规则提取
│   ├── statistical_extractor.py # 统计方法提取
│   ├── llm_extractor.py       # LLM提取
│   └── ranker.py              # 重要性排序
├── interest_predictor/          # 兴趣预测
│   └── predictor.py            # 预测器
├── knowledge/                  # 知识库
│   ├── models.py               # 数据模型
│   └── db.py                   # 数据库操作
├── memory/                      # 记忆系统
│   ├── context.py              # 短期记忆
│   └── long_term.py            # 长期记忆
├── review/                      # 复习模块
│   └── scheduler.py            # 艾宾浩斯调度器
├── fetcher/                     # 信息搜集
│   └── web.py                  # 网页抓取
├── features/                   # 扩展功能
│   ├── learning_path/          # 学习路径
│   ├── reminder/               # 提醒系统
│   ├── statistics/            # 统计分析
│   └── summary/                # 总结与思维导图
├── cli/                        # 命令行入口
│   ├── main.py                 # 入口
│   ├── interactive.py          # 交互模式
│   └── __main__.py             # 启动点
├── README.md
└── LEARNMATE_PRD_v3.md         # 产品需求文档
```

## 配置LLM

默认使用Mock客户端（用于测试）。配置以下环境变量启用真实LLM：

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
export LLM_PROVIDER="openai"
export LLM_MODEL="gpt-4"
```

### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export LLM_PROVIDER="anthropic"
export LLM_MODEL="claude-3-opus-20240229"
```

### Ollama (本地)
```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export LLM_PROVIDER="ollama"
export LLM_MODEL="llama2"
```

## 版本

v0.3.0
