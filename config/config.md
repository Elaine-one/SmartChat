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
| early_stopping_method | 提前停止方法 | generate |
| handle_parsing_errors | 解析错误处理提示 | - |
| verbose | 是否显示详细日志 | true |

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
