"""LLM 工厂，负责创建语言模型实例。"""

import os
from urllib.parse import urlparse
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from smart_chat.core.config import CONFIG


def _get_int_env(name: str, default: int) -> int:
    """从环境变量读取整数值。
    
    Args:
        name: 环境变量名
        default: 默认值
        
    Returns:
        整数值
    """
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_endpoint() -> str:
    """解析 API 端点，优先环境变量覆盖。
    
    Returns:
        API 端点 URL
    """
    api_config = CONFIG.get("api", {})
    return os.environ.get("SMARTCHAT_API_ENDPOINT") or api_config.get("endpoint")


def get_llm(model_name: str, temperature: float = 0.7, max_tokens: int | None = None) -> BaseChatModel:
    """根据配置创建 LLM 实例。
    
    Args:
        model_name: 模型名称
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        
    Returns:
        LLM 实例
    """
    api_config = CONFIG.get("api", {})
    endpoint = _resolve_endpoint()
    timeout = _get_int_env("SMARTCHAT_API_TIMEOUT", api_config.get("timeout", 120))

    parsed = urlparse(endpoint)
    port = parsed.port
    is_ollama = "ollama" in endpoint or port in (11434, 1314)
    if is_ollama:
        base_url = endpoint.replace("/api/chat", "").replace("/api/generate", "")
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=base_url,
            timeout=timeout,
            num_predict=max_tokens,
            streaming=True,
        )

    api_key = os.environ.get("SMARTCHAT_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "EMPTY")
    base_url = endpoint
    if "chat/completions" in base_url:
        base_url = base_url.replace("/chat/completions", "")
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base=base_url,
        timeout=timeout,
        max_tokens=max_tokens,
        streaming=True,
    )
