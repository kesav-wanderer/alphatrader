"""
Auto paper trader:
- Morning scan: finds BUY signals, places paper orders automatically
- Position monitor: checks open positions every 5 min, exits on SL/target
"""
import sys
sys.path.insert(0, ".")

import os
import time
import threading
from datetime import datetime, timedelta
from backend.data.fetcher import fetch_ohlcv, get_live_price, _is_market_hours
from backend.data.indicators import add_indicators, get_indicator_snapshot
from backend.strategies.signal_engine import evaluate_signals
from backend.broker.paper_broker import get_portfolio, place_order, get_pnl, calc_capital_per_trade
from backend.broker.decision_log import log_decision, update_outcome
from backend.data.watchlist import get_full_watchlist
from config import RISK_PER_TRADE_PCT


def _cfg():
    from backend.broker.paper_broker import load_trader_config
    return load_trader_config()

CAPITAL_PER_TRADE  = 25000  # default — overridden at runtime by _cfg()
MAX_OPEN_POSITIONS = 4      # default — overridden at runtime by _cfg()
LOG_FILE = os.path.join(os.getenv("DATA_DIR", "./data/cache"), "auto_trader.log")

_MONITOR_LOCK = threading.Lock()  # prevents concurrent monitor runs causing duplicate sells
_SCAN_LOCK    = threading.Lock()  # prevents concurrent morning scans


def _ist_now() -> datetime:
    """Always return current IST time (UTC+5:30), regardless of host timezone."""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def log(msg: str):
    ts = _ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


MIN_CAPITAL_PER_SLOT = 2000  # don't open a position if allocated capital is below this


def morning_scan(label: str = "Morning Scan"):
    """Run at market open — scan watchlist, place BUY orders for top signals."""
    if not _SCAN_LOCK.acquire(blocking=False):
        log(f"{label} already running — skipping duplicate call")
        return
    try:
        _morning_scan_inner(label)
    finally:
        _SCAN_LOCK.release()


def _morning_scan_inner(label: str = "Morning Scan"):
    cfg = _cfg()
    max_open_positions = cfg["max_open_positions"]
    log(f"=== {label} Started ===")
    portfolio = get_portfolio()
    open_pos  = len(portfolio.get("positions", {}))
    cash      = portfolio.get("cash", 0.0)

    if open_pos >= max_open_positions:
        log(f"Ceiling reached ({open_pos}/{max_open_positions} positions). Skipping scan.")
        return

    slots = max_open_positions - open_pos

    # Cap slots by how many the available cash can actually fund
    cap_per_slot = calc_capital_per_trade(cfg)
    if cap_per_slot < MIN_CAPITAL_PER_SLOT:
        log(f"Cash too low for new positions (₹{cap_per_slot:.0f}/slot < ₹{MIN_CAPITAL_PER_SLOT} min). Skipping.")
        return

    log(f"  {open_pos}/{max_open_positions} positions open · {slots} slot(s) available · ₹{cap_per_slot:,.0f}/slot")
    candidates = []

    for sym in get_full_watchlist():
        # Skip if already holding
        if sym in portfolio.get("positions", {}):
            continue
        try:
            df_raw   = fetch_ohlcv(sym, period="1y", use_cache=True)
            df_ind   = add_indicators(df_raw)
            snap     = get_indicator_snapshot(df_ind)
            decision = evaluate_signals(sym, snap, df_raw=df_raw)
            if decision.action == "BUY":
                candidates.append((decision.score, decision.confidence, sym, decision, snap))
        except Exception as e:
            log(f"  scan error {sym}: {e}")

    # Sort by score + confidence, take top N
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    placed = 0

    for score, conf, sym, decision, snap in candidates[:slots]:
        live = get_live_price(sym)
        price = live.get("price") or snap.get("close", 0)
        if not price:
            continue

        # Dynamic sizing: recalculate per slot so each trade uses fair share
        capital_per_trade = calc_capital_per_trade(cfg)
        qty = int(capital_per_trade / price)
        if qty == 0:
            continue

        trade = place_order(
            symbol=sym, action="BUY", qty=qty, price=price,
            stop_loss=decision.stop_loss, target=decision.target
        )
        if trade["status"] == "EXECUTED":
            log(f"  BUY  {sym:<18} qty={qty}  price=Rs{price:.2f}  "
                f"sl=Rs{decision.stop_loss}  target=Rs{decision.target}  score={score}  capital=Rs{capital_per_trade:.0f}")
            placed += 1
            try:
                news_sentiment = None
                from backend.data.news_fetcher import get_news_sentiment_signal
                ns = get_news_sentiment_signal(sym)
                news_sentiment = ns.get("value", 0) * ns.get("confidence", 0)
                log_decision(sym, "BUY", price, decision.signals, score, conf,
                             decision.stop_loss, decision.target, news_sentiment)
            except Exception:
                pass
        else:
            log(f"  REJECTED {sym}: {trade.get('reason')}")

    log(f"=== Morning Scan Done — {placed} orders placed ===")


