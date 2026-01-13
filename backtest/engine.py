# AI Quant Company - 轻量回测引擎
"""
Backtest Engine

轻量级、可复现的回测引擎，输出标准化产物。

输入:
- signals: 目标仓位或买卖信号
- prices: OHLCV 数据
- cost_model: 交易成本模型
- constraints: 约束条件

输出:
- positions.parquet: 每日持仓
- trades.parquet: 交易记录
- equity_curve.parquet: 净值曲线
- metrics.json: 绩效指标
- experiment_id: 唯一实验标识
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()


# ============================================
# 数据结构
# ============================================

@dataclass
class CostModel:
    """交易成本模型"""
    commission_rate: float = 0.001      # 手续费率 (0.1%)
    slippage_rate: float = 0.0005       # 滑点率 (0.05%)
    min_commission: float = 0.0         # 最小手续费
    
    # 市场冲击模型参数（可选）
    impact_coefficient: float = 0.0     # 冲击系数
    
    def calculate_cost(
        self,
        trade_value: float,
        volume: Optional[float] = None,
    ) -> float:
        """计算交易成本
        
        Args:
            trade_value: 交易金额（绝对值）
            volume: 市场成交量（用于冲击计算）
            
        Returns:
            总成本
        """
        # 手续费
        commission = max(
            abs(trade_value) * self.commission_rate,
            self.min_commission,
        )
        
        # 滑点
        slippage = abs(trade_value) * self.slippage_rate
        
        # 市场冲击
        impact = 0.0
        if self.impact_coefficient > 0 and volume and volume > 0:
            participation = abs(trade_value) / volume
            impact = abs(trade_value) * self.impact_coefficient * np.sqrt(participation)
        
        return commission + slippage + impact


@dataclass
class Constraints:
    """回测约束条件"""
    max_leverage: float = 1.0           # 最大杠杆
    max_position_size: float = 1.0      # 单一标的最大仓位
    max_turnover_daily: float = 2.0     # 日最大换手
    min_trade_size: float = 0.0         # 最小交易规模


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 1_000_000.0
    cost_model: CostModel = field(default_factory=CostModel)
    constraints: Constraints = field(default_factory=Constraints)
    
    # 执行细节
    execution_price: str = "close"      # 成交价: "open", "close", "vwap"
    rebalance_time: str = "close"       # 再平衡时间
    
    # 随机种子（用于复现）
    random_seed: Optional[int] = None


@dataclass
class Trade:
    """交易记录"""
    timestamp: datetime
    symbol: str
    side: str               # "buy" or "sell"
    quantity: float
    price: float
    value: float
    cost: float
    
    # 关联
    signal_value: float = 0.0


@dataclass
class BacktestResult:
    """回测结果"""
    experiment_id: str
    
    # 核心产物
    positions: pd.DataFrame       # 每日持仓
    trades: pd.DataFrame          # 交易记录
    equity_curve: pd.DataFrame    # 净值曲线
    metrics: dict                 # 绩效指标
    
    # 元数据
    config: BacktestConfig
    data_version_hash: str
    config_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # 产物路径
    artifacts_path: Optional[str] = None


# ============================================
# 回测引擎
# ============================================

class BacktestEngine:
    """轻量回测引擎
    
    支持:
    - 多标的组合回测
    - 交易成本建模
    - 约束检查
    - 标准化产物输出
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """初始化回测引擎
        
        Args:
            config: 回测配置
        """
        self.config = config or BacktestConfig()
        
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)
    
    def run(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        data_version_hash: str = "",
    ) -> BacktestResult:
        """运行回测
        
        Args:
            signals: 信号 DataFrame，columns=[timestamp, symbol, signal]
                     signal 可以是目标权重 (-1 到 1) 或买卖信号
            prices: 价格 DataFrame，columns=[timestamp, symbol, open, high, low, close, volume]
            data_version_hash: 数据版本哈希
            
        Returns:
            回测结果
        """
        logger.info("开始回测", initial_capital=self.config.initial_capital)
        
        # 生成实验 ID
        experiment_id = self._generate_experiment_id()
        config_hash = self._compute_config_hash()
        
        # 数据预处理
        signals = self._prepare_signals(signals)
        prices = self._prepare_prices(prices)
        
        # 获取时间序列
        timestamps = sorted(prices["timestamp"].unique())
        symbols = sorted(signals["symbol"].unique())
        
        # 初始化
        capital = self.config.initial_capital
        positions: dict[str, float] = {s: 0.0 for s in symbols}
        
        # 记录
        position_records = []
        trade_records = []
        equity_records = []
        
        # 遍历每个时间点
        for i, ts in enumerate(timestamps):
            # 获取当前价格
            current_prices = prices[prices["timestamp"] == ts].set_index("symbol")
            
            # 获取当前信号
            current_signals = signals[signals["timestamp"] == ts].set_index("symbol")
            
            # 计算目标仓位
            target_positions = self._calculate_target_positions(
                current_signals,
                current_prices,
                capital,
                positions,
            )
            
            # 执行交易
            trades, trade_cost = self._execute_trades(
                positions,
                target_positions,
                current_prices,
                ts,
            )
            
            # 更新持仓
            positions = target_positions.copy()
            
            # 记录交易
            trade_records.extend(trades)
            
            # 计算持仓价值
            position_value = sum(
                positions.get(s, 0) * current_prices.loc[s, "close"]
                for s in positions
                if s in current_prices.index
            )
            
            # 更新资本（扣除交易成本）
            cash = capital - position_value
            total_value = cash + position_value
            
            # 记录持仓
            for symbol, qty in positions.items():
                if symbol in current_prices.index:
                    position_records.append({
                        "timestamp": ts,
                        "symbol": symbol,
                        "quantity": qty,
                        "price": current_prices.loc[symbol, "close"],
                        "value": qty * current_prices.loc[symbol, "close"],
                    })
            
            # 记录净值
            equity_records.append({
                "timestamp": ts,
                "equity": total_value,
                "cash": cash,
                "position_value": position_value,
                "trade_cost": trade_cost,
            })
            
            # 更新资本
            capital = total_value - trade_cost
        
        # 构建结果 DataFrame
        positions_df = pd.DataFrame(position_records)
        trades_df = pd.DataFrame([
            {
                "timestamp": t.timestamp,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "price": t.price,
                "value": t.value,
                "cost": t.cost,
            }
            for t in trade_records
        ])
        equity_df = pd.DataFrame(equity_records)
        
        # 计算指标
        metrics = self._calculate_metrics(equity_df, trades_df)
        
        logger.info(
            "回测完成",
            experiment_id=experiment_id,
            final_equity=equity_df["equity"].iloc[-1] if not equity_df.empty else 0,
            total_trades=len(trade_records),
        )
        
        return BacktestResult(
            experiment_id=experiment_id,
            positions=positions_df,
            trades=trades_df,
            equity_curve=equity_df,
            metrics=metrics,
            config=self.config,
            data_version_hash=data_version_hash,
            config_hash=config_hash,
        )
    
    def _prepare_signals(self, signals: pd.DataFrame) -> pd.DataFrame:
        """预处理信号数据"""
        df = signals.copy()
        
        # 确保时间列
        if "timestamp" not in df.columns and "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        
        # 确保必要列
        required_cols = ["timestamp", "symbol", "signal"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"信号数据缺少列: {col}")
        
        return df.sort_values("timestamp")
    
    def _prepare_prices(self, prices: pd.DataFrame) -> pd.DataFrame:
        """预处理价格数据"""
        df = prices.copy()
        
        # 确保时间列
        if "timestamp" not in df.columns and "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        
        # 确保必要列
        required_cols = ["timestamp", "symbol", "close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"价格数据缺少列: {col}")
        
        return df.sort_values("timestamp")
    
    def _calculate_target_positions(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        capital: float,
        current_positions: dict[str, float],
    ) -> dict[str, float]:
        """计算目标仓位
        
        Args:
            signals: 当前信号
            prices: 当前价格
            capital: 当前资本
            current_positions: 当前持仓
            
        Returns:
            目标持仓字典 {symbol: quantity}
        """
        target = {}
        
        for symbol in signals.index:
            if symbol not in prices.index:
                continue
            
            signal = signals.loc[symbol, "signal"]
            price = prices.loc[symbol, "close"]
            
            # 信号转换为目标权重（假设 signal 已经是 -1 到 1 的权重）
            weight = np.clip(signal, -1, 1)
            
            # 应用约束
            weight = np.clip(
                weight,
                -self.config.constraints.max_position_size,
                self.config.constraints.max_position_size,
            )
            
            # 计算目标数量
            target_value = capital * weight * self.config.constraints.max_leverage
            target_qty = target_value / price if price > 0 else 0
            
            target[symbol] = target_qty
        
        return target
    
    def _execute_trades(
        self,
        current_positions: dict[str, float],
        target_positions: dict[str, float],
        prices: pd.DataFrame,
        timestamp: datetime,
    ) -> tuple[list[Trade], float]:
        """执行交易
        
        Returns:
            (交易列表, 总成本)
        """
        trades = []
        total_cost = 0.0
        
        for symbol, target_qty in target_positions.items():
            current_qty = current_positions.get(symbol, 0.0)
            diff = target_qty - current_qty
            
            if abs(diff) < 1e-8:  # 忽略极小差异
                continue
            
            if symbol not in prices.index:
                continue
            
            price = prices.loc[symbol, self.config.execution_price]
            volume = prices.loc[symbol, "volume"] if "volume" in prices.columns else None
            
            # 计算交易金额
            trade_value = diff * price
            
            # 计算成本
            cost = self.config.cost_model.calculate_cost(trade_value, volume)
            total_cost += cost
            
            # 记录交易
            trade = Trade(
                timestamp=timestamp,
                symbol=symbol,
                side="buy" if diff > 0 else "sell",
                quantity=abs(diff),
                price=price,
                value=abs(trade_value),
                cost=cost,
            )
            trades.append(trade)
        
        return trades, total_cost
    
    def _calculate_metrics(
        self,
        equity_df: pd.DataFrame,
        trades_df: pd.DataFrame,
    ) -> dict:
        """计算绩效指标"""
        if equity_df.empty:
            return {}
        
        equity = equity_df["equity"].values
        initial = equity[0]
        final = equity[-1]
        
        # 收益率序列
        returns = np.diff(equity) / equity[:-1]
        returns = returns[~np.isnan(returns)]
        
        # 基础指标
        total_return = (final - initial) / initial
        
        # 年化（假设日频）
        n_days = len(equity)
        annualized_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1
        
        # 波动率
        if len(returns) > 1:
            daily_vol = np.std(returns)
            annualized_vol = daily_vol * np.sqrt(252)
        else:
            daily_vol = annualized_vol = 0.0
        
        # Sharpe Ratio (假设无风险利率为 0)
        sharpe = annualized_return / annualized_vol if annualized_vol > 0 else 0.0
        
        # 下行波动率和 Sortino
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_vol = np.std(negative_returns) * np.sqrt(252)
            sortino = annualized_return / downside_vol if downside_vol > 0 else 0.0
        else:
            downside_vol = 0.0
            sortino = 0.0
        
        # 最大回撤
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_drawdown = abs(np.min(drawdown))
        
        # Calmar Ratio
        calmar = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # 交易统计
        n_trades = len(trades_df)
        if n_trades > 0:
            total_cost = trades_df["cost"].sum()
            turnover = trades_df["value"].sum() / initial
            annual_turnover = turnover * (252 / max(n_days, 1))
        else:
            total_cost = 0.0
            turnover = annual_turnover = 0.0
        
        # 胜率和盈亏比
        if len(returns) > 0:
            winning_returns = returns[returns > 0]
            losing_returns = returns[returns < 0]
            
            win_rate = len(winning_returns) / len(returns)
            
            if len(winning_returns) > 0 and len(losing_returns) > 0:
                avg_win = np.mean(winning_returns)
                avg_loss = abs(np.mean(losing_returns))
                profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
            else:
                profit_loss_ratio = 0.0
        else:
            win_rate = profit_loss_ratio = 0.0
        
        # 最大连续亏损
        max_consecutive_losses = 0
        current_streak = 0
        for r in returns:
            if r < 0:
                current_streak += 1
                max_consecutive_losses = max(max_consecutive_losses, current_streak)
            else:
                current_streak = 0
        
        return {
            "total_return": float(total_return),
            "annualized_return": float(annualized_return),
            "annualized_volatility": float(annualized_vol),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "max_drawdown": float(max_drawdown),
            "calmar_ratio": float(calmar),
            "win_rate": float(win_rate),
            "profit_loss_ratio": float(profit_loss_ratio),
            "total_trades": int(n_trades),
            "total_cost": float(total_cost),
            "annual_turnover": float(annual_turnover),
            "max_consecutive_losses": int(max_consecutive_losses),
            "initial_capital": float(initial),
            "final_capital": float(final),
            "n_days": int(n_days),
        }
    
    def _generate_experiment_id(self) -> str:
        """生成实验 ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_part = uuid4().hex[:8].upper()
        return f"EXP_{timestamp}_{random_part}"
    
    def _compute_config_hash(self) -> str:
        """计算配置哈希"""
        config_dict = {
            "initial_capital": self.config.initial_capital,
            "commission_rate": self.config.cost_model.commission_rate,
            "slippage_rate": self.config.cost_model.slippage_rate,
            "max_leverage": self.config.constraints.max_leverage,
            "max_position_size": self.config.constraints.max_position_size,
            "execution_price": self.config.execution_price,
            "random_seed": self.config.random_seed,
        }
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def save_results(
        self,
        result: BacktestResult,
        output_dir: str = "./artifacts/experiments",
    ) -> str:
        """保存回测结果
        
        Args:
            result: 回测结果
            output_dir: 输出目录
            
        Returns:
            产物目录路径
        """
        # 创建目录
        artifact_path = Path(output_dir) / result.experiment_id
        artifact_path.mkdir(parents=True, exist_ok=True)
        
        # 保存 parquet 文件
        result.positions.to_parquet(artifact_path / "positions.parquet")
        result.trades.to_parquet(artifact_path / "trades.parquet")
        result.equity_curve.to_parquet(artifact_path / "equity_curve.parquet")
        
        # 保存指标
        with open(artifact_path / "metrics.json", "w") as f:
            json.dump(result.metrics, f, indent=2)
        
        # 保存元数据
        metadata = {
            "experiment_id": result.experiment_id,
            "data_version_hash": result.data_version_hash,
            "config_hash": result.config_hash,
            "created_at": result.created_at.isoformat(),
            "config": {
                "initial_capital": result.config.initial_capital,
                "commission_rate": result.config.cost_model.commission_rate,
                "slippage_rate": result.config.cost_model.slippage_rate,
                "max_leverage": result.config.constraints.max_leverage,
            },
        }
        with open(artifact_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        result.artifacts_path = str(artifact_path)
        
        logger.info(
            "保存回测结果",
            experiment_id=result.experiment_id,
            path=str(artifact_path),
        )
        
        return str(artifact_path)
