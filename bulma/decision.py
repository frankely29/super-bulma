# bulma/decision.py

def adjust_confidence(base_confidence: float, features: dict) -> float:
    """
    Adjust Beerus confidence based on Bulma's features
    """
    conf = base_confidence

    # If momentum is strongly negative, reduce confidence
    if features.get("momentum", 0) < -0.5:
        conf -= 0.5

    # If volatility very high, reduce confidence a bit
    if features.get("volatility", 0) > 0.1:
        conf -= 0.2

    # Clamp confidence between 0-10
    conf = max(0, min(conf, 10))
    return conf
