from pathlib import Path
import pandas as pd
import numpy as np
import joblib

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = df["close"].ewm(span=fast).mean()
    slow_ema = df["close"].ewm(span=slow).mean()
    macd = fast_ema - slow_ema
    macd_sig = macd.ewm(span=signal).mean()
    return macd, macd_sig, macd - macd_sig

def gohan_strat(df: pd.DataFrame):
    if len(df) < 50:
        return 0.0
    rsi = calculate_rsi(df).iloc[-1]
    _, _, macd_hist = calculate_macd(df)
    macd_hist = macd_hist.iloc[-1]
    sma10 = df["close"].rolling(10).mean().iloc[-1]
    sma50 = df["close"].rolling(50).mean().iloc[-1]
    vol_now = df["volume"].iloc[-1]
    vol_avg = df["volume"].rolling(20).mean().iloc[-1]
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
    score = 0.0
    if 30 <= rsi <= 70: score += 2
    elif rsi < 30: score += 3
    if macd_hist > 0: score += 2
    if sma10 > sma50: score += 2
    if vol_now > vol_avg * 1.2: score += 1.5
    if price_change > 0.01: score += 1.5
    return score

def jiren_strat(df: pd.DataFrame):
    if len(df) < 50:
        return 0.0
    rsi = calculate_rsi(df).iloc[-1]
    macd_line, macd_sig, _ = calculate_macd(df)
    macd_line, macd_sig = macd_line.iloc[-1], macd_sig.iloc[-1]
    sma20 = df["close"].rolling(20).mean().iloc[-1]
    vol_now = df["volume"].iloc[-1]
    vol_avg = df["volume"].rolling(20).mean().iloc[-1]
    score = 0.0
    if 40 <= rsi <= 65: score += 2.5
    if macd_line > macd_sig: score += 2.5
    if df["close"].iloc[-1] > sma20: score += 2
    if vol_now > vol_avg * 1.1: score += 0.5
    return score

def freezer_strat(df: pd.DataFrame):
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

