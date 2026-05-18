"""
Phase 2 ML Training Pipeline.
Downloads NSE data, engineers features, trains XGBoost model.
Run: python -m backend.models.trainer
"""
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

from backend.data.fetcher import fetch_ohlcv
from backend.data.indicators import add_indicators
from config import WATCHLIST, MODELS_DIR

os.makedirs(MODELS_DIR, exist_ok=True)

LOOKAHEAD_DAYS = 3       # predict if price is higher in N days
MIN_RETURN_PCT = 0.02    # label as BUY if return > 2%
TRAIN_PERIOD   = "2y"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert indicator df to ML feature matrix."""
    df = df.copy()

    # Price-relative features (normalised, no data leakage)
    df["ret_1d"]  = df["Close"].pct_change(1)
    df["ret_3d"]  = df["Close"].pct_change(3)
    df["ret_5d"]  = df["Close"].pct_change(5)
    df["ret_10d"] = df["Close"].pct_change(10)

    df["close_vs_ema20"]  = (df["Close"] - df["EMA_20"])  / df["EMA_20"]
    df["close_vs_ema50"]  = (df["Close"] - df["EMA_50"])  / df["EMA_50"]
    df["close_vs_ema200"] = (df["Close"] - df["EMA_200"]) / df["EMA_200"]
    df["ema20_vs_ema50"]  = (df["EMA_20"] - df["EMA_50"]) / df["EMA_50"]

    df["bb_position"] = df["BB_pct"]
    df["rsi"]         = df["RSI_14"]
    df["macd_hist"]   = df["MACD_hist"]
    df["macd_norm"]   = df["MACD"] / df["Close"]
    df["adx"]         = df["ADX_14"]
    df["mfi"]         = df["MFI_14"]

    df["vol_ratio"]   = df["Volume"] / df["Volume"].rolling(20).mean()
    df["atr_pct"]     = df["ATR_14"] / df["Close"]

    # Stochastic
    df["stoch_k"] = df["STOCH_k"]
    df["stoch_d"] = df["STOCH_d"]

    # Label: will price be MIN_RETURN_PCT higher in LOOKAHEAD_DAYS?
    future_ret = df["Close"].shift(-LOOKAHEAD_DAYS) / df["Close"] - 1
    df["label"] = (future_ret > MIN_RETURN_PCT).astype(int)

    return df


FEATURE_COLS = [
    "ret_1d", "ret_3d", "ret_5d", "ret_10d",
    "close_vs_ema20", "close_vs_ema50", "close_vs_ema200", "ema20_vs_ema50",
    "bb_position", "rsi", "macd_hist", "macd_norm",
    "adx", "mfi", "vol_ratio", "atr_pct", "stoch_k", "stoch_d",
]


def load_dataset(symbols: list, period: str = TRAIN_PERIOD) -> tuple:
    """Returns X, y arrays from all symbols combined."""
    all_frames = []
    for sym in symbols:
        try:
            df_raw = fetch_ohlcv(sym, period=period)
            df_ind = add_indicators(df_raw)
            df_feat = build_features(df_ind)
            df_feat["symbol"] = sym
            all_frames.append(df_feat)
            print(f"  ✓ {sym}: {len(df_feat)} rows")
        except Exception as e:
            print(f"  ✗ {sym}: {e}")

    if not all_frames:
        raise ValueError("No data loaded")

    combined = pd.concat(all_frames).dropna(subset=FEATURE_COLS + ["label"])
    X = combined[FEATURE_COLS].values.astype(np.float32)
    y = combined["label"].values.astype(int)
    print(f"\nDataset: {len(X)} samples | BUY labels: {y.sum()} ({y.mean():.1%})")
    return X, y, combined


def train(symbols: list = None, period: str = TRAIN_PERIOD):
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, roc_auc_score
        from sklearn.preprocessing import StandardScaler
        import xgboost as xgb
    except ImportError:
        print("Run: pip install -r requirements-ml.txt")
        return

    symbols = symbols or WATCHLIST
    print(f"Loading data for {len(symbols)} symbols  period={period}...")
    X, y, df_full = load_dataset(symbols, period=period)

    # Time-aware split — last 20% as test (no shuffle, respects time order)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    # Class imbalance weight
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        eval_metric="logloss",
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining XGBoost model...")
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=50)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n--- Evaluation ---")
    print(classification_report(y_test, y_pred, target_names=["HOLD", "BUY"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.4f}")

    # Feature importance
    importances = sorted(zip(FEATURE_COLS, model.feature_importances_), key=lambda x: -x[1])
    print("\nTop features:")
    for feat, imp in importances[:8]:
        print(f"  {feat:<25} {imp:.4f}")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    model_path  = os.path.join(MODELS_DIR, f"xgb_{ts}.pkl")
    scaler_path = os.path.join(MODELS_DIR, f"scaler_{ts}.pkl")
    latest_model  = os.path.join(MODELS_DIR, "xgb_latest.pkl")
    latest_scaler = os.path.join(MODELS_DIR, "scaler_latest.pkl")

    with open(model_path,  "wb") as f: pickle.dump(model,  f)
    with open(scaler_path, "wb") as f: pickle.dump(scaler, f)
    with open(latest_model,  "wb") as f: pickle.dump(model,  f)
    with open(latest_scaler, "wb") as f: pickle.dump(scaler, f)

    print(f"\nModel saved → {model_path}")
    return model, scaler


if __name__ == "__main__":
    train()
