"""Agent 执行器工厂，负责创建 ReAct Agent。"""

from typing import Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel
from smart_chat.core.config import CONFIG
from smart_chat.prompts.react_prompt import REACT_PROMPT
from smart_chat.tools.factory import ToolsFactory
from smart_chat.tools.retriever import RetrieverToolFactory
from smart_chat.vectorstores.chroma import VectorStoreManager


def _get_retriever_tool() -> Optional[object]:
    """获取文档检索工具。
    
    Returns:
        检索工具实例，如果向量库未初始化则返回 None
    """
    vector_store = VectorStoreManager()
    if vector_store.initialized:
        return RetrieverToolFactory.create_retriever_tool()
    return None


def create_agent_executor(
    llm: BaseChatModel,
    use_tools: bool = True,
    search_config: dict | None = None,
) -> Optional[AgentExecutor]:
    """创建 ReAct Agent 执行器。
    
    Args:
        llm: 语言模型实例
        use_tools: 是否启用工具
        search_config: 搜索配置
        
    Returns:
        AgentExecutor 实例，如果未启用工具则返回 None
    """
    if not use_tools:
        return None

    tools = ToolsFactory.get_all_tools(llm, search_config)
    retriever_tool = _get_retriever_tool()
    if retriever_tool:
        tools.append(retriever_tool)
    if not tools:
        return None

    agent_config = CONFIG.get("agent", {})
    prompt = PromptTemplate.from_template(REACT_PROMPT)
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=agent_config.get("verbose", True),
        handle_parsing_errors=agent_config.get(
            "handle_parsing_errors",
            "输出格式不符合要求，请严格遵循 Thought/Action/Action Input/Observation/Final Answer 格式。",
        ),
        max_iterations=agent_config.get("max_iterations", 20),
        max_execution_time=agent_config.get("max_execution_time", 180),
        early_stopping_method=agent_config.get("early_stopping_method", "generate"),
    )
