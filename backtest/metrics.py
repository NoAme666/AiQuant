# AI Quant Company - 回测指标计算
"""
绩效指标计算模块

提供标准化的绩效指标计算函数。
"""

from typing import Optional

import numpy as np
import pandas as pd


def calculate_returns(prices: pd.Series) -> pd.Series:
    """计算收益率序列"""
    return prices.pct_change().dropna()


def calculate_log_returns(prices: pd.Series) -> pd.Series:
    """计算对数收益率序列"""
    return np.log(prices / prices.shift(1)).dropna()


def calculate_annualized_return(
    returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """计算年化收益率
    
    Args:
        returns: 收益率序列
        periods_per_year: 每年周期数（日频=252，周频=52）
    """
    total_return = (1 + returns).prod() - 1
    n_periods = len(returns)
    
    if n_periods == 0:
        return 0.0
    
    annualized = (1 + total_return) ** (periods_per_year / n_periods) - 1
    return float(annualized)


def calculate_annualized_volatility(
    returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """计算年化波动率"""
    if len(returns) < 2:
        return 0.0
    
    return float(returns.std() * np.sqrt(periods_per_year))


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """计算 Sharpe Ratio
    
    Args:
        returns: 收益率序列
        risk_free_rate: 年化无风险利率
        periods_per_year: 每年周期数
    """
    if len(returns) < 2:
        return 0.0
    
    excess_return = calculate_annualized_return(returns, periods_per_year) - risk_free_rate
    volatility = calculate_annualized_volatility(returns, periods_per_year)
    
    if volatility == 0:
        return 0.0
    
    return float(excess_return / volatility)


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """计算 Sortino Ratio（仅考虑下行风险）"""
    if len(returns) < 2:
        return 0.0
    
    excess_return = calculate_annualized_return(returns, periods_per_year) - risk_free_rate
    
    # 下行波动率
    negative_returns = returns[returns < 0]
    if len(negative_returns) < 2:
        return float('inf') if excess_return > 0 else 0.0
    
    downside_vol = negative_returns.std() * np.sqrt(periods_per_year)
    
    if downside_vol == 0:
        return 0.0
    
    return float(excess_return / downside_vol)


def calculate_max_drawdown(equity: pd.Series) -> tuple[float, int, int]:
    """计算最大回撤
    
    Returns:
        (最大回撤, 峰值索引, 谷底索引)
    """
    if len(equity) == 0:
        return 0.0, 0, 0
    
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak
    
    max_dd = abs(drawdown.min())
    trough_idx = drawdown.idxmin()
    peak_idx = equity[:trough_idx].idxmax() if trough_idx != equity.index[0] else equity.index[0]
    
    return float(max_dd), peak_idx, trough_idx


def calculate_drawdown_duration(equity: pd.Series) -> pd.DataFrame:
    """计算回撤持续时间
    
    Returns:
        DataFrame with columns [start, end, duration, depth]
    """
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak
    
    # 找出回撤期间
    in_drawdown = drawdown < 0
    
    # 标记回撤开始和结束
    dd_start = in_drawdown & ~in_drawdown.shift(1, fill_value=False)
    dd_end = ~in_drawdown & in_drawdown.shift(1, fill_value=False)
    
    starts = equity.index[dd_start].tolist()
    ends = equity.index[dd_end].tolist()
    
    # 如果当前还在回撤中
    if in_drawdown.iloc[-1]:
        ends.append(equity.index[-1])
    
    records = []
    for start, end in zip(starts, ends):
        dd_period = drawdown[start:end]
        depth = abs(dd_period.min())
        duration = len(dd_period)
        records.append({
            "start": start,
            "end": end,
            "duration": duration,
            "depth": depth,
        })
    
    return pd.DataFrame(records)


def calculate_calmar_ratio(
    returns: pd.Series,
    equity: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """计算 Calmar Ratio（年化收益/最大回撤）"""
    ann_return = calculate_annualized_return(returns, periods_per_year)
    max_dd, _, _ = calculate_max_drawdown(equity)
    
    if max_dd == 0:
        return 0.0
    
    return float(ann_return / max_dd)


def calculate_var(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """计算 VaR (Value at Risk)
    
    Args:
        returns: 收益率序列
        confidence: 置信度
    """
    if len(returns) == 0:
        return 0.0
    
    return float(np.percentile(returns, (1 - confidence) * 100))


def calculate_cvar(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """计算 CVaR (Conditional VaR / Expected Shortfall)"""
    if len(returns) == 0:
        return 0.0
    
    var = calculate_var(returns, confidence)
    return float(returns[returns <= var].mean())


def calculate_win_rate(returns: pd.Series) -> float:
    """计算胜率"""
    if len(returns) == 0:
        return 0.0
    
    return float((returns > 0).mean())


def calculate_profit_factor(returns: pd.Series) -> float:
    """计算盈利因子（总盈利/总亏损）"""
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    
    if losses == 0:
        return float('inf') if gains > 0 else 0.0
    
    return float(gains / losses)


def calculate_profit_loss_ratio(returns: pd.Series) -> float:
    """计算盈亏比（平均盈利/平均亏损）"""
    gains = returns[returns > 0]
    losses = returns[returns < 0]
    
    if len(gains) == 0 or len(losses) == 0:
        return 0.0
    
    avg_gain = gains.mean()
    avg_loss = abs(losses.mean())
    
    if avg_loss == 0:
        return float('inf') if avg_gain > 0 else 0.0
    
    return float(avg_gain / avg_loss)


def calculate_information_ratio(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """计算信息比率
    
    Args:
        returns: 策略收益率
        benchmark_returns: 基准收益率
    """
    if len(returns) != len(benchmark_returns):
        # 对齐数据
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        returns = aligned.iloc[:, 0]
        benchmark_returns = aligned.iloc[:, 1]
    
    if len(returns) < 2:
        return 0.0
    
    excess_returns = returns - benchmark_returns
    tracking_error = excess_returns.std() * np.sqrt(periods_per_year)
    
    if tracking_error == 0:
        return 0.0
    
    ann_excess = calculate_annualized_return(excess_returns, periods_per_year)
    
    return float(ann_excess / tracking_error)


def calculate_beta(
    returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """计算 Beta"""
    if len(returns) != len(benchmark_returns):
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        returns = aligned.iloc[:, 0]
        benchmark_returns = aligned.iloc[:, 1]
    
    if len(returns) < 2:
        return 0.0
    
    covariance = np.cov(returns, benchmark_returns)[0, 1]
    variance = np.var(benchmark_returns)
    
    if variance == 0:
        return 0.0
    
    return float(covariance / variance)


def calculate_alpha(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """计算 Alpha (Jensen's Alpha)"""
    beta = calculate_beta(returns, benchmark_returns)
    
    ann_return = calculate_annualized_return(returns, periods_per_year)
    ann_benchmark = calculate_annualized_return(benchmark_returns, periods_per_year)
    
    expected_return = risk_free_rate + beta * (ann_benchmark - risk_free_rate)
    
    return float(ann_return - expected_return)


def calculate_all_metrics(
    equity: pd.Series,
    benchmark: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> dict:
    """计算所有绩效指标
    
    Args:
        equity: 净值序列
        benchmark: 基准净值（可选）
        risk_free_rate: 无风险利率
        periods_per_year: 每年周期数
        
    Returns:
        指标字典
    """
    returns = calculate_returns(equity)
    
    metrics = {
        # 收益指标
        "total_return": float((equity.iloc[-1] / equity.iloc[0]) - 1) if len(equity) > 0 else 0.0,
        "annualized_return": calculate_annualized_return(returns, periods_per_year),
        
        # 风险指标
        "annualized_volatility": calculate_annualized_volatility(returns, periods_per_year),
        "max_drawdown": calculate_max_drawdown(equity)[0],
        "var_95": calculate_var(returns, 0.95),
        "cvar_95": calculate_cvar(returns, 0.95),
        
        # 风险调整收益
        "sharpe_ratio": calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year),
        "sortino_ratio": calculate_sortino_ratio(returns, risk_free_rate, periods_per_year),
        "calmar_ratio": calculate_calmar_ratio(returns, equity, periods_per_year),
        
        # 交易指标
        "win_rate": calculate_win_rate(returns),
        "profit_factor": calculate_profit_factor(returns),
        "profit_loss_ratio": calculate_profit_loss_ratio(returns),
    }
    
    # 如果有基准，计算相对指标
    if benchmark is not None:
        benchmark_returns = calculate_returns(benchmark)
        metrics["alpha"] = calculate_alpha(returns, benchmark_returns, risk_free_rate, periods_per_year)
        metrics["beta"] = calculate_beta(returns, benchmark_returns)
        metrics["information_ratio"] = calculate_information_ratio(returns, benchmark_returns, periods_per_year)
    
    return metrics
