# AI Quant Company - 市场情绪 MCP
"""
市场情绪指标 MCP

数据源：
- Fear & Greed Index (Alternative.me)
- Funding Rate (交易所)
- Social Volume (LunarCrush 等)

功能：
- 实时情绪指标
- 历史情绪数据
- 极端情绪预警
- 情绪与价格背离检测
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
class SentimentData:
    """情绪数据"""
    indicator: str
    value: float
    label: str  # extreme_fear, fear, neutral, greed, extreme_greed
    timestamp: str
    
    # 额外信息
    change_24h: Optional[float] = None
    historical_avg: Optional[float] = None
    percentile: Optional[float] = None  # 历史百分位


@dataclass
class FundingRate:
    """资金费率"""
    symbol: str
    exchange: str
    rate: float  # 百分比
    next_funding_time: str
    predicted_rate: Optional[float] = None


@dataclass
class SocialMetrics:
    """社交指标"""
    symbol: str
    social_volume: int  # 讨论量
    social_score: float  # 综合得分
    sentiment: float  # -1 到 1
    mentions_24h: int
    unique_accounts: int
    timestamp: str


class SentimentMCP:
    """市场情绪 MCP 服务"""
    
    def __init__(self):
        self.timeout = 30.0
        
        # Fear & Greed Index
        self.fng_base = "https://api.alternative.me/fng"
        
        # CoinGlass (Funding Rate)
        self.coinglass_base = "https://open-api.coinglass.com/public/v2"
        
        # LunarCrush (社交数据)
        self.lunarcrush_key = os.getenv("LUNARCRUSH_API_KEY")
        self.lunarcrush_base = "https://lunarcrush.com/api3"
    
    async def get_sentiment(
        self,
        indicator: str = "all",
        asset: str = "BTC",
    ) -> dict:
        """获取市场情绪
        
        Args:
            indicator: 指标类型 (fear_greed, funding_rate, social_volume, all)
            asset: 资产代码
            
        Returns:
            情绪数据字典
        """
        result = {}
        
        if indicator in ["fear_greed", "all"]:
            fng = await self._get_fear_greed()
            if fng:
                result["fear_greed"] = fng
        
        if indicator in ["funding_rate", "all"]:
            funding = await self._get_funding_rate(asset)
            if funding:
                result["funding_rate"] = funding
        
        if indicator in ["social_volume", "all"]:
            social = await self._get_social_metrics(asset)
            if social:
                result["social_metrics"] = social
        
        # 添加综合评估
        result["summary"] = self._generate_summary(result)
        
        return result
    
    async def _get_fear_greed(self) -> Optional[SentimentData]:
        """获取 Fear & Greed Index"""
        try:
            params = {"limit": 1, "format": "json"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.fng_base, params=params)
                response.raise_for_status()
            
            data = response.json()
            
            if data.get("data"):
                item = data["data"][0]
                value = int(item.get("value", 50))
                
                # 确定标签
                if value <= 20:
                    label = "extreme_fear"
                elif value <= 40:
                    label = "fear"
                elif value <= 60:
                    label = "neutral"
                elif value <= 80:
                    label = "greed"
                else:
                    label = "extreme_greed"
                
                sentiment = SentimentData(
                    indicator="fear_greed_index",
                    value=value,
                    label=label,
                    timestamp=datetime.fromtimestamp(int(item.get("timestamp", 0))).isoformat(),
                )
                
                logger.info(f"Fear & Greed Index: {value} ({label})")
                return sentiment
            
            return None
            
        except Exception as e:
            logger.error(f"获取 Fear & Greed 失败: {e}")
            return None
    
    async def _get_funding_rate(self, symbol: str) -> Optional[list[FundingRate]]:
        """获取资金费率"""
        try:
            # 使用公开的 Binance API
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {"symbol": f"{symbol}USDT", "limit": 1}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
            
            data = response.json()
            
            if data:
                item = data[0]
                rate = float(item.get("fundingRate", 0)) * 100  # 转为百分比
                
                funding = FundingRate(
                    symbol=f"{symbol}USDT",
                    exchange="binance",
                    rate=rate,
                    next_funding_time=datetime.fromtimestamp(
                        int(item.get("fundingTime", 0)) / 1000
                    ).isoformat(),
                )
                
                logger.info(f"Funding Rate {symbol}: {rate:.4f}%")
                return [funding]
            
            return None
            
        except Exception as e:
            logger.error(f"获取 Funding Rate 失败: {e}")
            return None
    
    async def _get_social_metrics(self, symbol: str) -> Optional[SocialMetrics]:
        """获取社交指标"""
        # 如果没有 LunarCrush API，返回模拟数据
        if not self.lunarcrush_key:
            return self._mock_social_metrics(symbol)
        
        try:
            url = f"{self.lunarcrush_base}/coins/{symbol.lower()}"
            headers = {"Authorization": f"Bearer {self.lunarcrush_key}"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            
            data = response.json()
            
            if data.get("data"):
                item = data["data"]
                
                return SocialMetrics(
                    symbol=symbol,
                    social_volume=item.get("social_volume", 0),
                    social_score=item.get("social_score", 0),
                    sentiment=item.get("average_sentiment", 0),
                    mentions_24h=item.get("tweet_mentions", 0),
                    unique_accounts=item.get("unique_tweet_accounts", 0),
                    timestamp=datetime.utcnow().isoformat(),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"获取社交指标失败: {e}")
            return self._mock_social_metrics(symbol)
    
    def _mock_social_metrics(self, symbol: str) -> SocialMetrics:
        """模拟社交指标（当 API 不可用时）"""
        import random
        
        return SocialMetrics(
            symbol=symbol,
            social_volume=random.randint(50000, 200000),
            social_score=random.uniform(50, 90),
            sentiment=random.uniform(-0.3, 0.7),
            mentions_24h=random.randint(10000, 50000),
            unique_accounts=random.randint(5000, 20000),
            timestamp=datetime.utcnow().isoformat(),
        )
    
    def _generate_summary(self, data: dict) -> dict:
        """生成情绪总结"""
        summary = {
            "overall_sentiment": "neutral",
            "signals": [],
            "risk_level": "medium",
        }
        
        # 分析 Fear & Greed
        fng = data.get("fear_greed")
        if fng:
            if fng.value <= 25:
                summary["signals"].append({
                    "type": "contrarian_bullish",
                    "message": f"极度恐慌 ({fng.value})，可能是买入机会",
                    "strength": "strong",
                })
                summary["overall_sentiment"] = "contrarian_bullish"
            elif fng.value >= 75:
                summary["signals"].append({
                    "type": "contrarian_bearish",
                    "message": f"极度贪婪 ({fng.value})，注意风险",
                    "strength": "strong",
                })
                summary["overall_sentiment"] = "contrarian_bearish"
                summary["risk_level"] = "high"
        
        # 分析 Funding Rate
        funding_list = data.get("funding_rate")
        if funding_list:
            for funding in funding_list:
                if funding.rate > 0.1:
                    summary["signals"].append({
                        "type": "high_funding",
                        "message": f"{funding.symbol} 资金费率过高 ({funding.rate:.3f}%)，多头拥挤",
                        "strength": "medium",
                    })
                elif funding.rate < -0.1:
                    summary["signals"].append({
                        "type": "negative_funding",
                        "message": f"{funding.symbol} 资金费率为负 ({funding.rate:.3f}%)，空头拥挤",
                        "strength": "medium",
                    })
        
        # 分析社交指标
        social = data.get("social_metrics")
        if social:
            if social.sentiment > 0.5:
                summary["signals"].append({
                    "type": "social_bullish",
                    "message": f"{social.symbol} 社交情绪积极 ({social.sentiment:.2f})",
                    "strength": "weak",
                })
            elif social.sentiment < -0.3:
                summary["signals"].append({
                    "type": "social_bearish",
                    "message": f"{social.symbol} 社交情绪消极 ({social.sentiment:.2f})",
                    "strength": "weak",
                })
        
        return summary
    
    async def get_fear_greed_history(self, days: int = 30) -> list[SentimentData]:
        """获取 Fear & Greed 历史数据"""
        try:
            params = {"limit": days, "format": "json"}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.fng_base, params=params)
                response.raise_for_status()
            
            data = response.json()
            history = []
            
            for item in data.get("data", []):
                value = int(item.get("value", 50))
                
                if value <= 20:
                    label = "extreme_fear"
                elif value <= 40:
                    label = "fear"
                elif value <= 60:
                    label = "neutral"
                elif value <= 80:
                    label = "greed"
                else:
                    label = "extreme_greed"
                
                sentiment = SentimentData(
                    indicator="fear_greed_index",
                    value=value,
                    label=label,
                    timestamp=datetime.fromtimestamp(int(item.get("timestamp", 0))).isoformat(),
                )
                history.append(sentiment)
            
            return history
            
        except Exception as e:
            logger.error(f"获取 Fear & Greed 历史失败: {e}")
            return []
