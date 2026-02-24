import os
import warnings
import logging
import asyncio

telemetry_config = {}
if os.path.exists(os.path.join(os.getcwd(), "config", "config.json")):
    try:
        import json
        with open(os.path.join(os.getcwd(), "config", "config.json"), "r", encoding="utf-8") as f:
            telemetry_config = json.load(f).get("telemetry", {})
    except Exception:
        telemetry_config = {}
if telemetry_config.get("disable_chromadb_telemetry", True):
    os.environ["ANONYMIZED_TELEMETRY"] = "False"

warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch, TextInput
from chainlit.types import ThreadDict
from dotenv import load_dotenv
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from smart_chat.core.config import CONFIG
from smart_chat.core.logging import setup_logging
from smart_chat.llms import get_llm
from smart_chat.agents import create_agent_executor
from smart_chat.document_loaders.processor import document_processor
from smart_chat.core.data_layer import data_layer as sqlalchemy_data_layer
from smart_chat.vectorstores.chroma import VectorStoreManager

load_dotenv()
setup_logging()

if not os.environ.get("CHAINLIT_AUTH_SECRET"):
    os.environ["CHAINLIT_AUTH_SECRET"] = "smartchat-dev-auth-secret-key-32bytes-long"


def _get_session_docs() -> list[str]:
    """获取当前会话的文档内容列表。"""
    return cl.user_session.get("session_doc_texts", [])


def _append_session_doc(text: str) -> None:
    """追加文档内容到当前会话的临时上下文。"""
    if not text or not text.strip():
        return
    docs = _get_session_docs()
    docs.append(text.strip())
    max_chars = 12000
    combined = "\n\n".join(docs)
    if len(combined) > max_chars:
        combined = combined[-max_chars:]
        docs = combined.split("\n\n")
    cl.user_session.set("session_doc_texts", docs)


def _build_session_doc_context() -> str:
    """构建会话级文档上下文。"""
    docs = _get_session_docs()
    return "\n\n".join([d for d in docs if d])


async def _warmup_vector_store() -> None:
    """异步预热向量数据库。"""
    def _init_store() -> None:
        VectorStoreManager().ensure_ready()
    try:
        await cl.make_async(_init_store)()
    except Exception as e:
        logging.error(f"Vector store warmup failed: {e}", exc_info=True)


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """登录鉴权回调。"""
    auth_config = CONFIG.get("auth", {})
    expected_user = os.environ.get("SMARTCHAT_USER", auth_config.get("default_user", "admin"))
    expected_password = os.environ.get("SMARTCHAT_PASSWORD", auth_config.get("default_password", "admin"))
    if username == expected_user and password == expected_password:
        return cl.User(identifier=username, metadata={"role": "admin"})
    return None


@cl.data_layer
def get_data_layer():
    """数据层回调，用于会话持久化。"""
    return sqlalchemy_data_layer


AVAILABLE_MODELS = list(CONFIG.get("models", {}).keys())

@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """历史会话恢复回调。"""
    settings = {
        "model": AVAILABLE_MODELS[0],
        "temperature": 0.7,
        "use_agent": True
    }
    cl.user_session.set("session_doc_texts", [])
    await setup_chat_engine(settings)
    await cl.Message(content=f"👋 欢迎回来！已加载历史会话，您可以继续提问。").send()

@cl.on_chat_start
async def start():
    """新会话初始化。"""
    settings = await cl.ChatSettings(
        [
            Select(
                id="model",
                label="选择模型 (Model)",
                values=AVAILABLE_MODELS,
                initial_index=0
            ),
            Switch(id="index_uploads", label="上传文件写入知识库", initial=False),
            Slider(
                id="temperature",
                label="随机性 (Temperature)",
                initial=0.7,
                min=0,
                max=1,
                step=0.1,
            ),
            Switch(id="use_agent", label="启用智能体 (Agent)", initial=False),
            Switch(id="show_cot", label="显示思维链 (CoT)", initial=False),
            Switch(id="clear_db_on_update", label="🗑️ 清空知识库 (选中并点击确认以执行)", initial=False),
            Switch(id="clear_history", label="🧹 清空历史记录 (选中并点击确认以执行)", initial=False),
        ]
    ).send()

    cl.user_session.set("chat_settings", {
        "model": AVAILABLE_MODELS[0],
        "index_uploads": False,
        "temperature": 0.7,
        "use_agent": False,
        "show_cot": False,
        "clear_db_on_update": False,
        "clear_history": False
    })
    cl.user_session.set("session_doc_texts", [])

    await setup_chat_engine(settings)

    await cl.Message(
        content="""👋 **欢迎使用 SmartChat**

**核心特性**:
- 🤖 多模型支持（Qwen、DeepSeek、Llama 等）
- 🧠 ReAct Agent 实时思维链
- 📚 RAG 文档问答（PDF/Word/图片）
- 🔍 中文语义优化（BAAI/bge-small-zh）

**快速上手**:
1. 在侧边栏设置面板选择模型
2. 直接输入问题或上传文档
3. 点击 "Process" 查看 Agent 思考过程
        """
    ).send()

