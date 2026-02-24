import os
from typing import List, Optional
import logging
try:
    from langchain_chroma import Chroma
except ImportError:
    try:
        from langchain_community.vectorstores import Chroma
    except ImportError:
        raise ImportError(
            "无法导入 Chroma，请安装 langchain-chroma 或 langchain-community"
        )
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from smart_chat.core.config import CONFIG

logger = logging.getLogger(__name__)

if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


def _resolve_embedding_model_name() -> str:
    """解析 Embedding 模型名称或本地路径，支持通过环境变量覆盖。"""
    local_path = os.environ.get("SMARTCHAT_EMBEDDING_MODEL_PATH")
    if local_path and os.path.exists(local_path):
        return local_path

    local_default = os.path.join(
        os.getcwd(),
        "models--BAAI--bge-small-zh",
        "snapshots",
        "c9745ed1d9f207416be6d2e6f8de32d1f16199bf",
    )
    if os.path.exists(local_default):
        return local_default

    return (
        os.environ.get("SMARTCHAT_EMBEDDING_MODEL_NAME")
        or CONFIG.get("rag", {}).get("embedding_model", "BAAI/bge-small-zh")
    )


import threading

class VectorStoreManager:
    """向量数据库管理器，封装 ChromaDB 操作"""

    _instance = None
    _vector_store_instance = None
    _lock = threading.RLock()
    _init_in_progress = False
    _init_error = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStoreManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "initialized", False):
            return
            
        with self._lock:
            if getattr(self, "initialized", False):
                return
            self.persist_directory = os.environ.get("SMARTCHAT_CHROMA_DIR") or os.path.join(
                os.getcwd(), "data", "chroma_db"
            )
            self.embedding_model_name = _resolve_embedding_model_name()
            
            # 确保数据目录存在
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # 延迟初始化
            self._embeddings = None
            self._vector_store_instance = None
            self.initialized = True  # 标记为已配置，但在首次使用时才加载模型

    def _load_resources(self):
        """懒加载向量化资源。"""
        if self._vector_store_instance:
            return

        with self._lock:
            if self._vector_store_instance:
                return
            if self._init_in_progress:
                return
            self._init_in_progress = True
            self._init_error = None

            if os.path.exists(self.embedding_model_name):
                logger.info(f"使用本地 Embedding 模型路径: {self.embedding_model_name}")
            else:
                logger.info(f"使用 Embedding 模型名称: {self.embedding_model_name}")
                
            logger.info(f"初始化向量数据库，存储路径: {self.persist_directory}")
            
            try:
                self._embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
                self._vector_store_instance = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self._embeddings,
                    collection_name="smart_chat_docs"
                )
            except Exception as e:
                logger.error(f"向量数据库资源加载失败: {e}", exc_info=True)
                self._init_error = str(e)
                raise e
            finally:
                self._init_in_progress = False

    @property
    def vector_store(self):
        """获取向量库实例（懒加载）。"""
        self._load_resources()
        return self._vector_store_instance

    def ensure_ready(self) -> bool:
        """确保向量库资源已初始化。
        
        Returns:
            是否初始化成功
        """
        try:
            self._load_resources()
            return self._vector_store_instance is not None
        except Exception:
            return False

    def get_last_error(self) -> Optional[str]:
        """获取最近一次初始化错误信息。
        
        Returns:
            错误信息字符串，如果没有错误则返回 None
        """
        return self._init_error

    def clear(self) -> bool:
        """清空向量库。
        
        Returns:
            是否清空成功
        """
        with self._lock:
            try:
                if not self._vector_store_instance:
                     self._load_resources()
                
                if self._vector_store_instance:
                    self._vector_store_instance.delete_collection()
                    self._vector_store_instance = None 
                    self._embeddings = None
                
                logger.info("向量库已清空")
                return True
            except Exception as e:
                logger.error(f"清空向量库失败: {e}")
                return False

    def add_documents(self, documents: List[Document]) -> bool:
        """添加文档到向量库。
        
        Args:
            documents: 文档列表
            
        Returns:
            是否添加成功
        """
        with self._lock:
            try:
                if not self.ensure_ready():
                    return False
                store = self.vector_store
                if not store:
                    return False

                logger.info(f"正在向向量库添加 {len(documents)} 个文档片段...")
                store.add_documents(documents)
                logger.info("文档添加完成")
                return True
            except Exception as e:
                logger.error(f"添加文档失败: {e}")
                return False
            
    def as_retriever(self, **kwargs):
        """获取检索器。
        
        Args:
            **kwargs: 传递给 as_retriever 的参数
            
        Returns:
            Retriever 对象
        """
        return self.vector_store.as_retriever(**kwargs)

    def search_similar(self, query: str, k: int = 4) -> List[Document]:
        """搜索相似文档。
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            相似文档列表
        """
        try:
            store = self.vector_store
            if not store:
                logger.warning("向量库未初始化，返回空结果")
                return []
            
            results = store.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"向量搜索失败: {e}", exc_info=True)
            return []

    def get_retriever(self, search_kwargs: dict = None):
        """获取 LangChain Retriever 对象。
        
        Args:
            search_kwargs: 检索参数
            
        Returns:
            Retriever 对象
        """
        kwargs = search_kwargs or {"k": 4}
        return self.as_retriever(search_kwargs=kwargs)
