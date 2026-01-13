# AI Quant Company - 鲁棒性实验
"""
鲁棒性验证模块

包含:
- Walk-forward validation
- 参数敏感性分析
- 随机信号对照
- 子样本稳定性
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
import structlog

from backtest.engine import BacktestConfig, BacktestEngine, BacktestResult
from backtest.metrics import calculate_all_metrics

logger = structlog.get_logger()


# ============================================
# Walk-Forward 验证
# ============================================

@dataclass
class WalkForwardWindow:
    """Walk-Forward 窗口"""
    id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_result: Optional[BacktestResult] = None
    test_result: Optional[BacktestResult] = None


@dataclass
class WalkForwardResult:
    """Walk-Forward 验证结果"""
    windows: list[WalkForwardWindow]
    aggregate_metrics: dict
    
    @property
    def avg_test_sharpe(self) -> float:
        sharpes = [
            w.test_result.metrics.get("sharpe_ratio", 0)
            for w in self.windows
            if w.test_result is not None
        ]
        return float(np.mean(sharpes)) if sharpes else 0.0
    
    @property
    def avg_test_return(self) -> float:
        returns = [
            w.test_result.metrics.get("annualized_return", 0)
            for w in self.windows
            if w.test_result is not None
        ]
        return float(np.mean(returns)) if returns else 0.0


def walk_forward_validation(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    config: BacktestConfig,
    train_period_days: int = 252,
    test_period_days: int = 63,
    step_days: int = 63,
    signal_generator: Optional[Callable] = None,
) -> WalkForwardResult:
    """执行 Walk-Forward 验证
    
    Args:
        signals: 信号数据（如果无 signal_generator）
        prices: 价格数据
        config: 回测配置
        train_period_days: 训练期天数
        test_period_days: 测试期天数
        step_days: 步进天数
        signal_generator: 信号生成函数（可选），用于重新生成信号
        
    Returns:
        Walk-Forward 结果
    """
    logger.info(
        "开始 Walk-Forward 验证",
        train_days=train_period_days,
        test_days=test_period_days,
    )
    
    # 获取时间范围
    timestamps = sorted(prices["timestamp"].unique())
    
    windows = []
    window_id = 0
    
    i = 0
    while i + train_period_days + test_period_days <= len(timestamps):
        train_start = timestamps[i]
        train_end = timestamps[i + train_period_days - 1]
        test_start = timestamps[i + train_period_days]
        test_end = timestamps[min(i + train_period_days + test_period_days - 1, len(timestamps) - 1)]
        
        window = WalkForwardWindow(
            id=window_id,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
        )
        
        # 训练期回测
        train_prices = prices[
            (prices["timestamp"] >= train_start) & 
            (prices["timestamp"] <= train_end)
        ]
        train_signals = signals[
            (signals["timestamp"] >= train_start) & 
            (signals["timestamp"] <= train_end)
        ]
        
        if not train_signals.empty and not train_prices.empty:
            engine = BacktestEngine(config)
            window.train_result = engine.run(train_signals, train_prices)
        
        # 测试期回测
        test_prices = prices[
            (prices["timestamp"] >= test_start) & 
            (prices["timestamp"] <= test_end)
        ]
        test_signals = signals[
            (signals["timestamp"] >= test_start) & 
            (signals["timestamp"] <= test_end)
        ]
        
        if not test_signals.empty and not test_prices.empty:
            engine = BacktestEngine(config)
            window.test_result = engine.run(test_signals, test_prices)
        
        windows.append(window)
        window_id += 1
        i += step_days
    
    # 计算聚合指标
    aggregate_metrics = _aggregate_walk_forward_metrics(windows)
    
    logger.info(
        "Walk-Forward 验证完成",
        windows=len(windows),
        avg_test_sharpe=aggregate_metrics.get("avg_test_sharpe", 0),
    )
    
    return WalkForwardResult(
        windows=windows,
        aggregate_metrics=aggregate_metrics,
    )


def _aggregate_walk_forward_metrics(windows: list[WalkForwardWindow]) -> dict:
    """聚合 Walk-Forward 指标"""
    test_sharpes = []
    test_returns = []
    test_drawdowns = []
    
    for w in windows:
        if w.test_result is None:
            continue
        m = w.test_result.metrics
        test_sharpes.append(m.get("sharpe_ratio", 0))
        test_returns.append(m.get("annualized_return", 0))
        test_drawdowns.append(m.get("max_drawdown", 0))
    
    return {
        "n_windows": len(windows),
        "avg_test_sharpe": float(np.mean(test_sharpes)) if test_sharpes else 0.0,
        "std_test_sharpe": float(np.std(test_sharpes)) if test_sharpes else 0.0,
        "avg_test_return": float(np.mean(test_returns)) if test_returns else 0.0,
        "avg_test_drawdown": float(np.mean(test_drawdowns)) if test_drawdowns else 0.0,
        "min_test_sharpe": float(np.min(test_sharpes)) if test_sharpes else 0.0,
        "max_test_sharpe": float(np.max(test_sharpes)) if test_sharpes else 0.0,
    }


# ============================================
# 参数敏感性分析
# ============================================

@dataclass
class ParameterSensitivityResult:
    """参数敏感性结果"""
    parameter_name: str
    base_value: Any
    variations: list[dict]  # [{value, metrics}, ...]
    conclusion: str = ""


def parameter_sensitivity_analysis(
    signals_generator: Callable[[Any], pd.DataFrame],
    prices: pd.DataFrame,
    config: BacktestConfig,
    parameter_name: str,
    base_value: Any,
    variations: list[Any],
) -> ParameterSensitivityResult:
    """参数敏感性分析
    
    Args:
        signals_generator: 信号生成函数，接受参数值返回信号 DataFrame
        prices: 价格数据
        config: 回测配置
        parameter_name: 参数名称
        base_value: 基准参数值
        variations: 参数变体列表
        
    Returns:
        敏感性分析结果
    """
    logger.info(
        "开始参数敏感性分析",
        parameter=parameter_name,
        base_value=base_value,
        n_variations=len(variations),
    )
    
    results = []
    
    for value in variations:
        try:
            signals = signals_generator(value)
            engine = BacktestEngine(config)
            result = engine.run(signals, prices)
            
            results.append({
                "value": value,
                "sharpe": result.metrics.get("sharpe_ratio", 0),
                "return": result.metrics.get("annualized_return", 0),
                "drawdown": result.metrics.get("max_drawdown", 0),
                "metrics": result.metrics,
            })
        except Exception as e:
            logger.warning(
                "参数变体回测失败",
                parameter=parameter_name,
                value=value,
                error=str(e),
            )
    
    # 生成结论
    conclusion = _generate_sensitivity_conclusion(parameter_name, base_value, results)
    
    return ParameterSensitivityResult(
        parameter_name=parameter_name,
        base_value=base_value,
        variations=results,
        conclusion=conclusion,
    )


def _generate_sensitivity_conclusion(
    parameter_name: str,
    base_value: Any,
    results: list[dict],
) -> str:
    """生成敏感性分析结论"""
    if not results:
        return "无法完成敏感性分析"
    
    sharpes = [r["sharpe"] for r in results]
    sharpe_std = np.std(sharpes)
    sharpe_range = max(sharpes) - min(sharpes)
    
    if sharpe_std < 0.1:
        return f"策略对 {parameter_name} 参数不敏感（Sharpe 标准差 = {sharpe_std:.3f}）"
    elif sharpe_std < 0.3:
        return f"策略对 {parameter_name} 参数中等敏感（Sharpe 标准差 = {sharpe_std:.3f}）"
    else:
        return f"策略对 {parameter_name} 参数高度敏感（Sharpe 标准差 = {sharpe_std:.3f}），需要注意过拟合风险"


# ============================================
# 随机化对照
# ============================================

@dataclass
class RandomizationTestResult:
    """随机化对照结果"""
    name: str
    strategy_sharpe: float
    random_sharpes: list[float]
    p_value: float
    significant: bool


def randomization_test(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    config: BacktestConfig,
    n_simulations: int = 100,
    random_seed: Optional[int] = None,
) -> RandomizationTestResult:
    """随机化对照实验
    
    通过打乱信号时序生成随机基线，检验策略是否显著优于随机。
    
    Args:
        signals: 策略信号
        prices: 价格数据
        config: 回测配置
        n_simulations: 模拟次数
        random_seed: 随机种子
        
    Returns:
        随机化测试结果
    """
    logger.info("开始随机化对照", n_simulations=n_simulations)
    
    if random_seed is not None:
        np.random.seed(random_seed)
    
    # 策略回测
    engine = BacktestEngine(config)
    strategy_result = engine.run(signals, prices)
    strategy_sharpe = strategy_result.metrics.get("sharpe_ratio", 0)
    
    # 随机模拟
    random_sharpes = []
    
    for i in range(n_simulations):
        # 打乱信号
        random_signals = signals.copy()
        random_signals["signal"] = np.random.permutation(random_signals["signal"].values)
        
        try:
            random_result = engine.run(random_signals, prices)
            random_sharpes.append(random_result.metrics.get("sharpe_ratio", 0))
        except Exception:
            pass
    
    # 计算 p-value
    if random_sharpes:
        p_value = float(np.mean([s >= strategy_sharpe for s in random_sharpes]))
    else:
        p_value = 1.0
    
    significant = p_value < 0.05
    
    logger.info(
        "随机化对照完成",
        strategy_sharpe=strategy_sharpe,
        avg_random_sharpe=np.mean(random_sharpes) if random_sharpes else 0,
        p_value=p_value,
    )
    
    return RandomizationTestResult(
        name="Signal Randomization",
        strategy_sharpe=strategy_sharpe,
        random_sharpes=random_sharpes,
        p_value=p_value,
        significant=significant,
    )


# ============================================
# 子样本稳定性
# ============================================

@dataclass
class SubsampleResult:
    """子样本结果"""
    regime: str
    description: str
    n_samples: int
    metrics: dict


def subsample_stability_analysis(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    config: BacktestConfig,
    regime_classifier: Optional[Callable[[pd.DataFrame], pd.Series]] = None,
) -> list[SubsampleResult]:
    """子样本稳定性分析
    
    在不同市场环境（牛市/熊市/震荡）下分析策略表现。
    
    Args:
        signals: 策略信号
        prices: 价格数据
        config: 回测配置
        regime_classifier: 市场环境分类函数（可选）
        
    Returns:
        各子样本的分析结果
    """
    logger.info("开始子样本稳定性分析")
    
    results = []
    
    # 默认按收益率划分市场环境
    if regime_classifier is None:
        regime_classifier = _default_regime_classifier
    
    # 计算市场环境
    regimes = regime_classifier(prices)
    
    for regime_name, regime_desc in [
        ("bull", "牛市（市场上涨）"),
        ("bear", "熊市（市场下跌）"),
        ("sideways", "震荡（横盘整理）"),
    ]:
        # 筛选该环境下的数据
        regime_mask = regimes == regime_name
        regime_dates = regimes[regime_mask].index
        
        if len(regime_dates) == 0:
            continue
        
        # 筛选对应的信号和价格
        regime_signals = signals[signals["timestamp"].isin(regime_dates)]
        regime_prices = prices[prices["timestamp"].isin(regime_dates)]
        
        if regime_signals.empty or regime_prices.empty:
            continue
        
        # 回测
        try:
            engine = BacktestEngine(config)
            result = engine.run(regime_signals, regime_prices)
            
            results.append(SubsampleResult(
                regime=regime_name,
                description=regime_desc,
                n_samples=len(regime_dates),
                metrics=result.metrics,
            ))
        except Exception as e:
            logger.warning(f"子样本回测失败: {regime_name}", error=str(e))
    
    return results


def _default_regime_classifier(prices: pd.DataFrame) -> pd.Series:
    """默认市场环境分类器
    
    基于滚动收益率将市场分为牛/熊/震荡。
    """
    # 假设价格数据有 close 列
    if "close" not in prices.columns:
        return pd.Series(index=prices.index, data="unknown")
    
    # 计算 20 日滚动收益
    returns = prices.groupby("symbol")["close"].pct_change(20)
    avg_returns = returns.groupby(prices["timestamp"]).mean()
    
    def classify(r):
        if r > 0.05:
            return "bull"
        elif r < -0.05:
            return "bear"
        else:
            return "sideways"
    
    return avg_returns.apply(classify)


# ============================================
# 综合鲁棒性报告
# ============================================

@dataclass
class RobustnessReport:
    """鲁棒性分析综合报告"""
    walk_forward: Optional[WalkForwardResult] = None
    parameter_sensitivity: list[ParameterSensitivityResult] = field(default_factory=list)
    randomization_test: Optional[RandomizationTestResult] = None
    subsample_analysis: list[SubsampleResult] = field(default_factory=list)
    
    # 综合评估
    overall_score: float = 0.0
    conclusion: str = ""
    concerns: list[str] = field(default_factory=list)


def generate_robustness_report(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    config: BacktestConfig,
    run_walk_forward: bool = True,
    run_randomization: bool = True,
    run_subsample: bool = True,
) -> RobustnessReport:
    """生成综合鲁棒性报告
    
    Args:
        signals: 策略信号
        prices: 价格数据
        config: 回测配置
        run_walk_forward: 是否运行 Walk-Forward
        run_randomization: 是否运行随机化对照
        run_subsample: 是否运行子样本分析
        
    Returns:
        综合鲁棒性报告
    """
    logger.info("生成鲁棒性报告")
    
    report = RobustnessReport()
    concerns = []
    scores = []
    
    # Walk-Forward
    if run_walk_forward:
        report.walk_forward = walk_forward_validation(signals, prices, config)
        wf_sharpe = report.walk_forward.avg_test_sharpe
        scores.append(min(wf_sharpe / 1.5, 1.0))  # 1.5 Sharpe = 满分
        
        if wf_sharpe < 0.5:
            concerns.append(f"Walk-Forward 平均 Sharpe 较低 ({wf_sharpe:.2f})")
    
    # 随机化对照
    if run_randomization:
        report.randomization_test = randomization_test(signals, prices, config)
        if not report.randomization_test.significant:
            concerns.append("策略未能显著优于随机基线")
            scores.append(0.3)
        else:
            scores.append(1.0)
    
    # 子样本分析
    if run_subsample:
        report.subsample_analysis = subsample_stability_analysis(signals, prices, config)
        
        # 检查各环境表现
        for sub in report.subsample_analysis:
            if sub.metrics.get("sharpe_ratio", 0) < 0:
                concerns.append(f"在 {sub.description} 下表现为负")
    
    # 计算综合分数
    report.overall_score = float(np.mean(scores)) if scores else 0.0
    report.concerns = concerns
    
    # 生成结论
    if report.overall_score >= 0.8:
        report.conclusion = "策略鲁棒性良好，通过主要验证测试"
    elif report.overall_score >= 0.5:
        report.conclusion = "策略鲁棒性一般，建议关注以下问题"
    else:
        report.conclusion = "策略鲁棒性较差，存在过拟合风险"
    
    logger.info(
        "鲁棒性报告生成完成",
        overall_score=report.overall_score,
        n_concerns=len(concerns),
    )
    
    return report
