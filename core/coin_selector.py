import json
import os
from datetime import datetime

STATE_FILE = "coin_state.json"

class CoinSelector:
    def __init__(self, client):
        self.client = client
        self.top_coins = [
            # 30 well-known
            "BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "MATIC",
            "LINK", "LTC", "BCH", "ATOM", "ALGO", "ETC", "XLM", "AAVE", "FIL", "NEAR", "APT",
            # 20 meme-type on Coinbase
            "DOGWIFHAT", "SHIB", "PEPE", "FLOKI", "BONK", "TURBO", "HOGE", "PUPS", "MOG", "TSUKA",
            "PIT", "ELON", "KEK", "CHAD", "MOON"
        ]

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
        return {}

    def save_state(self, state):
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

    def rotate_coins(self):
        state = self.load_state()
        held = state.get("held", [])
        rotated = []

        # remove worst performers under -15%
        if "entry_prices" in state:
            for sym, entry in state["entry_prices"].items():
                try:
                    price = self.client.get_product(sym).price
                    change = (price - entry) / entry * 100
                    if change < -15 and sym.split("-")[0] in held:
                        held.remove(sym.split("-")[0])
                        rotated.append(sym.split("-")[0])
                except Exception as e:
                    print(f"⚠️ rotation check failed for {sym}: {e}")
                    continue

        missing = 15 - len(held)
        if missing > 0:
            addable = [c for c in self.top_coins if c not in held]
            new = addable[:missing]
            held.extend(new)
            rotated.extend(new)

        state["held"] = held
        state["last_rotation"] = datetime.utcnow().isoformat()
        self.save_state(state)
        return rotated