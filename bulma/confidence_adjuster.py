# bulma/confidence_adjuster.py

class BulmaConfidenceAdjuster:
    def __init__(self):
        pass

    def adjust(self, beerus_confidence: float, features: dict, patterns: dict) -> float:
        """
        Adjust Beerus confidence using Bulma features and patterns.
        """

        adjustment = 0.0

        # Example: pattern signals
        if patterns.get("double_top"):
            adjustment -= 1.0
        if patterns.get("double_bottom"):
            adjustment += 1.0
        if patterns.get("trend_up"):
            adjustment += 0.5
        if patterns.get("trend_down"):
            adjustment -= 0.5
        if patterns.get("breakout"):
            adjustment += 1.5

        # Example: feature signals
        momentum = features.get("momentum", 0)
        volatility = features.get("volatility", 0)

        if momentum > 0:
            adjustment += 0.5
        else:
            adjustment -= 0.5

        # apply volatility as a confidence dampener
        if volatility > 0.05:
            adjustment -= 0.5

        # clamp final
        final_conf = beerus_confidence + adjustment
        final_conf = max(0, min(final_conf, 10))

        return final_conf
