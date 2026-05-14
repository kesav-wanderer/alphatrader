"""Load trained model and score live snapshots."""
import os
import pickle
import numpy as np
from config import MODELS_DIR
from backend.models.trainer import FEATURE_COLS, build_features
from backend.data.indicators import add_indicators

_model  = None
_scaler = None


def _load():
    global _model, _scaler
    mp = os.path.join(MODELS_DIR, "xgb_latest.pkl")
    sp = os.path.join(MODELS_DIR, "scaler_latest.pkl")
    if os.path.exists(mp) and os.path.exists(sp):
        with open(mp, "rb") as f: _model  = pickle.load(f)
        with open(sp, "rb") as f: _scaler = pickle.load(f)
        return True
    return False


def model_available() -> bool:
    return os.path.exists(os.path.join(MODELS_DIR, "xgb_latest.pkl"))


def predict_proba(df_raw) -> float:
    """Return BUY probability 0–1 for a raw OHLCV dataframe."""
    global _model, _scaler
    if _model is None and not _load():
        return None

    try:
        df_ind  = add_indicators(df_raw)
        df_feat = build_features(df_ind)
        df_feat = df_feat.dropna(subset=FEATURE_COLS)
        if df_feat.empty:
            return None

        row = df_feat[FEATURE_COLS].iloc[[-1]].values.astype(np.float32)
        row = _scaler.transform(row)
        prob = float(_model.predict_proba(row)[0][1])
        return round(prob, 4)
    except Exception as e:
        print(f"[predictor] {e}")
        return None
