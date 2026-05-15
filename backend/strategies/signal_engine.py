from dataclasses import dataclass, field
from typing import Optional
from config import MIN_SIGNALS_TO_BUY


@dataclass
class Signal:
    name: str
    value: int          # +1 bullish, -1 bearish, 0 neutral
    reason: str
    confidence: float


@dataclass
class StockDecision:
    symbol: str
    action: str
    score: int
    signals: list = field(default_factory=list)
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    confidence: float = 0.0
    ml_proba: Optional[float] = None


def evaluate_signals(symbol: str, snap: dict, df_raw=None, include_news: bool = False) -> StockDecision:
    signals = []
    close = snap.get("close", 0)

    # --- Signal 1: RSI — relaxed thresholds (35/65 instead of 30/70) ---
    rsi = snap.get("rsi")
    if rsi is not None:
        if rsi < 40:
            signals.append(Signal("RSI", +1, f"Oversold RSI={rsi:.1f} (<40)", 0.8))
        elif rsi > 62:
            signals.append(Signal("RSI", -1, f"Overbought RSI={rsi:.1f} (>62)", 0.8))
        elif rsi < 50:
            signals.append(Signal("RSI", +1, f"RSI bearish territory={rsi:.1f}, room to rise", 0.45))
        else:
            signals.append(Signal("RSI", 0, f"Neutral RSI={rsi:.1f}", 0.3))

    # --- Signal 2: MACD — fire on positive histogram, not just crossover ---
    macd_hist      = snap.get("macd_hist")
    macd_hist_prev = snap.get("macd_hist_prev")
    if macd_hist is not None and macd_hist_prev is not None:
        if macd_hist > 0 and macd_hist_prev <= 0:
            signals.append(Signal("MACD", +1, "Fresh bullish crossover", 0.9))
        elif macd_hist < 0 and macd_hist_prev >= 0:
            signals.append(Signal("MACD", -1, "Fresh bearish crossover", 0.9))
        elif macd_hist > 0 and macd_hist > macd_hist_prev:
            signals.append(Signal("MACD", +1, f"MACD histogram growing +{macd_hist:.3f}", 0.65))
        elif macd_hist < 0 and macd_hist < macd_hist_prev:
            signals.append(Signal("MACD", -1, f"MACD histogram shrinking {macd_hist:.3f}", 0.65))
        elif macd_hist > 0:
            signals.append(Signal("MACD", +1, "MACD above zero", 0.45))
        else:
            signals.append(Signal("MACD", -1, "MACD below zero", 0.45))

    # --- Signal 3: EMA trend — also check EMA20 vs EMA50 for short-term ---
    ema200 = snap.get("ema200")
    ema50  = snap.get("ema50")
    ema20  = snap.get("ema20")
    if ema200 and ema50 and ema20:
        if close > ema200 and ema50 > ema200:
            signals.append(Signal("EMA_Trend", +1, "Strong uptrend: price & EMA50 > EMA200", 0.85))
        elif close > ema50 and ema20 > ema50:
            signals.append(Signal("EMA_Trend", +1, "Short-term uptrend: EMA20 > EMA50", 0.6))
        elif close < ema200 and ema50 < ema200:
            signals.append(Signal("EMA_Trend", -1, "Downtrend: price & EMA50 < EMA200", 0.85))
        elif close < ema50:
            signals.append(Signal("EMA_Trend", -1, "Below EMA50", 0.5))
        else:
            signals.append(Signal("EMA_Trend", 0, "Mixed EMA signals", 0.3))

    # --- Signal 4: Volume — lower bar to 1.2x ---
    volume  = snap.get("volume", 0)
    vol_sma = snap.get("volume_sma20", 1)
    if vol_sma and vol_sma > 0:
        ratio = volume / vol_sma
        if ratio > 1.2:
            signals.append(Signal("Volume", +1, f"Above-avg volume {ratio:.1f}x", 0.7))
        elif ratio < 0.7:
            signals.append(Signal("Volume", -1, f"Weak volume {ratio:.1f}x avg", 0.5))
        else:
            signals.append(Signal("Volume", 0, f"Normal volume {ratio:.1f}x avg", 0.3))

    # --- Signal 5: Bollinger Band ---
    bb_pct = snap.get("bb_pct")
    if bb_pct is not None:
        if bb_pct < 0.25:
            signals.append(Signal("BB", +1, f"Near lower band BB%={bb_pct:.2f}", 0.7))
        elif bb_pct > 0.75:
            signals.append(Signal("BB", -1, f"Near upper band BB%={bb_pct:.2f}", 0.7))
        elif bb_pct < 0.45:
            signals.append(Signal("BB", +1, f"Lower-half BB%={bb_pct:.2f}, potential bounce", 0.45))
        else:
            signals.append(Signal("BB", 0, f"Mid-upper BB%={bb_pct:.2f}", 0.3))

    # --- Signal 6: MFI ---
    mfi = snap.get("mfi")
    if mfi is not None:
        if mfi < 30:
            signals.append(Signal("MFI", +1, f"Oversold money flow MFI={mfi:.1f}", 0.75))
        elif mfi > 70:
            signals.append(Signal("MFI", -1, f"Overbought MFI={mfi:.1f}", 0.75))
        elif mfi < 45:
            signals.append(Signal("MFI", +1, f"Weak money flow MFI={mfi:.1f}, room for inflow", 0.45))
        else:
            signals.append(Signal("MFI", 0, f"Neutral MFI={mfi:.1f}", 0.3))

    # --- Signal 7: XGBoost ML ---
    ml_proba = None
    if df_raw is not None:
        try:
            from backend.models.predictor import predict_proba, model_available
            if model_available():
                ml_proba = predict_proba(df_raw)
                if ml_proba is not None:
                    if ml_proba >= 0.60:
                        signals.append(Signal("ML_XGB", +1, f"XGBoost BUY prob={ml_proba:.0%}", 0.9))
                    elif ml_proba <= 0.40:
                        signals.append(Signal("ML_XGB", -1, f"XGBoost BUY prob={ml_proba:.0%} (low)", 0.9))
                    else:
                        signals.append(Signal("ML_XGB", 0, f"XGBoost uncertain={ml_proba:.0%}", 0.5))
        except Exception as e:
            print(f"[signal_engine] ML: {e}")

    # --- Signal 8: News sentiment (optional — skipped in batch scans) ---
    if include_news:
        try:
            from backend.data.news_fetcher import get_news_sentiment_signal
            ns = get_news_sentiment_signal(symbol)
            if ns["value"] != 0:
                signals.append(Signal("NEWS", ns["value"], ns["detail"], ns["confidence"]))
        except Exception as e:
            print(f"[signal_engine] news: {e}")

    # --- Decision ---
    bull_count = sum(1 for s in signals if s.value == +1)
    bear_count = sum(1 for s in signals if s.value == -1)
    score      = sum(s.value for s in signals)
    avg_conf   = sum(s.confidence for s in signals) / len(signals) if signals else 0
    atr        = snap.get("atr", close * 0.02) or close * 0.02

    threshold = MIN_SIGNALS_TO_BUY
    if ml_proba is not None and ml_proba >= 0.60:
        threshold = MIN_SIGNALS_TO_BUY - 1

    if bull_count >= threshold:
        action    = "BUY"
        stop_loss = round(close - 1.5 * atr, 2)
        target    = round(close + 3.0 * atr, 2)
    elif bear_count >= threshold:
        action    = "SELL"
        stop_loss = round(close + 1.5 * atr, 2)
        target    = round(close - 3.0 * atr, 2)
    else:
        action    = "HOLD"
        stop_loss = None
        target    = None

    return StockDecision(
        symbol=symbol, action=action, score=score,
        signals=signals, stop_loss=stop_loss, target=target,
        confidence=round(avg_conf, 2), ml_proba=ml_proba,
    )


def scan_watchlist(watchlist_data: dict, raw_frames: dict = None) -> list:
    decisions = []
    for symbol, snap in watchlist_data.items():
        try:
            df_raw   = (raw_frames or {}).get(symbol)
            decision = evaluate_signals(symbol, snap, df_raw=df_raw)
            decisions.append(decision)
        except Exception as e:
            print(f"[signal_engine] {symbol}: {e}")
    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions
