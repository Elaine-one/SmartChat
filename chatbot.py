import streamlit as st
from utils.theme import inject_custom_css
from utils.api import LLMClient
from components.sidebar import render_sidebar, update_system_prompt_for_language
from components.chat import display_chat_history, handle_user_input
from utils.document_processor import document_processor
from utils.config import CONFIG
import uuid
import datetime
import os

# 定义确保聊天标题使用当前语言的函数
def ensure_chat_titles_use_current_language(chat_histories, language):
    """确保聊天历史的标题使用当前语言"""
    # 获取URL参数中的语言设置，优先使用URL参数
    query_params = st.query_params
    url_lang = query_params.get("lang", language)
    is_chinese = url_lang == "zh"
    
    # 显示标题中英文切换映射
    title_mapping = {
        "新对话": "New Chat",
        "New Chat": "新对话"
    }

    for chat_id, chat in chat_histories.items():
        title = chat.get("title", "")
        
        # 处理默认标题
        if title in title_mapping:
            chat["title"] = "新对话" if is_chinese else "New Chat"
            
        # 检查标题中是否包含中英文默认标题部分
        for zh_title, en_title in title_mapping.items():
            if zh_title in title and not is_chinese:
                # 中文标题在英文模式下
                chat["title"] = title.replace(zh_title, en_title)
            elif en_title in title and is_chinese:
                # 英文标题在中文模式下
                chat["title"] = title.replace(en_title, zh_title)

