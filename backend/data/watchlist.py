"""Custom watchlist manager — extends the base config WATCHLIST without touching config.py."""
import json
import os
from config import WATCHLIST as _BASE_WATCHLIST, DATA_DIR

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
