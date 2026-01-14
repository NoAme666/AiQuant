# AI Quant Company - 论文 MCP
"""
学术论文检索 MCP

数据源：
- arXiv (免费，实时)
- Semantic Scholar (免费，有引用数据)
- CrossRef (DOI 解析)

功能：
- 关键词搜索
- 按领域过滤
- 引用网络分析
- 摘要提取
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class Paper:
    """论文数据结构"""
    id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    source: str  # arxiv, semantic_scholar
    published_date: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    citation_count: int = 0
    pdf_url: Optional[str] = None


class PapersMCP:
    """论文检索 MCP 服务"""
    
    def __init__(self):
        self.arxiv_base = "http://export.arxiv.org/api/query"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.timeout = 30.0
        
        # Semantic Scholar API Key (可选，提高限额)
        self.s2_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    
    async def search(
        self,
        query: str,
        source: str = "all",
        max_results: int = 10,
        year_from: Optional[int] = None,
        categories: Optional[list[str]] = None,
    ) -> list[Paper]:
        """搜索论文
        
        Args:
            query: 搜索关键词
            source: 数据源 (arxiv, semantic_scholar, all)
            max_results: 最大结果数
            year_from: 起始年份
            categories: 论文类别过滤
            
        Returns:
            论文列表
        """
        results = []
        
        if source in ["arxiv", "all"]:
            arxiv_results = await self._search_arxiv(query, max_results, year_from, categories)
            results.extend(arxiv_results)
        
        if source in ["semantic_scholar", "all"]:
            s2_results = await self._search_semantic_scholar(query, max_results, year_from)
            results.extend(s2_results)
        
        # 去重（按标题相似度）
        seen_titles = set()
        unique_results = []
        for paper in results:
            title_key = paper.title.lower()[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_results.append(paper)
        
        # 按引用数排序
        unique_results.sort(key=lambda x: x.citation_count, reverse=True)
        
        return unique_results[:max_results]
    
    async def _search_arxiv(
        self,
        query: str,
        max_results: int,
        year_from: Optional[int],
        categories: Optional[list[str]],
    ) -> list[Paper]:
        """搜索 arXiv"""
        try:
            # 构建查询
            search_query = f"all:{quote(query)}"
            
            # 添加类别过滤
            if categories:
                cat_filter = " OR ".join(f"cat:{cat}" for cat in categories)
                search_query = f"({search_query}) AND ({cat_filter})"
            
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
            
            # 解析 XML
            papers = self._parse_arxiv_response(response.text, year_from)
            
            logger.info(f"arXiv 搜索完成", query=query, results=len(papers))
            return papers
            
        except Exception as e:
            logger.error(f"arXiv 搜索失败: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_text: str, year_from: Optional[int]) -> list[Paper]:
        """解析 arXiv XML 响应"""
        import xml.etree.ElementTree as ET
        
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
            
            for entry in root.findall("atom:entry", ns):
                # 提取信息
                title = entry.find("atom:title", ns)
                title = title.text.strip().replace("\n", " ") if title is not None else ""
                
                summary = entry.find("atom:summary", ns)
                summary = summary.text.strip().replace("\n", " ") if summary is not None else ""
                
                published = entry.find("atom:published", ns)
                published_date = published.text[:10] if published is not None else None
                
                # 年份过滤
                if year_from and published_date:
                    year = int(published_date[:4])
                    if year < year_from:
                        continue
                
                # 作者
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)
                
                # ID 和 URL
                arxiv_id = entry.find("atom:id", ns)
                arxiv_id = arxiv_id.text if arxiv_id is not None else ""
                paper_id = arxiv_id.split("/abs/")[-1] if "/abs/" in arxiv_id else arxiv_id
                
                # 类别
                categories = []
                for cat in entry.findall("arxiv:primary_category", ns):
                    term = cat.get("term")
                    if term:
                        categories.append(term)
                
                # PDF URL
                pdf_url = None
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break
                
                paper = Paper(
                    id=paper_id,
                    title=title,
                    authors=authors[:5],  # 限制作者数
                    abstract=summary[:1000],  # 限制摘要长度
                    url=arxiv_id,
                    source="arxiv",
                    published_date=published_date,
                    categories=categories,
                    citation_count=0,  # arXiv 不提供引用数
                    pdf_url=pdf_url,
                )
                papers.append(paper)
        
        except ET.ParseError as e:
            logger.error(f"arXiv XML 解析失败: {e}")
        
        return papers
    
    async def _search_semantic_scholar(
        self,
        query: str,
        max_results: int,
        year_from: Optional[int],
    ) -> list[Paper]:
        """搜索 Semantic Scholar"""
        try:
            params = {
                "query": query,
                "limit": max_results,
                "fields": "paperId,title,abstract,authors,year,citationCount,url,openAccessPdf",
            }
            
            if year_from:
                params["year"] = f"{year_from}-"
            
            headers = {}
            if self.s2_api_key:
                headers["x-api-key"] = self.s2_api_key
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.semantic_scholar_base}/paper/search",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for item in data.get("data", []):
                # 作者
                authors = [a.get("name", "") for a in item.get("authors", [])[:5]]
                
                # PDF URL
                pdf_url = None
                if item.get("openAccessPdf"):
                    pdf_url = item["openAccessPdf"].get("url")
                
                paper = Paper(
                    id=item.get("paperId", ""),
                    title=item.get("title", ""),
                    authors=authors,
                    abstract=item.get("abstract", "")[:1000] if item.get("abstract") else "",
                    url=item.get("url", ""),
                    source="semantic_scholar",
                    published_date=str(item.get("year")) if item.get("year") else None,
                    categories=[],
                    citation_count=item.get("citationCount", 0) or 0,
                    pdf_url=pdf_url,
                )
                papers.append(paper)
            
            logger.info(f"Semantic Scholar 搜索完成", query=query, results=len(papers))
            return papers
            
        except Exception as e:
            logger.error(f"Semantic Scholar 搜索失败: {e}")
            return []
    
    async def get_paper_details(self, paper_id: str, source: str = "arxiv") -> Optional[Paper]:
        """获取论文详情"""
        if source == "arxiv":
            return await self._get_arxiv_paper(paper_id)
        elif source == "semantic_scholar":
            return await self._get_s2_paper(paper_id)
        return None
    
    async def _get_arxiv_paper(self, arxiv_id: str) -> Optional[Paper]:
        """获取 arXiv 论文详情"""
        try:
            params = {"id_list": arxiv_id}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.arxiv_base, params=params)
                response.raise_for_status()
            
            papers = self._parse_arxiv_response(response.text, None)
            return papers[0] if papers else None
            
        except Exception as e:
            logger.error(f"获取 arXiv 论文失败: {e}")
            return None
    
    async def _get_s2_paper(self, paper_id: str) -> Optional[Paper]:
        """获取 Semantic Scholar 论文详情"""
        try:
            fields = "paperId,title,abstract,authors,year,citationCount,url,openAccessPdf,references,citations"
            
            headers = {}
            if self.s2_api_key:
                headers["x-api-key"] = self.s2_api_key
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.semantic_scholar_base}/paper/{paper_id}",
                    params={"fields": fields},
                    headers=headers,
                )
                response.raise_for_status()
            
            item = response.json()
            
            authors = [a.get("name", "") for a in item.get("authors", [])[:5]]
            pdf_url = item.get("openAccessPdf", {}).get("url") if item.get("openAccessPdf") else None
            
            return Paper(
                id=item.get("paperId", ""),
                title=item.get("title", ""),
                authors=authors,
                abstract=item.get("abstract", "")[:1000] if item.get("abstract") else "",
                url=item.get("url", ""),
                source="semantic_scholar",
                published_date=str(item.get("year")) if item.get("year") else None,
                categories=[],
                citation_count=item.get("citationCount", 0) or 0,
                pdf_url=pdf_url,
            )
            
        except Exception as e:
            logger.error(f"获取 Semantic Scholar 论文失败: {e}")
            return None
    
    async def get_related_papers(self, paper_id: str, source: str = "semantic_scholar") -> list[Paper]:
        """获取相关论文（基于引用）"""
        # 目前只支持 Semantic Scholar
        if source != "semantic_scholar":
            return []
        
        try:
            headers = {}
            if self.s2_api_key:
                headers["x-api-key"] = self.s2_api_key
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.semantic_scholar_base}/paper/{paper_id}/citations",
                    params={
                        "fields": "paperId,title,authors,year,citationCount,url",
                        "limit": 10,
                    },
                    headers=headers,
                )
                response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for item in data.get("data", []):
                citing = item.get("citingPaper", {})
                if not citing.get("title"):
                    continue
                
                authors = [a.get("name", "") for a in citing.get("authors", [])[:3]]
                
                paper = Paper(
                    id=citing.get("paperId", ""),
                    title=citing.get("title", ""),
                    authors=authors,
                    abstract="",
                    url=citing.get("url", ""),
                    source="semantic_scholar",
                    published_date=str(citing.get("year")) if citing.get("year") else None,
                    citation_count=citing.get("citationCount", 0) or 0,
                )
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.error(f"获取相关论文失败: {e}")
            return []