# 文档上传组件
def render_document_upload():
    """渲染文档上传组件到主页面"""
    # 获取URL参数中的语言设置
    query_params = st.query_params
    url_lang = query_params.get("lang", "zh")
    is_chinese = url_lang == "zh"
    
    doc_config = CONFIG.get("document_processing", {})
    
    # 初始化文档内容的会话状态
    if "document_text" not in st.session_state:
        st.session_state.document_text = ""
        
    if "document_name" not in st.session_state:
        st.session_state.document_name = ""
        
    if "document_enabled" not in st.session_state:
        st.session_state.document_enabled = False
        
    if "document_upload_expanded" not in st.session_state:
        st.session_state.document_upload_expanded = False
    
    # 美化上传控件样式
    st.markdown("""
    <style>
    /* 美化上传整体区域 */
    .document-upload-area {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 10px;
    }
    
    /* 紧凑的上传按钮样式 */
    .stFileUploader {
        width: auto !important;
    }
    
    /* 美化上传控件容器 */
    div[data-testid="stFileUploader"] > div:first-child {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 20px !important;
        background-color: rgba(49, 51, 63, 0.1);
        padding: 5px 15px !important;
        transition: all 0.3s ease;
        min-height: 45px !important;
        display: flex;
        align-items: center;
        width: auto !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* 鼠标悬停效果 */
    div[data-testid="stFileUploader"] > div:first-child:hover {
        border-color: #4f8bf9;
        background-color: rgba(79, 139, 249, 0.05);
        box-shadow: 0 2px 5px rgba(79, 139, 249, 0.2);
        transform: translateY(-1px);
    }
    
    /* 当拖拽文件时的效果 */
    div[data-testid="stFileUploader"] > div:first-child.drag-active {
        border-color: #4285f4;
        background-color: rgba(66, 133, 244, 0.1);
        box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.3);
        animation: pulse 1.5s infinite;
    }
    
    /* 调整上传按钮文本样式 */
    div[data-testid="stFileUploader"] label {
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        white-space: nowrap;
    }
    
    /* 调整文件名显示样式 */
    div[data-testid="stFileUploader"] p {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 0.85rem !important;
    }
    
    /* 调整文件清除按钮 */
    div[data-testid="stFileUploader"] button {
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
    }
    
    /* 美化控制按钮区域 */
    .doc-controls {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* 调整预览区域 */
    .document-preview {
        margin-top: 8px;
        margin-bottom: 8px;
    }
    
    /* 添加动画效果 */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(66, 133, 244, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(66, 133, 244, 0); }
        100% { box-shadow: 0 0 0 0 rgba(66, 133, 244, 0); }
    }
    
    /* 文档状态信息样式 */
    .doc-status {
        font-size: 0.85rem;
        padding: 5px 10px;
        border-radius: 15px;
        background-color: rgba(45, 55, 72, 0.1);
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-left: 10px;
    }
    
    /* 调整文档预览区样式 */
    div.streamlit-expanderHeader {
        font-size: 0.9rem !important;
        padding: 0.5rem !important;
    }
    
    /* 使文档预览区更紧凑 */
    div.streamlit-expanderContent {
        padding: 0.5rem !important;
    }
    
    /* 进度环样式 */
    .progress-circle-container {
        position: relative;
        width: 60px;
        height: 60px;
        margin: 10px auto;
    }
    
    .progress-circle {
        transform: rotate(-90deg);
        width: 60px;
        height: 60px;
    }
    
    .progress-circle-bg {
        fill: none;
        stroke: rgba(0, 0, 0, 0.1);
        stroke-width: 4;
    }
    
    .progress-circle-progress {
        fill: none;
        stroke: #4f8bf9;
        stroke-width: 4;
        stroke-linecap: round;
        transition: stroke-dashoffset 0.5s ease;
    }
    
    .progress-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 14px;
        font-weight: bold;
        color: #4f8bf9;
    }
    </style>
    
    <script>
    // 检测语言并修改文本
    document.addEventListener('DOMContentLoaded', function() {
        // 检查当前语言
        const isEnglish = window.location.href.indexOf('lang=en') > -1;
        const isChinese = !isEnglish;
        
        // 定义翻译文本
        const translations = {
            'Drag and drop file here': '拖拽文件到这里',
            'Limit 200MB per file': '每个文件限制200MB',
            'Browse files': '浏览文件',
            'Clear file': '清除文件'
        };
        
        // 创建DOM修改函数
        function updateUploadTexts() {
            // 寻找所有上传组件
            document.querySelectorAll('div[data-testid="stFileUploader"]').forEach(uploader => {
                
                // 寻找并修改拖放区文本
                const dragTexts = uploader.querySelectorAll('p');
                dragTexts.forEach(text => {
                    if (text.textContent.includes('Drag and drop')) {
                        text.textContent = isChinese ? translations['Drag and drop file here'] : 'Drag and drop file here';
                    }
                });
                
                // 寻找并修改文件大小限制文本
                const limitTexts = uploader.querySelectorAll('small, span.st-emotion-cache-16idsys, div.st-emotion-cache-16idsys');
                limitTexts.forEach(text => {
                    if (text.textContent.includes('per file') || text.textContent.includes('每个文件')) {
                        if (isChinese) {
                            text.textContent = text.textContent.replace('Limit 200MB per file', translations['Limit 200MB per file']);
                        } else {
                            text.textContent = text.textContent.replace('每个文件限制200MB', 'Limit 200MB per file');
                        }
                    }
                });
                
                // 寻找并修改按钮文本
                const buttons = uploader.querySelectorAll('button');
                buttons.forEach(button => {
                    if (button.textContent.includes('Browse') || button.textContent.includes('浏览')) {
                        button.textContent = isChinese ? translations['Browse files'] : 'Browse files';
                    }
                    if (button.textContent.includes('Clear') || button.textContent.includes('清除')) {
                        button.textContent = isChinese ? translations['Clear file'] : 'Clear file';
                    }
                });
            });
        }
        
        // 首次运行
        setTimeout(updateUploadTexts, 100);
        
        // 创建观察器以响应DOM变化
        const observer = new MutationObserver(function(mutations) {
            updateUploadTexts();
        });
        
        // 配置观察器选项
        observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            characterData: true
        });
        
        // 每秒运行一次，确保修改生效
        setInterval(updateUploadTexts, 1000);
    });
    </script>
    """, unsafe_allow_html=True)
    
    # 创建一个带样式的容器
    doc_container = st.container()
    with doc_container:
        # 保持简洁的单行布局
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # 上传文件控件
            upload_label = "📄 上传文档" if is_chinese else "📄 Upload Document"
            supported_formats = doc_config.get("supported_formats", ["pdf", "png", "jpg", "jpeg", "docx", "doc", "txt"])
            
            # 支持的格式信息
            format_text = f"支持: {', '.join(supported_formats)}" if is_chinese else f"Supported: {', '.join(supported_formats)}"
            
            # 更简洁的上传控件
            uploaded_file = st.file_uploader(
                upload_label, 
                type=supported_formats,
                key="main_document_uploader",
                help=format_text,
                label_visibility="collapsed" if st.session_state.document_name else "visible"
            )
            
            # 显示当前文档状态
            if st.session_state.document_text:
                file_name = st.session_state.document_name
                status_icon = "✅" if st.session_state.document_enabled else "⏸️"
                status_text = f"{status_icon} {file_name}"
                st.markdown(f'<div class="doc-status">{status_text}</div>', unsafe_allow_html=True)
        
        with col2:
            # 紧凑的控制按钮区域
            if st.session_state.document_text:
                st.markdown('<div class="doc-controls">', unsafe_allow_html=True)
                
                # 使用文档开关
                enable_doc_label = "启用" if is_chinese else "Enable"
                st.session_state.document_enabled = st.toggle(
                    enable_doc_label,
                    value=st.session_state.document_enabled,
                    key="main_doc_toggle",
                    help="使用文档内容增强AI回复" if is_chinese else "Use document context for AI responses",
                    label_visibility="collapsed"
                )
                
                # 查看预览按钮
                preview_label = "预览" if is_chinese else "Preview"
                if st.button(preview_label, key="preview_doc_btn", type="secondary", use_container_width=False):
                    st.session_state.document_upload_expanded = not st.session_state.document_upload_expanded
                
                # 清除文档按钮
                clear_label = "清除" if is_chinese else "Clear"
                if st.button(clear_label, key="main_clear_doc_btn", type="secondary", use_container_width=False):
                    st.session_state.document_text = ""
                    st.session_state.document_name = ""
                    st.session_state.document_enabled = False
                    st.session_state.document_upload_expanded = False
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理上传的文件
    if uploaded_file:
        # 只有当上传了新文件时才处理
        if st.session_state.document_name != uploaded_file.name:
            # 使用更紧凑的处理状态显示
            with st.status("处理文档中..." if is_chinese else "Processing document...", expanded=True) as status:
                try:
                    # 获取最大页数
                    max_pages = doc_config.get("max_pages", 10)
                    
                    # 创建进度条展示区域
                    progress_container = st.empty()
                    
                    # 创建圆环进度指示器
                    def show_progress_circle(percent, message):
                        circumference = 2 * 3.14 * 28  # 2π × 半径
                        offset = circumference - (percent / 100 * circumference)
                        progress_container.markdown(f"""
                        <div class="progress-circle-container">
                            <svg class="progress-circle" viewBox="0 0 60 60">
                                <circle class="progress-circle-bg" cx="30" cy="30" r="28" />
                                <circle class="progress-circle-progress" cx="30" cy="30" r="28" 
                                    stroke-dasharray="{circumference}" 
                                    stroke-dashoffset="{offset}" />
                            </svg>
                            <div class="progress-text">{percent}%</div>
                        </div>
                        <div style="text-align: center; margin-bottom: 10px;">{message}</div>
                        """, unsafe_allow_html=True)
                    
                    # 处理进度显示
                    show_progress_circle(10, "正在准备文档..." if is_chinese else "Preparing document...")
                    show_progress_circle(40, "正在提取文本..." if is_chinese else "Extracting text...")
                    
                    # 实际处理文档
                    document_text = document_processor.process_document(uploaded_file, max_pages)
                    
                    show_progress_circle(90, "整理文档内容..." if is_chinese else "Finalizing content...")
                    
                    # 更新会话状态
                    st.session_state.document_text = document_text
                    st.session_state.document_name = uploaded_file.name
                    st.session_state.document_enabled = True
                    st.session_state.document_upload_expanded = False
                    
                    # 完成进度
                    show_progress_circle(100, "处理完成！" if is_chinese else "Complete!")
                    
                    # 更新状态
                    status.update(label="文档处理完成！" if is_chinese else "Document processed!", state="complete", expanded=False)
                    
                except Exception as e:
                    error_msg = f"处理文档时出错: {str(e)}" if is_chinese else f"Error processing document: {str(e)}"
                    status.update(label=error_msg, state="error", expanded=True)
    
    # 有条件地显示文档预览
    if st.session_state.document_text and st.session_state.document_upload_expanded:
        with st.expander(f"📄 {st.session_state.document_name}", expanded=False):
            # 显示前500个字符
            preview_text = st.session_state.document_text[:500]
            if len(st.session_state.document_text) > 500:
                preview_text += "..."
            st.markdown(f'<div class="document-preview">{preview_text}</div>', unsafe_allow_html=True)
    
    # 如果启用了文档增强但没有显示预览，则显示小提示
    if st.session_state.document_enabled and st.session_state.document_text and not st.session_state.document_upload_expanded:
        file_name = st.session_state.document_name
        info_text = f"📄 使用「{file_name}」增强对话" if is_chinese else f"📄 Using '{file_name}' to enhance conversation"
        st.info(info_text)

