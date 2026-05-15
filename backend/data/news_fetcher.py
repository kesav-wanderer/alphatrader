"""Stock news fetcher using yfinance — caches results to avoid rate limits."""
import time
import yfinance as yf
from config import DATA_DIR

_news_cache: dict = {}
_CACHE_TTL = 900  # 15 min

POSITIVE_KEYWORDS = {
    "profit", "growth", "surge", "rally", "beat", "upgrade", "buy", "strong",
    "record", "gain", "outperform", "expansion", "dividend", "acquisition",
    "approval", "launch", "win", "deal", "partnership", "breakthrough", "high",
    "revenue", "bullish", "positive", "rises", "rises", "jumps", "soars",
}
NEGATIVE_KEYWORDS = {
    "loss", "decline", "fall", "drop", "miss", "downgrade", "sell", "weak",
    "penalty", "fraud", "fine", "probe", "default", "crash", "layoff",
    "resign", "exit", "concern", "risk", "debt", "warning", "investigation",
    "bearish", "negative", "falls", "slumps", "tumbles", "plunges", "cut",
}


def _sentiment_score(text: str) -> float:
    """Keyword-based sentiment, returns -1.0 to +1.0."""
    words = set(text.lower().split())
    pos = len(words & POSITIVE_KEYWORDS)
    neg = len(words & NEGATIVE_KEYWORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def get_stock_news(symbol: str, max_articles: int = 5) -> list:
    """Fetch recent news headlines for a stock. Cached for 15 min."""
    entry = _news_cache.get(symbol)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"][:max_articles]

    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
        articles = []
        for item in raw_news[:max_articles]:
            content = item.get("content", {})
            if content and isinstance(content, dict):
                title = content.get("title", "")
                summary = (content.get("summary") or "")[:200]
                provider_obj = content.get("provider", {})
                publisher = provider_obj.get("displayName", "") if isinstance(provider_obj, dict) else ""
                pub_date = content.get("pubDate", "")
                url_obj = content.get("canonicalUrl", {})
                link = url_obj.get("url", "") if isinstance(url_obj, dict) else ""
            else:
                title = item.get("title", "")
                summary = (item.get("summary") or "")[:200]
                publisher = item.get("publisher", "")
                pub_date = str(item.get("providerPublishTime", ""))
                link = item.get("link", "")

            if not title:
                continue
            sentiment = _sentiment_score(title + " " + summary)
            articles.append({
                "title": title,
                "summary": summary,
                "publisher": publisher or "News",
                "published": str(pub_date)[:19].replace("T", " "),
                "link": link,
                "sentiment": sentiment,
            })

        _news_cache[symbol] = {"ts": time.time(), "data": articles}
        return articles
    except Exception:
        return []


def get_news_sentiment_signal(symbol: str) -> dict:
    """Returns signal dict: value (+1/0/-1), confidence, label, detail."""
    articles = get_stock_news(symbol, max_articles=5)
    if not articles:
        return {"value": 0, "confidence": 0.0, "label": "NEWS", "detail": "No news available"}

    avg_sentiment = sum(a["sentiment"] for a in articles) / len(articles)

    if avg_sentiment >= 0.15:
        conf = min(0.4 + abs(avg_sentiment), 0.7)
        return {"value": 1, "confidence": round(conf, 2), "label": "NEWS",
                "detail": f"Positive news sentiment ({avg_sentiment:+.2f})"}
    elif avg_sentiment <= -0.15:
        conf = min(0.4 + abs(avg_sentiment), 0.7)
        return {"value": -1, "confidence": round(conf, 2), "label": "NEWS",
                "detail": f"Negative news sentiment ({avg_sentiment:+.2f})"}
    else:
        return {"value": 0, "confidence": 0.3, "label": "NEWS",
                "detail": f"Neutral news sentiment ({avg_sentiment:+.2f})"}
