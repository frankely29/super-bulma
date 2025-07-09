# bulma/features.py

import numpy as np

class BulmaFeatures:
    def __init__(self):
        pass  # in the future, you could load configs here

    def extract(self, candles, sentiment=0.0, orderbook_ratio=0.5):
        """
        Extract 4 features from live candles
        - candles: pandas DataFrame with ['close'] column
        - sentiment: float from Vader
        - orderbook_ratio: float, simplified (can be refined later)

        returns: np.array with 4 features
        """
        closes = candles['close']

        # trend strength over last 5 bars
        if len(closes) >= 5:
            trend_strength = closes.iloc[-1] - closes.iloc[-5]
        else:
            trend_strength = 0.0

        # volatility
        volatility = closes.std()

        # keep orderbook_ratio and sentiment as placeholders for now
        features = np.array([
            trend_strength,
            volatility,
            orderbook_ratio,
            sentiment
        ])

        return features