# 页面配置
# 获取URL参数来确定页面标题
query_params = st.query_params
lang_param = query_params.get("lang", "zh")
is_english = lang_param == "en"

st.set_page_config(
    page_title="AI Chat Assistant" if is_english else "智能聊天助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"  # 默认展开侧边栏
)

# 初始化页面样式
inject_custom_css()

# 初始化LLM客户端 - 只创建一次实例
if "llm_client" not in st.session_state:
    try:
        st.session_state.llm_client = LLMClient()
    except Exception as e:
        st.error(f"初始化LLM客户端失败: {e}，请确保Ollama服务已启动")
        st.session_state.llm_client = LLMClient()  # 尝试再次创建，即使失败也能继续运行UI

# 初始化聊天历史管理
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}

# 初始化当前聊天ID
if "current_chat_id" not in st.session_state:
    # 创建新的聊天会话
    new_chat_id = str(uuid.uuid4())
    st.session_state.current_chat_id = new_chat_id
    st.session_state.chat_histories[new_chat_id] = {
        "title": f"新对话 {datetime.datetime.now().strftime('%m-%d %H:%M')}",
        "messages": [],
        "created_at": datetime.datetime.now(),
        "model_changes": []
    }

# 初始化语言设置
if "language" not in st.session_state:
    st.session_state.language = "zh"  # 默认中文

