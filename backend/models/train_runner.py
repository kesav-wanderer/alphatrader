"""Background ML training runner — captures output to a log file so the UI can stream it."""
import json
import os
import sys
import threading
from datetime import datetime
from config import DATA_DIR, MODELS_DIR

TRAIN_LOG_FILE   = os.path.join(DATA_DIR, "ml_training.log")
TRAIN_STATE_FILE = os.path.join(DATA_DIR, "ml_training_state.json")

_lock = threading.Lock()


class _LogCapture:
    """Tees sys.stdout writes to the training log file."""
    def __init__(self, log_path: str, original):
        self._path = log_path
        self._orig = original

    def write(self, msg: str):
        self._orig.write(msg)
        if msg.strip():
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(msg if msg.endswith("\n") else msg + "\n")

    def flush(self):
        self._orig.flush()


def _set_state(status: str, message: str = "", metrics: dict = None):
    state = {
        "status": status,
        "message": message,
        "updated": datetime.now().isoformat(),
        "metrics": metrics or {},
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRAIN_STATE_FILE, "w") as f:
        json.dump(state, f)


def get_training_state() -> dict:
    if os.path.exists(TRAIN_STATE_FILE):
        try:
            with open(TRAIN_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"status": "idle", "message": "", "updated": "", "metrics": {}}


def get_training_log(last_n: int = 80) -> str:
    if not os.path.exists(TRAIN_LOG_FILE):
        return ""
    with open(TRAIN_LOG_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-last_n:])


def get_model_info() -> dict:
    mp = os.path.join(MODELS_DIR, "xgb_latest.pkl")
    if not os.path.exists(mp):
        return {"exists": False}
    mtime = os.path.getmtime(mp)
    return {
        "exists": True,
        "trained_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
        "size_kb": round(os.path.getsize(mp) / 1024, 1),
    }


def _run_training(symbols: list, period: str):
    orig_stdout = sys.stdout
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        open(TRAIN_LOG_FILE, "w").close()           # clear previous log
        sys.stdout = _LogCapture(TRAIN_LOG_FILE, orig_stdout)

        _set_state("running", f"Training on {len(symbols)} stocks…")
        print(f"=== ML Training started  |  stocks={len(symbols)}  period={period} ===")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        from backend.models.trainer import train
        result = train(symbols=symbols, period=period)

        if result:
            model, scaler = result
            info = get_model_info()
            _set_state("done",
                       f"Model ready — trained {datetime.now().strftime('%H:%M')}",
                       {"trained_at": info.get("trained_at", "")})
            print(f"\n=== Training complete — model saved ===")
        else:
            _set_state("error", "Training returned no result — check log")
            print("\n=== Training returned no result ===")

    except Exception as e:
        _set_state("error", f"Failed: {e}")
        print(f"\n=== Training FAILED: {e} ===")
    finally:
        sys.stdout = orig_stdout


def start_training(symbols: list = None, period: str = "2y") -> tuple[bool, str]:
    """Launch training in background thread. Returns (started, message)."""
    with _lock:
        state = get_training_state()
        if state.get("status") == "running":
            return False, "Training already in progress"

        if symbols is None:
            from backend.data.watchlist import get_full_watchlist
            symbols = get_full_watchlist()

        t = threading.Thread(target=_run_training, args=(symbols, period), daemon=True)
        t.start()
        return True, f"Training started on {len(symbols)} stocks"