async def setup_chat_engine(settings, status_msg: cl.Message = None):
    """根据设置初始化聊天引擎。
    
    Args:
        settings: 用户配置
        status_msg: 状态消息对象
    """
    if status_msg:
        status_msg.content = "⏳ 正在初始化模型引擎，请稍候..."
        await status_msg.update()
    else:
        status_msg = cl.Message(content="⏳ 正在初始化模型引擎，请稍候...", author="System")
        await status_msg.send()

    try:
        model = settings.get("model", AVAILABLE_MODELS[0])
        temp = settings.get("temperature", 0.7)
        use_agent = settings.get("use_agent", True)
        
        model_config = CONFIG.get("models", {}).get(model, {})
        max_tokens = model_config.get("max_tokens", 2048)

        cl.user_session.set("show_cot", settings.get("show_cot", True))
        cl.user_session.set("index_uploads", settings.get("index_uploads", True))
        
        def _build_engine():
            llm = get_llm(model, temp, max_tokens=max_tokens)
            
            agent_executor = None
            if use_agent:
                search_config = CONFIG.get("search", {})
                agent_executor = create_agent_executor(llm, search_config=search_config)
                
            return llm, agent_executor

        llm, agent_executor = await cl.make_async(_build_engine)()
        
        cl.user_session.set("llm", llm)
        if use_agent:
            cl.user_session.set("agent", agent_executor)
        else:
            cl.user_session.set("agent", None)
        if cl.user_session.get("index_uploads", True):
            asyncio.create_task(_warmup_vector_store())
        
    except Exception as e:
        error_content = f"❌ 引擎初始化失败: {str(e)}"
        if status_msg:
            status_msg.content = error_content
            await status_msg.update()
        else:
            await cl.Message(content=error_content).send()
            
        logging.error(f"Setup chat engine failed: {e}", exc_info=True)
        raise e

@cl.on_settings_update
async def setup_agent(settings):
    """配置变更回调。
    
    Args:
        settings: 更新的配置项
    """
    status_msg = cl.Message(content="⚙️ 正在应用配置更改...", author="System")
    await status_msg.send()

    old_settings = cl.user_session.get("chat_settings", {})
    merged_settings = {**old_settings, **settings}
    changes = []
    changed_keys = set(settings.keys())
    
    if ("model" in changed_keys) or (merged_settings.get("model") != old_settings.get("model")):
        changes.append(f"🤖 模型: **{merged_settings.get('model')}**")
        
    if ("temperature" in changed_keys) or (merged_settings.get("temperature") != old_settings.get("temperature")):
        changes.append(f"🌡️ 随机性: **{merged_settings.get('temperature')}**")
        
    if ("use_agent" in changed_keys) or (merged_settings.get("use_agent") != old_settings.get("use_agent")):
        status = "启用" if merged_settings.get("use_agent") else "禁用"
        changes.append(f"🕵️ 智能体 (Agent): **{status}**")

    if ("show_cot" in changed_keys) or (merged_settings.get("show_cot") != old_settings.get("show_cot")):
        status = "显示" if merged_settings.get("show_cot") else "隐藏"
        changes.append(f"🧠 思维链 (CoT): **{status}**")
        
    if ("index_uploads" in changed_keys) or (merged_settings.get("index_uploads") != old_settings.get("index_uploads")):
        status = "开启" if merged_settings.get("index_uploads") else "关闭"
        changes.append(f"📂 上传写入知识库: **{status}**")

    if merged_settings.get("clear_db_on_update"):
        def _clear_db():
            return VectorStoreManager().clear()
        
        success = await cl.make_async(_clear_db)()
        if success:
            changes.append("🗑️ 知识库已清空")
            cl.user_session.set("session_doc_texts", [])

    if merged_settings.get("clear_history"):
        user = cl.user_session.get("user")
        user_id = user.identifier if user else None
        await sqlalchemy_data_layer.delete_all_user_threads(user_id)
        changes.append("🧹 历史记录已清空")
        cl.user_session.set("session_doc_texts", [])

    try:
        await setup_chat_engine(merged_settings, status_msg=status_msg)
    except Exception:
        return
    
    settings_to_save = merged_settings.copy()
    settings_to_save["clear_db_on_update"] = False
    settings_to_save["clear_history"] = False
    cl.user_session.set("chat_settings", settings_to_save)

    if merged_settings.get("clear_db_on_update") or merged_settings.get("clear_history"):
        await cl.ChatSettings(
            [
                Select(
                    id="model",
                    label="选择模型 (Model)",
                    values=AVAILABLE_MODELS,
                    initial_index=AVAILABLE_MODELS.index(merged_settings["model"]) if merged_settings["model"] in AVAILABLE_MODELS else 0
                ),
                Switch(id="index_uploads", label="上传文件写入知识库", initial=merged_settings["index_uploads"]),
                Slider(
                    id="temperature",
                    label="随机性 (Temperature)",
                    initial=merged_settings["temperature"],
                    min=0,
                    max=1,
                    step=0.1,
                ),
                Switch(id="use_agent", label="启用智能体 (Agent)", initial=merged_settings["use_agent"]),
                Switch(id="show_cot", label="显示思维链 (CoT)", initial=merged_settings["show_cot"]),
                
                Switch(id="clear_db_on_update", label="🗑️ 清空知识库 (选中并点击确认以执行)", initial=False),
                Switch(id="clear_history", label="🧹 清空历史记录 (选中并点击确认以执行)", initial=False),
            ]
        ).send()
        
        changes.append("ℹ️ **操作开关已自动复位**")
        feedback = "\n".join([f"- {c}" for c in changes])
        status_msg.content = f"✅ **配置已更新**:\n{feedback}"
        await status_msg.update()
        
    elif changes:
        feedback = "\n".join([f"- {c}" for c in changes])
        status_msg.content = f"✅ **配置已更新**:\n{feedback}"
        await status_msg.update()
        
    else:
        await status_msg.remove()


