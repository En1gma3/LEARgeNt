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
| `/sessions` | 查看会话历史 |
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
├── utils/                      # 工具模块
│   └── logger.py               # 日志系统
├── config/                     # 配置文件
│   └── config.yaml             # 默认配置
├── data/                       # 数据存储
│   ├── knowledge.db            # 知识库
│   ├── sessions.json           # 会话历史
│   └── logs/                   # 日志文件
├── README.md
└── LEARNMATE_PRD_v3.md         # 产品需求文档
```

## 配置LLM

LearnMate 支持多种 LLM provider，默认使用 Mock 客户端（用于测试）。

### 配置文件方式

配置文件位于 `config/config.yaml`，支持以下配置项：

```yaml
llm:
  provider: "minimax"    # openai/anthropic/ollama/minimax/mock
  api_key: ""          # API密钥
  base_url: ""         # 自定义API地址
  model: "MiniMax-M2.5" # 模型名称
  temperature: 0.7    # 温度参数
  max_tokens: 1000     # 最大token数
```

配置文件路径优先级：
1. `LEARNMATE_CONFIG` 环境变量指定的位置
2. 项目根目录 `config/config.yaml`
3. `~/.learnmate/config.yaml`

### MiniMax (推荐)

```bash
# 编辑 config/config.yaml
llm:
  provider: "minimax"
  api_key: "sk-cp-..."
  base_url: "https://api.minimaxi.com/anthropic"
  model: "MiniMax-M2.5"
```

或使用环境变量：
```bash
export ANTHROPIC_AUTH_TOKEN="sk-cp-..."
export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export LLM_MODEL="MiniMax-M2.5"
export LLM_PROVIDER="minimax"
```

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

## 日志系统

LearnMate 提供集中式日志系统，便于排查问题。

### 日志文件位置
```
data/logs/learnmate.log
```

### 日志级别
通过环境变量控制:
```bash
export LEARNMATE_LOG_LEVEL=DEBUG  # DEBUG/INFO/WARNING/ERROR
```

### 在代码中使用日志
```python
from utils import get_logger

logger = get_logger(__name__)
logger.info("消息")
logger.debug("调试信息")
logger.warning("警告")
logger.error("错误")
```

## 会话持久化

### 会话保存位置
```
data/sessions.json
```

每次退出时，当前进度会自动保存。下次启动会自动加载。

### 查看会话历史
```
/sessions          # 列出最近会话
/sessions view <id>  # 查看会话详情
```

### 数据目录结构
```
data/
├── knowledge.db      # 知识库
├── memory.json       # 长期记忆（已学名词、偏好）
├── sessions.json     # 会话历史
├── review.json       # 复习计划
├── statistics.json   # 统计数据
└── logs/
    └── learnmate.log # 运行日志
```

## 版本

v0.3.0
