"""
配置文件 - 包含应用程序的全局配置
"""
import os
import json
import streamlit as st

# 默认配置
DEFAULT_CONFIG = {
    # API配置
    "api": {
        "endpoint": "http://localhost:1314/api/chat",  # Ollama API端点，需要使用POST方法
        "max_retries": 3,                             # 最大重试次数
        "retry_delay": 1,                             # 初始重试延迟（秒）
        "timeout": 30                                 # 初始超时时间（秒）
    },
    # 模型配置
    "models": {
        "qwen2.5:3b": {
            "display_name": "通义千问2.5-3B",
            "description": "适合一般对话和简单问答的轻量级模型",
            "max_tokens": 2048
        },
        "deepseek-r1:8b": {
            "display_name": "深度求索-8B",
            "description": "擅长中文理解和生成的中型模型",
            "max_tokens": 3072
        },
        "llama3.1:latest": {
            "display_name": "Llama 3.1",
            "description": "多语言能力强，知识面广的大型模型",
            "max_tokens": 4096
        },
        "granite3.2-vision:latest": {
            "display_name": "Granite Vision 3.2",
            "description": "支持图像理解和多模态对话的视觉模型",
            "max_tokens": 4096
        }
    },
    # 界面配置
    "ui": {
        "theme": "dark",
        "max_message_display": 50,  # 显示的最大消息数
        "auto_scroll": True         # 自动滚动到最新消息
    },
    # 会话相关配置：控制上下文长度、输入节流和默认的简洁回复策略
    "conversation": {
        "max_history_messages": 10,   # 发送到API的最近消息数（越大上下文越长）
        "cooldown_seconds": 1.0,      # 连续发送时的最小间隔（秒）
        "post_generate_cooldown_seconds": 2.0, # 生成完成后前端应等待的秒数
        "generating_watchdog_timeout": 5.0,    # 生成被认为卡住前的超时时间（秒）
        "concise_by_default": True    # 是否默认要求简洁回复（true=简洁，false=详细）
    },
    # 缓存配置
    "cache": {
        "enabled": True,
        "ttl": 3600,               # 缓存生存时间（秒）
        "max_entries": 100         # 最大缓存条目数
    }
}

def load_config():
    """
    加载配置，优先从文件加载，如果文件不存在则使用默认配置
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # 深度合并配置
                return deep_merge(DEFAULT_CONFIG, user_config)
    except Exception as e:
        st.warning(f"加载配置文件失败: {str(e)}，使用默认配置")
    
    return DEFAULT_CONFIG

def deep_merge(dict1, dict2):
    """
    递归合并两个字典，dict2的值会覆盖dict1的值
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result

# 导出配置
CONFIG = load_config() 