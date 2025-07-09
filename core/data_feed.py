import pandas as pd
from datetime import datetime
import time
from frankelly_telegram.bot import send_telegram_message

# Hard-coded top 50 coins
HARDCODED_TOP_50 = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "DOT", "TON",
    "MATIC", "LINK", "LTC", "TRX", "BCH", "XLM", "ICP", "FIL", "ETC", "ATOM",
    "HBAR", "APT", "CRO", "ALGO", "FTM", "OP", "NEAR", "INJ", "QNT", "EGLD",
    "SUI", "AR", "RNDR", "STX", "XMR", "IMX", "GRT", "AAVE", "MKR", "RUNE",
    "LDO", "ENS", "DYDX", "XTZ", "KAVA", "ZEC", "MANA", "SAND", "GALA", "PEPE"
]

def fetch_live_candles(client, symbol="BTC-USD", granularity="ONE_HOUR", limit=150):
    """
    Fetch recent OHLCV candle data via Coinbase Advanced API.
    Returns a DataFrame with columns: date, open, high, low, close, volume (all floats).
    """
    if not symbol or "-" not in symbol:
        print(f"⚠️ Invalid symbol passed: '{symbol}'")
        send_telegram_message(f"⚠️ Skipping invalid symbol: '{symbol}'", force_send=True)
        return pd.DataFrame()

    granularity_map = {
        "ONE_HOUR": 3600,
        "FIVE_MINUTE": 300,
        "FIFTEEN_MINUTE": 900,
        "THIRTY_MINUTE": 1800,
        "ONE_DAY": 86400,
    }
    gs = granularity_map.get(granularity, 3600)

    for attempt in range(3):
        try:
            end_ts = int(datetime.utcnow().timestamp())
            start_ts = end_ts - gs * limit
            if start_ts <= 0:
                raise ValueError("Invalid start timestamp")
            if limit > 350:
                raise ValueError("Limit exceeds 350")

            print(f"🔎 [DEBUG] Fetching candles for {symbol} "
                  f"start={start_ts} end={end_ts} limit={limit}")
            resp = client.get_candles(
                product_id=symbol,
                start=str(start_ts),
                end=str(end_ts),
                granularity=granularity,
                limit=limit
            )

            data = resp.to_dict() if hasattr(resp, "to_dict") else resp
            raw = data.get("candles", []) if isinstance(data, dict) else []

            if not raw:
                print(f"⚠️ No candles returned for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(raw, columns=[
                'start', 'low', 'high', 'open', 'close', 'volume'
            ])
            for col in ['low', 'high', 'open', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['date'] = pd.to_datetime(df['start'].astype(int), unit='s')
            df = df.sort_values('date').reset_index(drop=True)
            return df[['date', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"❌ Candle fetch error for {symbol}: {e}")
            send_telegram_message(f"❌ Candle fetch error: {symbol}\n{e}", force_send=True)
            if "rate limit" in str(e).lower() or "invalid" in str(e).lower():
                time.sleep(5)
                continue
            return pd.DataFrame()

    print(f"❌ Failed to fetch candles for {symbol} after retries")
    send_telegram_message(f"❌ Failed to fetch candles for {symbol}", force_send=True)
    return pd.DataFrame()

def fetch_top_performers(client, limit=50):
    """
    Return a hard-coded list of the top 50 known coins to manage.
    """
    top_bases = HARDCODED_TOP_50[:limit]
    print(f"🔎 [DEBUG] Using hard-coded top 50: {top_bases}")
    return top_bases