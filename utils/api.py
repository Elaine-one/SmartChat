import requests
import streamlit as st
import time
import logging
import os
import json
import traceback
import re
from utils.config import CONFIG

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMClient:
    """大语言模型API客户端"""
    
    def __init__(self):
        # 从配置文件读取设置
        api_config = CONFIG["api"]
        self.endpoint = api_config["endpoint"]
        self.max_retries = api_config["max_retries"]
        self.retry_delay = api_config["retry_delay"]
        self.base_timeout = api_config["timeout"]
        self.session = requests.Session()  # 使用会话保持连接
        self.available_models = self._get_available_models()
        logger.info(f"初始化LLM客户端，API端点: {self.endpoint}")
        logger.info(f"可用模型: {', '.join(self.available_models) if self.available_models else '无'}")

    def _get_available_models(self):
        """获取API可用的模型列表"""
        try:
            # 检查API类型
            api_type = self._detect_api_type()
            
            # 根据API类型获取模型列表
            if api_type == "ollama":
                # Ollama API使用单独的端点获取模型列表
                models_endpoint = self.endpoint.replace("/api/chat", "/api/tags")
                if models_endpoint == self.endpoint:
                    models_endpoint = "http://localhost:1314/api/tags"  # 使用1314端口
                
                try:
                    response = self.session.get(models_endpoint, timeout=self.base_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if "models" in data:
                            return [model['name'] for model in data['models']]
                except requests.exceptions.RequestException as e:
                    logger.warning(f"连接到Ollama API失败: {e}，使用配置中的模型列表")
                    # 返回固定的模型列表
                    return ["qwen2.5:3b", "deepseek-r1:8b", "llama3.1:latest"]
            
            # 默认返回config.json中定义的模型
            return list(CONFIG.get("models", {}).keys())
        except Exception as e:
            logger.warning(f"获取可用模型列表失败: {e}")
            # 确保返回当前已知可用的模型
            return ["qwen2.5:3b", "deepseek-r1:8b", "llama3.1:latest"]  # 返回固定模型列表作为备选

    def generate_response(self, messages, model="llama3", temperature=0.7, max_tokens=2048, stream=True):
        """生成AI回复，添加重试机制，支持流式输出"""
        # 记录请求开始
        logger.info(f"开始请求模型 {model}，消息数量: {len(messages)}")
        
        # 准备API密钥和请求头
        headers = {"Content-Type": "application/json"}
        
        # 检查API类型
        api_type = self._detect_api_type()
        logger.info(f"检测到API类型: {api_type}")
        
        # 验证模型是否可用，如果不可用则切换到默认模型
        model = self._validate_model(model)
        
        # 根据API类型准备请求数据
        if api_type == "ollama":
            data = self._prepare_ollama_request(messages, model, temperature, max_tokens, stream)
        elif api_type == "openai":
            data = self._prepare_openai_request(messages, model, temperature, max_tokens, stream)
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                logger.warning("使用OpenAI API但未设置OPENAI_API_KEY环境变量")
        else:
            # 默认格式
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
        
        # 记录详细的请求信息
        logger.info(f"API请求详情: endpoint={self.endpoint}, model={model}, stream={stream}, temperature={temperature}, max_tokens={max_tokens}")
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                # 计算当前尝试的超时时间（逐渐增加）
                current_timeout = self.base_timeout * (1 + attempt * 0.5)
                logger.info(f"尝试 #{attempt+1}/{self.max_retries}, 设置超时: {current_timeout}秒")
                
                # 发送请求
                # 使用 (connect_timeout, read_timeout) 方式，避免在长时间流式读取时无限阻塞
                connect_timeout = min(10, current_timeout)
                read_timeout = max(30, current_timeout)
                response = self.session.post(
                    self.endpoint,
                    headers=headers,
                    json=data,
                    timeout=(connect_timeout, read_timeout)
                )
                
                # 记录响应状态
                logger.info(f"API响应状态码: {response.status_code}")
                
                # 检查响应状态
                response.raise_for_status()
                
                # 如果是流式输出
                if stream:
                    # 返回完整回复字符串和错误信息
                    return self._handle_streaming_response(response, api_type), None
                else:
                    # 处理正常JSON响应
                    resp_data = response.json()
                    logger.info(f"收到JSON响应")
                    
                    # 根据不同API格式提取内容
                    content = self._extract_content_from_response(resp_data, api_type)
                    return content, None
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt+1}/{self.max_retries})")
                # 如果不是最后一次尝试，则等待后重试
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    time.sleep(sleep_time)
                else:
                    return "", "请求超时，服务器未响应"
            
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                logger.error(f"HTTP错误: {status_code}, {e}")
                
                # 记录响应内容以便调试
                try:
                    error_content = e.response.text
                    logger.error(f"错误响应内容: {error_content[:500]}")
                except:
                    logger.error("无法读取错误响应内容")
                
                # 根据状态码处理不同错误
                if status_code == 429:  # 过多请求
                    if attempt < self.max_retries - 1:
                        sleep_time = self.retry_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                    else:
                        return "", "服务器繁忙，请稍后再试"
                elif status_code == 401:  # 未授权
                    return "", "API密钥无效或不正确"
                elif status_code == 404:  # 资源不存在
                    return "", f"无法连接到API服务器，请确保Ollama服务已启动并在端口1314运行"
                else:
                    return "", f"HTTP错误 {status_code}: {e}"
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"连接错误: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"等待 {sleep_time}秒后重试...")
                    time.sleep(sleep_time)
                else:
                    # 尝试使用备用端点
                    backup_result = self._try_backup_endpoint(messages, model, temperature, max_tokens)
                    if backup_result:
                        return backup_result, None
                    return "", f"连接错误: 无法连接到API服务器 ({self.endpoint})，请检查网络或服务是否运行"
            
            except Exception as e:
                logger.error(f"请求异常: {e}", exc_info=True)
                return "", f"请求出错: {str(e)}"
    
    def _validate_model(self, model):
        """验证模型是否可用，不可用时返回备选模型"""
        if not self.available_models or model in self.available_models:
            return model
            
        # 如果指定的模型不可用，尝试找到匹配前缀的模型
        model_prefix = model.split(':')[0]
        for available_model in self.available_models:
            if available_model.startswith(model_prefix):
                logger.warning(f"指定的模型 {model} 不可用，自动切换到 {available_model}")
                return available_model
                
        # 如果找不到匹配的模型，返回第一个可用模型
        if self.available_models:
            logger.warning(f"指定的模型 {model} 不可用，自动切换到 {self.available_models[0]}")
            return self.available_models[0]
            
        # 如果没有可用模型，返回原始模型（可能会导致错误）
        return model
    
    def _try_backup_endpoint(self, messages, model, temperature, max_tokens):
        """尝试使用备用API端点"""
        try:
            logger.info("尝试使用备用API端点")
            # 构建简单的响应
            important_content = self._extract_important_content(messages[-1]["content"])
            return f'无法连接到API服务。您的问题是关于："{important_content}"。请检查API服务是否运行。'
        except Exception as e:
            logger.error(f"使用备用端点失败: {e}")
            return None
            
    def _extract_important_content(self, text):
        """从文本中提取重要内容"""
        # 如果文本很短，直接返回
        if len(text) < 100:
            return text
            
        # 否则提取前100个字符
        return text[:100] + "..."
    
    def generate_stream(self, messages, model="llama3", temperature=0.7, max_tokens=2048):
        """生成流式响应，直接返回生成器，供前端处理"""
        # 记录请求开始
        logger.info(f"开始流式请求模型 {model}，消息数量: {len(messages)}")
        
        # 准备API密钥和请求头
        headers = {"Content-Type": "application/json"}
        
        # 检查API类型
        api_type = self._detect_api_type()
        logger.info(f"检测到API类型: {api_type}")
        
        # 验证模型是否可用
        model = self._validate_model(model)
        
        # 记录详细日志
        logger.info(f"使用API端点: {self.endpoint}")
        
        # 根据API类型准备请求数据
        if api_type == "ollama":
            data = self._prepare_ollama_request(messages, model, temperature, max_tokens, True)
        elif api_type == "openai":
            data = self._prepare_openai_request(messages, model, temperature, max_tokens, True)
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        else:
            # 默认格式
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
        
        # 最大重试次数
        for attempt in range(self.max_retries):
            try:
                # 记录尝试信息
                logger.info(f"尝试 #{attempt+1}/{self.max_retries} 连接到 {self.endpoint}")
                
                # 计算当前尝试的超时时间
                current_timeout = self.base_timeout * (1 + attempt * 0.5)
                
                # 发送请求前先确认请求的信息
                logger.info(f"请求数据: model={model}, temperature={temperature}, max_tokens={max_tokens}")
                
                # 发送请求：使用 (connect_timeout, read_timeout) 元组以避免在流式读取时长时间阻塞
                # 对于流式请求，使用专门的可配置 read timeout（默认更保守的20秒）以便在服务返回非分块响应时能更快回退
                connect_timeout = min(10, current_timeout)
                stream_read_timeout = CONFIG.get("api", {}).get("stream_read_timeout", 20)
                # 保证 read_timeout 不小于当前计算值的一部分，以避免过早超时
                read_timeout = max(stream_read_timeout, current_timeout)
                response = self.session.post(
                    self.endpoint,
                    headers=headers,
                    json=data,
                    timeout=(connect_timeout, read_timeout),
                    stream=True
                )
                
                # 记录响应信息
                logger.info(f"收到响应，状态码: {response.status_code}")
                
                # 检查响应状态
                response.raise_for_status()
                
                # 获取流式响应的迭代器
                line_iterator = response.iter_lines()
                
                # 标记是否收到任何内容
                received_content = False

                # 处理流式响应（按行迭代）
                try:
                    for line in line_iterator:
                        if not line:
                            continue

                        # 解析数据行
                        if line.startswith(b'data: '):
                            data_text = line[6:].decode('utf-8', errors='replace')

                            if data_text.strip() == "[DONE]":
                                logger.info("收到流结束标记 [DONE]")
                                break

                            # 尝试解析JSON
                            try:
                                chunk = json.loads(data_text)

                                # 根据不同API类型提取内容
                                content = None
                                if api_type == "ollama":
                                    if "message" in chunk and "content" in chunk["message"]:
                                        content = chunk["message"]["content"]
                                    elif "response" in chunk:
                                        content = chunk["response"]
                                elif api_type == "openai":
                                    if "choices" in chunk and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                else:
                                    # 通用格式解析
                                    content = self._extract_stream_chunk(chunk)

                                if content:
                                    received_content = True
                                    yield content
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析失败: {data_text[:100]}")
                            except Exception as e:
                                logger.error(f"处理数据块时出错: {e}")
                                logger.error(traceback.format_exc())
                        else:
                            # 处理没有data:前缀的行
                            try:
                                line_text = line.decode('utf-8', errors='replace')

                                # 尝试解析非标准行为JSON
                                try:
                                    chunk = json.loads(line_text)
                                    content = self._extract_stream_chunk(chunk)
                                    if content:
                                        received_content = True
                                        yield content
                                except json.JSONDecodeError:
                                    # 不是JSON，可能是普通文本
                                    if line_text and not line_text.startswith("{") and not line_text.startswith("["):
                                        received_content = True
                                        yield line_text
                            except Exception as e:
                                logger.error(f"处理非标准行时出错: {e}")
                except requests.exceptions.ChunkedEncodingError as e:
                    # 在某些情况下，response.iter_lines() 可能抛出分块编码错误，记录并继续尝试回退方案
                    logger.warning(f"读取流式响应时出现分块编码错误: {e}")

                # 如果没有收到任何分块内容，尝试回退：读取完整响应体并解析JSON或作为纯文本返回
                if not received_content:
                    try:
                        raw = response.content
                        if raw:
                            text = raw.decode('utf-8', errors='replace')
                            # 尝试解析为JSON
                            try:
                                resp = json.loads(text)
                                content = self._extract_content_from_response(resp, api_type)
                                if content:
                                    yield content
                                else:
                                    logger.warning("回退解析：解析到JSON但无法提取内容，返回原始文本摘要")
                                    yield text
                            except json.JSONDecodeError:
                                # 不是JSON，直接作为纯文本返回（trim）
                                logger.info("回退解析：响应不是JSON，作为纯文本返回")
                                yield text
                        else:
                            logger.warning("从API接收到响应，但既没有流式分块也没有主体内容")
                            yield "未能从模型获取有效响应"
                    except Exception as e:
                        logger.error(f"回退解析响应时出错: {e}")
                        yield "处理响应时出错"
                
                # 成功完成生成，退出重试循环
                break
                
            except requests.exceptions.ConnectionError as e:
                logger.error(f"连接错误: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"等待 {sleep_time}秒后重试...")
                    time.sleep(sleep_time)
                else:
                    error_msg = f"无法连接到API服务器 ({self.endpoint})，请检查网络或服务是否运行"
                    logger.error(error_msg)
                    yield error_msg
            except Exception as e:
                logger.error(f"流式生成出错: {e}")
                logger.error(traceback.format_exc())
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    # 最后一次尝试失败，返回错误消息
                    error_msg = f"生成过程中出错: {str(e)}"
                    logger.error(error_msg)
                    yield error_msg
    
    def _detect_api_type(self):
        """检测API类型"""
        if "ollama" in self.endpoint:
            return "ollama"
        elif "openai.com" in self.endpoint:
            return "openai"
        else:
            return "unknown"
    
    def _prepare_ollama_request(self, messages, model, temperature, max_tokens, stream):
        """准备Ollama API请求格式"""
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
    
    def _prepare_openai_request(self, messages, model, temperature, max_tokens, stream):
        """准备OpenAI API请求格式"""
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
    
    def _extract_content_from_response(self, response_data, api_type):
        """从不同API响应格式中提取内容"""
        if api_type == "ollama":
            if "message" in response_data and "content" in response_data["message"]:
                return response_data["message"]["content"]
        elif api_type == "openai":
            if "choices" in response_data and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["message"]["content"]
        
        # 通用格式，尝试各种可能的路径
        if "content" in response_data:
            return response_data["content"]
        elif "message" in response_data and "content" in response_data["message"]:
            return response_data["message"]["content"]
        elif "choices" in response_data and len(response_data["choices"]) > 0:
            if "message" in response_data["choices"][0]:
                return response_data["choices"][0]["message"]["content"]
            elif "text" in response_data["choices"][0]:
                return response_data["choices"][0]["text"]
        
        logger.warning(f"无法从响应中提取内容")
        return ""
    
    def _extract_stream_chunk(self, chunk_data):
        """从流式响应数据块中提取内容"""
        # 尝试各种可能的路径提取内容
        if "content" in chunk_data:
            return chunk_data["content"]
        elif "message" in chunk_data and "content" in chunk_data["message"]:
            return chunk_data["message"]["content"]
        elif "choices" in chunk_data and len(chunk_data["choices"]) > 0:
            if "delta" in chunk_data["choices"][0] and "content" in chunk_data["choices"][0]["delta"]:
                return chunk_data["choices"][0]["delta"]["content"]
            elif "text" in chunk_data["choices"][0]:
                return chunk_data["choices"][0]["text"]
        elif "response" in chunk_data:
            return chunk_data["response"]
            
        return ""

    def _handle_streaming_response(self, response, api_type="unknown"):
        """处理流式响应"""
        full_response = ""
        
        # 记录调试信息
        logger.info("开始处理流式响应")
        
        # 直接在聊天界面创建一个助手消息框
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            
            # 设置初始"思考中"状态
            message_placeholder.markdown(
                """<div style="display: flex; align-items: center; color: #aaa;">
                <div class="typing-dots">
                <span>.</span><span>.</span><span>.</span>
                </div>思考中</div>""", 
                unsafe_allow_html=True
            )
            
            try:
                # 处理流式响应
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    # 解析数据行
                    if line.startswith(b'data: '):
                        data = line[6:].decode('utf-8', errors='replace')
                        
                        if data.strip() == "[DONE]":
                            break
                        
                        # 尝试解析JSON
                        try:
                            chunk = json.loads(data)
                            
                            # 根据不同API类型提取内容
                            content = None
                            if api_type == "ollama":
                                if "message" in chunk and "content" in chunk["message"]:
                                    content = chunk["message"]["content"]
                                elif "response" in chunk:
                                    content = chunk["response"]
                            elif api_type == "openai":
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                            else:
                                # 通用格式解析
                                content = self._extract_stream_chunk(chunk)
                            
                            if content:
                                full_response += content
                                # 显示光标效果
                                message_placeholder.markdown(full_response + "▌")
                        except json.JSONDecodeError:
                            logger.warning(f"JSON解析失败: {data[:100]}")
                        except Exception as e:
                            logger.error(f"处理数据块时出错: {e}")
                    else:
                        # 处理没有data:前缀的行
                        try:
                            line_text = line.decode('utf-8', errors='replace')
                            
                            # 尝试解析为JSON
                            try:
                                chunk = json.loads(line_text)
                                content = self._extract_stream_chunk(chunk)
                                if content:
                                    full_response += content
                                    message_placeholder.markdown(full_response + "▌")
                            except json.JSONDecodeError:
                                # 不是JSON，可能是普通文本
                                if line_text and not line_text.startswith("{") and not line_text.startswith("["):
                                    full_response += line_text
                                    message_placeholder.markdown(full_response + "▌")
                        except Exception as e:
                            logger.error(f"处理非标准行时出错: {e}")
                
                # 显示最终结果（无光标）
                if full_response:
                    message_placeholder.markdown(full_response)
                else:
                    # 如果没有收到任何响应，显示错误消息
                    message_placeholder.error("未收到有效的响应")
                    
            except Exception as e:
                # 显示错误信息
                logger.error(f"处理流式响应时出错: {e}", exc_info=True)
                message_placeholder.error(f"处理响应时出错: {str(e)}")
        
        return full_response 