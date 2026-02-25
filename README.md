# 智能聊天助手 (SmartChat)

SmartChat 是一个基于 **Chainlit** 开发的现代化智能聊天应用，集成 LangChain 架构和 RAG（检索增强生成）技术，支持多种大语言模型，提供智能问答、文档分析和多模态交互功能。

## ✨ 功能特点

- **多模型支持**：无缝集成 Ollama、OpenAI 等多种大语言模型（Qwen、DeepSeek、Llama 等）
- **ReAct Agent**：采用先进的 ReAct Agent 模式，支持动态工具调用和多步推理
- **RAG 文档对话**：支持 PDF、Word、TXT、图片等多种格式文档的上传与问答，基于 ChromaDB 向量数据库实现精准检索
- **中文语义优化**：使用 BAAI/bge-small-zh 中文 Embedding 模型，提升中文文档检索效果
- **智能交互**：
  - 实时展示 AI 思考过程（思维链 CoT）
  - 联网搜索能力（Bing Lite，免 Key）
  - 会话历史持久化
  - 动态配置面板
- **知识库系统**：预定义高质量网站链接，提升搜索质量和可靠性

## 📂 项目结构

```
smart_chat/
├── agents/             # Agent 执行器
│   └── executor.py     # ReAct Agent 构建
├── llms/               # LLM 工厂
│   └── factory.py      # 模型实例创建
├── tools/              # Agent 工具集
│   ├── factory.py      # 工具工厂（搜索/计算/时间/Python/知识库/网页抓取）
│   └── retriever.py    # RAG 检索工具
├── vectorstores/       # 向量数据库
│   └── chroma.py       # ChromaDB 管理器
├── document_loaders/   # 文档处理
│   └── processor.py    # 文档解析与向量化
├── prompts/            # Prompt 模板
│   └── react_prompt.py # ReAct 提示词
├── core/               # 核心层
│   ├── config.py       # 配置管理
│   ├── logging.py      # 日志系统
│   └── data_layer.py   # 数据持久化
└── utils/              # 工具函数
    └── __init__.py

app.py                  # Chainlit 应用入口
config/
├── config.json         # 用户配置文件
├── config.example.json # 配置模板
├── config.md           # 配置说明文档
└── knowledge_base.json # 知识库配置
docs/                   # 文档目录
requirements.txt        # Python 依赖
.env.example            # 环境变量模板
```

## 🚀 快速开始

### 1. 环境准备

**系统要求**：Python 3.10+

```bash
# 克隆项目
git clone <repository-url>
cd SmartChat

# 创建虚拟环境
conda create -n smartchat python=3.10
conda activate smartchat

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的参数
```

**关键环境变量**：
- `SMARTCHAT_API_ENDPOINT`: LLM API 端点（默认 http://localhost:1314/api/chat）
- `SMARTCHAT_USER` / `SMARTCHAT_PASSWORD`: 登录凭据
- `CHAINLIT_AUTH_SECRET`: 安全密钥（至少 32 字节）
- `SMARTCHAT_EMBEDDING_MODEL_NAME`: Embedding 模型（默认 BAAI/bge-small-zh）

### 3. 配置模型

确保本地已安装 Ollama 并运行以下模型（可选）：

```bash
# 推荐模型
ollama pull qwen2.5:3b        # 默认模型，中文优秀
ollama pull deepseek-r1:8b    # 深度推理
ollama pull llama3.1:latest   # 多语言能力强
ollama pull granite3.2-vision:latest  # 视觉模型（文档 OCR）
```

### 4. 启动应用

```bash
chainlit run app.py -w
```

参数说明：`-w` 开启热重载模式，代码修改后自动刷新。

访问 http://localhost:8000 打开应用。

## 📖 使用指南

### 界面功能

- **侧边栏**：
  - **历史记录**：查看和管理过往对话
  - **设置面板**：调整模型、Temperature、Agent 开关、思维链显示等
- **主对话区**：
  - **文件上传**：支持 PDF、Word、图片等格式
  - **思维链**：Agent 思考过程实时展示

### 功能开关说明

