import os
import sys
import time
import uuid
import decimal
from threading import Thread
from datetime import datetime
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from bulma.bulma_engine import BulmaEngine
from core.data_feed import fetch_live_candles
from core.coin_selector import CoinSelector
from core.position_manager import PositionManager
from core.portfolio_tracker import get_portfolio
from frankelly_telegram.bot import send_telegram_message
from frankelly_telegram.commands import get_command_handlers, error_handler
from frankelly_telegram.shared_state import BOT_STATE, STATS

do_bulma = True

# === ENV ===
load_dotenv()
API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_PRIVATE_KEY_CONTENT")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not (API_KEY and API_SECRET and TELE_TOKEN):
    print("❌ Missing credentials")
    sys.exit(1)

send_telegram_message("✅ API credentials loaded", force_send=True)

try:
    from coinbase.rest import RESTClient
    cb = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
    send_telegram_message("✅ Coinbase client initialized", force_send=True)
except Exception as e:
    send_telegram_message(f"❌ Coinbase init failed: {e}", force_send=True)
    sys.exit(1)

try:
    accounts = cb.get_accounts().to_dict().get("accounts", [])
    ok = []
    for a in accounts:
        cur = a["currency"]
        bal = float(a["available_balance"]["value"])
        if bal > 0:
            ok.append(cur)
        print(f"🔎 {cur} = {bal}")
    send_telegram_message(f"✅ Accounts OK: {', '.join(ok)}", force_send=True)
except Exception as e:
    send_telegram_message(f"❌ Account check failed: {e}", force_send=True)
    sys.exit(1)

MODE = os.getenv("MODE", "live").lower()
send_telegram_message(f"✅ MODE: {MODE.upper()}", force_send=True)

CHECK_INTERVAL = 600
MIN_TRADE_USD = 50
DUST_CLEAN_INTERVAL = 172800  # 48 hours
last_dust_cleanup = 0

def get_base_precision(cb, product_id):
    try:
        product = cb.get_product(product_id).to_dict()
        base_increment = product.get("base_increment", "1")
        decimals = abs(decimal.Decimal(base_increment).as_tuple().exponent)
        return decimals
    except Exception as e:
        print(f"[DEBUG] precision lookup failed for {product_id}: {e}")
        return 0

def run_dust_cleaner(cb):
    try:
        portfolio, _ = get_portfolio(cb)
        for base, amt, _ in portfolio:
            if base == "USD":
                continue
            sym = f"{base}-USD"
            try:
                price = fetch_live_candles(cb, sym, "ONE_HOUR", 1)["close"].iloc[-1]
                usd_value = amt * price
                if 0 < usd_value < MIN_TRADE_USD:
                    prec = get_base_precision(cb, sym)
                    size_str = format(round(amt, prec), f".{prec}f")
                    cb.create_order(
                        client_order_id=str(uuid.uuid4()),
                        product_id=sym,
                        side="SELL",
                        order_configuration={"market_market_ioc": {"base_size": size_str}},
                    )
            except Exception as e:
                print(f"[DEBUG] Dust clean failed for {sym}: {e}")
    except Exception as e:
        print(f"[DEBUG] Dust cleaner failed: {e}")

