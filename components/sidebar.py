import streamlit as st
import uuid
import datetime
import os
import sys
from utils.document_processor import document_processor
from utils.config import CONFIG
from utils.domain_experts import DomainExperts
from components.upload import sidebar_upload_ui

def render_sidebar(current_chat):
    """渲染侧边栏设置和聊天历史"""
    # 获取URL参数中的语言设置
    query_params = st.query_params
    url_lang = query_params.get("lang", "zh")
    is_chinese = url_lang == "zh"
    
    # 初始化聊天设置
    if "system_prompt" not in st.session_state:
        # 根据语言设置初始默认系统提示词
        if is_chinese:
            st.session_state.system_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力"""
        else:
            st.session_state.system_prompt = """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like ��) to add warmth"""
    
    with st.sidebar:
        # 获取当前语言
        is_chinese = st.session_state.language == "zh"

        # 渲染侧边栏上传控件（已抽离到 components/upload.py）
        sidebar_upload_ui()

        # ===== 新建聊天按钮 =====
        new_chat_text = "➕ 新建聊天" if is_chinese else "➕ New Chat"
        if st.button(new_chat_text, type="primary", use_container_width=True):
            # 创建新的聊天会话
            new_chat_id = str(uuid.uuid4())
            st.session_state.current_chat_id = new_chat_id
            # 使用当前语言创建标题
            new_title = "新对话" if is_chinese else "New Chat"
            timestamp = datetime.datetime.now().strftime('%m-%d %H:%M')
            st.session_state.chat_histories[new_chat_id] = {
                "title": f"{new_title} {timestamp}",
                "messages": [],
                "created_at": datetime.datetime.now(),
                "model_changes": []
            }
            st.rerun()
        
        # 聊天历史列表 - 移除标题
        # 按创建时间倒序排列聊天历史
        sorted_chats = sorted(
            st.session_state.chat_histories.items(),
            key=lambda x: x[1].get("created_at", datetime.datetime.now()),
            reverse=True
        )
        
        # 显示聊天历史列表
        for chat_id, chat in sorted_chats:
            # 获取聊天标题 - 如果是默认标题，则使用第一条用户消息作为标题
            title = chat.get("title", "新对话" if is_chinese else "New Chat")
            if (title == "新对话" or title == "New Chat") and chat["messages"]:
                for msg in chat["messages"]:
                    if msg["role"] == "user":
                        # 使用第一条用户消息作为标题
                        title = msg["content"][:15] + ("..." if len(msg["content"]) > 15 else "")
                        break
            
            # 如果是当前聊天，高亮显示
            if chat_id == st.session_state.current_chat_id:
                st.markdown(f"**🔹 {title}**")
                
                # 显示当前聊天的所有用户问题
                if chat["messages"]:
                    messages_label = "聊天记录" if is_chinese else "Chat History"
                    with st.expander(messages_label, expanded=True):
                        for i, msg in enumerate(chat["messages"]):
                            if msg["role"] == "user":
                                # 截取前30个字符，如果超过则添加省略号
                                question = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                                st.markdown(f"- {question}")
            else:
                # 创建一个可折叠的聊天历史项
                with st.expander(f"🔸 {title}", expanded=False):
                    # 显示该聊天的所有用户问题
                    if chat["messages"]:
                        for i, msg in enumerate(chat["messages"]):
                            if msg["role"] == "user":
                                # 截取前30个字符，如果超过则添加省略号
                                question = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                                st.markdown(f"- {question}")
                    
                    # 添加切换按钮
                    if st.button("切换", key=f"switch_{chat_id}"):
                        st.session_state.current_chat_id = chat_id
        
        # 分隔线
        st.divider()
        
        # 设置部分
        settings_title = "设置" if is_chinese else "Settings"
        st.header(settings_title)
        
        # 使用缓存避免重置选择
        if "model_choice" not in st.session_state:
            # 设置默认模型为qwen2.5:3b
            st.session_state.model_choice = "qwen2.5:3b"
        if "system_prompt" not in st.session_state:
            # 根据语言设置默认系统提示词
            if is_chinese:
                st.session_state.system_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力"""
            else:
                st.session_state.system_prompt = """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
        else:
            # 当语言切换时，更新系统提示词
            if is_chinese and "你是一个友好" not in st.session_state.system_prompt:
                st.session_state.system_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力"""
            elif not is_chinese and "You are a friendly" not in st.session_state.system_prompt:
                st.session_state.system_prompt = """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
        if "temperature" not in st.session_state:
            st.session_state.temperature = 0.7
        if "max_tokens" not in st.session_state:
            st.session_state.max_tokens = 2048
        if "auto_model_select" not in st.session_state:
            st.session_state.auto_model_select = CONFIG.get("auto_model_select", True)
        if "emotion_detection" not in st.session_state:
            st.session_state.emotion_detection = CONFIG.get("emotion_detection", {}).get("enabled", True)
        if "domain_expert" not in st.session_state:
            st.session_state.domain_expert = "none"
            
        # 获取领域专家配置
        try:
            experts = DomainExperts.get_experts(language="zh" if is_chinese else "en")
            expert_options = ["none"] + list(experts.keys())
            expert_display_names = {
                "none": "通用助手" if is_chinese else "General Assistant"
            }
            
            # 添加专家的显示名称
            for key, expert in experts.items():
                expert_display_names[key] = f"{expert['icon']} {expert['name']}"
                
            # 当语言切换时，需要检查当前domain_expert是否在新语言的专家列表中
            # 如果不在，则重置为"none"
            if st.session_state.domain_expert != "none" and st.session_state.domain_expert not in experts:
                st.session_state.domain_expert = "none"
        except Exception as e:
            # 如果获取专家列表出错，使用默认值
            import logging
            logging.error(f"Error loading experts: {e}")
            experts = {}
            expert_options = ["none"]
            expert_display_names = {
                "none": "通用助手" if is_chinese else "General Assistant"
            }
            st.session_state.domain_expert = "none"
            
        # 定义专家模式切换回调函数
        def on_expert_mode_change():
            # 只有当选择真正变化时才执行
            if "domain_expert_select" in st.session_state:
                selected_domain = st.session_state.domain_expert_select
                if selected_domain != st.session_state.domain_expert:
                    # 更新当前专家模式
                    st.session_state.domain_expert = selected_domain
                    
                    # 更新系统提示词
                    if selected_domain != "none":
                        # 应用专家系统提示词
                        try:
                            expert = experts[selected_domain]
                            st.session_state.system_prompt = expert["system_prompt"]
                            st.session_state.system_prompt_input = expert["system_prompt"]
                        except KeyError:
                            # 如果找不到对应的专家，重置为none
                            st.session_state.domain_expert = "none"
                            default_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力""" if is_chinese else """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
                            st.session_state.system_prompt = default_prompt
                            st.session_state.system_prompt_input = default_prompt
                        else:
                            # 恢复默认系统提示词
                            default_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力""" if is_chinese else """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
                            st.session_state.system_prompt = default_prompt
                            st.session_state.system_prompt_input = default_prompt
        
        # 专家模式选择下拉框 - 使用回调函数立即响应变化
        domain_label = "专家模式" if is_chinese else "Expert Mode"
        
        # 如果当前选中的专家不在选项列表中，默认显示"none"
        default_index = 0  # "none"的索引
        if st.session_state.domain_expert in expert_options:
            default_index = expert_options.index(st.session_state.domain_expert)
        
        selected_domain = st.selectbox(
            domain_label,
            options=expert_options,
            format_func=lambda x: expert_display_names[x],
            index=default_index,
            key="domain_expert_select",
            on_change=on_expert_mode_change
        )
        
        # 显示当前专家描述（如果有）
        if st.session_state.domain_expert != "none":
            try:
                # 确保专家在当前语言的列表中
                if st.session_state.domain_expert in experts:
                    expert = experts[st.session_state.domain_expert]
                    st.info(expert["description"])
                else:
                    # 如果专家不在当前语言列表中，不显示任何描述
                    pass
            except Exception as e:
                # 如果发生任何错误，记录并忽略
                import logging
                logging.warning(f"Error displaying expert description: {e}")
        
        # 模型选择回调函数
        def on_model_change():
            # 只有当模型真正改变时才记录
            if st.session_state.model_choice != st.session_state.model_select:
                # 添加新的模型切换记录
                if "model_changes" not in current_chat:
                    current_chat["model_changes"] = []
                
                # 计算当前消息索引 - 找到最后一条助手消息的索引
                assistant_messages = [i for i, msg in enumerate(current_chat["messages"]) 
                                     if msg["role"] == "assistant"]
                last_assistant_index = len(assistant_messages) if assistant_messages else 0
                
                current_chat["model_changes"].append({
                    "from": st.session_state.model_choice,
                    "to": st.session_state.model_select,
                    "after_message_index": last_assistant_index,  # 记录应该在哪条消息后显示
                    "displayed": False  # 标记为未显示
                })
                # 更新当前模型选择
                st.session_state.model_choice = st.session_state.model_select
        
        # 模型选择下拉框
        model_label = "选择模型" if is_chinese else "Select Model"
        available_models = ["qwen2.5:3b", "deepseek-r1:8b", "llama3.1:latest"]
        # 确保当前选择的模型在可用列表中，否则默认使用第一个
        if st.session_state.model_choice not in available_models:
            st.session_state.model_choice = available_models[0]
        
        st.selectbox(
            model_label,
            available_models,
            index=available_models.index(st.session_state.model_choice),
            key="model_select",
            on_change=on_model_change
        )
        
        # 系统提示词 - 修复空标签警告
        def on_prompt_change():
            st.session_state.system_prompt = st.session_state.system_prompt_input

        # 创建一个固定高度的文本区域
        prompt_title = "系统提示词" if is_chinese else "System Prompt"
        st.markdown(f"### {prompt_title}")
        # 默认只显示3行
        fixed_height = 150  # 大约3行的高度

        st.text_area(
            label=prompt_title,  # 使用标题作为标签
            value=st.session_state.system_prompt,
            key="system_prompt_input",
            on_change=on_prompt_change,
            height=fixed_height,
            label_visibility="collapsed"  # 隐藏标签但保持可访问性
        )
        
        # 温度参数
        temp_label = "温度 (创造性)" if is_chinese else "Temperature (Creativity)"
        temp_help = "较低的值使回答更确定，较高的值使回答更多样化" if is_chinese else "Lower values make responses more deterministic, higher values more diverse"
        st.slider(
            temp_label, 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.temperature,
            step=0.1,
            format="%.1f",
            help=temp_help,
            key="temperature"
        )
        
        # 最大生成长度
        tokens_label = "最大生成长度" if is_chinese else "Max Response Length"
        tokens_help = "限制AI回复的最大长度" if is_chinese else "Limit the maximum length of AI responses"
        st.number_input(
            tokens_label,
            min_value=256,
            max_value=4096,
            value=st.session_state.max_tokens,
            step=256,
            help=tokens_help,
            key="max_tokens"
        )
        
        # 添加智能功能设置区域
        st.subheader("🧠 智能功能" if is_chinese else "🧠 Smart Features")
        
        # 自动模型选择
        auto_model_label = "自动模型选择" if is_chinese else "Auto Model Selection"
        auto_model_help = "根据问题类型自动选择最合适的模型" if is_chinese else "Automatically select the best model for each question type"
        st.checkbox(
            auto_model_label,
            value=st.session_state.auto_model_select,
            help=auto_model_help,
            key="auto_model_select"
        )
        
        # 情感响应功能
        emotion_label = "情感响应" if is_chinese else "Emotional Response"
        emotion_help = "识别用户情绪并给予相应回应" if is_chinese else "Detect user's emotion and provide appropriate response"
        st.checkbox(
            emotion_label,
            value=st.session_state.emotion_detection,
            help=emotion_help,
            key="emotion_detection"
        )
        
        # 模型信息
        model_info = {
            "qwen2.5:3b": "通义千问2.5-3B模型，适合一般对话和简单问答。" if is_chinese else "Qwen 2.5-3B model, suitable for general conversation and simple Q&A.",
            "deepseek-r1:8b": "深度求索8B模型，擅长中文理解和生成。" if is_chinese else "DeepSeek 8B model, excels at Chinese understanding and generation.",
            "llama3.1:latest": "Meta最新Llama 3.1模型，多语言能力强，知识面广。" if is_chinese else "Meta's latest Llama 3.1 model, strong multilingual capabilities and broad knowledge."
        }
        
        # 添加模型信息显示
        st.divider()
        st.caption(f"当前模型: {st.session_state.model_choice}")
        
        # 根据不同模型显示不同的能力说明
        if st.session_state.model_choice in model_info:
            st.info(model_info[st.session_state.model_choice])
        
        # 会话相关设置使用配置文件中的默认值（不在UI中显示）
        conversation_cfg = CONFIG.get("conversation", {})
        max_history = int(conversation_cfg.get("max_history_messages", 10))
        cooldown = float(conversation_cfg.get("cooldown_seconds", 1.0))
        concise = bool(conversation_cfg.get("concise_by_default", True))

        # 返回设置
        return {
            "model": st.session_state.model_choice,
            "system_prompt": st.session_state.system_prompt,
            "temperature": st.session_state.temperature,
            "max_tokens": st.session_state.max_tokens,
            "auto_model_select": st.session_state.auto_model_select,
            "emotion_detection": st.session_state.emotion_detection,
            "domain_expert": st.session_state.domain_expert,
            # conversation settings
            "max_history_messages": int(max_history),
            "cooldown_seconds": float(cooldown),
            "concise_by_default": bool(concise)
        } 

def update_system_prompt_for_language(language="zh"):
    """根据当前语言更新系统提示词"""
    # 获取URL参数中的语言设置，优先使用URL参数
    query_params = st.query_params
    url_lang = query_params.get("lang", language)
    
    # 确定是否使用中文
    is_chinese = url_lang == "zh"
    
    # 检查是否使用的是默认系统提示词，如果是，则更新为对应语言的默认提示词
    # 如果使用的是自定义系统提示词（如专家提示词），则不进行更改
    if "system_prompt" in st.session_state:
        current_prompt = st.session_state.system_prompt
        
        # 检测是否为默认中文提示词
        is_default_chinese = "你是一个友好、乐于助人的AI助手" in current_prompt[:50]
        is_default_english = "You are a friendly and helpful AI assistant" in current_prompt[:50]
        
        # 如果是默认提示词，更新为当前语言的默认提示词
        if is_default_chinese or is_default_english:
            if is_chinese and not is_default_chinese:
                # 切换到中文
                st.session_state.system_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力"""
                if "system_prompt_input" in st.session_state:
                    st.session_state.system_prompt_input = st.session_state.system_prompt
            elif not is_chinese and not is_default_english:
                # 切换到英文
                st.session_state.system_prompt = """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
                if "system_prompt_input" in st.session_state:
                    st.session_state.system_prompt_input = st.session_state.system_prompt 