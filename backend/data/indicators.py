import pandas as pd
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    # Trend — EMAs
    df["EMA_20"]  = ta.trend.ema_indicator(close, window=20)
    df["EMA_50"]  = ta.trend.ema_indicator(close, window=50)
    df["EMA_200"] = ta.trend.ema_indicator(close, window=200)

    # Momentum
    df["RSI_14"]  = ta.momentum.rsi(close, window=14)

    macd = ta.trend.MACD(close, window_fast=12, window_slow=26, window_sign=9)
    df["MACD"]        = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"]   = macd.macd_diff()

    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    df["STOCH_k"] = stoch.stoch()
    df["STOCH_d"] = stoch.stoch_signal()

    df["CCI_20"] = ta.trend.cci(high, low, close, window=20)

    # Volatility — Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["BB_upper"]  = bb.bollinger_hband()
    df["BB_lower"]  = bb.bollinger_lband()
    df["BB_mid"]    = bb.bollinger_mavg()
    df["BB_pct"]    = bb.bollinger_pband()   # 0–1 position within bands
    df["ATR_14"]    = ta.volatility.average_true_range(high, low, close, window=14)

    # Volume
    df["OBV"] = ta.volume.on_balance_volume(close, vol)
    df["MFI_14"] = ta.volume.money_flow_index(high, low, close, vol, window=14)

    # ADX
    adx = ta.trend.ADXIndicator(high, low, close, window=14)
    df["ADX_14"] = adx.adx()
    df["ADX_pos"] = adx.adx_pos()
    df["ADX_neg"] = adx.adx_neg()

    # Only require core indicators — EMA200 needs 200 bars so exclude from mandatory drop
    core = ["RSI_14", "MACD", "MACD_signal", "MACD_hist", "EMA_20", "EMA_50",
            "BB_upper", "BB_lower", "BB_pct", "ATR_14", "OBV", "MFI_14"]
    df.dropna(subset=core, inplace=True)
    return df


def get_indicator_snapshot(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 2:
        return {}
    row  = df.iloc[-1]
    prev = df.iloc[-2]

    return {
        "close":          row["Close"],
        "volume":         row["Volume"],
        "rsi":            row.get("RSI_14"),
        "macd":           row.get("MACD"),
        "macd_signal":    row.get("MACD_signal"),
        "macd_hist":      row.get("MACD_hist"),
        "macd_hist_prev": prev.get("MACD_hist"),
        "ema20":          row.get("EMA_20"),
        "ema50":          row.get("EMA_50"),
        "ema200":         row.get("EMA_200"),
        "bb_upper":       row.get("BB_upper"),
        "bb_lower":       row.get("BB_lower"),
        "bb_pct":         row.get("BB_pct"),
        "atr":            row.get("ATR_14"),
        "adx":            row.get("ADX_14"),
        "obv":            row.get("OBV"),
        "obv_prev":       prev.get("OBV"),
        "mfi":            row.get("MFI_14"),
        "volume_sma20":   df["Volume"].rolling(20).mean().iloc[-1],
    }
