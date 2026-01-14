# AI Quant Company - 新闻 MCP
"""
新闻聚合 MCP

数据源：
- NewsAPI (需要 API Key)
- Google News RSS (免费)
- 加密货币新闻聚合

功能：
- 关键词搜索
- 多语言支持
- 时间范围过滤
- 来源可信度评估
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class NewsArticle:
    """新闻文章数据结构"""
    id: str
    title: str
    description: str
    url: str
    source: str
    source_name: str
    published_at: str
    author: Optional[str] = None
    image_url: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral
    relevance_score: float = 0.0


class NewsMCP:
    """新闻聚合 MCP 服务"""
    
    def __init__(self):
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        self.newsapi_base = "https://newsapi.org/v2"
        self.timeout = 30.0
        
        # 加密货币新闻源
        self.crypto_sources = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptonews.com/news/feed/",
        ]
    
    async def search(
        self,
        query: str,
        source: str = "all",
        language: str = "en",
        hours_ago: int = 24,
        max_results: int = 20,
    ) -> list[NewsArticle]:
        """搜索新闻
        
        Args:
            query: 搜索关键词
            source: 数据源 (newsapi, google, crypto, all)
            language: 语言
            hours_ago: 时间范围（小时）
            max_results: 最大结果数
            
        Returns:
            新闻列表
        """
        results = []
        
        if source in ["newsapi", "all"] and self.newsapi_key:
            newsapi_results = await self._search_newsapi(query, language, hours_ago, max_results)
            results.extend(newsapi_results)
        
        if source in ["google", "all"]:
            google_results = await self._search_google_news(query, language)
            results.extend(google_results)
        
        if source in ["crypto", "all"]:
            crypto_results = await self._search_crypto_news(query)
            results.extend(crypto_results)
        
        # 按时间排序
        results.sort(key=lambda x: x.published_at, reverse=True)
        
        return results[:max_results]
    
    async def _search_newsapi(
        self,
        query: str,
        language: str,
        hours_ago: int,
        max_results: int,
    ) -> list[NewsArticle]:
        """搜索 NewsAPI"""
        if not self.newsapi_key:
            return []
        
        try:
            from_date = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat()
            
            params = {
                "q": query,
                "language": language,
                "from": from_date,
                "sortBy": "publishedAt",
                "pageSize": min(max_results, 100),
                "apiKey": self.newsapi_key,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.newsapi_base}/everything", params=params)
                response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data.get("articles", []):
                article = NewsArticle(
                    id=item.get("url", ""),
                    title=item.get("title", ""),
                    description=item.get("description", "")[:500] if item.get("description") else "",
                    url=item.get("url", ""),
                    source="newsapi",
                    source_name=item.get("source", {}).get("name", "Unknown"),
                    published_at=item.get("publishedAt", ""),
                    author=item.get("author"),
                    image_url=item.get("urlToImage"),
                )
                articles.append(article)
            
            logger.info(f"NewsAPI 搜索完成", query=query, results=len(articles))
            return articles
            
        except Exception as e:
            logger.error(f"NewsAPI 搜索失败: {e}")
            return []
    
    async def _search_google_news(self, query: str, language: str) -> list[NewsArticle]:
        """搜索 Google News RSS"""
        try:
            # Google News RSS
            rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl={language}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(rss_url)
                response.raise_for_status()
            
            articles = self._parse_rss(response.text, "google")
            
            logger.info(f"Google News 搜索完成", query=query, results=len(articles))
            return articles
            
        except Exception as e:
            logger.error(f"Google News 搜索失败: {e}")
            return []
    
    async def _search_crypto_news(self, query: str) -> list[NewsArticle]:
        """搜索加密货币新闻"""
        all_articles = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for rss_url in self.crypto_sources:
                try:
                    response = await client.get(rss_url)
                    if response.status_code == 200:
                        articles = self._parse_rss(response.text, "crypto")
                        # 按关键词过滤
                        query_lower = query.lower()
                        filtered = [
                            a for a in articles
                            if query_lower in a.title.lower() or query_lower in a.description.lower()
                        ]
                        all_articles.extend(filtered)
                except Exception as e:
                    logger.warning(f"RSS 获取失败: {rss_url}, {e}")
        
        logger.info(f"Crypto News 搜索完成", query=query, results=len(all_articles))
        return all_articles
    
    def _parse_rss(self, xml_text: str, source: str) -> list[NewsArticle]:
        """解析 RSS XML"""
        import xml.etree.ElementTree as ET
        
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            
            # 处理不同的 RSS 格式
            items = root.findall(".//item")
            
            for item in items[:20]:  # 限制数量
                title = item.find("title")
                title = title.text if title is not None else ""
                
                description = item.find("description")
                description = description.text[:500] if description is not None and description.text else ""
                
                link = item.find("link")
                link = link.text if link is not None else ""
                
                pub_date = item.find("pubDate")
                pub_date = pub_date.text if pub_date is not None else ""
                
                source_elem = item.find("source")
                source_name = source_elem.text if source_elem is not None else source
                
                article = NewsArticle(
                    id=link,
                    title=title,
                    description=description,
                    url=link,
                    source=source,
                    source_name=source_name,
                    published_at=pub_date,
                )
                articles.append(article)
        
        except ET.ParseError as e:
            logger.error(f"RSS 解析失败: {e}")
        
        return articles
    
    async def get_top_headlines(
        self,
        category: str = "business",
        country: str = "us",
        max_results: int = 10,
    ) -> list[NewsArticle]:
        """获取头条新闻"""
        if not self.newsapi_key:
            return []
        
        try:
            params = {
                "category": category,
                "country": country,
                "pageSize": max_results,
                "apiKey": self.newsapi_key,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.newsapi_base}/top-headlines", params=params)
                response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data.get("articles", []):
                article = NewsArticle(
                    id=item.get("url", ""),
                    title=item.get("title", ""),
                    description=item.get("description", "")[:500] if item.get("description") else "",
                    url=item.get("url", ""),
                    source="newsapi_headlines",
                    source_name=item.get("source", {}).get("name", "Unknown"),
                    published_at=item.get("publishedAt", ""),
                )
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"获取头条失败: {e}")
            return []
