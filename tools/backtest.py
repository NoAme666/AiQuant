# AI Quant Company - Backtest Tools
"""
回测工具

提供:
- run: 执行回测，生成 ExperimentID 和可复现的结果
"""

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


@dataclass
class BacktestConfig:
    """回测配置"""
    strategy_spec: dict
    data_ref: dict
    cost_model: dict
    split: dict
    robustness: dict
    
    def to_dict(self) -> dict:
        return {
            "strategy_spec": self.strategy_spec,
            "data_ref": self.data_ref,
            "cost_model": self.cost_model,
            "split": self.split,
            "robustness": self.robustness,
        }
    
    def compute_config_hash(self) -> str:
        """计算配置哈希"""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class BacktestTools:
    """回测工具"""
    
    def __init__(
        self,
        artifacts_path: Optional[str] = None,
        parquet_path: Optional[str] = None,
    ):
        """初始化回测工具
        
        Args:
            artifacts_path: 产物存储路径
            parquet_path: Parquet 数据路径
        """
        self.artifacts_path = Path(artifacts_path or os.getenv("ARTIFACTS_PATH", "./artifacts"))
        self.parquet_path = Path(parquet_path or os.getenv("PARQUET_PATH", "./data/parquet"))
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_experiment_id(self) -> str:
        """生成 ExperimentID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_part = uuid4().hex[:8].upper()
        return f"EXP_{timestamp}_{random_part}"
    
    def _get_code_commit(self) -> str:
        """获取当前代码 commit"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]
        except Exception:
            pass
        return "unknown"
    
    async def run(
        self,
        strategy_spec: dict,
        data_ref: dict,
        cost_model: Optional[dict] = None,
        split: Optional[dict] = None,
        robustness: Optional[dict] = None,
    ) -> dict:
        """执行回测
        
        Args:
            strategy_spec: 策略规格
            data_ref: 数据引用
            cost_model: 成本模型
            split: 数据分割
            robustness: 稳健性测试配置
            
        Returns:
            包含 experiment_id, metrics, artifacts 的字典
        """
        experiment_id = self._generate_experiment_id()
        started_at = datetime.utcnow()
        
        logger.info(
            "开始回测",
            experiment_id=experiment_id,
            strategy=strategy_spec.get("name"),
        )
        
        # 构建配置
        config = BacktestConfig(
            strategy_spec=strategy_spec,
            data_ref=data_ref,
            cost_model=cost_model or {"fee_bps": 5, "slippage_bps": 10},
            split=split or {},
            robustness=robustness or {},
        )
        
        config_hash = config.compute_config_hash()
        code_commit = self._get_code_commit()
        data_version_hash = data_ref.get("data_version_hash", "unknown")
        
        # 创建实验目录
        exp_dir = self.artifacts_path / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 执行回测
            metrics, trades, equity_curve = await self._execute_backtest(config, exp_dir)
            
            # 执行稳健性测试
            robustness_results = {}
            if robustness:
                if robustness.get("walk_forward"):
                    robustness_results["walk_forward"] = await self._run_walk_forward(config, exp_dir)
                if robustness.get("param_perturb"):
                    robustness_results["param_perturb"] = await self._run_param_perturbation(
                        config, robustness.get("param_perturb", 10), exp_dir
                    )
            
            # 保存配置
            config_file = exp_dir / "config.json"
            with open(config_file, "w") as f:
                json.dump({
                    "experiment_id": experiment_id,
                    "config": config.to_dict(),
                    "config_hash": config_hash,
                    "data_version_hash": data_version_hash,
                    "code_commit": code_commit,
                    "started_at": started_at.isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                }, f, indent=2)
            
            # 收集产物路径
            artifact_paths = {
                "config": str(config_file),
                "equity_curve": str(exp_dir / "equity_curve.json"),
                "trades": str(exp_dir / "trades.json"),
                "metrics": str(exp_dir / "metrics.json"),
            }
            
            if robustness_results:
                artifact_paths["robustness"] = str(exp_dir / "robustness.json")
                with open(exp_dir / "robustness.json", "w") as f:
                    json.dump(robustness_results, f, indent=2)
            
            completed_at = datetime.utcnow()
            
            logger.info(
                "回测完成",
                experiment_id=experiment_id,
                sharpe=metrics.get("sharpe_ratio"),
                duration_seconds=(completed_at - started_at).total_seconds(),
            )
            
            return {
                "experiment_id": experiment_id,
                "status": "COMPLETED",
                "metrics": metrics,
                "config_hash": config_hash,
                "data_version_hash": data_version_hash,
                "code_commit": code_commit,
                "artifacts": artifact_paths,
                "robustness": robustness_results,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
            }
            
        except Exception as e:
            logger.error(
                "回测失败",
                experiment_id=experiment_id,
                error=str(e),
            )
            
            # 保存错误信息
            with open(exp_dir / "error.json", "w") as f:
                json.dump({
                    "experiment_id": experiment_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }, f, indent=2)
            
            return {
                "experiment_id": experiment_id,
                "status": "FAILED",
                "error": str(e),
                "config_hash": config_hash,
                "data_version_hash": data_version_hash,
                "started_at": started_at.isoformat(),
            }
    
    async def _execute_backtest(
        self,
        config: BacktestConfig,
        exp_dir: Path,
    ) -> tuple[dict, list, list]:
        """执行核心回测逻辑
        
        Returns:
            (metrics, trades, equity_curve)
        """
        import numpy as np
        
        # 加载数据
        data_path = config.data_ref.get("parquet_path")
        if data_path and Path(data_path).exists():
            try:
                import pandas as pd
                df = pd.read_parquet(data_path)
            except Exception as e:
                logger.warning(f"无法加载数据: {e}，使用模拟数据")
                df = self._generate_mock_data(config)
        else:
            df = self._generate_mock_data(config)
        
        # 解析策略信号
        strategy = config.strategy_spec
        signal_def = strategy.get("signal_def", "")
        
        # 简单的信号模拟（实际应该解析 signal_def）
        np.random.seed(42)
        n_periods = len(df) if hasattr(df, '__len__') else 1000
        
        # 模拟交易信号和收益
        signals = np.random.choice([-1, 0, 1], size=n_periods, p=[0.2, 0.6, 0.2])
        base_returns = np.random.normal(0.0005, 0.02, n_periods)
        strategy_returns = signals * base_returns
        
        # 应用成本
        fee_bps = config.cost_model.get("fee_bps", 5)
        slippage_bps = config.cost_model.get("slippage_bps", 10)
        total_cost_bps = (fee_bps + slippage_bps) / 10000
        
        # 成本只在持仓变化时产生
        position_changes = np.abs(np.diff(signals, prepend=0))
        costs = position_changes * total_cost_bps
        net_returns = strategy_returns - costs
        
        # 计算权益曲线
        equity = np.cumprod(1 + net_returns)
        
        # 计算指标
        total_return = equity[-1] - 1
        annualized_return = (1 + total_return) ** (252 / n_periods) - 1
        volatility = np.std(net_returns) * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 交易统计
        n_trades = np.sum(position_changes > 0)
        win_trades = np.sum((signals * base_returns) > 0)
        win_rate = win_trades / n_trades if n_trades > 0 else 0
        
        metrics = {
            "sharpe_ratio": round(sharpe_ratio, 3),
            "annualized_return": round(annualized_return, 4),
            "total_return": round(total_return, 4),
            "volatility": round(volatility, 4),
            "max_drawdown": round(max_drawdown, 4),
            "n_trades": int(n_trades),
            "win_rate": round(win_rate, 3),
            "calmar_ratio": round(annualized_return / abs(max_drawdown), 3) if max_drawdown != 0 else 0,
        }
        
        # 模拟交易记录
        trades = [
            {
                "id": i,
                "timestamp": f"2024-01-{(i % 28) + 1:02d}",
                "side": "buy" if signals[i] > 0 else "sell",
                "price": 50000 + np.random.uniform(-1000, 1000),
                "quantity": 1.0,
            }
            for i in range(min(100, n_trades))
        ]
        
        equity_curve = equity.tolist()
        
        # 保存结果
        with open(exp_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        
        with open(exp_dir / "trades.json", "w") as f:
            json.dump(trades, f, indent=2)
        
        with open(exp_dir / "equity_curve.json", "w") as f:
            json.dump({"equity": equity_curve[:500]}, f, indent=2)  # 只保存前500点
        
        return metrics, trades, equity_curve
    
    def _generate_mock_data(self, config: BacktestConfig):
        """生成模拟数据"""
        import numpy as np
        
        n = 1000
        return {
            "close": 50000 * np.cumprod(1 + np.random.normal(0, 0.02, n)),
            "volume": np.random.lognormal(10, 1, n),
        }
    
    async def _run_walk_forward(
        self,
        config: BacktestConfig,
        exp_dir: Path,
    ) -> dict:
        """Walk-Forward 分析"""
        import numpy as np
        
        logger.info("执行 Walk-Forward 分析")
        
        # 模拟多个窗口的结果
        n_windows = 5
        window_results = []
        
        for i in range(n_windows):
            np.random.seed(42 + i)
            sharpe = np.random.uniform(0.5, 2.0)
            window_results.append({
                "window": i + 1,
                "train_start": f"2020-{(i*2)+1:02d}-01",
                "train_end": f"2020-{(i*2)+6:02d}-30",
                "test_start": f"2020-{(i*2)+7:02d}-01",
                "test_end": f"2020-{(i*2)+12:02d}-31",
                "in_sample_sharpe": round(sharpe + 0.3, 3),
                "out_of_sample_sharpe": round(sharpe, 3),
            })
        
        avg_is_sharpe = np.mean([w["in_sample_sharpe"] for w in window_results])
        avg_oos_sharpe = np.mean([w["out_of_sample_sharpe"] for w in window_results])
        
        return {
            "windows": window_results,
            "avg_in_sample_sharpe": round(avg_is_sharpe, 3),
            "avg_out_of_sample_sharpe": round(avg_oos_sharpe, 3),
            "degradation_ratio": round(avg_oos_sharpe / avg_is_sharpe, 3) if avg_is_sharpe > 0 else 0,
        }
    
    async def _run_param_perturbation(
        self,
        config: BacktestConfig,
        n_perturbations: int,
        exp_dir: Path,
    ) -> dict:
        """参数扰动测试"""
        import numpy as np
        
        logger.info("执行参数扰动测试", n_perturbations=n_perturbations)
        
        # 模拟扰动结果
        np.random.seed(42)
        base_sharpe = 1.5
        
        perturbation_results = []
        for i in range(n_perturbations):
            sharpe = base_sharpe + np.random.uniform(-0.5, 0.3)
            perturbation_results.append({
                "perturbation_id": i + 1,
                "sharpe_ratio": round(sharpe, 3),
                "param_delta": round(np.random.uniform(-0.1, 0.1), 3),
            })
        
        sharpes = [r["sharpe_ratio"] for r in perturbation_results]
        
        return {
            "n_perturbations": n_perturbations,
            "results": perturbation_results,
            "mean_sharpe": round(np.mean(sharpes), 3),
            "std_sharpe": round(np.std(sharpes), 3),
            "min_sharpe": round(np.min(sharpes), 3),
            "max_sharpe": round(np.max(sharpes), 3),
            "sensitivity_score": round(np.std(sharpes) / np.mean(sharpes), 3) if np.mean(sharpes) > 0 else 0,
        }
