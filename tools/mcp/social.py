# AI Quant Company - 社交媒体 MCP
"""
社交媒体监控 MCP

数据源：
- Twitter/X (需要 API Key 或第三方)
- Reddit (免费 API)
- Hacker News (免费 API)

功能：
- 话题追踪
- KOL 监控
- 情绪分析
- 热点识别
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class SocialPost:
    """社交媒体帖子"""
    id: str
    platform: str  # twitter, reddit, hackernews
    author: str
    content: str
    url: str
    created_at: str
    
    # 互动数据
    likes: int = 0
    comments: int = 0
    shares: int = 0
    score: int = 0  # Reddit/HN 特有
    
    # 分析数据
    sentiment: Optional[str] = None
    is_kol: bool = False
    followers: int = 0


@dataclass
class SocialTrend:
    """社交媒体趋势"""
    topic: str
    platform: str
    post_count: int
    sentiment_score: float  # -1 到 1
    top_posts: list[SocialPost] = field(default_factory=list)


class SocialMCP:
    """社交媒体监控 MCP 服务"""
    
    def __init__(self):
        self.timeout = 30.0
        
        # Reddit API
        self.reddit_base = "https://www.reddit.com"
        
        # Hacker News API
        self.hn_base = "https://hacker-news.firebaseio.com/v0"
        
        # Twitter (需要配置)
        self.twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
    
    async def search(
        self,
        query: str,
        platform: str = "all",
        sort: str = "recent",
        max_results: int = 20,
    ) -> list[SocialPost]:
        """搜索社交媒体
        
        Args:
            query: 搜索关键词
            platform: 平台 (twitter, reddit, hackernews, all)
            sort: 排序方式 (recent, popular, relevant)
            max_results: 最大结果数
            
        Returns:
            帖子列表
        """
        results = []
        
        if platform in ["reddit", "all"]:
            reddit_posts = await self._search_reddit(query, sort, max_results)
            results.extend(reddit_posts)
        
        if platform in ["hackernews", "all"]:
            hn_posts = await self._search_hackernews(query, max_results)
            results.extend(hn_posts)
        
        if platform in ["twitter", "all"] and self.twitter_bearer:
            twitter_posts = await self._search_twitter(query, max_results)
            results.extend(twitter_posts)
        
        # 排序
        if sort == "popular":
            results.sort(key=lambda x: x.score + x.likes, reverse=True)
        elif sort == "recent":
            results.sort(key=lambda x: x.created_at, reverse=True)
        
        return results[:max_results]
    
    async def _search_reddit(
        self,
        query: str,
        sort: str,
        max_results: int,
    ) -> list[SocialPost]:
        """搜索 Reddit"""
        try:
            # Reddit 搜索 API
            reddit_sort = {
                "recent": "new",
                "popular": "top",
                "relevant": "relevance",
            }.get(sort, "relevance")
            
            url = f"{self.reddit_base}/search.json"
            params = {
                "q": query,
                "sort": reddit_sort,
                "limit": max_results,
                "t": "week",  # 时间范围
            }
            
            headers = {"User-Agent": "AIQuantCompany/1.0"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for item in data.get("data", {}).get("children", []):
                post_data = item.get("data", {})
                
                post = SocialPost(
                    id=post_data.get("id", ""),
                    platform="reddit",
                    author=post_data.get("author", ""),
                    content=post_data.get("title", "") + "\n" + post_data.get("selftext", "")[:500],
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    created_at=datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                    likes=post_data.get("ups", 0),
                    comments=post_data.get("num_comments", 0),
                    score=post_data.get("score", 0),
                )
                posts.append(post)
            
            logger.info(f"Reddit 搜索完成", query=query, results=len(posts))
            return posts
            
        except Exception as e:
            logger.error(f"Reddit 搜索失败: {e}")
            return []
    
    async def _search_hackernews(self, query: str, max_results: int) -> list[SocialPost]:
        """搜索 Hacker News (通过 Algolia)"""
        try:
            url = "https://hn.algolia.com/api/v1/search"
            params = {
                "query": query,
                "tags": "story",
                "hitsPerPage": max_results,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for item in data.get("hits", []):
                post = SocialPost(
                    id=str(item.get("objectID", "")),
                    platform="hackernews",
                    author=item.get("author", ""),
                    content=item.get("title", ""),
                    url=item.get("url", "") or f"https://news.ycombinator.com/item?id={item.get('objectID')}",
                    created_at=item.get("created_at", ""),
                    comments=item.get("num_comments", 0),
                    score=item.get("points", 0),
                )
                posts.append(post)
            
            logger.info(f"Hacker News 搜索完成", query=query, results=len(posts))
            return posts
            
        except Exception as e:
            logger.error(f"Hacker News 搜索失败: {e}")
            return []
    
    async def _search_twitter(self, query: str, max_results: int) -> list[SocialPost]:
        """搜索 Twitter (需要 Bearer Token)"""
        if not self.twitter_bearer:
            return []
        
        try:
            url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                "query": query,
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics,author_id",
            }
            
            headers = {"Authorization": f"Bearer {self.twitter_bearer}"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for item in data.get("data", []):
                metrics = item.get("public_metrics", {})
                
                post = SocialPost(
                    id=item.get("id", ""),
                    platform="twitter",
                    author=item.get("author_id", ""),
                    content=item.get("text", ""),
                    url=f"https://twitter.com/i/web/status/{item.get('id')}",
                    created_at=item.get("created_at", ""),
                    likes=metrics.get("like_count", 0),
                    comments=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                )
                posts.append(post)
            
            logger.info(f"Twitter 搜索完成", query=query, results=len(posts))
            return posts
            
        except Exception as e:
            logger.error(f"Twitter 搜索失败: {e}")
            return []
    
    async def get_subreddit_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
    ) -> list[SocialPost]:
        """获取 Subreddit 帖子"""
        try:
            url = f"{self.reddit_base}/r/{subreddit}/{sort}.json"
            params = {"limit": limit}
            headers = {"User-Agent": "AIQuantCompany/1.0"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for item in data.get("data", {}).get("children", []):
                post_data = item.get("data", {})
                
                post = SocialPost(
                    id=post_data.get("id", ""),
                    platform="reddit",
                    author=post_data.get("author", ""),
                    content=post_data.get("title", "") + "\n" + post_data.get("selftext", "")[:500],
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    created_at=datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                    likes=post_data.get("ups", 0),
                    comments=post_data.get("num_comments", 0),
                    score=post_data.get("score", 0),
                )
                posts.append(post)
            
            return posts
            
        except Exception as e:
            logger.error(f"获取 Subreddit 失败: {e}")
            return []
    
    async def get_crypto_reddit(self, limit: int = 25) -> list[SocialPost]:
        """获取加密货币相关 Reddit 热帖"""
        subreddits = ["cryptocurrency", "bitcoin", "ethereum", "CryptoMarkets"]
        all_posts = []
        
        for sub in subreddits:
            posts = await self.get_subreddit_posts(sub, "hot", limit // len(subreddits))
            all_posts.extend(posts)
        
        # 按分数排序
        all_posts.sort(key=lambda x: x.score, reverse=True)
        return all_posts[:limit]
    
    async def get_hn_top_stories(self, limit: int = 30) -> list[SocialPost]:
        """获取 Hacker News 热门故事"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 获取热门故事 ID
                response = await client.get(f"{self.hn_base}/topstories.json")
                story_ids = response.json()[:limit]
                
                posts = []
                for story_id in story_ids[:limit]:
                    story_response = await client.get(f"{self.hn_base}/item/{story_id}.json")
                    item = story_response.json()
                    
                    if item and item.get("type") == "story":
                        post = SocialPost(
                            id=str(item.get("id", "")),
                            platform="hackernews",
                            author=item.get("by", ""),
                            content=item.get("title", ""),
                            url=item.get("url", "") or f"https://news.ycombinator.com/item?id={item.get('id')}",
                            created_at=datetime.fromtimestamp(item.get("time", 0)).isoformat(),
                            comments=item.get("descendants", 0),
                            score=item.get("score", 0),
                        )
                        posts.append(post)
                
                return posts
                
        except Exception as e:
            logger.error(f"获取 HN 热门失败: {e}")
            return []
