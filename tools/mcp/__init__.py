# AI Quant Company - MCP 工具层
"""
MCP (Model Context Protocol) 工具接口

为所有 Agent 提供统一的外部信息获取能力：
- 论文检索 (arXiv, Semantic Scholar)
- 新闻聚合 (NewsAPI, RSS)
- 社交媒体 (Twitter, Reddit)
- 市场情绪 (Fear & Greed, Funding Rate)

架构：
    Agent → MCP Tool → MCP Server → 外部数据源

使用方式：
    from tools.mcp import get_mcp_tools
    tools = get_mcp_tools()
    papers = await tools.search_papers("momentum trading")
"""

from tools.mcp.papers import PapersMCP
from tools.mcp.news import NewsMCP
from tools.mcp.social import SocialMCP
from tools.mcp.sentiment import SentimentMCP
from tools.mcp.quant import QuantMCP


class MCPTools:
    """MCP 工具集合
    
    统一管理所有 MCP 工具的入口
    """
    
    def __init__(self):
        self.papers = PapersMCP()
        self.news = NewsMCP()
        self.social = SocialMCP()
        self.sentiment = SentimentMCP()
        self.quant = QuantMCP()  # 量化专业资讯
    
    def get_tool_schemas(self) -> list[dict]:
        """获取所有 MCP 工具的 Schema（用于 LLM function calling）"""
        return [
            # Papers
            {
                "type": "function",
                "function": {
                    "name": "mcp_search_papers",
                    "description": "搜索学术论文（arXiv, Semantic Scholar）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "source": {"type": "string", "enum": ["arxiv", "semantic_scholar", "all"], "default": "all"},
                            "max_results": {"type": "integer", "default": 10},
                            "year_from": {"type": "integer", "description": "起始年份"},
                        },
                        "required": ["query"]
                    }
                }
            },
            # News
            {
                "type": "function",
                "function": {
                    "name": "mcp_search_news",
                    "description": "搜索新闻资讯",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "source": {"type": "string", "enum": ["newsapi", "google", "crypto", "all"], "default": "all"},
                            "language": {"type": "string", "default": "en"},
                            "hours_ago": {"type": "integer", "default": 24},
                        },
                        "required": ["query"]
                    }
                }
            },
            # Social
            {
                "type": "function",
                "function": {
                    "name": "mcp_search_social",
                    "description": "搜索社交媒体讨论",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "platform": {"type": "string", "enum": ["twitter", "reddit", "hackernews", "all"], "default": "all"},
                            "sort": {"type": "string", "enum": ["recent", "popular", "relevant"], "default": "recent"},
                        },
                        "required": ["query"]
                    }
                }
            },
            # Sentiment
            {
                "type": "function",
                "function": {
                    "name": "mcp_get_market_sentiment",
                    "description": "获取市场情绪指标",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "indicator": {
                                "type": "string",
                                "enum": ["fear_greed", "funding_rate", "social_volume", "all"],
                                "default": "all"
                            },
                            "asset": {"type": "string", "default": "BTC"},
                        },
                        "required": []
                    }
                }
            },
            # Quant 量化专业资讯
            {
                "type": "function",
                "function": {
                    "name": "mcp_get_quant_news",
                    "description": "获取量化专业资讯（arXiv q-fin、Quantocracy、AQR、Reddit 量化社区）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "enum": ["arxiv", "quantocracy", "aqr", "reddit", "blogs", "all"],
                                "default": "all",
                                "description": "数据源"
                            },
                            "max_results": {"type": "integer", "default": 20},
                            "days": {"type": "integer", "default": 7, "description": "时间范围（天）"},
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mcp_search_quant_papers",
                    "description": "搜索量化金融论文（arXiv q-fin）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "max_results": {"type": "integer", "default": 10},
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mcp_get_crypto_research",
                    "description": "获取加密货币研究报告（Messari、Glassnode）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "default": 10},
                        },
                        "required": []
                    }
                }
            },
        ]


# 全局单例
_mcp_tools = None


def get_mcp_tools() -> MCPTools:
    """获取 MCP 工具单例"""
    global _mcp_tools
    if _mcp_tools is None:
        _mcp_tools = MCPTools()
    return _mcp_tools
