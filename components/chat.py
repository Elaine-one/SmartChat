# chat.py
import streamlit as st
import json
import time
from utils.config import CONFIG
from utils.model_selector import model_selector
from utils.emotion_detector import emotion_detector
from utils.document_processor import document_processor

# 获取缓存配置
CACHE_CONFIG = CONFIG["cache"]

@st.cache_data(ttl=CACHE_CONFIG["ttl"], max_entries=CACHE_CONFIG["max_entries"])
def cached_generate_response(messages_json, model, temperature, max_tokens):
    """缓存模型响应，避免相同提问重复请求API"""
    # 获取LLM客户端
    llm_client = st.session_state.llm_client
    # 从JSON还原消息
    messages = json.loads(messages_json)
    # 调用API
    return llm_client.generate_response(
        messages, 
        model,
        temperature=temperature,
        max_tokens=max_tokens
    )

def display_chat_history(messages, model_changes=None):
    """显示聊天历史"""
    # 获取UI配置
    ui_config = CONFIG["ui"]
    max_messages = ui_config.get("max_message_display", 50)
    
    # 获取当前语言
    is_chinese = st.session_state.get("language", "zh") == "zh"
    
    # 如果消息过多，只显示最近的max_messages条
    display_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    # 简化的聊天历史显示，使用表情符号作为头像
    message_count = 0
    for msg in display_messages:
        # 跳过系统消息
        if msg["role"] == "system":
            continue
            
        # 直接显示消息内容
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])
        message_count += 1
        
        # 在每条助手消息后检查是否有相关的模型切换记录
        if msg["role"] == "assistant" and model_changes:
            # 计算此消息的索引位置
            current_index = message_count // 2  # 每对用户-助手消息算一组
            
            # 筛选出应该显示在这条消息后的所有模型切换记录
            relevant_changes = [change for change in model_changes 
                               if change.get("after_message_index", 0) == current_index]
            
            # 如果有相关的模型切换记录，显示它们
            for change in relevant_changes:
                # 获取当前语言
                is_chinese = st.session_state.get("language", "zh") == "zh"
                
                # 显示轻量级的模型切换提示
                model_change_text = f"模型已从 {change['from']} 切换为 {change['to']}" if is_chinese else f"Model changed from {change['from']} to {change['to']}"
                
                # 如果是自动切换的，显示不同的文本
                if change.get("auto", False):
                    model_change_text = f"系统自动将模型从 {change['from']} 切换为 {change['to']}，以更好地回答您的问题" if is_chinese else f"System automatically changed model from {change['from']} to {change['to']} to better answer your question"
                
                st.markdown(
                    f"""<div style="text-align: center; padding: 5px; 
                    color: rgba(255,255,255,0.5); font-size: 0.8rem; 
                    margin: 10px 0; font-style: italic; border-top: 1px solid rgba(255,255,255,0.1);
                    border-bottom: 1px solid rgba(255,255,255,0.1); padding: 8px 0;">
                    {model_change_text}
                    </div>""", 
                    unsafe_allow_html=True
                )
    
    # 优化自动滚动：定位聊天区域的可滚动父容器、使用防抖/节流，并在用户主动滚动时暂停自动滚动，减少卡顿
    if message_count > 0:
        st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)
        st.markdown(
            """
            <script>
            (function(){
                const CHAT_BOTTOM_ID = 'chat-bottom';
                let userInteracting = false;
                let interactionTimeout = null;
                let scrollContainer = null;
                let batchedScrollTimeout = null;
                const BATCHING_DELAY = 80; // ms

                function findScrollableAncestor(el){
                    let p = el.parentElement;
                    while(p){
                        const style = window.getComputedStyle(p);
                        const overflowY = style.overflowY;
                        if(overflowY === 'auto' || overflowY === 'scroll') return p;
                        p = p.parentElement;
                    }
                    return document.scrollingElement || document.documentElement;
                }

                function setUserInteracting(){
                    userInteracting = true;
                    if(interactionTimeout) clearTimeout(interactionTimeout);
                    interactionTimeout = setTimeout(()=>{ userInteracting = false; }, 1500);
                }

                // Fast immediate scroll to bottom (non-smooth) for high-frequency updates
                function immediateScroll(){
                    if(userInteracting) return;
                    const el = document.getElementById(CHAT_BOTTOM_ID);
                    if(!el) return;
                    try{
                        if(!scrollContainer) scrollContainer = findScrollableAncestor(el);
                        // Wait for next frame so layout/scrollHeight is updated
                        requestAnimationFrame(()=>{
                            try{
                                // If the scroll container is the document, use window.scrollTo as a reliable fallback
                                if(scrollContainer === document.scrollingElement || scrollContainer === document.documentElement){
                                    const h = Math.max(document.documentElement.scrollHeight || 0, document.body.scrollHeight || 0);
                                    window.scrollTo({ top: h, left: 0, behavior: 'auto' });
                                } else {
                                    scrollContainer.scrollTop = scrollContainer.scrollHeight;
                                }
                            }catch(e){
                                try{ el.scrollIntoView(false); }catch(e){}
                            }
                        });

                        // Fallback: schedule another immediate set after a short delay in case layout updates late
                        setTimeout(()=>{
                            try{
                                if(scrollContainer === document.scrollingElement || scrollContainer === document.documentElement){
                                    const h = Math.max(document.documentElement.scrollHeight || 0, document.body.scrollHeight || 0);
                                    window.scrollTo(0, h);
                                } else {
                                    scrollContainer.scrollTop = scrollContainer.scrollHeight;
                                }
                            }catch(e){/* ignore */}
                        }, 60);
                    }catch(e){
                        try{ el.scrollIntoView(false); }catch(e){}
                    }
                }

                // Batched scroll to avoid many layout/reflow calls during rapid appends
                function scheduleBatchedScroll(){
                    if(batchedScrollTimeout) return;
                    batchedScrollTimeout = setTimeout(()=>{
                        batchedScrollTimeout = null;
                        immediateScroll();
                    }, BATCHING_DELAY);
                }

                // Attach lightweight listeners to detect user intent to scroll
                document.addEventListener('wheel', setUserInteracting, {passive:true});
                document.addEventListener('touchstart', setUserInteracting, {passive:true});
                document.addEventListener('keydown', (e)=>{
                    if(['PageUp','PageDown','ArrowUp','ArrowDown','Home','End'].includes(e.key)) setUserInteracting();
                }, {passive:true});

                requestAnimationFrame(()=>{
                    const el = document.getElementById(CHAT_BOTTOM_ID);
                    if(!el) return;
                    scrollContainer = findScrollableAncestor(el);

                    try{
                        scrollContainer.addEventListener('scroll', setUserInteracting, {passive:true});
                    }catch(e){ /* ignore */ }

                    if(!window._chatObserverAdded){
                        const observer = new MutationObserver((mutations)=>{
                            // Count added nodes to decide immediate vs batched scroll
                            let added = 0;
                            for(const m of mutations){
                                if(m.addedNodes) added += m.addedNodes.length;
                                // small optimization: if any added node is our chat-bottom, prefer immediate
                                for(const node of m.addedNodes || []){
                                    if(node && node.querySelector && node.querySelector('#' + CHAT_BOTTOM_ID)){
                                        added += 1;
                                    }
                                }
                            }
                            if(added >= 6){
                                // many nodes added quickly — do an immediate fast scroll
                                immediateScroll();
                            } else {
                                // otherwise batch a single fast scroll shortly
                                scheduleBatchedScroll();
                            }
                        });
                        observer.observe(document.body, { childList: true, subtree: true });
                        window._chatObserverAdded = true;
                    }

                    // initial fast scroll when not interacting
                    immediateScroll();
                });
            })();
            </script>
            """,
            unsafe_allow_html=True
        )

