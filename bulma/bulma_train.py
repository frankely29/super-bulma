import glob
import pathlib
from datetime import datetime
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import RobustScaler

# Paths
BULMA_DIR = pathlib.Path(__file__).resolve().parent
CSV_GLOB = str(BULMA_DIR / "*.csv")
MODEL_PATH = BULMA_DIR / "bulma_model.joblib"
SCALER_PATH = BULMA_DIR / "bulma_scaler.joblib"

# Indicators
def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)

def calculate_macd(df, fast=12, slow=26, signal=9):
    fast_ema = df["close"].ewm(span=fast).mean()
    slow_ema = df["close"].ewm(span=slow).mean()
    macd = fast_ema - slow_ema
    macd_sig = macd.ewm(span=signal).mean()
    return macd, macd_sig, macd - macd_sig

# Champions
def gohan_strat(df):
    if len(df) < 50:
        return 0.0
    rsi = calculate_rsi(df).iloc[-1]
    _, _, macd_hist = calculate_macd(df)
    macd_hist = macd_hist.iloc[-1]
    sma10 = df["close"].rolling(10).mean().iloc[-1]
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    vol_now, vol_avg = df["volume"].iloc[-1], df["volume"].rolling(20).mean().iloc[-1]
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
    score = 0.0
    if 30 <= rsi <= 70: score += 2
    elif rsi < 30:      score += 3
    if macd_hist > 0:   score += 2
    if sma10 > sma50:   score += 2
    if vol_now > vol_avg * 1.2: score += 1.5
    if price_change > 0.01:     score += 1.5
    return score

def jiren_strat(df):
    if len(df) < 50:
        return 0.0
    rsi = calculate_rsi(df).iloc[-1]
    macd_line, macd_sig, _ = calculate_macd(df)
    macd_line, macd_sig = macd_line.iloc[-1], macd_sig.iloc[-1]
    sma20 = df["close"].rolling(20).mean().iloc[-1]
    vol_now, vol_avg = df["volume"].iloc[-1], df["volume"].rolling(20).mean().iloc[-1]
    score = 0.0
    if 40 <= rsi <= 65: score += 2.5
    if macd_line > macd_sig: score += 2.5
    if df["close"].iloc[-1] > sma20: score += 2
    if vol_now > vol_avg * 1.1: score += 0.5
    return score

def freezer_strat(df):
    if len(df) < 30:
        return 0.0
    rsi = calculate_rsi(df).iloc[-1]
    _, _, macd_hist = calculate_macd(df)
    macd_hist = macd_hist.iloc[-1]
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]
    score = 0.0
    if rsi > 50: score += 2
    if macd_hist > 0: score += 2
    if price_change > 0.02: score += 2
    return score

def beerus_vote(g, j, f):
    return (g + j + f) / 3

# Load CSVs
def load_all_csv():
    files = glob.glob(CSV_GLOB)
    if not files:
        raise ValueError("❌ No CSVs found in bulma/")
    frames = []
    for f in files:
        df = pd.read_csv(f)
        if {"unix", "open", "high", "low", "close"}.issubset(df.columns):
            df = df[
                ["unix", "open", "high", "low", "close", df.columns[-1]]
            ].rename(columns={df.columns[-1]: "volume"})
            frames.append(df)
            print(f"✅ Loaded {f} shape={df.shape}")
    raw = pd.concat(frames).sort_values("unix").reset_index(drop=True)
    return raw

# Features
def engineer(df):
    out = df.copy()
    out["pct_1"] = out["close"].pct_change()
    out["pct_6"] = out["close"].pct_change(6)
    out["pct_24"] = out["close"].pct_change(24)
    out["momentum"] = out["close"].pct_change().ewm(span=12).mean()
    out["volatility"] = out["pct_1"].rolling(24).std()
    out["range_atr"] = (out["high"] - out["low"]).rolling(14).mean()
    roll_hi = out["high"].rolling(24).max()
    roll_lo = out["low"].rolling(24).min()
    out["pos_in_range"] = (out["close"] - roll_lo) / (roll_hi - roll_lo + 1e-9)
    ma20 = out["close"].rolling(20).mean()
    std20 = out["close"].rolling(20).std()
    out["bollinger_b"] = (out["close"] - ma20) / (2 * std20 + 1e-9)
    vol_med = out["volume"].rolling(24).median()
    vol_iqr = out["volume"].rolling(24).quantile(0.75) - out["volume"].rolling(24).quantile(0.25)
    out["vol_z"] = (out["volume"] - vol_med) / (vol_iqr + 1e-9)
    ts = pd.to_datetime(out["unix"], unit="s")
    out["sin_hour"] = np.sin(2 * np.pi * ts.dt.hour / 24)
    out["cos_hour"] = np.cos(2 * np.pi * ts.dt.hour / 24)
    out["sin_dow"] = np.sin(2 * np.pi * ts.dt.dayofweek / 7)
    out["cos_dow"] = np.cos(2 * np.pi * ts.dt.dayofweek / 7)
    out["pct_1_lag1"] = out["pct_1"].shift(1)
    out["pct_1_lag2"] = out["pct_1"].shift(2)
    out["volatility_lag1"] = out["volatility"].shift(1)
    out["volatility_lag2"] = out["volatility"].shift(2)
    out["momentum_lag1"] = out["momentum"].shift(1)
    out["momentum_lag2"] = out["momentum"].shift(2)

    # Beerus champions
    g_list, j_list, f_list, b_list = [], [], [], []
    for idx in range(len(out)):
        window = out.iloc[max(0, idx - 100):idx+1]
        g = gohan_strat(window)
        j = jiren_strat(window)
        f = freezer_strat(window)
        b = beerus_vote(g, j, f)
        g_list.append(g)
        j_list.append(j)
        f_list.append(f)
        b_list.append(b)
    out["gohan_conf"] = g_list
    out["jiren_conf"] = j_list
    out["freezer_conf"] = f_list
    out["beerus_conf"] = b_list

    return out.dropna().reset_index(drop=True)

# Labels
def make_labels(df):
    fwd_ret = df["close"].shift(-3) / df["close"] - 1
    label = pd.Series("hold", index=df.index)
    label[fwd_ret > 0.003] = "buy"
    label[fwd_ret < -0.003] = "sell"
    return label[:-3]

# Main
def main():
    print("🚀 Bulma training starting...")

    raw = load_all_csv()
    print(f"✅ Combined shape: {raw.shape}")

    feat = engineer(raw)
    y = make_labels(feat)
    X = feat.loc[y.index].drop(["unix","open","high","low","close","volume"], axis=1)

    scaler = RobustScaler()
    scaler.fit(X)
    X_scaled = scaler.transform(X)

    cv = TimeSeriesSplit(n_splits=5)
    model = HistGradientBoostingClassifier(max_iter=300, random_state=42)
    scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")
    print(f"⚡ mean accuracy = {scores.mean():.4f}")

    model.fit(X_scaled, y)
    calib = CalibratedClassifierCV(model, method="isotonic", cv=cv)
    calib.fit(X_scaled, y)

    joblib.dump(calib, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"✅ trained Bulma ({ts}) with {len(y):,} samples")
    print(f"   model: {MODEL_PATH}")
    print(f"   scaler: {SCALER_PATH}")

if __name__ == "__main__":
    main()
