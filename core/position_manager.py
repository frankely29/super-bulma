class PositionManager:
    def __init__(self, hold_ratio=0.3, min_cash_ratio=0.1, max_trade_ratio=0.9):
        self.hold_ratio = hold_ratio
        self.min_cash_ratio = min_cash_ratio
        self.max_trade_ratio = max_trade_ratio

    def allocate(self, portfolio: list, targets: list[str]) -> dict[str, float]:
        current_map = {}
        total_value = 0.0

        for item in portfolio:
            print(f"[DEBUG] PositionManager item: {item}")
            if isinstance(item, dict):
                cur, val = item['currency'], float(item['value'])
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                cur, val = item[0], float(item[2])
            else:
                print(f"⚠️ skipping bad portfolio item: {item}")
                continue

            current_map[cur] = val
            total_value += val

        reserve = max(total_value * self.hold_ratio, total_value * self.min_cash_ratio)
        deployable = max(total_value - reserve, 0.0)
        per_coin = deployable / len(targets) if targets else 0.0

        allocations = {}
        for c in targets:
            held_val = current_map.get(c, 0.0)
            if held_val < per_coin:
                allocations[c] = per_coin - held_val

        print(f"[DEBUG] allocations: {allocations}")
        return allocations