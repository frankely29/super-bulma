from coinbase.rest import RESTClient
from frankelly_telegram.bot import send_telegram_message

def get_portfolio(client: RESTClient):
    """
    Returns list of (currency, amount, usd_value) and total USD value.
    """
    try:
        resp = client.get_accounts()
        data = resp.to_dict() if hasattr(resp, "to_dict") else resp
        accounts = data.get("accounts", [])
        portfolio = []
        total = 0.0

        for acct in accounts:
            cur = acct.get("currency")
            amt = float(acct.get("available_balance", {}).get("value", 0))
            if amt <= 0:
                continue

            # treat USD and USDC as deployable cash
            if cur in ["USD", "USDC"]:
                portfolio.append((cur, amt, amt))  # 1:1 stable value
                total += amt
                continue

            try:
                pr = client.get_product(product_id=f"{cur}-USD")
                price = float(pr.price)
            except Exception as e:
                print(f"⚠️ price fetch failed for {cur}: {e}")
                price = 0.0

            usd_val = amt * price
            if not isinstance(usd_val, (int, float)) or usd_val <= 0:
                usd_val = 0.0

            portfolio.append((cur, amt, usd_val))
            total += usd_val

        print(f"[DEBUG] get_portfolio final: {portfolio}")
        return portfolio, total

    except Exception as e:
        print(f"❌ Error fetching portfolio: {e}")
        send_telegram_message(f"❌ Portfolio fetch error: {e}", force_send=True)
        return [], 0.0