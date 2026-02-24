# SmartChat 智能助手

基于 Chainlit 构建的本地智能对话系统，集成 LangChain 架构和 RAG 技术。

## 核心功能

- **多模型支持**：无缝切换 Ollama 本地模型（Qwen、DeepSeek、Llama 等）
- **ReAct Agent**：具备多步推理和工具调用能力，实时展示思考过程
- **RAG 文档问答**：支持 PDF、Word、图片等多种格式文档上传与检索
- **向量数据库**：基于 ChromaDB 的本地知识库，中文语义优化（BAAI/bge-small-zh）
- **多模态解析**：自动识别扫描版 PDF，支持视觉模型 OCR

## 快速开始

1. **选择模型**：在侧边栏设置面板选择适合的模型
2. **开始对话**：直接输入问题，Agent 会自动思考并调用工具
3. **上传文档**：点击输入框左侧附件图标上传文档，自动建立知识库
4. **查看思考过程**：点击 "Process" 展开 Agent 的推理链

## 技术栈

- **前端**：Chainlit（原生 Python Web 框架）
- **LLM 框架**：LangChain（ReAct Agent + Tools）
- **向量数据库**：ChromaDB（嵌入式本地存储）
- **Embedding**：BAAI/bge-small-zh（中文优化）
