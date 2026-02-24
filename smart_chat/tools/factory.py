from typing import List, Optional
import datetime
from langchain_core.tools import Tool, tool
from langchain_experimental.tools import PythonREPLTool
from langchain.chains import LLMMathChain
from langchain_core.language_models import BaseChatModel

class ToolsFactory:
    """Agent 工具工厂类，负责创建和管理各种增强工具。"""
    
    @staticmethod
    def create_search_tool(search_config: dict = None) -> Tool:
        """创建联网搜索工具（Bing Lite，免 Key 免代理）。"""
        search_config = search_config or {}
        timeout = search_config.get("timeout", 15)
        count = search_config.get("count", 8)
        def bing_lite_search(query: str) -> str:
            """执行 Bing 国内版网页搜索。"""
            try:
                import requests
                from bs4 import BeautifulSoup
                import urllib.parse
                import chainlit as cl

                import random
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]

                async def send_search_step():
                    async with cl.Step(name="Bing Search", type="tool") as step:
                        step.output = "正在进行联网搜索中..."
                        await step.send()
                
                try:
                    cl.run_sync(send_search_step())
                except:
                    pass

                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                }
                
                # 使用 Bing 国内版
                base_url = "https://cn.bing.com/search"
                params = {"q": query, "count": count}
                
                response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                
                for item in soup.find_all('li', class_='b_algo'):
                    try:
                        title_tag = item.find('h2')
                        link_tag = item.find('a')
                        caption_tag = item.find('p') or item.find('div', class_='b_caption') or item.find('div', class_='b_snippet')
                        source_tag = item.find('cite')
                        date_tag = item.find('span', class_='news_dt')

                        if title_tag and link_tag:
                            title = title_tag.get_text().strip()
                            link = link_tag.get('href')
                            caption = caption_tag.get_text().strip() if caption_tag else "No description"
                            
                            extra_info = []
                            if source_tag: extra_info.append(f"Source: {source_tag.get_text().strip()}")
                            if date_tag: extra_info.append(f"Date: {date_tag.get_text().strip()}")
                            
                            extra_str = f" | {' '.join(extra_info)}" if extra_info else ""
                            
                            results.append(f"Title: {title}\nLink: {link}\nSnippet: {caption}{extra_str}")
                    except Exception:
                        continue

                for item in soup.find_all('li', class_='b_ans'):
                     try:
                        title_tag = item.find(['h2', 'strong', 'div'], class_=['b_entityTitle', 'b_title'])
                        content_tag = item.find(['div', 'p'], class_=['b_entityDesc', 'b_snippet', 'rwrl'])
                        
                        if title_tag and content_tag:
                             title = title_tag.get_text().strip()
                             content = content_tag.get_text().strip()
                             results.append(f"[Featured] Title: {title}\nContent: {content}")
                     except Exception:
                        continue

                if len(results) < 2:
                     for item in soup.select('li h2 a'):
                        try:
                            title = item.get_text().strip()
                            link = item.get('href')
                            if link and link.startswith('http'):
                                results.append(f"Title: {title}\nLink: {link}\nSnippet: (Simple Result)")
                        except: pass

                unique_results = []
                seen = set()
                for r in results:
                    if r not in seen:
                        seen.add(r)
                        unique_results.append(r)
                
                final_results = unique_results[:6]

                if not final_results:
                    return "未找到相关搜索结果。建议尝试更换关键词。"
                    
                return "\n\n".join(final_results)
                
            except Exception as e:
                return f"Search Error: {str(e)}\nTip: Bing 搜索可能因网络波动失败，请重试。"

        return Tool(
            name="internet_search",
            func=bing_lite_search,
            description="用于搜索互联网信息 (via Bing Lite)。无需 Key，支持国内直连。"
        )


    @staticmethod
    def create_calculator_tool(llm: BaseChatModel) -> Tool:
        """创建数学计算工具（LLMMathChain）。"""
        try:
            llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
            return Tool(
                name="calculator",
                func=llm_math_chain.run,
                description="用于执行复杂的数学计算。输入应该是数学表达式或需要计算的问题。"
            )
        except Exception as e:
            print(f"Warning: Failed to create calculator tool: {e}")
            return None

    @staticmethod
    def create_time_tool() -> Tool:
        """创建时间工具。"""
        @tool
        def get_current_time(query: str = "") -> str:
            """返回当前日期和时间。"""
            now = datetime.datetime.now()
            return now.strftime("%Y-%m-%d %H:%M:%S %A")
            
        return Tool(
            name="current_time",
            func=get_current_time.run,
            description="用于获取当前日期和时间。"
        )

    @staticmethod
    def create_python_repl_tool() -> Tool:
        """创建 Python 代码执行工具。"""
        try:
            return PythonREPLTool(
                name="python_repl",
                description="Python 代码执行器，用于数据分析、绘图等。"
            )
        except Exception as e:
            print(f"Warning: Failed to create Python REPL tool: {e}")
            return None

    @staticmethod
    def get_all_tools(llm: BaseChatModel, search_config: dict = None) -> List[Tool]:
        """获取所有可用的工具列表。
        
        Args:
            llm: LLM 实例
            search_config: 搜索配置
            
        Returns:
            工具列表
        """
        tools = []
        
        search_tool = ToolsFactory.create_search_tool(search_config)
        if search_tool:
            tools.append(search_tool)
            
        calc_tool = ToolsFactory.create_calculator_tool(llm)
        if calc_tool:
            tools.append(calc_tool)
            
        time_tool = ToolsFactory.create_time_tool()
        if time_tool:
            tools.append(time_tool)
            
        repl_tool = ToolsFactory.create_python_repl_tool()
        if repl_tool:
            tools.append(repl_tool)
            
        return tools
