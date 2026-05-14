"""
Runs backtest across all watchlist stocks.
Generates signal history from past data then tests each trade.
"""
import sys
sys.path.insert(0, ".")

import pandas as pd
from backend.data.fetcher import fetch_ohlcv
from backend.data.indicators import add_indicators, get_indicator_snapshot
from backend.strategies.signal_engine import evaluate_signals
from backend.models.predictor import model_available, predict_proba
from backend.backtest.engine import run_backtest
from config import WATCHLIST


def generate_signal_history(symbol: str, df: pd.DataFrame) -> list:
    """
    Walk through historical data day-by-day and collect BUY signals.
    Uses a 200-bar rolling window so indicators always have enough data.
    """
    signals = []
    min_bars = 210   # need 200 for EMA200 + buffer

    for i in range(min_bars, len(df)):
        window = df.iloc[:i]
        try:
            df_ind = add_indicators(window)
            if df_ind.empty:
                continue
            snap     = get_indicator_snapshot(df_ind)
            decision = evaluate_signals(symbol, snap)   # no ML in history scan (too slow)
            if decision.action == "BUY":
                last_row = df_ind.iloc[-1]
                signals.append({
                    "date":       window.index[-1],
                    "action":     "BUY",
                    "close":      float(last_row["Close"]),
                    "stop_loss":  decision.stop_loss,
                    "target":     decision.target,
                })
        except Exception:
            continue

    return signals


def run_full_backtest(
    symbols: list = None,
    period: str = "2y",
    capital_per_trade: float = 25000,
    target_pct: float = 0.06,
    stop_loss_pct: float = 0.02,
    hold_days: int = 5,
):
    symbols = symbols or WATCHLIST
    all_results = []

    print(f"\nBacktesting {len(symbols)} stocks | capital/trade=₹{capital_per_trade:,.0f} "
          f"| target={target_pct:.0%} | sl={stop_loss_pct:.0%} | hold={hold_days}d\n")

    for sym in symbols:
        try:
            df_raw = fetch_ohlcv(sym, period=period)
            signals = generate_signal_history(sym, df_raw)
            if not signals:
                print(f"  {sym:<18} no signals generated")
                continue

            result = run_backtest(
                symbol=sym,
                df=df_raw,
                decisions=signals,
                capital_per_trade=capital_per_trade,
                stop_loss_pct=stop_loss_pct,
                target_pct=target_pct,
                hold_days=hold_days,
            )
            all_results.append(result)

            flag = "✅" if result.win_rate >= 55 else ("⚠️" if result.win_rate >= 45 else "❌")
            print(f"  {sym:<18} {flag} trades={result.total_trades:>3} "
                  f"win={result.win_rate:>5.1f}%  avg={result.avg_return:>+6.2f}%  "
                  f"pnl=₹{result.total_pnl:>8,.0f}  dd={result.max_drawdown:.1f}%  sharpe={result.sharpe:.2f}")
        except Exception as e:
            print(f"  {sym:<18} ERROR: {e}")

    if not all_results:
        print("No results.")
        return []

    # Summary
    total_pnl  = sum(r.total_pnl  for r in all_results)
    avg_win    = sum(r.win_rate    for r in all_results) / len(all_results)
    avg_sharpe = sum(r.sharpe      for r in all_results) / len(all_results)
    total_trades = sum(r.total_trades for r in all_results)

    print(f"\n{'='*70}")
    print(f"OVERALL  trades={total_trades}  avg_win_rate={avg_win:.1f}%  "
          f"total_pnl=₹{total_pnl:,.0f}  avg_sharpe={avg_sharpe:.2f}")

    # Top performers
    top = sorted(all_results, key=lambda r: r.total_pnl, reverse=True)[:5]
    print(f"\nTop 5 stocks by P&L:")
    for r in top:
        print(f"  {r.symbol:<18} ₹{r.total_pnl:>8,.0f}  win={r.win_rate:.0f}%  trades={r.total_trades}")

    return all_results


if __name__ == "__main__":
    run_full_backtest()
