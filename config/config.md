# SmartChat 配置说明

本文档说明 config.json 中各配置项的含义。

## api

| 字段 | 说明 | 默认值 |
|------|------|--------|
| endpoint | LLM API 端点 | http://localhost:1314/api/chat |
| max_retries | 请求失败重试次数 | 3 |
| retry_delay | 重试间隔（秒） | 1 |
| timeout | 请求超时（秒） | 120 |

## cache

| 字段 | 说明 | 默认值 |
|------|------|--------|
| enabled | 是否启用缓存 | true |
| ttl | 缓存有效期（秒） | 3600 |
| max_entries | 最大缓存条目数 | 100 |

## ui

| 字段 | 说明 | 默认值 |
|------|------|--------|
| theme | 主题（dark/light） | dark |
| max_message_display | 最大显示消息数 | 50 |
| auto_scroll | 是否自动滚动 | true |
| scroll_batching_delay_ms | 滚动批处理延迟（毫秒） | 80 |
| scroll_batch_threshold | 滚动批处理阈值 | 6 |

## conversation

| 字段 | 说明 | 默认值 |
|------|------|--------|
| max_history_messages | 最大历史消息数 | 10 |
| cooldown_seconds | 冷却时间（秒） | 1.0 |
| post_generate_cooldown_seconds | 生成后冷却（秒） | 2.0 |
| generating_watchdog_timeout | 生成超时（秒） | 5.0 |
| concise_by_default | 默认简洁模式 | true |

## document_processing

| 字段 | 说明 | 默认值 |
|------|------|--------|
| enabled | 是否启用文档处理 | true |
| vision_model | 视觉模型名称 | granite3.2-vision:latest |
| api_endpoint | 视觉模型 API 端点 | http://localhost:1314/api/generate |
| supported_formats | 支持的文件格式 | ["pdf", "jpg", ...] |
| max_pages | PDF 最大处理页数 | 10 |
| temp_dir | 临时文件目录 | ./temp |
| cache_size | 缓存大小 | 10 |
| show_in_main_ui | 是否在主 UI 显示 | false |

## models

模型配置，每个模型包含：

| 字段 | 说明 |
|------|------|
| display_name | 显示名称 |
| description | 模型描述 |
| max_tokens | 最大生成 token 数 |
| context_window | 上下文窗口大小 |
| priority | 优先级（越小越靠前） |

## agent

| 字段 | 说明 | 默认值 |
|------|------|--------|
| max_iterations | 最大迭代次数 | 20 |
| max_execution_time | 最大执行时间（秒） | 180 |
| early_stopping_method | 提前停止方法 | force |
| handle_parsing_errors | 解析错误处理提示 | - |
| verbose | 是否显示详细日志 | true |

**early_stopping_method 说明**：
- `force`: 达到最大迭代次数后，强制返回 Agent 的第一个响应
- `iter`: 返回第一个不是工具调用的响应

## search

| 字段 | 说明 | 默认值 |
|------|------|--------|
| provider | 搜索提供商 | bing_lite |
| timeout | 搜索超时（秒） | 15 |
| count | 返回结果数量 | 8 |

## auth

| 字段 | 说明 | 默认值 |
|------|------|--------|
| enabled | 是否启用认证 | true |
| default_user | 默认用户名 | admin |
| default_password | 默认密码 | admin |

## telemetry

| 字段 | 说明 | 默认值 |
|------|------|--------|
| disable_chromadb_telemetry | 禁用 ChromaDB 遥测 | true |

## 知识库配置 (knowledge_base.json)

知识库配置文件位于 `config/knowledge_base.json`，包含预定义的高质量网站链接。

### 配置结构

```json
{
  "category_key": {
    "name": "类别名称",
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

### 预定义类别

| 类别键 | 名称 | 用途 |
|--------|------|------|
| weather | 天气查询 | 天气预报、实时天气 |
| news | 新闻资讯 | 最新新闻、热点资讯 |
| tech | 技术文档 | 编程语言、框架文档 |
| encyclopedia | 百科知识 | 概念解释、定义 |
| finance | 财经金融 | 股票、基金、投资 |
| travel | 旅游出行 | 旅游攻略、景点介绍 |
| health | 健康医疗 | 医疗信息、疾病知识 |
| education | 教育学习 | 在线课程、学术资料 |
| entertainment | 娱乐休闲 | 电影、音乐、游戏 |
| sports | 体育竞技 | 体育新闻、赛事直播 |
| tools | 实用工具 | 在线工具、计算器 |
| government | 政府服务 | 政策、公共服务 |
| legal | 法律法规 | 法律条文、案例分析 |

### 添加新类别

1. 编辑 `config/knowledge_base.json`
2. 添加新的类别对象
3. 设置 `keywords` 以便 Agent 匹配查询

## 环境变量

以下环境变量可覆盖配置文件中的设置：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| SMARTCHAT_API_ENDPOINT | LLM API 端点 | http://localhost:1314/api/chat |
| SMARTCHAT_USER | 登录用户名 | admin |
| SMARTCHAT_PASSWORD | 登录密码 | admin123 |
| SMARTCHAT_EMBEDDING_MODEL_NAME | Embedding 模型 | BAAI/bge-small-zh |
| SMARTCHAT_CHROMA_DIR | ChromaDB 存储目录 | ./data/chroma_db |
| CHAINLIT_AUTH_SECRET | Chainlit 安全密钥 | 至少32字节 |

## 配置优先级

配置加载优先级（从高到低）：

1. 环境变量（`SMARTCHAT_*`）
2. `config/config.json`
3. `DEFAULT_CONFIG`（代码内默认值）
