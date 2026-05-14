import yfinance as yf
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta
from config import DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

# IST market hours
MARKET_OPEN  = 9 * 60 + 15   # 9:15 in minutes
MARKET_CLOSE = 15 * 60 + 30  # 15:30 in minutes


def _is_market_hours() -> bool:
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)  # UTC -> IST
    mins = now.hour * 60 + now.minute
    return now.weekday() < 5 and MARKET_OPEN <= mins <= MARKET_CLOSE


def _cache_ttl() -> int:
    """5 min during market hours, 60 min otherwise."""
    return 5 if _is_market_hours() else 60


def _cache_path(symbol: str, key: str) -> str:
    h = hashlib.md5(f"{symbol}_{key}".encode()).hexdigest()[:8]
    return os.path.join(DATA_DIR, f"{symbol.replace('.', '_')}_{h}.parquet")


def fetch_ohlcv(symbol: str, period: str = "1y", interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
    cache_file = _cache_path(symbol, f"{period}_{interval}")
    ttl = _cache_ttl()

    if use_cache and os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - mtime < timedelta(minutes=ttl):
            return pd.read_parquet(cache_file)

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f"No data for {symbol}")

    df.index = pd.to_datetime(df.index)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.to_parquet(cache_file)
    return df


def get_live_price(symbol: str) -> dict:
    """Fast live price using yfinance fast_info — no cache."""
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        return {
            "symbol":        symbol,
            "price":         round(fi.last_price, 2),
            "prev_close":    round(fi.previous_close, 2),
            "change":        round(fi.last_price - fi.previous_close, 2),
            "change_pct":    round(((fi.last_price - fi.previous_close) / fi.previous_close) * 100, 2),
            "day_high":      round(fi.day_high, 2),
            "day_low":       round(fi.day_low, 2),
            "volume":        int(fi.three_month_average_volume or 0),
            "timestamp":     datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        return {"symbol": symbol, "price": None, "error": str(e)}


def get_live_prices(symbols: list) -> dict:
    """Returns {symbol: live_price_dict} for all symbols."""
    return {sym: get_live_price(sym) for sym in symbols}


def fetch_multiple(symbols: list, period: str = "1y", interval: str = "1d") -> dict:
    result = {}
    for sym in symbols:
        try:
            result[sym] = fetch_ohlcv(sym, period, interval)
        except Exception as e:
            print(f"[fetcher] skipping {sym}: {e}")
    return result


def fetch_info(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info
        return {
            "name":        info.get("longName", symbol),
            "sector":      info.get("sector", "N/A"),
            "industry":    info.get("industry", "N/A"),
            "market_cap":  info.get("marketCap", 0),
            "pe_ratio":    info.get("trailingPE"),
            "52w_high":    info.get("fiftyTwoWeekHigh"),
            "52w_low":     info.get("fiftyTwoWeekLow"),
            "current_price": info.get("currentPrice"),
        }
    except Exception:
        return {"name": symbol}
