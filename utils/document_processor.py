import os
import base64
import hashlib
import streamlit as st
import requests
import sys
import tempfile
from utils.config import CONFIG

# 确保临时目录存在
def ensure_temp_dir():
    """确保临时目录存在"""
    temp_dir = "./temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

class DocumentProcessor:
    """文档处理类，用于处理上传的文档（Word/PDF/图片）"""
    
    def __init__(self):
        """初始化文档处理器"""
        self.temp_dir = ensure_temp_dir()
        self.vision_model = "granite3.2-vision:latest"  # 使用官方提供的视觉模型
        self.ollama_api = "http://localhost:1314/api/generate" 
        self.cache = {}  # 简单的缓存字典
        self.cache_size = CONFIG.get("document_processing", {}).get("cache_size", 10)
        
    def process_document(self, uploaded_file, max_pages=10):
        """处理上传的文档（支持Word/PDF/图片）"""
        if uploaded_file is None:
            return ""
            
        # 计算文件哈希值用于缓存
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # 检查缓存中是否已有结果
        if file_hash in self.cache:
            return self.cache[file_hash]
            
        # 没有缓存，处理文档
        result = self._process_document(file_hash, uploaded_file, max_pages)
        
        # 更新缓存
        self.cache[file_hash] = result
        
        # 如果缓存太大，移除最早添加的项
        if len(self.cache) > self.cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            
        return result
    
    def _process_document(self, file_hash, uploaded_file, max_pages):
        """处理文档的内部函数"""
        # 保存临时文件
        temp_path = os.path.join(self.temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 获取文件扩展名（小写）
        file_ext = os.path.splitext(uploaded_file.name.lower())[1]
        
        # 根据文件类型处理
        if file_ext in ['.docx', '.doc']:
            # Word文档处理
            return self._process_word_document(temp_path)
            
        elif file_ext == '.pdf':
            # PDF处理
            return self._process_pdf_document(temp_path, max_pages)
            
        elif file_ext in ['.txt', '.md', '.csv']:
            # 文本文件直接读取
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(temp_path, 'r', encoding='gbk') as f:
                        return f.read()
                except:
                    # 如果还是失败，将文件作为图像处理
                    return self._process_images([temp_path])
        else:
            # 图片和其他文件作为图像处理
            return self._process_images([temp_path])
    
    def _process_word_document(self, doc_path):
        """处理Word文档并提取文本"""
        # 获取URL参数中的语言设置
        query_params = st.query_params
        url_lang = query_params.get("lang", "zh")
        is_chinese = url_lang == "zh"
        
        try:
            # 尝试导入docx库
            try:
                import docx
                document = docx.Document(doc_path)
                # 提取文本
                text = "\n\n".join([para.text for para in document.paragraphs if para.text.strip()])
                if text:
                    return text
            except ImportError:
                # 如果docx库不可用，使用图像处理方式
                st.info("使用图像处理方式提取Word文档内容..." if is_chinese else 
                       "Using image-based processing to extract Word document content...")
                return self._process_images([doc_path])
            except Exception as e:
                st.warning(f"使用python-docx提取文本失败，将尝试图像处理" if is_chinese else 
                          f"Failed to extract text with python-docx, trying image processing")
            
            # 如果文本提取失败，使用图像处理
            return self._process_images([doc_path])
                
        except Exception as e:
            error_msg = f"处理Word文档时出错: {str(e)}" if is_chinese else f"Error processing Word document: {str(e)}"
            st.error(error_msg)
            return error_msg
    
    def _process_pdf_document(self, pdf_path, max_pages):
        """处理PDF文档并提取文本"""
        # 获取URL参数中的语言设置
        query_params = st.query_params
        url_lang = query_params.get("lang", "zh")
        is_chinese = url_lang == "zh"
        
        try:
            # 尝试使用pdf2image提取图像
            try:
                from pdf2image import convert_from_path
                
                # 转换PDF为图片
                images = convert_from_path(
                    pdf_path,
                    first_page=1,
                    last_page=max_pages
                )
                
                # 成功转换
                image_paths = []
                
                # 保存转换后的图片
                for i, img in enumerate(images):
                    img_path = os.path.join(self.temp_dir, f"page_{i}_{os.path.basename(pdf_path)}.jpg")
                    img.save(img_path, "JPEG")
                    image_paths.append(img_path)
                
                # 处理所有图片
                return self._process_images(image_paths)
                
            except ImportError:
                # 如果pdf2image不可用，尝试使用PyPDF2
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(pdf_path)
                    text = ""
                    for i, page in enumerate(reader.pages):
                        if i >= max_pages:
                            break
                        text += page.extract_text() + "\n\n"
                    
                    if text.strip():
                        return text
                    else:
                        # 如果没有提取到文本，可能是图像PDF
                        return self._process_images([pdf_path])
                        
                except ImportError:
                    # 如果两个库都不可用，使用图像处理
                    st.warning("PDF处理库未安装，使用图像处理方式提取PDF内容" if is_chinese else 
                              "PDF processing libraries not installed, using image-based processing")
                    return self._process_images([pdf_path])
                    
        except Exception as e:
            error_msg = f"处理PDF文档时出错: {str(e)}" if is_chinese else f"Error processing PDF document: {str(e)}"
            st.error(error_msg)
            return error_msg
    
    def _process_images(self, image_paths):
        """处理图片列表并提取文本内容"""
        # 获取URL参数中的语言设置
        query_params = st.query_params
        url_lang = query_params.get("lang", "zh")
        is_chinese = url_lang == "zh"
        
        parsed_text = []
        
        total_images = len(image_paths)
        
        for i, img_path in enumerate(image_paths):
            try:
                # 转换图片为base64
                with open(img_path, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode()
                
                # 构建适合当前语言的提示词
                prompt = "提取此文档中的所有文字内容，保持原格式" if is_chinese else "Extract all text content from this document, maintaining the original format"
                
                # 调用模型解析
                response = requests.post(
                    self.ollama_api,
                    json={
                        "model": self.vision_model,
                        "prompt": prompt,
                        "images": [img_base64],
                        "stream": False
                    },
                    timeout=60
                )
                
                # 检查响应状态
                if response.status_code == 200:
                    result = response.json()
                    parsed_text.append(result.get("response", ""))
                else:
                    error_msg = f"API请求失败: HTTP {response.status_code}" if is_chinese else f"API request failed: HTTP {response.status_code}"
                    parsed_text.append(error_msg)
                    
            except Exception as e:
                error_msg = f"处理图片时出错: {str(e)}" if is_chinese else f"Error processing image: {str(e)}"
                parsed_text.append(error_msg)
                
        return "\n\n".join(parsed_text)
    
    def generate_document_enhanced_response(self, prompt, document_text, model):
        """基于文档内容生成增强回复"""
        # 获取URL参数中的语言设置
        query_params = st.query_params
        url_lang = query_params.get("lang", "zh")
        is_chinese = url_lang == "zh"
        
        # 构造合适的提示词
        context_prompt = (
            f"根据以下文档内容回答问题：\n\n{document_text}\n\n问题：{prompt}" 
            if is_chinese else 
            f"Based on the following document content, answer the question:\n\n{document_text}\n\nQuestion: {prompt}"
        )
        
        try:
            # 调用标准LLM生成回答
            response = requests.post(
                self.ollama_api,
                json={
                    "model": model,
                    "prompt": context_prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                error_msg = f"生成回答失败: HTTP {response.status_code}" if is_chinese else f"Failed to generate response: HTTP {response.status_code}"
                st.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"生成回答失败: {str(e)}" if is_chinese else f"Failed to generate response: {str(e)}"
            st.error(error_msg)
            return error_msg
            
# 创建单例实例
document_processor = DocumentProcessor() 