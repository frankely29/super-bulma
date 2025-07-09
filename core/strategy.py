# core/strategy.py
"""
Beerus Strategy (balanced version)

• Opens/closes positions **only when at least TWO champion strategies agree**.
• Keeps aggressive “add-on” buys when one champion gives an exceptional score.
• Confidence = average score of all agreeing champions.
• Stop-loss handling identical to previous implementation.
• No external modules beyond pandas and code already present in the repo.
"""

import pandas as pd
from core.data_feed import fetch_live_candles

# ────────────────────────── Indicator helpers ──────────────────────────
def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - 100 / (1 + rs)

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = df["close"].ewm(span=fast).mean()
    slow_ema = df["close"].ewm(span=slow).mean()
    macd     = fast_ema - slow_ema
    macd_sig = macd.ewm(span=signal).mean()
    return macd, macd_sig, macd - macd_sig

# ────────────────────────── Champion strategies ────────────────────────
def gohan_strat(df: pd.DataFrame):
    if len(df) < 50:
        return "hold", 0.0

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

    if score >= 6: return "buy",  score
    if score < 3:  return "sell", score
    return "hold", score

def jiren_strat(df: pd.DataFrame):
    if len(df) < 50:
        return "hold", 0.0

    rsi = calculate_rsi(df).iloc[-1]
    macd_line, macd_sig, _ = calculate_macd(df)
    macd_line, macd_sig = macd_line.iloc[-1], macd_sig.iloc[-1]
    sma20 = df["close"].rolling(20).mean().iloc[-1]
    vol_now, vol_avg = df["volume"].iloc[-1], df["volume"].rolling(20).mean().iloc[-1]

    score = 0.0
    if 40 <= rsi <= 65:            score += 2.5
    if macd_line > macd_sig:       score += 2.5
    if df["close"].iloc[-1] > sma20: score += 2
    if vol_now > vol_avg * 1.1:      score += 0.5

    if score >= 7.5: return "buy",  score
    if score < 2:    return "sell", score
    return "hold", score

def freezer_strat(df: pd.DataFrame):
    if len(df) < 30:
        return "hold", 0.0

    rsi = calculate_rsi(df).iloc[-1]
    _, _, macd_hist = calculate_macd(df)
    macd_hist = macd_hist.iloc[-1]
    price_change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]

    score = 0.0
    if rsi > 50:            score += 2
    if macd_hist > 0:       score += 2
    if price_change > 0.02: score += 2

    if score >= 4.5: return "buy",  score
    return "hold", score

# ────────────────────────── Beerus balanced strategy ───────────────────
class BeerusStrategy:
    """
    Balanced Beerus:
      • Requires ≥2 champions to agree for opening or closing a position.
      • Allows aggressive add-on buys when a single champion score is very high.
      • Maintains ATR-based stop-loss and confidence logic.
    """

    def __init__(self, client):
        self.client = client
        self.entry_prices: dict[str, float] = {}
        self.stop_losses:  dict[str, float] = {}

    # static helper
    @staticmethod
    def _average(scores):
        return sum(scores) / len(scores) if scores else 0.0

    # main method
    def run(self, symbol: str, current_balance: float = 0.0):
        df = fetch_live_candles(self.client, symbol, "ONE_HOUR", 300)
        if df.empty or len(df) < 60:
            return "hold", 0.0

        close_price = df["close"].iloc[-1]
        atr = calculate_atr(df).iloc[-1] or close_price * 0.02

        # ───── Stop-loss check ─────
        if symbol in self.stop_losses and df["low"].iloc[-1] <= self.stop_losses[symbol]:
            self.entry_prices.pop(symbol, None)
            self.stop_losses.pop(symbol, None)
            print(f"[DEBUG] {symbol}: SL triggered → SELL")
            return "sell", 1.0  # confident exit

        # ───── Champion signals ─────
        g_sig, g_sc = gohan_strat(df)
        j_sig, j_sc = jiren_strat(df)
        f_sig, f_sc = freezer_strat(df)

        print(
            f"[DEBUG] {symbol}: "
            f"Gohan {g_sig}:{g_sc:.1f} | "
            f"Jiren {j_sig}:{j_sc:.1f} | "
            f"Freezer {f_sig}:{f_sc:.1f}"
        )

        buy_votes  = [(g_sc, 'Gohan')]   if g_sig == "buy"  else []
        buy_votes += [(j_sc, 'Jiren')]   if j_sig == "buy"  else []
        buy_votes += [(f_sc, 'Freezer')] if f_sig == "buy"  else []

        sell_votes  = [(g_sc, 'Gohan')]   if g_sig == "sell" else []
        sell_votes += [(j_sc, 'Jiren')]   if j_sig == "sell" else []
        sell_votes += [(f_sc, 'Freezer')] if f_sig == "sell" else []

        # ───── Entry logic (≥2 buy votes) ─────
        if current_balance == 0 and len(buy_votes) >= 2:
            self.entry_prices[symbol] = close_price
            self.stop_losses[symbol]  = close_price - 2 * atr
            confidence = self._average([sc for sc, _ in buy_votes])
            print(f"[DEBUG] {symbol}: OPEN position, conf={confidence:.2f} (votes: {[n for _,n in buy_votes]})")
            return "buy", confidence

        # ───── Add-on buy (aggressive) ─────
        if current_balance > 0:
            if g_sc >= 7 or j_sc >= 8 or f_sc >= 6:
                confidence = max(g_sc, j_sc, f_sc)
                print(f"[DEBUG] {symbol}: ADD-ON buy, conf={confidence:.2f}")
                return "buy", confidence

        # ───── Exit logic (≥2 sell votes) ─────
        if current_balance > 0 and len(sell_votes) >= 2:
            self.entry_prices.pop(symbol, None)
            self.stop_losses.pop(symbol, None)
            confidence = max(self._average([sc for sc, _ in sell_votes]), 0.5)
            print(f"[DEBUG] {symbol}: CLOSE position, conf={confidence:.2f} (votes: {[n for _,n in sell_votes]})")
            return "sell", confidence

        # default → hold
        return "hold", 0.0