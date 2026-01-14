#!/usr/bin/env python3
# AI Quant Company - MCP 工具测试脚本
"""
测试所有 MCP 工具的连通性

用法:
    python scripts/test_mcp.py           # 测试所有
    python scripts/test_mcp.py papers    # 只测试论文
    python scripts/test_mcp.py news      # 只测试新闻
    python scripts/test_mcp.py social    # 只测试社交
    python scripts/test_mcp.py sentiment # 只测试情绪
    python scripts/test_mcp.py quant     # 只测试量化资讯
"""

import asyncio
import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_papers():
    """测试论文检索"""
    print("\n📚 测试论文检索...")
    print("-" * 40)
    
    from tools.mcp.papers import PapersMCP
    papers_mcp = PapersMCP()
    
    # 测试 arXiv（不需要 API Key）
    print("1. arXiv 搜索...")
    results = await papers_mcp.search(
        query="momentum trading",
        source="arxiv",
        max_results=3,
        year_from=2023,
    )
    
    if results:
        print(f"   ✅ arXiv: 找到 {len(results)} 篇论文")
        for i, paper in enumerate(results[:2], 1):
            print(f"      {i}. {paper.title[:60]}...")
    else:
        print("   ❌ arXiv: 无结果")
    
    # 测试 Semantic Scholar
    print("\n2. Semantic Scholar 搜索...")
    s2_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    print(f"   API Key: {'已配置 ✅' if s2_key else '未配置 (仍可使用，限额较低)'}")
    
    results = await papers_mcp.search(
        query="cryptocurrency trading",
        source="semantic_scholar",
        max_results=3,
    )
    
    if results:
        print(f"   ✅ Semantic Scholar: 找到 {len(results)} 篇论文")
        for i, paper in enumerate(results[:2], 1):
            print(f"      {i}. {paper.title[:60]}... (引用: {paper.citation_count})")
    else:
        print("   ⚠️  Semantic Scholar: 无结果或请求失败")


async def test_news():
    """测试新闻聚合"""
    print("\n📰 测试新闻聚合...")
    print("-" * 40)
    
    from tools.mcp.news import NewsMCP
    news_mcp = NewsMCP()
    
    # 测试 Google News（不需要 API Key）
    print("1. Google News RSS...")
    results = await news_mcp.search(
        query="bitcoin",
        source="google",
        max_results=3,
    )
    
    if results:
        print(f"   ✅ Google News: 找到 {len(results)} 条新闻")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. {article.title[:60]}...")
    else:
        print("   ⚠️  Google News: 无结果")
    
    # 测试 NewsAPI
    print("\n2. NewsAPI...")
    newsapi_key = os.getenv("NEWSAPI_KEY")
    print(f"   API Key: {'已配置 ✅' if newsapi_key else '❌ 未配置'}")
    
    if newsapi_key:
        results = await news_mcp.search(
            query="cryptocurrency",
            source="newsapi",
            max_results=3,
        )
        
        if results:
            print(f"   ✅ NewsAPI: 找到 {len(results)} 条新闻")
            for i, article in enumerate(results[:2], 1):
                print(f"      {i}. [{article.source_name}] {article.title[:50]}...")
        else:
            print("   ⚠️  NewsAPI: 无结果或请求失败")
    else:
        print("   跳过（需要 NEWSAPI_KEY）")
        print("   获取: https://newsapi.org/register")
    
    # 测试加密货币新闻
    print("\n3. 加密货币新闻 RSS...")
    results = await news_mcp.search(
        query="bitcoin",
        source="crypto",
        max_results=3,
    )
    
    if results:
        print(f"   ✅ Crypto News: 找到 {len(results)} 条新闻")
    else:
        print("   ⚠️  Crypto News: 无结果")


async def test_social():
    """测试社交媒体"""
    print("\n🐦 测试社交媒体...")
    print("-" * 40)
    
    from tools.mcp.social import SocialMCP
    social_mcp = SocialMCP()
    
    # 测试 Reddit（不需要 API Key）
    print("1. Reddit 搜索...")
    results = await social_mcp.search(
        query="bitcoin",
        platform="reddit",
        max_results=5,
    )
    
    if results:
        print(f"   ✅ Reddit: 找到 {len(results)} 条帖子")
        for i, post in enumerate(results[:2], 1):
            print(f"      {i}. [👍{post.score}] {post.content[:50]}...")
    else:
        print("   ⚠️  Reddit: 无结果")
    
    # 测试 Hacker News（不需要 API Key）
    print("\n2. Hacker News 搜索...")
    results = await social_mcp.search(
        query="trading algorithm",
        platform="hackernews",
        max_results=5,
    )
    
    if results:
        print(f"   ✅ Hacker News: 找到 {len(results)} 条帖子")
        for i, post in enumerate(results[:2], 1):
            print(f"      {i}. [⬆️{post.score}] {post.content[:50]}...")
    else:
        print("   ⚠️  Hacker News: 无结果")
    
    # 测试 Twitter
    print("\n3. Twitter 搜索...")
    twitter_token = os.getenv("TWITTER_BEARER_TOKEN")
    print(f"   API Key: {'已配置 ✅' if twitter_token else '❌ 未配置'}")
    
    if twitter_token:
        results = await social_mcp.search(
            query="bitcoin",
            platform="twitter",
            max_results=5,
        )
        
        if results:
            print(f"   ✅ Twitter: 找到 {len(results)} 条推文")
        else:
            print("   ⚠️  Twitter: 无结果或请求失败")
    else:
        print("   跳过（需要 TWITTER_BEARER_TOKEN）")
        print("   获取: https://developer.twitter.com/en/portal/dashboard")