def monitor_positions():
    """Check all open positions against live prices. Exit on SL/target."""
    if not _MONITOR_LOCK.acquire(blocking=False):
        log("monitor_positions already running — skipping duplicate call")
        return
    try:
        _monitor_positions_inner()
    finally:
        _MONITOR_LOCK.release()


def _monitor_positions_inner():
    portfolio = get_portfolio()
    positions = portfolio.get("positions", {})
    if not positions:
        return

    syms = list(positions.keys())
    log(f"--- monitor: checking {len(syms)} position(s): {', '.join(s.replace('.NS','') for s in syms)}")

    for sym, pos in list(positions.items()):
        try:
            live  = get_live_price(sym)
            price = live.get("price")
            if not price:
                continue

            sl     = pos.get("stop_loss")
            target = pos.get("target")
            qty    = pos["qty"]
            avg    = pos["avg_price"]
            pnl_pct = ((price - avg) / avg) * 100

            reason = None
            if sl and price <= sl:
                reason = f"STOPLOSS hit ₹{price:.2f} <= sl=₹{sl}"
            elif target and price >= target:
                reason = f"TARGET hit ₹{price:.2f} >= target=₹{target}"
            elif pnl_pct <= -3.0:
                reason = f"Emergency exit pnl={pnl_pct:.1f}%"

            if reason:
                # Re-read portfolio right before selling to avoid duplicate sells
                # from concurrent monitor calls all seeing the same snapshot
                live_portfolio = get_portfolio()
                if sym not in live_portfolio.get("positions", {}):
                    log(f"  SKIP {sym} — position already closed by concurrent call")
                    continue
                trade = place_order(sym, "SELL", qty, price)
                if trade["status"] == "EXECUTED":
                    log(f"  SELL {sym:<18} qty={qty}  price=Rs{price:.2f}  "
                        f"pnl={pnl_pct:+.1f}%  reason={reason}")
                    try:
                        update_outcome(sym, price, pnl_pct, reason)
                    except Exception:
                        pass
                else:
                    log(f"  SELL FAILED {sym}: {trade.get('reason')}")
            # HOLD is a non-event — don't log it, keeps activity log clean

        except Exception as e:
            log(f"  monitor error {sym}: {e}")


def run_loop(scan_interval_min: int = 5):
    """
    Run continuously during market hours.
    - Does morning scan once at open
    - Monitors positions every scan_interval_min minutes
    """
    log("Auto trader started. Ctrl+C to stop.")
    morning_done = False

    while True:
        now = datetime.now()

        if not _is_market_hours():
            log("Market closed. Waiting...")
            morning_done = False     # reset for next day
            time.sleep(300)
            continue

        # Morning scan — run once between 9:15 and 9:25 IST
        ist = _ist_now()
        if ist.hour == 9 and 15 <= ist.minute <= 25 and not morning_done:
            morning_scan()
            morning_done = True

        # Position monitor
        monitor_positions()
        time.sleep(scan_interval_min * 60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        morning_scan()
    elif len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_positions()
    else:
        run_loop()
