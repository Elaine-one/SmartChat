from langchain_core.tools import Tool
from typing import Optional
from smart_chat.vectorstores.chroma import VectorStoreManager

class RetrieverToolFactory:
    """RAG 检索工具工厂。"""

    @staticmethod
    def create_retriever_tool(
        name: str = "document_retriever",
        description: str = "用于检索知识库或已上传文档中的信息。"
    ) -> Optional[Tool]:
        """创建文档检索工具。
        
        Args:
            name: 工具名称
            description: 工具描述
            
        Returns:
            检索工具实例，如果向量库未初始化则返回 None
        """
        vector_store = VectorStoreManager()
        if not vector_store.initialized:
            return None

        def retrieve_func(query: str) -> str:
            """执行文档检索。"""
            try:
                docs = vector_store.search_similar(query, k=4)
                if not docs:
                    return "未找到相关文档内容。"

                result = "从本地知识库找到以下相关文档片段：\n\n"
                for i, doc in enumerate(docs):
                    source = doc.metadata.get("source", "未知来源")
                    content = doc.page_content
                    result += f"--- 片段 {i+1} (来源: {source}) ---\n{content}\n\n"

                return result
            except Exception as e:
                return f"检索出错: {str(e)}"

        return Tool(
            name=name,
            func=retrieve_func,
            description=description
        )
