# theme.py
import streamlit as st
from streamlit.components.v1 import html

def inject_custom_css():
    """注入自定义CSS和主题检测脚本"""
    st.markdown("""
    <style>
        /* 全局样式 */
        * {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            scroll-behavior: smooth !important;
        }
        
        /* 美化滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.1);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(110, 181, 255, 0.3);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(110, 181, 255, 0.5);
        }
        
        /* 主题基础变量 */
        :root {
            --primary: #4287f5;
            --primary-light: rgba(66, 135, 245, 0.1);
            --primary-dark: #3a75d8;
            --secondary: #7c5cff;
            --secondary-light: rgba(124, 92, 255, 0.1);
            --text: #f0f2f6;
            --background: #0e1117;
            --card-bg: rgba(27, 31, 40, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --shadow: rgba(0, 0, 0, 0.2);
            --radius: 12px;
            --spacing: 16px;
            --header-height: 85px;
            --content-width: 900px;
        }
        
        /* 页面背景 */
        .main .block-container {
            padding-top: 2rem !important;
            max-width: 900px;
            margin: 0 auto;
        }
        
        /* 标题样式 */
        .app-title-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
        }
        
        .app-title {
            display: flex;
            align-items: center;
            text-align: center;
            width: auto;
        }
        
        .app-title span {
            font-size: 32px;
            margin-right: 12px;
        }
        
        .app-title h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin: 0;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 15px rgba(124, 92, 255, 0.2);
            letter-spacing: 1px;
        }
        
        /* 聊天容器样式 */
        [data-testid="stVerticalBlock"] {
            scroll-behavior: smooth !important;
            overflow-y: auto !important;
            border-top-left-radius: var(--radius);
            border-top-right-radius: var(--radius);
            will-change: transform, scroll-position;
            transform: translateZ(0);
        }
        
        /* 聊天消息样式 */
        .stChatMessage {
            background-color: rgba(30, 34, 45, 0.5) !important;
            border-radius: 12px !important;
            padding: 0.8rem !important;
            margin-bottom: 1.2rem !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }
        
        .stChatMessage:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }
        
        /* 用户消息样式 */
        .stChatMessage[data-testid="user-message"] {
            background-color: rgba(66, 135, 245, 0.1) !important;
            border-color: rgba(66, 135, 245, 0.3) !important;
        }
        
        /* AI消息样式 */
        .stChatMessage[data-testid="assistant-message"] {
            background-color: rgba(124, 92, 255, 0.1) !important;
            border-color: rgba(124, 92, 255, 0.3) !important;
        }
        
        /* 聊天输入框样式优化 */
        .stChatInputContainer {
            padding: 0.75rem 1rem !important;
            background: linear-gradient(
                to top,
                rgba(30, 34, 45, 0.9) 0%,
                rgba(30, 34, 45, 0.7) 50%,
                rgba(30, 34, 45, 0.4) 100%
            ) !important;
            border-radius: 16px 16px 8px 8px !important;
            border: none !important;
            margin-top: 0.5rem !important;
            box-shadow: 
                0 -2px 6px rgba(0, 0, 0, 0.1),
                0 1px 12px rgba(0, 0, 0, 0.15) !important;
            backdrop-filter: blur(4px) !important;
            transition: all 0.3s ease !important;
            position: sticky !important;
            bottom: 0 !important;
            z-index: 100 !important;
        }

        /* 模型切换提示样式 */
        div[style*="text-align: center"][style*="border-top"] {
            background-color: rgba(30, 34, 45, 0.5) !important;
            border-radius: 8px !important;
            padding: 8px 0 !important;
            margin: 15px 0 !important;
        }
        
        /* 加载指示器 */
        .loading-container {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: calc(var(--spacing) * 0.8);
            color: rgba(255, 255, 255, 0.7);
            font-style: italic;
            background: linear-gradient(135deg, var(--primary-light), var(--secondary-light));
            border-radius: calc(var(--radius) * 0.8);
            border: 1px solid var(--border);
            box-shadow: 0 2px 8px var(--shadow);
        }
        
        /* 代码块样式 */
        pre {
            background-color: rgba(0, 0, 0, 0.2) !important;
            border-radius: 8px !important;
            padding: 1rem !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            overflow-x: auto !important;
            position: relative;
        }
        
        code {
            font-family: 'Fira Code', monospace !important;
            font-size: 0.9rem !important;
        }
        
        /* 修复复制按钮样式 */
        .stCodeBlock button {
            background-color: rgba(66, 135, 245, 0.2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            opacity: 0.8 !important;
            transition: all 0.2s ease !important;
            z-index: 10 !important;
            padding: 0.25rem 0.5rem !important;
        }
        
        .stCodeBlock button:hover {
            background-color: rgba(66, 135, 245, 0.4) !important;
            opacity: 1 !important;
            transform: scale(1.05) !important;
        }
        
        /* 隐藏不需要的UI元素，但保留侧边栏切换按钮 */
        footer[data-testid="stFooter"],
        [data-testid="stToolbar"] {
            display: none !important;
        }
        
        /* 只隐藏header中的标题和其他元素，保留侧边栏切换按钮 */
        header[data-testid="stHeader"] .main-header {
            display: none !important;
        }
        
        /* 确保侧边栏切换按钮可见 */
        [data-testid="stSidebarToggle"] {
            display: block !important;
            position: fixed !important;
            top: 20px !important;
            left: 20px !important;
            z-index: 9999 !important;
        }
        
        /* 侧边栏样式 */
        section[data-testid="stSidebar"] {
            background-color: rgba(30, 34, 45, 0.8) !important;
            border-right: 1px solid rgba(255,255,255,0.1) !important;
        }
        
        /* 侧边栏按钮样式 */
        .stButton > button {
            background-color: transparent !important;
            color: var(--text) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 8px !important;
            transition: all 0.3s !important;
            text-align: left !important;
            padding: 0.5rem 1rem !important;
        }
        
        /* 侧边栏按钮悬停样式 */
        .stButton > button:hover {
            background-color: rgba(110, 181, 255, 0.1) !important;
            border-color: var(--primary) !important;
        }
        
        /* 表单元素统一样式 */
        .stTextArea textarea,
        .stSelectbox > div > div,
        .stNumberInput > div > div > input {
            background-color: rgba(30, 34, 45, 0.5) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
        }
        
        /* 滑块样式 */
        .stSlider > div > div > div {
            background-color: var(--primary) !important;
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
        // 滚动到底部
        function scrollToBottom() {
            const chatContainer = document.querySelector('[data-testid="stVerticalBlock"]');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            window.scrollTo(0, document.body.scrollHeight);
        }
        
        // 监听DOM变化
        document.addEventListener('DOMContentLoaded', function() {
            // 隐藏不需要的UI元素
            function hideElements() {
                document.querySelectorAll('header, footer, [data-testid="stToolbar"]').forEach(el => {
                    if (el) el.style.display = 'none';
                });
            }
            
            // 初始执行
            hideElements();
            setTimeout(scrollToBottom, 100);
            
            // 注意：为了避免与聊天组件自己的自动滚动逻辑冲突，
            // 这里只在初始加载时做一次滚动，不再对所有 DOM 变动强制滚动。
            // 这样可以让 components/chat.py 中的增量渲染和用户交互检测接管自动滚动行为。
            // 如果需要更精细的行为，请在 components/chat.py 中实现。
            
            // 定期检查并隐藏元素
            setInterval(hideElements, 1000);
        });
    </script>
    """, unsafe_allow_html=True)