def _update_default_theme(theme: str) -> bool:
    """更新主题配置（已弃用）。"""
    return False


@cl.action_callback("clear_db")
async def on_clear_db(action: cl.Action):
    """清空知识库回调。"""
    def _clear():
        return VectorStoreManager().clear()

    if await cl.make_async(_clear)():
        await cl.Message(content="✅ 知识库已清空。").send()
    else:
        await cl.Message(content="❌ 清空失败，请查看日志。").send()


@cl.on_message
async def main(message: cl.Message):
    """消息处理主函数。
    
    Args:
        message: 用户消息对象
    """
    if message.elements:
        index_uploads = cl.user_session.get("index_uploads", True)
        processing_msg = cl.Message(content="📄 正在处理文档...", author="System")
        await processing_msg.send()

        for element in message.elements:
            try:
                if element.path:
                    text_content = await cl.make_async(document_processor.process_document)(
                        element.path, index_to_kb=index_uploads
                    )

                    if text_content and not text_content.startswith("Error"):
                        if not index_uploads:
                            _append_session_doc(text_content)
                        if index_uploads:
                            await cl.Message(content=f"✅ 文档 {element.name} 已写入知识库。").send()
                        else:
                            await cl.Message(content=f"✅ 文档 {element.name} 已解析。").send()
                    else:
                        error_msg = text_content if text_content else "无内容"
                        await cl.Message(content=f"⚠️ 文档 {element.name} 处理异常: {error_msg}").send()
            except Exception as e:
                await cl.Message(content=f"❌ 文档 {element.name} 处理失败: {str(e)}").send()

        processing_msg.content = "✅ 文档处理完成。"
        await processing_msg.update()

        if not (message.content or "").strip():
            await cl.Message(content="文档已处理，请继续提问。").send()
            return

    agent_executor = cl.user_session.get("agent")
    llm = cl.user_session.get("llm")

    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True,
        answer_prefix_tokens=["Final Answer"]
    )
    session_context = _build_session_doc_context()

    if agent_executor:
        agent_input = message.content
        if session_context:
            agent_input = (
                "请优先根据以下文档内容回答问题，如与常识冲突，以文档为准。\n\n"
                f"{session_context}\n\n问题：{message.content}"
            )
        res = await agent_executor.ainvoke(
            {"input": agent_input, "chat_history": []},
            config=RunnableConfig(callbacks=[cb])
        )
        if not cb.has_streamed_final_answer:
            await cl.Message(content=res["output"]).send()
    else:
        messages = [HumanMessage(content=message.content)]
        if session_context:
            messages = [
                SystemMessage(
                    content=(
                        "以下为用户在本会话上传的文档内容，请优先依据这些内容回答问题。\n\n"
                        f"{session_context}"
                    )
                ),
                HumanMessage(content=message.content),
            ]
        res = await llm.ainvoke(
            messages,
            config=RunnableConfig(callbacks=[cb])
        )
        if not cb.has_streamed_final_answer:
             await cl.Message(content=res.content).send()
