from typing import List, Optional
import datetime
import json
import os
import requests
from bs4 import BeautifulSoup
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
            description="""【互联网搜索工具】
用途：通用搜索引擎，搜索互联网上的各类信息
适用场景：
- 知识库中没有相关链接时的备选方案
- 搜索最新、实时性强的信息
- 搜索特定产品、公司、人物等

注意：优先使用 query_knowledge_base + fetch_webpage，此工具作为兜底"""
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
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday = weekdays[now.weekday()]
            return f"当前时间：{now.strftime('%Y年%m月%d日')} {weekday} {now.strftime('%H:%M:%S')}"
            
        return Tool(
            name="current_time",
            func=get_current_time.run,
            description="获取当前系统日期和时间。当用户询问今天的日期、现在几点、当前时间、今天星期几等问题时，必须调用此工具。"
        )

    @staticmethod
    def create_knowledge_base_tool() -> Tool:
        """创建知识库查询工具。"""
        def query_knowledge_base(query: str = "") -> str:
            """根据问题查询知识库，返回相关链接。"""
            try:
                kb_path = os.path.join(os.getcwd(), "config", "knowledge_base.json")
                if not os.path.exists(kb_path):
                    return "知识库文件不存在，请使用 internet_search 代替。"
                
                with open(kb_path, "r", encoding="utf-8") as f:
                    knowledge_base = json.load(f)
                
                results = []
                query_lower = query.lower()
                
                for category, data in knowledge_base.items():
                    category_match = False
                    for link in data["links"]:
                        for keyword in link["keywords"]:
                            if keyword in query_lower:
                                category_match = True
                                break
                        if category_match:
                            results.append(f"类别: {data['name']}\n名称: {link['name']}\n链接: {link['url']}\n描述: {link['description']}")
                            break
                
                if not results:
                    return "知识库中没有找到相关链接，请使用 internet_search 进行搜索。"
                
                return "\n\n".join(results[:3])
            except Exception as e:
                return f"知识库查询错误: {str(e)}，请使用 internet_search 代替。"
            
        return Tool(
            name="query_knowledge_base",
            func=query_knowledge_base,
            description="""【知识库查询工具】
用途：查询预定义的高质量网站链接，适用于常见问题类型。
支持类别：
- 天气查询：天气、气温、降雨、预报等
- 新闻资讯：新闻、头条、热点、时事等  
- 技术文档：Python、React、Vue、Web开发等
- 百科知识：概念解释、定义、百科等
- 财经金融：股票、基金、投资等

返回：相关网站链接和描述
下一步：如果返回链接，必须使用 fetch_webpage 抓取内容"""
        )

    @staticmethod
    def create_webpage_fetcher_tool() -> Tool:
        """创建网页抓取工具。"""
        def fetch_webpage(url: str = "") -> str:
            """抓取指定网页的内容。"""
            if not url or not url.startswith("http"):
                return "错误：请提供有效的 URL 地址（以 http:// 或 https:// 开头）"
            
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                response.encoding = response.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(response.text, "html.parser")
                
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                    element.decompose()
                
                main_content = None
                for selector in ['article', 'main', '.content', '.article', '.post', '#content', '#main']:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break
                
                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)
                
                if len(text) > 4000:
                    text = text[:4000] + "\n\n... (内容已截断，完整内容请访问原网页)"
                
                return text if text else "网页内容为空或无法解析"
            except requests.exceptions.Timeout:
                return "网页抓取超时，请尝试其他链接或使用 internet_search"
            except requests.exceptions.RequestException as e:
                return f"网页抓取失败: {str(e)}，请尝试其他链接或使用 internet_search"
            except Exception as e:
                return f"网页解析错误: {str(e)}"
            
        return Tool(
            name="fetch_webpage",
            func=fetch_webpage,
            description="""【网页内容抓取工具】
用途：抓取指定 URL 的网页文本内容
输入：完整的 URL 地址（如 https://example.com）
输出：网页的文本内容（自动清理无关元素）

使用场景：
- 获取知识库返回链接的具体内容
- 访问特定网页获取详细信息

注意：如果抓取失败，可以尝试其他链接或改用 internet_search"""
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
            
        kb_tool = ToolsFactory.create_knowledge_base_tool()
        if kb_tool:
            tools.append(kb_tool)
            
        fetch_tool = ToolsFactory.create_webpage_fetcher_tool()
        if fetch_tool:
            tools.append(fetch_tool)
            
        repl_tool = ToolsFactory.create_python_repl_tool()
        if repl_tool:
            tools.append(repl_tool)
            
        return tools
