# trade_engine.py

from frankelly_telegram.bot import send_telegram_message
from bulma.bulma_engine import BulmaEngine
from data_feed import fetch_candles
import pandas as pd

# Initialize BulmaEngine once
ebulma = BulmaEngine()

# Account balance helper
def get_account_balance(client, symbol: str = "BTC-USD") -> float:
    """
    Returns the available balance of the base asset.
    """
    base = symbol.split("-")[0]
    try:
        resp = client.get_accounts()
        accounts = resp.to_dict().get("accounts", []) if hasattr(resp, "to_dict") else resp
        for acct in accounts:
            if acct.get("currency") == base:
                return float(acct["available_balance"]["value"])
    except Exception as e:
        print(f"❌ Error fetching balance for {base}: {e}")
        send_telegram_message(f"❌ Balance fetch error for {base}: {e}", force_send=True)
    return 0.0

# Market order helper
def place_market_order(client, symbol: str, side: str, quote_size: float):
    """
    Places a market IOC order for `symbol`, spending `quote_size` USD.
    """
    try:
        side_lower = side.lower()
        if side_lower == "buy":
            order = client.market_order_buy(product_id=symbol, quote_size=str(quote_size))
        else:
            order = client.market_order_sell(product_id=symbol, quote_size=str(quote_size))
        print(f"✅ ORDER PLACED: {side.upper()} ${quote_size} of {symbol}")
        send_telegram_message(f"✅ Order Placed: {side.upper()} {symbol} for ${quote_size}", force_send=True)
        return order
    except Exception as e:
        print(f"❌ ERROR placing {side.upper()} order for {symbol}: {e}")
        send_telegram_message(f"❌ Order error for {symbol}: {e}", force_send=True)
        return {"error": str(e)}

# Main evaluation and trade function
def evaluate_and_trade(client, symbol: str, beerus_engine, gohan, jiren, freezer):
    """
    Full pipeline: fetch candles, compute confidences, adjust with Bulma, aggregate, and place orders.
    """
    # 1) Fetch recent candles as a DataFrame
    candles = fetch_candles(client, symbol, limit=100)  # must return a pd.DataFrame with 'close'

    # DEBUG: show fetched candle data
    try:
        print(f"[DEBUG] main.py fetched candles for {symbol}, last closes:\n{candles['close'].tail()}")
    except Exception as e:
        print(f"[DEBUG] Error displaying fetched candles for {symbol}: {e}")

    # 2) Base confidence from Beerus
    beerus_conf = beerus_engine.get_confidence(symbol)

    # 3) Adjust via Bulma using actual candle DataFrame
    bulma_conf = ebulma.adjust_confidence(beerus_conf, candles)

    # 4) Other confidences
    gohan_conf = gohan.get_confidence(symbol)
    jiren_conf = jiren.get_confidence(symbol)
    freezer_conf = freezer.get_confidence(symbol)

    # 5) Aggregate final signal
    final_signal, final_conf = aggregate_signals(
        beerus_conf, bulma_conf,
        gohan_conf, jiren_conf, freezer_conf
    )

    # DEBUG: final result
    print(f"[DEBUG] {symbol} final signal={final_signal}, conf={final_conf:.2f}")

    # 6) Execute trade if needed
    if final_signal in ("buy", "sell"):
        balance = get_account_balance(client, symbol)
        # decide quote_size based on final_conf or portfolio logic
        quote_size = balance * (final_conf / 10)
        place_market_order(client, symbol, final_signal, quote_size)
    else:
        print(f"[DEBUG] No trade for {symbol}")

# Note: Ensure fetch_candles() and aggregate_signals() are correctly implemented elsewhere.