async def test_sentiment():
    """测试市场情绪"""
    print("\n📊 测试市场情绪...")
    print("-" * 40)
    
    from tools.mcp.sentiment import SentimentMCP
    sentiment_mcp = SentimentMCP()
    
    # 测试 Fear & Greed（不需要 API Key）
    print("1. Fear & Greed Index...")
    result = await sentiment_mcp.get_sentiment(indicator="fear_greed")
    
    if result.get("fear_greed"):
        fng = result["fear_greed"]
        emoji = {
            "extreme_fear": "😱",
            "fear": "😰",
            "neutral": "😐",
            "greed": "😀",
            "extreme_greed": "🤑",
        }.get(fng.label, "❓")
        print(f"   ✅ Fear & Greed: {fng.value} {emoji} ({fng.label})")
    else:
        print("   ⚠️  Fear & Greed: 获取失败")
    
    # 测试 Funding Rate（不需要 API Key）
    print("\n2. Funding Rate (Binance)...")
    result = await sentiment_mcp.get_sentiment(indicator="funding_rate", asset="BTC")
    
    if result.get("funding_rate"):
        for fr in result["funding_rate"]:
            sign = "+" if fr.rate > 0 else ""
            print(f"   ✅ {fr.symbol}: {sign}{fr.rate:.4f}%")
    else:
        print("   ⚠️  Funding Rate: 获取失败")
    
    # 综合情绪
    print("\n3. 综合市场情绪...")
    result = await sentiment_mcp.get_sentiment(indicator="all", asset="BTC")
    
    if result.get("summary"):
        summary = result["summary"]
        print(f"   整体情绪: {summary.get('overall_sentiment', 'unknown')}")
        print(f"   风险级别: {summary.get('risk_level', 'unknown')}")
        
        signals = summary.get("signals", [])
        if signals:
            print(f"   信号:")
            for sig in signals[:3]:
                print(f"      • {sig.get('message', '')}")


async def test_quant():
    """测试量化资讯"""
    print("\n📈 测试量化专业资讯...")
    print("-" * 40)
    
    from tools.mcp.quant import QuantMCP
    quant_mcp = QuantMCP()
    
    # 测试 arXiv q-fin
    print("1. arXiv 量化金融论文...")
    results = await quant_mcp.get_latest(source="arxiv", max_results=5)
    
    if results:
        print(f"   ✅ arXiv q-fin: 找到 {len(results)} 篇论文")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. {article.title[:55]}...")
            print(f"         分类: {', '.join(article.tags)}")
    else:
        print("   ⚠️  arXiv q-fin: 无结果")
    
    # 测试 Quantocracy
    print("\n2. Quantocracy 博客聚合...")
    results = await quant_mcp.get_latest(source="quantocracy", max_results=5)
    
    if results:
        print(f"   ✅ Quantocracy: 找到 {len(results)} 篇文章")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. {article.title[:55]}...")
    else:
        print("   ⚠️  Quantocracy: 无结果")
    
    # 测试 Reddit 量化社区
    print("\n3. Reddit 量化社区...")
    results = await quant_mcp.get_latest(source="reddit", max_results=5)
    
    if results:
        print(f"   ✅ Reddit: 找到 {len(results)} 条帖子")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. [⬆️{article.score}] [{article.source_name}] {article.title[:40]}...")
    else:
        print("   ⚠️  Reddit: 无结果")
    
    # 测试量化论文搜索
    print("\n4. 搜索量化论文...")
    results = await quant_mcp.search_quant_papers("momentum trading", max_results=3)
    
    if results:
        print(f"   ✅ 搜索结果: 找到 {len(results)} 篇论文")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. {article.title[:55]}...")
    else:
        print("   ⚠️  搜索: 无结果")
    
    # 测试加密货币研究
    print("\n5. 加密货币研究...")
    results = await quant_mcp.get_crypto_research(max_results=5)
    
    if results:
        print(f"   ✅ Crypto Research: 找到 {len(results)} 篇")
        for i, article in enumerate(results[:2], 1):
            print(f"      {i}. [{article.source_name}] {article.title[:45]}...")
    else:
        print("   ⚠️  Crypto Research: 无结果或 RSS 不可用")


async def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 AI Quant Company - MCP 工具测试")
    print("=" * 50)
    
    # 检查参数
    test_target = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_target in ["papers", "all"]:
        await test_papers()
    
    if test_target in ["news", "all"]:
        await test_news()
    
    if test_target in ["social", "all"]:
        await test_social()
    
    if test_target in ["sentiment", "all"]:
        await test_sentiment()
    
    if test_target in ["quant", "all"]:
        await test_quant()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成！")
    print("=" * 50)
    
    # 打印 API Key 状态总结
    print("\n📋 API Key 状态:")
    print(f"   NEWSAPI_KEY:              {'✅' if os.getenv('NEWSAPI_KEY') else '❌ (可选)'}")
    print(f"   SEMANTIC_SCHOLAR_API_KEY: {'✅' if os.getenv('SEMANTIC_SCHOLAR_API_KEY') else '⚪ (可选，无也能用)'}")
    print(f"   TWITTER_BEARER_TOKEN:     {'✅' if os.getenv('TWITTER_BEARER_TOKEN') else '❌ (可选)'}")
    print(f"   LUNARCRUSH_API_KEY:       {'✅' if os.getenv('LUNARCRUSH_API_KEY') else '⚪ (可选)'}")


if __name__ == "__main__":
    asyncio.run(main())