def run_bot():
    global last_dust_cleanup
    try:
        strat = BulmaEngine()
        selector = CoinSelector(cb)
        pm = PositionManager(hold_ratio=0.3, min_cash_ratio=0.1, max_trade_ratio=0.9)
        send_telegram_message("🔎 Trading bot initialized with Bulma", force_send=True)
    except Exception as e:
        send_telegram_message(f"❌ Bot init error: {e}", force_send=True)
        return

    state = selector.load_state()
    held = state.get("held", [])

    portfolio, _ = get_portfolio(cb)
    lines = ["📊 **Initial Portfolio Summary**"]
    for base, bal, _ in portfolio:
        lines.append(f"{base}: {bal:.4f}")
    send_telegram_message("\n".join(lines), force_send=True)

    while True:
        try:
            rotated = selector.rotate_coins()
            if rotated:
                send_telegram_message("🔁 Rotated coins: " + ", ".join(rotated), force_send=True)

            if not BOT_STATE["running"]:
                time.sleep(CHECK_INTERVAL)
                continue

            state = selector.load_state()
            held = state.get("held", [])
            symbols = [f"{c}-USD" for c in held]
            portfolio, _ = get_portfolio(cb)
            allocations = pm.allocate(portfolio, held)

            balance_map = {base: bal for base, bal, _ in portfolio}
            traded_this_cycle = set()

            for sym in symbols:
                if sym in traded_this_cycle:
                    continue

                base = sym.split("-")[0]
                current_balance = balance_map.get(base, 0.0)
                # --- BULMA prediction ---
                try:
                    candles = fetch_live_candles(cb, sym, "ONE_HOUR", 100)
                    signal, conf = strat.predict(sym, candles, current_balance=current_balance)
                except Exception as e:
                    print(f"[DEBUG] Bulma error: {e}")
                    signal, conf = "hold", 0.0
                print(f"[DEBUG] {sym} signal={signal}, conf={conf:.2f}")

                # === BUY ===
                if signal == "buy" and conf > 0:
                    usd_size = allocations.get(base, 0.0) or MIN_TRADE_USD
                    usd_size = max(usd_size, MIN_TRADE_USD)

                    # === Enforce 25% max allocation per coin and only 1 add-on
                    try:
                        price = fetch_live_candles(cb, sym, "ONE_HOUR", 1)["close"].iloc[-1]
                        current_usd_value = current_balance * price
                        total_value = sum(
                            balance_map.get(c, 0.0) * fetch_live_candles(cb, f"{c}-USD", "ONE_HOUR", 1)["close"].iloc[-1]
                            for c in balance_map if c != "USD"
                        ) + balance_map.get("USD", 0.0)
                        max_allowed = total_value * 0.25

                        if current_usd_value > 0 and current_usd_value >= (max_allowed / 2):
                            continue  # Already added on once

                        if current_usd_value + usd_size > max_allowed:
                            usd_size = max_allowed - current_usd_value

                        if usd_size < MIN_TRADE_USD:
                            continue
                    except Exception as e:
                        print(f"[DEBUG] allocation check failed for {sym}: {e}")
                        continue

                    available_usd = balance_map.get("USD", 0.0)
                    if available_usd < usd_size:
                        continue

                    try:
                        resp = cb.create_order(
                            client_order_id=str(uuid.uuid4()),
                            product_id=sym,
                            side="BUY",
                            order_configuration={"market_market_ioc": {"quote_size": str(round(usd_size, 2))}},
                        )
                        # no Beerus ATR/entry/stop logic needed here
                        STATS["trades"] += 1
                        portfolio, total = get_portfolio(cb)
                        holdings = "\n".join([f"{b}: {amt:.4f}" for b, amt, _ in portfolio])
                        msg = (
                            f"💸 *BUY {sym}* (conf: {conf:.2f})\n{resp}\n\n"
                            f"**Portfolio Balance**: ${total:.2f}\n**Holdings:**\n{holdings}\n\n"
                            f"Profit %: {STATS['profit_pct']:.2f}%\nTrades: {STATS['trades']}"
                        )
                        send_telegram_message(msg, force_send=True)
                        traded_this_cycle.add(sym)
                    except Exception as e:
                        print(f"[DEBUG] buy error: {e}")

                # === SELL ===
                elif signal == "sell" and conf > 0 and current_balance > 0:
                    price = fetch_live_candles(cb, sym, "ONE_HOUR", 1)["close"].iloc[-1]
                    usd_value = current_balance * price

                    if usd_value < MIN_TRADE_USD:
                        continue

                    partial_sell = current_balance * 0.7
                    partial_usd = partial_sell * price
                    remaining_usd = (current_balance - partial_sell) * price

                    if partial_usd >= MIN_TRADE_USD and remaining_usd >= MIN_TRADE_USD:
                        sell_size = partial_sell
                    else:
                        sell_size = current_balance

                    if sell_size <= 0:
                        continue

                    prec = get_base_precision(cb, sym)
                    sell_size_str = format(round(sell_size, prec), f".{prec}f")

                    try:
                        resp = cb.create_order(
                            client_order_id=str(uuid.uuid4()),
                            product_id=sym,
                            side="SELL",
                            order_configuration={"market_market_ioc": {"base_size": sell_size_str}},
                        )
                        STATS["trades"] += 1
                        portfolio, total = get_portfolio(cb)
                        holdings = "\n".join([f"{b}: {amt:.4f}" for b, amt, _ in portfolio])
                        msg = (
                            f"💸 *SELL {sym}* (conf: {conf:.2f})\n{resp}\n\n"
                            f"**Portfolio Balance**: ${total:.2f}\n**Holdings:**\n{holdings}\n\n"
                            f"Profit %: {STATS['profit_pct']:.2f}%\nTrades: {STATS['trades']}"
                        )
                        send_telegram_message(msg, force_send=True)
                        traded_this_cycle.add(sym)
                    except Exception as e:
                        print(f"[DEBUG] sell error: {e}")

            if time.time() - last_dust_cleanup >= DUST_CLEAN_INTERVAL:
                run_dust_cleaner(cb)
                last_dust_cleanup = time.time()

        except Exception as e:
            send_telegram_message(f"❌ Bot loop error: {e}", force_send=True)
            time.sleep(30)

        time.sleep(CHECK_INTERVAL)

def run_telegram():
    try:
        app = ApplicationBuilder().token(TELE_TOKEN).build()
        for h in get_command_handlers():
            app.add_handler(h)
        app.add_error_handler(error_handler)
        send_telegram_message("✅ Telegram bot started OK.", force_send=True)
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Telegram thread failed: {e}")

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    run_telegram()