def handle_user_input(prompt, messages, llm_client, settings):
    """处理用户输入并获取AI回复"""
    # 并发保护：如果当前已有生成进行中，先检查 watchdog 以避免挂起状态长期阻塞
    now = time.time()
    if st.session_state.get('is_generating', False):
        # watchdog 时间阈值（秒），超时后认为之前的生成已卡住并清理
        watchdog_timeout = float(CONFIG.get('conversation', {}).get('generating_watchdog_timeout', 30.0))
        wd_ts = st.session_state.get('_generating_watchdog_ts', None)
        if wd_ts and (now - wd_ts) > watchdog_timeout:
            # 清理挂起状态，让新的请求可以继续
            try:
                st.session_state['is_generating'] = False
                if '_generating_watchdog_ts' in st.session_state:
                    del st.session_state['_generating_watchdog_ts']
            except Exception:
                pass
        else:
            is_chinese = st.session_state.get('language', 'zh') == 'zh'
            warning_text = "正在生成，请稍候再试..." if is_chinese else "AI is still responding, please wait..."
            st.warning(warning_text)
            return

    # 标记正在生成，禁用输入（由主界面读取该状态）
    st.session_state['is_generating'] = True
    # watchdog 时间戳，用于检测卡住的生成并在外层恢复
    import time as _time
    st.session_state['_generating_watchdog_ts'] = _time.time()

    # 显示用户消息
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    # 添加到消息历史
    messages.append({"role": "user", "content": prompt})

    # 获取系统提示词
    system_prompt = settings["system_prompt"]
    
    # 获取当前URL参数中的语言设置，这更能反映用户的实际界面语言选择
    query_params = st.query_params
    url_lang = query_params.get("lang", "zh")
    
    # 确保系统提示词与当前语言一致
    is_chinese = url_lang == "zh"
    if is_chinese and "你是一个友好" not in system_prompt[:50]:
        system_prompt = """你是一个友好、乐于助人的AI助手。用自然的口语化风格交流，回答简洁清晰（1-3句话）。遵循规则：  
1. 积极共情，避免负面表达  
2. 不清楚时礼貌询问细节  
3. 拒绝回答敏感话题，引导至安全方向  
4. 适当使用表情符号（如😊）增加亲和力"""
    elif not is_chinese and "You are a friendly" not in system_prompt[:50]:
        system_prompt = """You are a friendly and helpful AI assistant. Use a natural, conversational style and keep answers concise (1-3 sentences). Follow these rules:
1. Be positive and empathetic, avoid negative expressions
2. Politely ask for clarification when unsure
3. Decline to answer sensitive topics and redirect to safe areas
4. Use appropriate emojis (like 😊) to add warmth"""
    
    # 情感分析 - 使用设置中的开关
    emotion = None
    if settings.get("emotion_detection", False):
        emotion = emotion_detector.detect_emotion(prompt)
    
    # 如果检测到情感，增强系统提示词
    emotional_response = ""
    if emotion:
        emotional_response = emotion_detector.get_emotional_response(emotion)
        if emotional_response and len(emotional_response) > 0:
            # 将情感回应添加到系统提示词
            if is_chinese:
                system_prompt = system_prompt + f"\n\n用户情绪似乎是{emotion}。在回复的开头加上以下情感回应：\n{emotional_response}"
            else:
                system_prompt = system_prompt + f"\n\nThe user's emotion seems to be {emotion}. Start your response with this emotional acknowledgement:\n{emotional_response}"
    
    # 强制发送冷却：防止用户过快连续提交（如果配置了冷却）
    cooldown = float(settings.get("cooldown_seconds", CONFIG.get("conversation", {}).get("cooldown_seconds", 1.0)))
    now = time.time()
    last_send = st.session_state.get("_last_send_ts", 0)
    if cooldown > 0 and now - last_send < cooldown:
        remaining = round(cooldown - (now - last_send), 2)
        is_chinese = st.session_state.get('language', 'zh') == 'zh'
        st.warning((f"请等待 {remaining} 秒后再发送..." if is_chinese else f"Please wait {remaining}s before sending another message..."))
        st.session_state['is_generating'] = False
        return
    # 更新最后发送时间戳
    st.session_state["_last_send_ts"] = now

    # 构造请求数据 - 使用侧边栏配置的上下文长度
    max_history = int(settings.get("max_history_messages", CONFIG.get("conversation", {}).get("max_history_messages", 10)))
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages += messages[-max_history:]
    
    # 如果开启了默认简洁回答选项并且未自定义系统提示，则在system_prompt中加入简洁约束
    concise_default = bool(settings.get("concise_by_default", CONFIG.get("conversation", {}).get("concise_by_default", True)))
    if concise_default and "简洁" not in system_prompt and "concise" not in system_prompt[:50]:
        if is_chinese:
            system_prompt = system_prompt + "\n\n请尽量回答简洁（1-3句），必要时给出要点。"
        else:
            system_prompt = system_prompt + "\n\nPlease keep answers concise (1-3 sentences) and provide key points when necessary."

    # 检查是否启用自动模型选择
    if settings.get("auto_model_select", False):
        # 使用智能模型选择器确定最佳模型
        recommended_model = model_selector.select_model(prompt, messages)
        
        # 如果推荐模型与当前不同，进行模型切换
        if recommended_model != settings["model"]:
            # 记录模型变更
            if "model_changes" not in st.session_state.chat_histories[st.session_state.current_chat_id]:
                st.session_state.chat_histories[st.session_state.current_chat_id]["model_changes"] = []
            
            # 计算当前消息索引
            assistant_messages = [i for i, msg in enumerate(messages) 
                                 if msg["role"] == "assistant"]
            last_assistant_index = len(assistant_messages) if assistant_messages else 0
            
            # 添加模型变更记录
            st.session_state.chat_histories[st.session_state.current_chat_id]["model_changes"].append({
                "from": settings["model"],
                "to": recommended_model,
                "after_message_index": last_assistant_index,
                "displayed": False,
                "auto": True
            })
            
            # 将模型更新为推荐模型
            settings["model"] = recommended_model
            
            # 更新会话状态中的模型
            st.session_state.model_choice = recommended_model
    
    # 检查是否启用了文档增强回复功能
    document_enabled = st.session_state.get("document_enabled", False)
    document_text = st.session_state.get("document_text", "")
    
    # 如果启用了文档增强且有文档内容
    if document_enabled and document_text:
        try:
            with st.chat_message("assistant", avatar="🤖"):
                # 创建文档增强提示
                doc_info = (
                    "我正在使用文档内容来回答您的问题..." if is_chinese else 
                    "I'm using the document content to answer your question..."
                )

                with st.spinner(doc_info):
                    # 使用文档处理器生成基于文档的回复（同步）
                    reply = document_processor.generate_document_enhanced_response(
                        prompt, 
                        document_text, 
                        settings["model"]
                    )

                    # 显示回复
                    st.markdown(reply)

            # 记录响应到聊天历史
            if reply:
                messages.append({"role": "assistant", "content": reply})
                # 设置生成后冷却时间，前端会依据该时间显示剩余等待
                try:
                    post_cd = float(settings.get("post_generate_cooldown_seconds", CONFIG.get("conversation", {}).get("post_generate_cooldown_seconds", 2.0)))
                    st.session_state['post_generate_cooldown_until'] = time.time() + post_cd
                except Exception:
                    pass
        finally:
            # 生成结束，恢复输入
            st.session_state['is_generating'] = False

        # 在文档回复模式下不需要调用普通API
        return
    
    # 使用流式输出API - 以增量形式渲染回复
    try:
        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            accumulated = ""

            # 选择流式生成器接口（如果可用）
            stream_generator = None
            # 优先使用显式的 generate_stream 方法（返回生成器）
            if hasattr(llm_client, 'generate_stream'):
                stream_generator = llm_client.generate_stream(
                    api_messages,
                    model=settings["model"],
                    temperature=settings["temperature"],
                    max_tokens=settings["max_tokens"]
                )
            else:
                # 否则尝试使用 generate_response 返回的可迭代对象
                result = llm_client.generate_response(
                    api_messages,
                    settings["model"],
                    temperature=settings["temperature"],
                    max_tokens=settings["max_tokens"],
                    stream=True
                )
                # 如果返回 (reply, error) 的形式，尝试取第一个可迭代对象
                if isinstance(result, tuple) and len(result) == 2:
                    stream_generator = result[0]
                else:
                    stream_generator = result

            # 如果stream_generator是字符串（非迭代器），直接显示
            if isinstance(stream_generator, str):
                accumulated = stream_generator
                placeholder.markdown(accumulated)
            else:
                # 迭代生成块，增量更新UI
                try:
                    for chunk in stream_generator:
                        # 有些实现可能yield None或空字符串，跳过
                        if not chunk:
                            continue
                        accumulated += chunk
                        placeholder.markdown(accumulated)
                        # 每收到一次 chunk 刷新 watchdog 时间戳，表示还在进行中
                        try:
                            st.session_state['_generating_watchdog_ts'] = _time.time()
                        except Exception:
                            pass
                except TypeError:
                    # 非可迭代返回，尝试直接显示其字符串表示
                    placeholder.markdown(str(stream_generator))

        # 将完整响应记录到历史（如果有内容）
        if accumulated:
            messages.append({"role": "assistant", "content": accumulated})
            # 记录生成后冷却，前端会依据该时间提示用户等待
            try:
                post_cd = float(settings.get("post_generate_cooldown_seconds", CONFIG.get("conversation", {}).get("post_generate_cooldown_seconds", 2.0)))
                st.session_state['post_generate_cooldown_until'] = time.time() + post_cd
            except Exception:
                pass
        # 确保在成功处理后清理生成状态，避免状态残留
        try:
            st.session_state['is_generating'] = False
        except Exception:
            pass

    except Exception as e:
        error_msg = f"流式生成出错: {e}"
        st.error(error_msg)
        # 出错时确保清理生成状态
        try:
            st.session_state['is_generating'] = False
        except Exception:
            pass

    finally:
        # 生成结束，恢复输入（再做一次保险性清理）
        try:
            st.session_state['is_generating'] = False
        except Exception:
            pass
        # 清理 watchdog
        if '_generating_watchdog_ts' in st.session_state:
            try:
                del st.session_state['_generating_watchdog_ts']
            except Exception:
                pass