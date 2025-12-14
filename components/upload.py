import streamlit as st
from utils.config import CONFIG
from utils.document_processor import document_processor

def sidebar_upload_ui():
    """在侧边栏渲染上传控件并处理上传逻辑，返回None。"""
    # 获取当前语言
    is_chinese = st.session_state.get("language", "zh") == "zh"

    st.markdown("""
    <style>
    .sidebar-upload-card {
        border: 1.5px solid #e0e0e0;
        border-radius: 12px;
        background: rgba(245,247,250,0.85);
        padding: 18px 12px 10px 12px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .sidebar-upload-title {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 8px;
        color: #4f8bf9;
        letter-spacing: 1px;
    }
    .sidebar-upload-status {
        font-size: 0.85rem;
        color: #666;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-upload-card">', unsafe_allow_html=True)
    upload_title = '上传文档' if is_chinese else 'Upload Document'
    st.markdown(f'<div class="sidebar-upload-title">📄 {upload_title}</div>', unsafe_allow_html=True)

    supported_formats = CONFIG.get("document_processing", {}).get("supported_formats", ["pdf", "png", "jpg", "jpeg", "docx", "doc", "txt"]) 
    format_text = f"支持: {', '.join(supported_formats)}" if is_chinese else f"Supported: {', '.join(supported_formats)}"
    uploaded_file = st.file_uploader(
        label=" ",
        type=supported_formats,
        key="sidebar_document_uploader",
        help=format_text,
        label_visibility="collapsed"
    )

    # 状态与操作
    if st.session_state.get("document_text"):
        file_name = st.session_state.get("document_name", "")
        status_icon = "✅" if st.session_state.get("document_enabled") else "⏸️"
        st.markdown(f'<div class="sidebar-upload-status">{status_icon} {file_name}</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1,1])
        with col1:
            enable_doc_label = "启用" if is_chinese else "Enable"
            st.session_state.document_enabled = st.toggle(
                enable_doc_label,
                value=st.session_state.document_enabled,
                key="sidebar_doc_toggle",
                help="使用文档内容增强AI回复" if is_chinese else "Use document context for AI responses",
                label_visibility="collapsed"
            )
        with col2:
            clear_label = "清除" if is_chinese else "Clear"
            if st.button(clear_label, key="sidebar_clear_doc_btn", use_container_width=True):
                st.session_state.document_text = ""
                st.session_state.document_name = ""
                st.session_state.document_enabled = False
                st.session_state.document_upload_expanded = False
                st.rerun()

    # 处理上传的文件
    if uploaded_file:
        if st.session_state.get("document_name") != uploaded_file.name:
            with st.spinner("处理文档中..." if is_chinese else "Processing document..."):
                try:
                    max_pages = CONFIG.get("document_processing", {}).get("max_pages", 10)
                    document_text = document_processor.process_document(uploaded_file, max_pages)
                    st.session_state.document_text = document_text
                    st.session_state.document_name = uploaded_file.name
                    st.session_state.document_enabled = True
                    st.session_state.document_upload_expanded = False
                    st.success("文档处理完成！" if is_chinese else "Document processed!")
                except Exception as e:
                    error_msg = f"处理文档时出错: {str(e)}" if is_chinese else f"Error processing document: {str(e)}"
                    st.error(error_msg)

    st.markdown('</div>', unsafe_allow_html=True)

    return None
