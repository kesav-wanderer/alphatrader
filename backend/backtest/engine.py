"""
Simple vectorised backtester.
No external dependencies — pure pandas.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List


@dataclass
class Trade:
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    qty: int
    pnl: float
    pnl_pct: float
    exit_reason: str   # TARGET / STOPLOSS / SIGNAL_EXIT / END


@dataclass
class BacktestResult:
    symbol: str
    trades: List[Trade] = field(default_factory=list)
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    total_trades: int = 0


def run_backtest(
    symbol: str,
    df: pd.DataFrame,           # must have indicators already added
    decisions: list,            # list of (date, action, stop_loss, target)
    capital_per_trade: float = 25000,
    stop_loss_pct: float = 0.02,
    target_pct: float = 0.06,
    hold_days: int = 5,
) -> BacktestResult:
    """
    decisions: list of dicts with keys: date, action, close, stop_loss, target
    """
    trades = []
    equity_curve = [capital_per_trade]

    buy_signals = [d for d in decisions if d["action"] == "BUY"]

    for sig in buy_signals:
        entry_price = sig["close"]
        entry_date  = sig["date"]
        qty         = int(capital_per_trade / entry_price)
        if qty == 0:
            continue

        sl     = sig.get("stop_loss") or round(entry_price * (1 - stop_loss_pct), 2)
        target = sig.get("target")    or round(entry_price * (1 + target_pct), 2)

        # Walk forward from entry
        future = df[df.index > entry_date].head(hold_days + 3)
        exit_price  = entry_price
        exit_date   = entry_date
        exit_reason = "END"

        for ts, row in future.iterrows():
            if row["Low"] <= sl:
                exit_price  = sl
                exit_date   = str(ts.date())
                exit_reason = "STOPLOSS"
                break
            if row["High"] >= target:
                exit_price  = target
                exit_date   = str(ts.date())
                exit_reason = "TARGET"
                break
        else:
            if not future.empty:
                exit_price  = future["Close"].iloc[-1]
                exit_date   = str(future.index[-1].date())
                exit_reason = "TIME_EXIT"

        pnl     = round((exit_price - entry_price) * qty, 2)
        pnl_pct = round((exit_price - entry_price) / entry_price * 100, 2)
        equity_curve.append(equity_curve[-1] + pnl)

        trades.append(Trade(
            symbol=symbol,
            entry_date=str(pd.Timestamp(entry_date).date()),
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            qty=qty,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
        ))

    if not trades:
        return BacktestResult(symbol=symbol)

    wins       = [t for t in trades if t.pnl > 0]
    win_rate   = round(len(wins) / len(trades) * 100, 1)
    avg_return = round(np.mean([t.pnl_pct for t in trades]), 2)
    total_pnl  = round(sum(t.pnl for t in trades), 2)

    # Max drawdown on equity curve
    eq = np.array(equity_curve)
    roll_max  = np.maximum.accumulate(eq)
    drawdowns = (eq - roll_max) / roll_max * 100
    max_dd    = round(float(drawdowns.min()), 2)

    # Sharpe (daily returns approximation)
    returns = np.diff(eq) / eq[:-1]
    sharpe  = round(float(np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)), 2) if len(returns) > 1 else 0.0

    return BacktestResult(
        symbol=symbol,
        trades=trades,
        total_pnl=total_pnl,
        win_rate=win_rate,
        avg_return=avg_return,
        max_drawdown=max_dd,
        sharpe=sharpe,
        total_trades=len(trades),
    )
