# AI Quant Company - 量化资讯 MCP
"""
量化专业资讯 MCP

数据源：
- arXiv q-fin（量化金融论文）
- SSRN（金融学术预印本）
- Quantocracy（量化博客聚合）
- AQR Insights（机构研究）
- Reddit r/algotrading, r/quant
- 加密货币研究（Messari, Glassnode）

功能：
- 量化论文追踪
- 策略博客聚合
- 社区热点监控
- 机构研报获取
"""

import asyncio
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class QuantArticle:
    """量化文章/论文"""
    id: str
    title: str
    summary: str
    url: str
    source: str  # arxiv_qfin, ssrn, quantocracy, aqr, reddit
    source_name: str
    published_at: str
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    score: int = 0  # Reddit upvotes / citations


class QuantMCP:
    """量化资讯 MCP 服务"""
    
    def __init__(self):
        self.timeout = 30.0
        
        # arXiv 量化金融
        self.arxiv_base = "http://export.arxiv.org/api/query"
        
        # RSS 源
        self.rss_sources = {
            "quantocracy": "https://quantocracy.com/feed/",
            "alpha_architect": "https://alphaarchitect.com/feed/",
            "robot_wealth": "https://robotwealth.com/feed/",
            "aqr": "https://www.aqr.com/Insights/Research/RSS",
        }
        
        # Reddit
        self.reddit_base = "https://www.reddit.com"
        self.quant_subreddits = ["algotrading", "quant", "quantfinance"]
    
    async def get_latest(
        self,
        source: str = "all",
        max_results: int = 20,
        days: int = 7,
    ) -> list[QuantArticle]:
        """获取最新量化资讯
        
        Args:
            source: 数据源 (arxiv, quantocracy, aqr, reddit, all)
            max_results: 最大结果数
            days: 时间范围（天）
            
        Returns:
            文章列表
        """
        results = []
        
        if source in ["arxiv", "all"]:
            arxiv_results = await self._get_arxiv_qfin(max_results, days)
            results.extend(arxiv_results)
        
        if source in ["quantocracy", "all"]:
            quant_results = await self._get_rss("quantocracy", max_results)
            results.extend(quant_results)
        
        if source in ["aqr", "all"]:
            aqr_results = await self._get_rss("aqr", max_results)
            results.extend(aqr_results)
        
        if source in ["reddit", "all"]:
            reddit_results = await self._get_reddit_quant(max_results)
            results.extend(reddit_results)
        
        if source in ["blogs", "all"]:
            for blog in ["alpha_architect", "robot_wealth"]:
                blog_results = await self._get_rss(blog, max_results // 2)
                results.extend(blog_results)
        
        # 按时间排序
        results.sort(key=lambda x: x.published_at, reverse=True)
        
        return results[:max_results]
    
    async def _get_arxiv_qfin(self, max_results: int, days: int) -> list[QuantArticle]:
        """获取 arXiv 量化金融最新论文"""
        try:
            # 量化金融分类
            categories = [
                "q-fin.PM",   # Portfolio Management
                "q-fin.TR",   # Trading and Market Microstructure
                "q-fin.RM",   # Risk Management
                "q-fin.ST",   # Statistical Finance
                "q-fin.CP",   # Computational Finance
                "q-fin.MF",   # Mathematical Finance
            ]
            
            cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
            
            params = {
                "search_query": f"({cat_query})",
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.arxiv_base, params=params)
                response.raise_for_status()
            
            articles = self._parse_arxiv_response(response.text)
            
            logger.info(f"arXiv q-fin: 获取 {len(articles)} 篇论文")
            return articles
            
        except Exception as e:
            logger.error(f"arXiv q-fin 获取失败: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_text: str) -> list[QuantArticle]:
        """解析 arXiv XML"""
        import xml.etree.ElementTree as ET
        
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
            
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                title = title.text.strip().replace("\n", " ") if title is not None else ""
                
                summary = entry.find("atom:summary", ns)
                summary = summary.text.strip().replace("\n", " ")[:500] if summary is not None else ""
                
                published = entry.find("atom:published", ns)
                published_at = published.text[:10] if published is not None else ""
                
                arxiv_id = entry.find("atom:id", ns)
                url = arxiv_id.text if arxiv_id is not None else ""
                paper_id = url.split("/abs/")[-1] if "/abs/" in url else url
                
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)
                
                # 提取分类作为标签
                tags = []
                for cat in entry.findall("arxiv:primary_category", ns):
                    term = cat.get("term")
                    if term:
                        tags.append(term)
                
                article = QuantArticle(
                    id=paper_id,
                    title=title,
                    summary=summary,
                    url=url,
                    source="arxiv_qfin",
                    source_name="arXiv Quantitative Finance",
                    published_at=published_at,
                    authors=authors[:3],
                    tags=tags,
                )
                articles.append(article)
        
        except ET.ParseError as e:
            logger.error(f"arXiv XML 解析失败: {e}")
        
        return articles
    
    async def _get_rss(self, source: str, max_results: int) -> list[QuantArticle]:
        """获取 RSS 源内容"""
        rss_url = self.rss_sources.get(source)
        if not rss_url:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(rss_url)
                response.raise_for_status()
            
            articles = self._parse_rss(response.text, source)
            
            logger.info(f"{source}: 获取 {len(articles)} 篇文章")
            return articles[:max_results]
            
        except Exception as e:
            logger.error(f"{source} RSS 获取失败: {e}")
            return []
    
    def _parse_rss(self, xml_text: str, source: str) -> list[QuantArticle]:
        """解析 RSS XML"""
        import xml.etree.ElementTree as ET
        
        articles = []
        source_names = {
            "quantocracy": "Quantocracy",
            "alpha_architect": "Alpha Architect",
            "robot_wealth": "Robot Wealth",
            "aqr": "AQR Insights",
        }
        
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")
            
            for item in items[:20]:
                title = item.find("title")
                title = title.text if title is not None else ""
                
                description = item.find("description")
                desc_text = description.text if description is not None else ""
                # 清理 HTML 标签
                summary = re.sub(r'<[^>]+>', '', desc_text)[:500]
                
                link = item.find("link")
                url = link.text if link is not None else ""
                
                pub_date = item.find("pubDate")
                published_at = pub_date.text if pub_date is not None else ""
                
                # 尝试解析作者
                author = item.find("dc:creator", {"dc": "http://purl.org/dc/elements/1.1/"})
                if author is None:
                    author = item.find("author")
                authors = [author.text] if author is not None and author.text else []
                
                # 提取分类标签
                tags = []
                for cat in item.findall("category"):
                    if cat.text:
                        tags.append(cat.text)
                
                article = QuantArticle(
                    id=url,
                    title=title,
                    summary=summary,
                    url=url,
                    source=source,
                    source_name=source_names.get(source, source),
                    published_at=published_at,
                    authors=authors,
                    tags=tags[:5],
                )
                articles.append(article)
        
        except ET.ParseError as e:
            logger.error(f"RSS 解析失败: {e}")
        
        return articles
    
    async def _get_reddit_quant(self, max_results: int) -> list[QuantArticle]:
        """获取 Reddit 量化社区热帖"""
        all_posts = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for subreddit in self.quant_subreddits:
                try:
                    url = f"{self.reddit_base}/r/{subreddit}/hot.json"
                    params = {"limit": max_results // len(self.quant_subreddits)}
                    headers = {"User-Agent": "AIQuantCompany/1.0"}
                    
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code != 200:
                        continue
                    
                    data = response.json()
                    
                    for item in data.get("data", {}).get("children", []):
                        post_data = item.get("data", {})
                        
                        # 跳过置顶帖
                        if post_data.get("stickied"):
                            continue
                        
                        article = QuantArticle(
                            id=post_data.get("id", ""),
                            title=post_data.get("title", ""),
                            summary=post_data.get("selftext", "")[:500],
                            url=f"https://reddit.com{post_data.get('permalink', '')}",
                            source="reddit",
                            source_name=f"r/{subreddit}",
                            published_at=datetime.fromtimestamp(
                                post_data.get("created_utc", 0)
                            ).isoformat(),
                            authors=[post_data.get("author", "")],
                            tags=[subreddit],
                            score=post_data.get("score", 0),
                        )
                        all_posts.append(article)
                
                except Exception as e:
                    logger.error(f"Reddit r/{subreddit} 获取失败: {e}")
        
        # 按分数排序
        all_posts.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Reddit 量化社区: 获取 {len(all_posts)} 条帖子")
        return all_posts[:max_results]
    
    async def search_quant_papers(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[QuantArticle]:
        """搜索量化相关论文"""
        try:
            # 限制在量化金融分类
            search_query = f"all:{quote(query)} AND (cat:q-fin.* OR cat:stat.ML)"
            
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.arxiv_base, params=params)
                response.raise_for_status()
            
            articles = self._parse_arxiv_response(response.text)
            
            logger.info(f"量化论文搜索: {query}, 找到 {len(articles)} 篇")
            return articles
            
        except Exception as e:
            logger.error(f"量化论文搜索失败: {e}")
            return []
    
    async def get_ssrn_finance(self, max_results: int = 10) -> list[QuantArticle]:
        """获取 SSRN 金融论文（通过 RSS）"""
        try:
            # SSRN 金融网络 RSS
            url = "https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=2966936&Network=no&lim=false&npage=1"
            
            # SSRN 没有好用的公开 API，这里返回空
            # 实际使用中可以考虑爬虫或付费 API
            logger.info("SSRN 暂不支持自动获取，请手动访问 https://www.ssrn.com/")
            return []
            
        except Exception as e:
            logger.error(f"SSRN 获取失败: {e}")
            return []
    
    async def get_crypto_research(self, max_results: int = 10) -> list[QuantArticle]:
        """获取加密货币研究"""
        articles = []
        
        # Messari RSS
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get("https://messari.io/rss")
                if response.status_code == 200:
                    messari_articles = self._parse_rss(response.text, "messari")
                    for a in messari_articles:
                        a.source_name = "Messari Research"
                    articles.extend(messari_articles[:max_results // 2])
        except Exception as e:
            logger.warning(f"Messari 获取失败: {e}")
        
        # Glassnode Insights RSS
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get("https://insights.glassnode.com/rss/")
                if response.status_code == 200:
                    glassnode_articles = self._parse_rss(response.text, "glassnode")
                    for a in glassnode_articles:
                        a.source_name = "Glassnode Insights"
                    articles.extend(glassnode_articles[:max_results // 2])
        except Exception as e:
            logger.warning(f"Glassnode 获取失败: {e}")
        
        logger.info(f"加密货币研究: 获取 {len(articles)} 篇")
        return articles[:max_results]


# 添加到 MCP 工具集
def get_quant_mcp() -> QuantMCP:
    """获取量化资讯 MCP"""
    return QuantMCP()
