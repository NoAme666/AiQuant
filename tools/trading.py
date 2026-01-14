# AI Quant Company - Trading Tools
"""
交易执行工具

提供:
- 模拟交易执行
- 实盘交易执行 (OKX)
- 订单管理
- 仓位监控
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class ExecutionMode(str, Enum):
    """执行模式"""
    SIMULATION = "simulation"
    LIVE = "live"


@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    order_id: str
    exchange_order_id: Optional[str] = None
    
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    price: float = 0.0
    filled_quantity: float = 0.0
    average_price: float = 0.0
    
    commission: float = 0.0
    slippage_bps: float = 0.0
    
    status: str = "pending"
    error: Optional[str] = None
    
    executed_at: Optional[datetime] = None
    metadata: dict = None


class TradingTools:
    """交易工具"""
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        """初始化交易工具
        
        Args:
            mode: 执行模式（模拟/实盘）
        """
        self.mode = mode
        self._exchange = None
        self._simulated_positions = {}
        self._simulated_balance = {
            "USDT": 10000.0,  # 模拟初始资金
        }
        
        if mode == ExecutionMode.LIVE:
            self._init_exchange()
        
        logger.info(f"TradingTools 初始化", mode=mode.value)
    
    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            import ccxt
            
            api_key = os.getenv("OKX_API_KEY")
            api_secret = os.getenv("OKX_API_SECRET")
            passphrase = os.getenv("OKX_PASSPHRASE")
            
            if not all([api_key, api_secret, passphrase]):
                logger.warning("OKX API 凭证未配置")
                return
            
            self._exchange = ccxt.okx({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                },
            })
            
            logger.info("OKX 交易所连接初始化成功")
            
        except ImportError:
            logger.warning("ccxt 未安装")
        except Exception as e:
            logger.error(f"交易所初始化失败: {e}")
    
    # ============================================
    # 下单接口
    # ============================================
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # buy, sell
        quantity: float,
        order_type: str = "market",  # market, limit
        price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        client_order_id: str = None,
    ) -> TradeResult:
        """下单
        
        Args:
            symbol: 交易对 (如 BTC/USDT)
            side: 买卖方向
            quantity: 数量
            order_type: 订单类型
            price: 限价（限价单必填）
            stop_loss: 止损价
            take_profit: 止盈价
            client_order_id: 客户端订单 ID
            
        Returns:
            交易结果
        """
        order_id = client_order_id or str(uuid4())
        
        if self.mode == ExecutionMode.SIMULATION:
            return await self._simulate_order(
                order_id, symbol, side, quantity, order_type, price
            )
        else:
            return await self._live_order(
                order_id, symbol, side, quantity, order_type, price
            )
    
    async def _simulate_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float,
    ) -> TradeResult:
        """模拟订单执行"""
        logger.info(
            "模拟下单",
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
        )
        
        # 获取当前价格
        current_price = await self._get_price(symbol)
        if not current_price:
            return TradeResult(
                success=False,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                error="无法获取价格",
            )
        
        # 模拟滑点
        import random
        slippage_pct = random.uniform(0.0001, 0.001)  # 0.01% - 0.1%
        
        if side == "buy":
            executed_price = current_price * (1 + slippage_pct)
        else:
            executed_price = current_price * (1 - slippage_pct)
        
        slippage_bps = abs(executed_price - current_price) / current_price * 10000
        
        # 模拟手续费
        commission = quantity * executed_price * 0.001  # 0.1%
        
        # 更新模拟持仓
        base_currency = symbol.split("/")[0]
        quote_currency = symbol.split("/")[1] if "/" in symbol else "USDT"
        
        if side == "buy":
            cost = quantity * executed_price + commission
            if self._simulated_balance.get(quote_currency, 0) < cost:
                return TradeResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    error="余额不足",
                )
            
            self._simulated_balance[quote_currency] = self._simulated_balance.get(quote_currency, 0) - cost
            self._simulated_balance[base_currency] = self._simulated_balance.get(base_currency, 0) + quantity
        else:
            if self._simulated_balance.get(base_currency, 0) < quantity:
                return TradeResult(
                    success=False,
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    error="持仓不足",
                )
            
            self._simulated_balance[base_currency] = self._simulated_balance.get(base_currency, 0) - quantity
            revenue = quantity * executed_price - commission
            self._simulated_balance[quote_currency] = self._simulated_balance.get(quote_currency, 0) + revenue
        
        logger.info(
            "模拟订单成交",
            order_id=order_id,
            executed_price=executed_price,
            slippage_bps=slippage_bps,
        )
        
        return TradeResult(
            success=True,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=current_price,
            filled_quantity=quantity,
            average_price=executed_price,
            commission=commission,
            slippage_bps=slippage_bps,
            status="filled",
            executed_at=datetime.utcnow(),
            metadata={"mode": "simulation"},
        )
    
    async def _live_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: float,
    ) -> TradeResult:
        """实盘订单执行"""
        if not self._exchange:
            return TradeResult(
                success=False,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                error="交易所未连接",
            )
        
        logger.info(
            "实盘下单",
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
        )
        
        try:
            # 执行订单
            if order_type == "market":
                order = self._exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=quantity,
                    params={'clientOrderId': order_id}
                )
            else:
                order = self._exchange.create_limit_order(
                    symbol=symbol,
                    side=side,
                    amount=quantity,
                    price=price,
                    params={'clientOrderId': order_id}
                )
            
            # 等待成交（简化处理）
            await asyncio.sleep(1)
            
            # 获取订单状态
            order_info = self._exchange.fetch_order(order['id'], symbol)
            
            filled_quantity = float(order_info.get('filled', 0))
            average_price = float(order_info.get('average', 0) or order_info.get('price', 0))
            
            # 计算滑点
            if order.get('price'):
                slippage_bps = abs(average_price - float(order['price'])) / float(order['price']) * 10000
            else:
                slippage_bps = 0
            
            logger.info(
                "实盘订单执行完成",
                order_id=order_id,
                exchange_order_id=order['id'],
                filled_quantity=filled_quantity,
                average_price=average_price,
            )
            
            return TradeResult(
                success=True,
                order_id=order_id,
                exchange_order_id=order['id'],
                symbol=symbol,
                side=side,
                quantity=quantity,
                filled_quantity=filled_quantity,
                average_price=average_price,
                slippage_bps=slippage_bps,
                status=order_info.get('status', 'unknown'),
                executed_at=datetime.utcnow(),
                metadata={"exchange": "okx", "order_info": order_info},
            )
            
        except Exception as e:
            logger.error(f"实盘下单失败: {e}")
            return TradeResult(
                success=False,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                error=str(e),
            )
    
    # ============================================
    # 订单管理
    # ============================================
    
    async def cancel_order(
        self,
        order_id: str,
        symbol: str,
    ) -> bool:
        """取消订单"""
        if self.mode == ExecutionMode.SIMULATION:
            logger.info(f"模拟取消订单: {order_id}")
            return True
        
        if not self._exchange:
            return False
        
        try:
            self._exchange.cancel_order(order_id, symbol)
            logger.info(f"订单已取消: {order_id}")
            return True
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
    
    async def get_order(
        self,
        order_id: str,
        symbol: str,
    ) -> Optional[dict]:
        """获取订单信息"""
        if self.mode == ExecutionMode.SIMULATION:
            return None  # 模拟模式没有持久化订单
        
        if not self._exchange:
            return None
        
        try:
            return self._exchange.fetch_order(order_id, symbol)
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return None
    
    async def get_open_orders(self, symbol: str = None) -> list[dict]:
        """获取未成交订单"""
        if self.mode == ExecutionMode.SIMULATION:
            return []
        
        if not self._exchange:
            return []
        
        try:
            return self._exchange.fetch_open_orders(symbol)
        except Exception as e:
            logger.error(f"获取未成交订单失败: {e}")
            return []
    
    # ============================================
    # 仓位和余额
    # ============================================
    
    async def get_balance(self) -> dict:
        """获取账户余额"""
        if self.mode == ExecutionMode.SIMULATION:
            return {
                "mode": "simulation",
                "balances": self._simulated_balance.copy(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        if not self._exchange:
            return {"error": "交易所未连接", "balances": {}}
        
        try:
            balance = self._exchange.fetch_balance()
            
            result = {
                "mode": "live",
                "exchange": "okx",
                "balances": {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            for asset, amount in balance.get('total', {}).items():
                if amount and float(amount) > 0:
                    result["balances"][asset] = {
                        "free": float(balance['free'].get(asset, 0) or 0),
                        "locked": float(balance['used'].get(asset, 0) or 0),
                        "total": float(amount),
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return {"error": str(e), "balances": {}}
    
    async def get_positions(self) -> list[dict]:
        """获取持仓"""
        if self.mode == ExecutionMode.SIMULATION:
            positions = []
            for asset, amount in self._simulated_balance.items():
                if amount > 0 and asset != "USDT":
                    price = await self._get_price(f"{asset}/USDT")
                    positions.append({
                        "symbol": f"{asset}/USDT",
                        "side": "long",
                        "quantity": amount,
                        "entry_price": price or 0,
                        "current_price": price or 0,
                        "unrealized_pnl": 0,
                        "mode": "simulation",
                    })
            return positions
        
        if not self._exchange:
            return []
        
        try:
            # OKX 现货没有持仓概念，用余额代替
            balance = await self.get_balance()
            positions = []
            
            for asset, data in balance.get("balances", {}).items():
                if asset != "USDT" and data.get("total", 0) > 0:
                    price = await self._get_price(f"{asset}/USDT")
                    positions.append({
                        "symbol": f"{asset}/USDT",
                        "side": "long",
                        "quantity": data["total"],
                        "entry_price": price or 0,
                        "current_price": price or 0,
                        "value_usd": data["total"] * (price or 0),
                        "mode": "live",
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    # ============================================
    # 市场数据
    # ============================================
    
    async def _get_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        try:
            import ccxt
            
            # 使用公共 API
            exchange = ccxt.okx({'enableRateLimit': True})
            ticker = exchange.fetch_ticker(symbol)
            return float(ticker['last'])
            
        except Exception as e:
            logger.warning(f"获取价格失败 {symbol}: {e}")
            
            # 返回模拟价格
            if "BTC" in symbol:
                return 95000.0
            elif "ETH" in symbol:
                return 3500.0
            else:
                return 100.0
    
    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """获取行情"""
        try:
            import ccxt
            exchange = ccxt.okx({'enableRateLimit': True})
            ticker = exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker['last'],
                "bid": ticker['bid'],
                "ask": ticker['ask'],
                "high": ticker['high'],
                "low": ticker['low'],
                "volume": ticker['baseVolume'],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return None
    
    # ============================================
    # 风险检查
    # ============================================
    
    async def check_risk_limits(
        self,
        symbol: str,
        side: str,
        quantity: float,
        max_position_pct: float = 0.1,
        max_order_value: float = 10000,
    ) -> dict:
        """检查风险限额
        
        Args:
            symbol: 交易对
            side: 方向
            quantity: 数量
            max_position_pct: 最大仓位占比
            max_order_value: 最大订单价值 (USDT)
            
        Returns:
            风险检查结果
        """
        price = await self._get_price(symbol)
        if not price:
            return {"passed": False, "error": "无法获取价格"}
        
        order_value = quantity * price
        
        # 检查订单价值
        if order_value > max_order_value:
            return {
                "passed": False,
                "error": f"订单价值 ${order_value:.2f} 超过限额 ${max_order_value:.2f}",
            }
        
        # 获取当前余额
        balance = await self.get_balance()
        total_balance = sum(
            v.get("total", v) * await self._get_price(f"{k}/USDT") if k != "USDT" else v.get("total", v)
            for k, v in balance.get("balances", {}).items()
        ) if isinstance(balance.get("balances"), dict) else 10000
        
        # 检查仓位占比
        position_pct = order_value / total_balance if total_balance > 0 else 1
        if position_pct > max_position_pct:
            return {
                "passed": False,
                "error": f"仓位占比 {position_pct:.1%} 超过限额 {max_position_pct:.1%}",
            }
        
        return {
            "passed": True,
            "order_value": order_value,
            "position_pct": position_pct,
            "price": price,
        }


# ============================================
# 便捷函数
# ============================================

_trading_tools: dict[str, TradingTools] = {}


def get_trading_tools(mode: ExecutionMode = ExecutionMode.SIMULATION) -> TradingTools:
    """获取交易工具实例"""
    if mode.value not in _trading_tools:
        _trading_tools[mode.value] = TradingTools(mode)
    return _trading_tools[mode.value]


async def place_simulation_order(
    symbol: str,
    side: str,
    quantity: float,
    **kwargs,
) -> TradeResult:
    """下模拟订单"""
    tools = get_trading_tools(ExecutionMode.SIMULATION)
    return await tools.place_order(symbol, side, quantity, **kwargs)


async def place_live_order(
    symbol: str,
    side: str,
    quantity: float,
    **kwargs,
) -> TradeResult:
    """下实盘订单"""
    tools = get_trading_tools(ExecutionMode.LIVE)
    return await tools.place_order(symbol, side, quantity, **kwargs)
