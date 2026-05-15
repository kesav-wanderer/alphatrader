"""Paper trading broker — simulates orders without real money."""
import json
import os
from datetime import datetime
from config import DATA_DIR

PORTFOLIO_FILE = os.path.join(DATA_DIR, "paper_portfolio.json")


def _load() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return {"cash": 100000.0, "positions": {}, "trades": []}


def _save(portfolio: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)


def get_portfolio() -> dict:
    return _load()


def place_order(symbol: str, action: str, qty: int, price: float, stop_loss: float = None, target: float = None) -> dict:
    portfolio = _load()
    cost = qty * price
    trade = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "qty": qty,
        "price": price,
        "cost": cost,
        "stop_loss": stop_loss,
        "target": target,
        "status": "EXECUTED",
    }

    if action == "BUY":
        if portfolio["cash"] < cost:
            trade["status"] = "REJECTED"
            trade["reason"] = "Insufficient cash"
        else:
            portfolio["cash"] -= cost
            pos = portfolio["positions"].get(symbol, {"qty": 0, "avg_price": 0})
            total_qty = pos["qty"] + qty
            avg = ((pos["qty"] * pos["avg_price"]) + cost) / total_qty
            portfolio["positions"][symbol] = {
                "qty": total_qty,
                "avg_price": round(avg, 2),
                "stop_loss": stop_loss,
                "target": target,
                "entry_time": datetime.now().isoformat(),
            }

    elif action == "SELL":
        pos = portfolio["positions"].get(symbol)
        if not pos or pos["qty"] < qty:
            trade["status"] = "REJECTED"
            trade["reason"] = "No position to sell"
        else:
            portfolio["cash"] += cost
            new_qty = pos["qty"] - qty
            if new_qty == 0:
                del portfolio["positions"][symbol]
            else:
                portfolio["positions"][symbol]["qty"] = new_qty

    portfolio["trades"].append(trade)
    _save(portfolio)
    return trade


def get_pnl(current_prices: dict) -> dict:
    portfolio = _load()
    pnl = {}
    total_invested = 0
    total_current = 0

    for sym, pos in portfolio["positions"].items():
        cur = current_prices.get(sym, pos["avg_price"])
        invested = pos["qty"] * pos["avg_price"]
        current = pos["qty"] * cur
        pl = current - invested
        pnl[sym] = {
            "qty": pos["qty"],
            "avg_price": pos["avg_price"],
            "current_price": cur,
            "invested": round(invested, 2),
            "current_value": round(current, 2),
            "pnl": round(pl, 2),
            "pnl_pct": round((pl / invested) * 100, 2) if invested else 0,
        }
        total_invested += invested
        total_current += current

    return {
        "positions": pnl,
        "cash": round(portfolio["cash"], 2),
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_current - total_invested, 2),
        "total_pnl_pct": round(((total_current - total_invested) / total_invested) * 100, 2) if total_invested else 0,
    }


CONFIG_FILE = os.path.join(DATA_DIR, "trader_config.json")
_DEFAULT_CFG = {"capital_per_trade": 25000, "max_open_positions": 4, "starting_cash": 100000}


def load_trader_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return {**_DEFAULT_CFG, **json.load(f)}
        except Exception:
            pass
    return _DEFAULT_CFG.copy()


def save_trader_config(cfg: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({**_DEFAULT_CFG, **cfg}, f, indent=2)


def reset_portfolio(starting_cash: float = 100000.0):
    """Wipe all positions and trades, restore cash to starting_cash."""
    _save({"cash": round(starting_cash, 2), "positions": {}, "trades": []})