class BulmaEngine:
    def __init__(self):
        here = Path(__file__).resolve().parent
        self.model = None
        self.scaler = None
        self.entry_prices = {}
        self.stop_losses = {}
        self.profit_tiers = {}
        self.trailing_highs = {}

        model_path = here / "bulma_model.joblib"
        scaler_path = here / "bulma_scaler.joblib"

        print(f"Current directory: {here}")
        print(f"Model path: {model_path}")
        print(f"Scaler path: {scaler_path}")
        print(f"Model file exists: {model_path.exists()}")
        print(f"Scaler file exists: {scaler_path.exists()}")
        if model_path.exists():
            print(f"Model file size: {model_path.stat().st_size} bytes")
        if scaler_path.exists():
            print(f"Scaler file size: {scaler_path.stat().st_size} bytes")

        try:
            print("Loading scaler...")
            self.scaler = joblib.load(scaler_path)
            print("Scaler loaded successfully")
            print(f"Scaler features: {self.scaler.feature_names_in_.tolist()}")
        except Exception as e:
            print(f"❌ Scaler load failed: {repr(e)}")
            raise
        try:
            print("Loading model...")
            self.model = joblib.load(model_path)
            print("Model loaded successfully")
        except Exception as e:
            print(f"❌ Model load failed: {repr(e)}")
            raise

    def predict(self, symbol: str, candles: pd.DataFrame, current_balance: float = 0.0):
        if self.model is None or candles.empty or len(candles) < 50:
            return "hold", 0.0

        df = candles.copy()
        if "volume" not in df.columns and len(df.columns) >= 6:
            df.rename(columns={df.columns[-1]: "volume"}, inplace=True)
        df.index = pd.to_datetime(df.index, unit="s")

        # Feature calculations
        df["pct_1"] = df["close"].pct_change()
        df["pct_6"] = df["close"].pct_change(6)
        df["pct_24"] = df["close"].pct_change(24)
        df["momentum"] = df["close"].pct_change().ewm(span=12).mean()
        df["volatility"] = df["pct_1"].rolling(24).std()
        df["range_atr"] = (df["high"] - df["low"]).rolling(14).mean()
        roll_hi = df["high"].rolling(24).max()
        roll_lo = df["low"].rolling(24).min()
        df["pos_in_range"] = (df["close"] - roll_lo) / (roll_hi - roll_lo + 1e-9)
        ma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        df["bollinger_b"] = (df["close"] - ma20) / (2 * std20 + 1e-9)
        vol_med = df["volume"].rolling(24).median()
        vol_iqr = df["volume"].rolling(24).quantile(0.75) - df["volume"].rolling(24).quantile(0.25)
        df["vol_z"] = (df["volume"] - vol_med) / (vol_iqr + 1e-9)
        ts = pd.to_datetime(df.index, unit="s")
        df["sin_hour"] = np.sin(2 * np.pi * ts.hour / 24)
        df["cos_hour"] = np.cos(2 * np.pi * ts.hour / 24)
        df["sin_dow"] = np.sin(2 * np.pi * ts.dayofweek / 7)
        df["cos_dow"] = np.cos(2 * np.pi * ts.dayofweek / 7)
        df["pct_1_lag1"] = df["pct_1"].shift(1)
        df["pct_1_lag2"] = df["pct_1"].shift(2)
        df["volatility_lag1"] = df["volatility"].shift(1)
        df["volatility_lag2"] = df["volatility"].shift(2)
        df["momentum_lag1"] = df["momentum"].shift(1)
        df["momentum_lag2"] = df["momentum"].shift(2)

        df = df.dropna()
        latest = df.iloc[-1]

        g = gohan_strat(df)
        j = jiren_strat(df)
        f = freezer_strat(df)
        bvote = beerus_vote(g, j, f)

        # Build DataFrame with exact scaler columns
        expected_columns = [
            'pct_1', 'pct_6', 'pct_24', 'momentum', 'volatility', 'range_atr',
            'pos_in_range', 'bollinger_b', 'vol_z', 'sin_hour', 'cos_hour',
            'sin_dow', 'cos_dow', 'pct_1_lag1', 'pct_1_lag2', 'volatility_lag1', 'volatility_lag2',
            'momentum_lag1', 'momentum_lag2', 'gohan_conf', 'jiren_conf', 'freezer_conf', 'beerus_conf'
        ]
        features = pd.DataFrame([[
            latest["pct_1"], latest["pct_6"], latest["pct_24"],
            latest["momentum"], latest["volatility"], latest["range_atr"],
            latest["pos_in_range"], latest["bollinger_b"], latest["vol_z"],
            latest["sin_hour"], latest["cos_hour"],
            latest["sin_dow"], latest["cos_dow"],
            latest["pct_1_lag1"], latest["pct_1_lag2"],
            latest["volatility_lag1"], latest["volatility_lag2"],
            latest["momentum_lag1"], latest["momentum_lag2"],
            g, j, f, bvote
        ]], columns=expected_columns)

        scaler_cols = list(self.scaler.feature_names_in_)
        try:
            for col in scaler_cols:
                if col not in features.columns:
                    features[col] = 0.0
            features = features[scaler_cols]
        except Exception as align_error:
            print(f"❌ Column alignment failed: {align_error}")
            raise

        try:
            X_scaled = self.scaler.transform(features)
        except Exception as scale_err:
            print(f"❌ Scaler.transform failed: {scale_err}")
            raise

        pred = self.model.predict(X_scaled)[0]
        conf_proba = self.model.predict_proba(X_scaled)[0]
        confidence = bvote * 0.5 + max(conf_proba) * 10 * 0.5

        close_price = latest["close"]
        atr = calculate_atr(df).iloc[-1] if not pd.isna(calculate_atr(df).iloc[-1]) else close_price * 0.02

        if symbol in self.entry_prices:
            self.trailing_highs[symbol] = max(
                self.trailing_highs.get(symbol, self.entry_prices[symbol]),
                close_price
            )
            tier = self.profit_tiers.get(symbol, 0)
            # ---- LESS AGGRESSIVE SELL: raise thresholds by 15% and require higher confidence ----
            if tier == 0 and (close_price - self.entry_prices[symbol]) >= 1.72 * atr and confidence >= 7.5:
                self.profit_tiers[symbol] = 1
                return "sell", confidence
            if tier == 1 and (close_price - self.entry_prices[symbol]) >= 3.45 * atr and confidence >= 7.5:
                self.profit_tiers[symbol] = 2
                self.stop_losses[symbol] = close_price - 4.6 * atr
                return "sell", confidence
            if tier >= 2 and close_price <= self.trailing_highs[symbol] - 4.6 * atr and confidence >= 7.5:
                self._clear_position(symbol)
                return "sell", confidence
            # Stop-loss further away and only at high confidence
            if df["low"].iloc[-1] <= self.stop_losses.get(symbol, 0) and confidence >= 7.5:
                self._clear_position(symbol)
                return "sell", confidence

        if current_balance == 0 and pred == "buy":
            self.entry_prices[symbol] = close_price
            self.stop_losses[symbol] = close_price - 2 * atr
            self.profit_tiers[symbol] = 0
            self.trailing_highs[symbol] = close_price
            return "buy", confidence

        return pred, round(confidence, 2)

    def _clear_position(self, symbol):
        self.entry_prices.pop(symbol, None)
        self.stop_losses.pop(symbol, None)
        self.profit_tiers.pop(symbol, None)
        self.trailing_highs.pop(symbol, None)

if __name__ == "__main__":
    print("Testing BulmaEngine initialization")
    try:
        engine = BulmaEngine()
        print("BulmaEngine initialized successfully")
        import pandas as pd
        candles = pd.read_csv("bulma/Bitstamp_XLMUSD_1h.csv")
        pred, conf = engine.predict("XLMUSD", candles)
        print(f"Prediction: {pred}, Confidence: {conf}")
    except Exception as e:
        print(f"Failed to initialize or predict with BulmaEngine: {repr(e)}")