| 设置项 | 说明 |
|--------|------|
| 上传文件写入知识库 | 开启后，上传的文档会持久化到向量库 |
| 启用智能体 (Agent) | 开启后，AI 可使用工具（搜索/计算等） |
| 显示思维链 (CoT) | 开启后，展示 Agent 思考过程 |
| 清空知识库 | 选中并确认后清空所有文档 |
| 清空历史记录 | 选中并确认后删除所有会话 |

## ⚙️ 配置说明

### 配置文件 (config/config.json)

主要配置项：

```json
{
  "api": {
    "endpoint": "http://localhost:1314/api/chat",
    "timeout": 120
  },
  "models": {
    "qwen2.5:3b": {
      "display_name": "Qwen 2.5-3B",
      "max_tokens": 4096
    }
  },
  "agent": {
    "max_iterations": 20,
    "max_execution_time": 180,
    "early_stopping_method": "force"
  },
  "document_processing": {
    "enabled": true,
    "vision_model": "granite3.2-vision:latest"
  }
}
```

详细配置说明请参考 [config/config.md](config/config.md)。

### 环境变量 (.env)

```bash
# 鉴权
SMARTCHAT_USER=admin
SMARTCHAT_PASSWORD=admin123

# 模型服务
SMARTCHAT_API_ENDPOINT=http://localhost:1314/api/chat

# RAG 配置
SMARTCHAT_EMBEDDING_MODEL_NAME=BAAI/bge-small-zh
SMARTCHAT_CHROMA_DIR=./data/chroma_db
```

### 知识库配置 (config/knowledge_base.json)

知识库包含预定义的高质量网站链接，Agent 会优先查询知识库获取相关链接：

- **天气查询**：中国天气网、2345天气网等
- **新闻资讯**：百度新闻、新浪新闻、澎湃新闻等
- **技术文档**：Python 官方文档、MDN Web 文档等
- **财经金融**：新浪财经、东方财富网等
- **百科知识**：百度百科、维基百科等

## 🛠️ 开发指南

### 添加新工具

在 `smart_chat/tools/factory.py` 中创建工具：

```python
@staticmethod
def create_my_tool() -> Tool:
    """创建自定义工具。"""
    def my_func(query: str) -> str:
        return f"处理结果: {query}"
    
    return Tool(
        name="my_tool",
        func=my_func,
        description="工具描述，Agent 据此决定是否使用"
    )
```

然后在 `get_all_tools()` 中添加新工具。

### 自定义 Embedding 模型

修改环境变量或配置：

```bash
SMARTCHAT_EMBEDDING_MODEL_NAME=BAAI/bge-large-zh
```

支持的模型：
- `BAAI/bge-small-zh`（默认，轻量快速）
- `BAAI/bge-large-zh`（效果更好，资源占用更大）
- `sentence-transformers/all-MiniLM-L6-v2`（英文场景）

### 扩展知识库

编辑 `config/knowledge_base.json`，添加新的类别和链接：

```json
{
  "new_category": {
    "name": "新类别名称",
    "description": "类别描述",
    "links": [
      {
        "url": "https://example.com",
        "name": "网站名称",
        "description": "网站描述",
        "keywords": ["关键词1", "关键词2"]
      }
    ]
  }
}
```

## 📚 文档目录

- [API 文档](docs/API.md) - 核心模块 API 说明
- [依赖说明](docs/dependencies.md) - 依赖安装与常见问题
- [技术面试指南](docs/interview_guide.md) - 架构设计与技术选型深度解析
- [RAG 技术详解](docs/rag.md) - RAG 实现原理与优化策略
- [Agent 技术详解](docs/agent.md) - ReAct Agent 设计与实现
- [配置说明](config/config.md) - 配置文件详细说明

## 📝 版本历史

- **v2.2**: 添加知识库系统，优化 Agent 工具调用流程，修复编码问题
- **v2.1**: Chainlit 框架迁移，支持原生思维链展示，中文 Embedding 模型优化
- **v2.0**: 全面架构重构，引入 LangChain 和 RAG
- **v1.0**: 基础 Streamlit 聊天应用

## 📄 许可证

MIT License
