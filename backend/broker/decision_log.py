"""Decision logger — records every signal evaluation + trade outcome as training data."""
import json
import os
from datetime import datetime
from config import DATA_DIR

DECISION_LOG_FILE = os.path.join(DATA_DIR, "decision_log.jsonl")


def log_decision(symbol: str, action: str, price: float,
                 signals: list, score: int, confidence: float,
                 stop_loss: float = None, target: float = None,
                 news_sentiment: float = None):
    """Append one decision record. Signals is a list of dicts or Signal objects."""
    sig_dicts = []
    for s in signals:
        if hasattr(s, "__dict__"):
            sig_dicts.append({"name": s.name, "value": s.value,
                              "reason": s.reason, "confidence": s.confidence})
        else:
            sig_dicts.append(s)

    record = {
        "ts": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "action": action,
        "price": price,
        "score": score,
        "confidence": confidence,
        "stop_loss": stop_loss,
        "target": target,
        "news_sentiment": news_sentiment,
        "signals": sig_dicts,
        "outcome": None,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DECISION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def update_outcome(symbol: str, exit_price: float, pnl_pct: float, exit_reason: str):
    """Update the most recent unresolved BUY record for this symbol with outcome."""
    if not os.path.exists(DECISION_LOG_FILE):
        return
    with open(DECISION_LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for i in range(len(lines) - 1, -1, -1):
        try:
            rec = json.loads(lines[i])
            if (rec.get("symbol") == symbol
                    and rec.get("action") == "BUY"
                    and rec.get("outcome") is None):
                rec["outcome"] = {
                    "exit_price": exit_price,
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "exit_ts": datetime.utcnow().isoformat(),
                    "profitable": pnl_pct > 0,
                }
                lines[i] = json.dumps(rec, default=str) + "\n"
                updated = True
                break
        except Exception:
            pass

    if updated:
        with open(DECISION_LOG_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)


def get_recent_decisions(limit: int = 100) -> list:
    """Return most recent decision records, newest first."""
    if not os.path.exists(DECISION_LOG_FILE):
        return []
    with open(DECISION_LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    records = []
    for line in reversed(lines):
        try:
            records.append(json.loads(line.strip()))
            if len(records) >= limit:
                break
        except Exception:
            pass
    return records


def export_training_csv() -> str:
    """Return CSV string of completed (outcome-known) decisions for ML training."""
    records = get_recent_decisions(limit=10000)
    completed = [r for r in records if r.get("outcome")]
    if not completed:
        return "ts,symbol,action,price,score,confidence,news_sentiment,pnl_pct,profitable\n"

    lines = ["ts,symbol,action,price,score,confidence,news_sentiment,pnl_pct,profitable"]
    for r in completed:
        o = r["outcome"]
        lines.append(",".join([
            r.get("ts", ""),
            r.get("symbol", ""),
            r.get("action", ""),
            str(r.get("price", "")),
            str(r.get("score", "")),
            str(r.get("confidence", "")),
            str(r.get("news_sentiment") or ""),
            str(o.get("pnl_pct", "")),
            str(int(o.get("profitable", False))),
        ]))
    return "\n".join(lines)
