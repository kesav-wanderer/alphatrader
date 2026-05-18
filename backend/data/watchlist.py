"""Custom watchlist manager — extends the base config WATCHLIST without touching config.py."""
import json
import os
from config import WATCHLIST as _BASE_WATCHLIST, DATA_DIR

_NSE_EXCHANGES = {"NSE", "NSI", "NMS"}
_BSE_EXCHANGES = {"BOM", "BSE"}


def search_stocks(query: str, max_results: int = 12) -> list:
    """
    Search Yahoo Finance for stocks matching query.
    Returns list sorted by relevance: exact symbol > symbol starts-with > name match.
    NSE preferred over BSE for duplicate symbols.
    """
    if not query or len(query.strip()) < 2:
        return []

    q_upper = query.strip().upper()

    try:
        import yfinance as yf
        s = yf.Search(query.strip(), max_results=max_results * 3, news_count=0)
        quotes = s.quotes or []
    except Exception:
        return []

    full_wl = set(get_full_watchlist())
    seen_base = set()   # deduplicate: keep NSE over BSE for same base symbol
    candidates = []

    for q in quotes:
        exch = q.get("exchange", "")
        sym  = q.get("symbol", "")
        name = q.get("shortname") or q.get("longname") or sym
        if not sym:
            continue

        if exch in _NSE_EXCHANGES:
            display_sym = sym if sym.endswith(".NS") else sym + ".NS"
        elif exch in _BSE_EXCHANGES:
            display_sym = sym if sym.endswith(".BO") else sym + ".BO"
        else:
            continue

        # base symbol without suffix for dedup
        base = display_sym.replace(".NS", "").replace(".BO", "")
        if base in seen_base:
            continue
        seen_base.add(base)

        # Relevance score — lower = higher priority
        if base == q_upper:
            rank = 0                          # exact symbol match
        elif base.startswith(q_upper):
            rank = 1                          # symbol starts with query
        elif name.upper().startswith(q_upper):
            rank = 2                          # company name starts with query
        elif q_upper in base:
            rank = 3                          # query anywhere in symbol
        else:
            rank = 4                          # name contains query

        # NSE preferred within same rank
        exch_order = 0 if exch in _NSE_EXCHANGES else 1

        candidates.append({
            "symbol":        display_sym,
            "name":          name,
            "exchange":      exch,
            "already_added": display_sym in full_wl,
            "_rank":         (rank, exch_order),
        })

    candidates.sort(key=lambda x: x["_rank"])
    for c in candidates:
        c.pop("_rank")

    return candidates[:max_results]

CUSTOM_WL_FILE = os.path.join(DATA_DIR, "custom_watchlist.json")


def get_custom_stocks() -> list:
    if os.path.exists(CUSTOM_WL_FILE):
        try:
            with open(CUSTOM_WL_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def get_full_watchlist() -> list:
    """Base watchlist + any custom stocks added via UI."""
    custom = get_custom_stocks()
    base = list(_BASE_WATCHLIST)
    for s in custom:
        if s not in base:
            base.append(s)
    return base


def normalise(symbol: str) -> str:
    s = symbol.upper().strip().replace(" ", "")
    if not s.endswith(".NS") and not s.endswith(".BO"):
        s += ".NS"
    return s


def add_stock(symbol: str) -> tuple[bool, str]:
    """Add a stock. Returns (success, message)."""
    sym = normalise(symbol)
    if sym in _BASE_WATCHLIST:
        return False, f"{sym} is already in the base watchlist"
    custom = get_custom_stocks()
    if sym in custom:
        return False, f"{sym} already added"
    custom.append(sym)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CUSTOM_WL_FILE, "w") as f:
        json.dump(custom, f)
    return True, f"{sym} added to watchlist"


def remove_stock(symbol: str) -> tuple[bool, str]:
    """Remove a custom stock. Cannot remove base-watchlist stocks."""
    sym = normalise(symbol)
    if sym in _BASE_WATCHLIST:
        return False, f"{sym} is in the base watchlist and cannot be removed here"
    custom = get_custom_stocks()
    if sym not in custom:
        return False, f"{sym} not found in custom watchlist"
    custom.remove(sym)
    with open(CUSTOM_WL_FILE, "w") as f:
        json.dump(custom, f)
    return True, f"{sym} removed"
