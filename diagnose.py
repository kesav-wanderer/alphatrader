"""Quick diagnostic — run to see signal + ML output for all watchlist stocks."""
import sys
sys.path.insert(0, ".")

from config import WATCHLIST
from backend.data.fetcher import fetch_ohlcv
from backend.data.indicators import add_indicators, get_indicator_snapshot
from backend.strategies.signal_engine import evaluate_signals
from backend.models.predictor import model_available, predict_proba

print(f"ML model available: {model_available()}\n")
print(f"{'Symbol':<15} {'Action':<6} {'Score':>5}  {'ML%':>5}  Signals")
print("-" * 70)

for sym in WATCHLIST:
    try:
        df_raw = fetch_ohlcv(sym, period="1y")
        df_ind = add_indicators(df_raw)
        snap   = get_indicator_snapshot(df_ind)
        d      = evaluate_signals(sym, snap, df_raw=df_raw)
        bulls  = sum(1 for s in d.signals if s.value == +1)
        bears  = sum(1 for s in d.signals if s.value == -1)
        ml_str = f"{d.ml_proba:.0%}" if d.ml_proba is not None else " N/A"
        print(f"{sym:<15} {d.action:<6} {d.score:>5}  {ml_str:>5}  🟢{bulls} 🔴{bears} — RSI={snap.get('rsi',0):.0f}")
    except Exception as e:
        print(f"{sym:<15} ERROR: {e}")