# 初始化生成状态标志，用于在生成期间禁用输入
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

# 不使用队列：我们采用前端冷却 + 后端校验的方式防止重复请求

# 获取当前聊天会话
current_chat = st.session_state.chat_histories[st.session_state.current_chat_id]

# 定义语言切换回调函数
def switch_language(lang):
    if st.session_state.language != lang:
        # 先更新URL参数，这样即使后面刷新也能保持正确的语言
        query_params = st.query_params
        query_params["lang"] = lang
        
        # 更新会话状态中的语言
        st.session_state.language = lang
        
        # 更新系统提示词以匹配新语言
        update_system_prompt_for_language(lang)
        
        # 确保聊天标题使用正确的语言
        ensure_chat_titles_use_current_language(st.session_state.chat_histories, lang)
        
        # 使用JavaScript重定向实现页面刷新，替代st.experimental_rerun()
        current_url = f"?lang={lang}"
        st.markdown(
            f"""
            <script>
                window.location.href = "{current_url}";
            </script>
            """,
            unsafe_allow_html=True
        )

# 页面标题和语言切换按钮
col1, col2 = st.columns([5, 1])
with col1:
    # 强制使用URL参数中的语言来显示标题，而不是依赖session_state
    # 这样可以确保在页面加载时标题显示正确
    current_lang = st.query_params.get("lang", "zh")
    title_text = "AI Chat Assistant" if current_lang == "en" else "智能聊天助手"
    
    st.markdown(
        f'<div class="app-title-wrapper">'
        f'<div class="app-title">'
        f'<span>🤖</span>'
        f'<h1>{title_text}</h1>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    # 直接使用columns并排显示按钮，不使用额外容器
    zh_col, en_col = st.columns(2, gap="small")
    
    with zh_col:
        zh_btn = st.button(
            "中", 
            key="zh_btn",
            on_click=switch_language,
            args=("zh",),
            type="primary" if st.session_state.language == "zh" else "secondary"
        )
    
    with en_col:
        en_btn = st.button(
            "EN", 
            key="en_btn",
            on_click=switch_language,
            args=("en",),
            type="primary" if st.session_state.language == "en" else "secondary"
        )

# 添加CSS美化语言切换按钮
st.markdown("""
<style>
/* 调整标题和语言切换按钮的布局 */
.app-title-wrapper {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    margin-bottom: 0;
    padding-left: 20px;
}

/* 响应式布局：确保语言切换按钮在不同屏幕尺寸下都能正常显示 */
@media (max-width: 768px) {
    .app-title-wrapper {
        flex-direction: column;
        align-items: flex-start;
        padding-left: 10px;
    }
}

/* 美化语言切换按钮 */
.stButton > button {
    border-radius: 20px !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    min-width: 60px !important; /* 确保按钮不会过于狭窄 */
    height: 36px !important; /* 固定高度，确保一致 */
    padding: 0 12px !important; /* 优化内边距 */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

/* 激活按钮样式 */
button[kind="primary"] {
    background-color: #4287f5 !important;
    color: white !important;
    border: 1px solid #3a75d8 !important;
}

/* 非激活按钮样式 */
button[kind="secondary"] {
    background-color: rgba(30, 34, 45, 0.5) !important;
    color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* 激活按钮悬停效果 */
button[kind="primary"]:hover {
    background-color: #3a75d8 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(66, 135, 245, 0.3) !important;
}

/* 非激活按钮悬停效果 */
button[kind="secondary"]:hover {
    background-color: rgba(66, 135, 245, 0.1) !important;
    border-color: #4287f5 !important;
    transform: translateY(-1px) !important;
}

/* 调整语言按钮容器的间距 */
[data-testid="stHorizontalBlock"] {
    gap: 8px !important; /* 按钮之间的间距 */
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}

/* 调整语言按钮所在列的样式 */
[data-testid="stColumn"] {
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}

/* 确保按钮容器不会出现滚动条 */
[data-testid="stVerticalBlock"] {
    overflow: visible !important;
    width: auto !important;
    height: auto !important;
    min-height: auto !important;
}

/* 确保按钮元素不会出现滚动条 */
.stButton {
    overflow: visible !important;
    height: auto !important;
    width: auto !important;
}

/* 调整语言按钮元素容器样式 */
.stElementContainer {
    overflow: visible !important;
    width: auto !important;
    height: auto !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* 确保按钮文本容器不会导致滚动 */
[data-testid="stMarkdownContainer"] {
    overflow: visible !important;
    width: auto !important;
    height: auto !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# 检查URL参数中的语言设置
query_params = st.query_params
if "lang" in query_params:
    lang = query_params["lang"]
    if lang in ["zh", "en"] and st.session_state.language != lang:
        # 更新会话状态中的语言
        st.session_state.language = lang
        
        # 更新系统提示词以匹配新语言
        update_system_prompt_for_language(lang)
        
        # 确保聊天标题使用正确的语言
        ensure_chat_titles_use_current_language(st.session_state.chat_histories, lang)
        
        # 这里不需要rerun，因为是在页面初始加载时检测的

# 侧边栏设置和聊天历史
settings = render_sidebar(current_chat)

# 显示聊天历史
display_chat_history(current_chat["messages"], current_chat.get("model_changes", []))

# 检查是否在主界面显示文档上传功能
doc_config = CONFIG.get("document_processing", {})
if doc_config.get("show_in_main_ui", True):
    # 渲染文档上传组件到主界面
    st.markdown("---")  # 添加分隔线
    render_document_upload()
    st.markdown("---")  # 添加分隔线

# 用户输入处理
query_params = st.query_params
url_lang = query_params.get("lang", "zh")
placeholder_text = "输入消息..." if url_lang == "zh" else "Type a message..."
# helper: 计算剩余冷却时间
# 输入框始终启用（用户可以输入），提交时使用前端冷却保护
def cooldown_chat_input(placeholder: str = "", cooldown_seconds: float = 1.0, key: str = "chat_input"):
    """基于时间戳的非阻塞冷却输入框（无线程），返回用户输入或 None。
    在冷却期间会显示提示但仍保持输入框可见。
    """
    import time as _time

    if 'last_submit_time' not in st.session_state:
        st.session_state['last_submit_time'] = 0.0

    elapsed = _time.time() - st.session_state.get('last_submit_time', 0.0)
    remaining = max(0.0, cooldown_seconds - elapsed)

    # 在冷却期显示提示信息（非阻塞）
    if remaining > 0:
        is_chinese = st.session_state.get('language', 'zh') == 'zh'
        msg = (f"请等待 {remaining:.1f} 秒..." if is_chinese else f"Please wait {remaining:.1f}s...")
        st.info(msg)

    # 始终渲染输入框（不禁用），用户可以继续编辑但提交会被后端校验
    user_input = st.chat_input(placeholder, key=key)

    if user_input:
        # 如果仍在冷却期，则提示并忽略本次提交（后端也有队列保护）
        if remaining > 0:
            is_chinese = st.session_state.get('language', 'zh') == 'zh'
            st.warning(("服务器繁忙，请稍等再发送" if is_chinese else "Please wait before sending again"))
            return None

        # 接受提交并更新时间戳
        st.session_state['last_submit_time'] = _time.time()
        return user_input

    return None


# 使用冷却输入框获取用户输入并直接调用处理函数
if prompt := cooldown_chat_input(placeholder_text, cooldown_seconds=1.0, key="chat_input"):
    # 如果是新聊天且没有标题，使用第一条消息作为标题
    if len(current_chat["messages"]) == 0:
        title = prompt[:15] + ("..." if len(prompt) > 15 else "")
        current_chat["title"] = title

    handle_user_input(
        prompt,
        current_chat["messages"],
        st.session_state.llm_client,
        settings
    )