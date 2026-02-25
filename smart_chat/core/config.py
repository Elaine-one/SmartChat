"""全局配置管理模块。

配置加载优先级：环境变量 > config.json > DEFAULT_CONFIG
"""
import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 默认配置
DEFAULT_CONFIG = {
    # API配置
    "api": {
        "endpoint": "http://localhost:1314/api/chat",  # Ollama API端点
        "max_retries": 3,
        "retry_delay": 1,
        "timeout": 30
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
        "max_message_display": 50,
        "auto_scroll": True
    },
    # RAG 配置
    "rag": {
        "embedding_model": "BAAI/bge-small-zh",
        "chunk_size": 800,
        "chunk_overlap": 100,
        "persist_directory": "chroma_db"
    },
    # 会话相关配置
    "conversation": {
        "max_history_messages": 10,
        "cooldown_seconds": 1.0,
        "post_generate_cooldown_seconds": 2.0,
        "generating_watchdog_timeout": 5.0,
        "concise_by_default": True
    },
    # 缓存配置
    "cache": {
        "enabled": True,
        "ttl": 3600,
        "max_entries": 100
    },
    "agent": {
        "max_iterations": 20,
        "max_execution_time": 180,
        "early_stopping_method": "force",
        "handle_parsing_errors": "输出格式不符合要求，请严格遵循 Thought/Action/Action Input/Observation/Final Answer 格式。",
        "verbose": True
    },
    "search": {
        "provider": "bing_lite",
        "timeout": 15,
        "count": 8
    },
    "auth": {
        "enabled": True,
        "default_user": "admin",
        "default_password": "admin"
    },
    "telemetry": {
        "disable_chromadb_telemetry": True
    }
}

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并两个字典，dict2 的值会覆盖 dict1 的值。"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """使用环境变量覆盖配置。"""
    # API 覆盖
    if os.environ.get("SMARTCHAT_API_ENDPOINT"):
        config["api"]["endpoint"] = os.environ.get("SMARTCHAT_API_ENDPOINT")
    
    if os.environ.get("SMARTCHAT_API_TIMEOUT"):
        try:
            config["api"]["timeout"] = int(os.environ.get("SMARTCHAT_API_TIMEOUT"))
        except ValueError:
            pass

    # RAG 覆盖
    if os.environ.get("SMARTCHAT_CHROMA_DIR"):
        config["rag"]["persist_directory"] = os.environ.get("SMARTCHAT_CHROMA_DIR")
    
    if os.environ.get("SMARTCHAT_EMBEDDING_MODEL_NAME"):
        config["rag"]["embedding_model"] = os.environ.get("SMARTCHAT_EMBEDDING_MODEL_NAME")

    # 搜索覆盖
    if os.environ.get("SMARTCHAT_SEARCH_TIMEOUT"):
        try:
            config["search"]["timeout"] = int(os.environ.get("SMARTCHAT_SEARCH_TIMEOUT"))
        except ValueError:
            pass

    # 鉴权覆盖
    if os.environ.get("SMARTCHAT_USER"):
        config["auth"]["default_user"] = os.environ.get("SMARTCHAT_USER")
    
    if os.environ.get("SMARTCHAT_PASSWORD"):
        config["auth"]["default_password"] = os.environ.get("SMARTCHAT_PASSWORD")

    # 遥测覆盖
    if os.environ.get("ANONYMIZED_TELEMETRY") is not None:
        val = os.environ.get("ANONYMIZED_TELEMETRY").lower()
        config["telemetry"]["disable_chromadb_telemetry"] = (val == "false")

    return config

def load_config() -> Dict[str, Any]:
    """加载配置。
    
    加载优先级：环境变量 > config.json > DEFAULT_CONFIG
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # 尝试多个可能的配置文件路径
    possible_paths = [
        os.path.join(project_root, "config", "config.json"),
        os.path.join(project_root, "config.json"),
    ]
    
    config = DEFAULT_CONFIG.copy()
    
    for config_path in possible_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    logger.info(f"已加载配置文件: {config_path}")
                    config = deep_merge(DEFAULT_CONFIG, user_config)
                    break
            except Exception as e:
                logger.error(f"加载配置文件失败 {config_path}: {str(e)}")
    
    config = apply_env_overrides(config)
    return config


CONFIG = load_config()
