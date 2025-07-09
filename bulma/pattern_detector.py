# bulma/pattern_detector.py

class BulmaPatternDetector:
    def __init__(self):
        pass

    def detect(self, candles):
        """
        Detect chart patterns from candle dataframe
        returns a dict of pattern booleans
        """
        patterns = {}

        if len(candles) < 10:
            return patterns

        closes = candles['close']
        highs = candles['high']
        lows = candles['low']

        # Double top
        if highs.iloc[-1] < highs.max() and highs.iloc[-2] < highs.max():
            patterns['double_top'] = True
        else:
            patterns['double_top'] = False

        # Double bottom
        if lows.iloc[-1] > lows.min() and lows.iloc[-2] > lows.min():
            patterns['double_bottom'] = True
        else:
            patterns['double_bottom'] = False

        # Trend strength
        patterns['trend_up'] = closes.diff().iloc[-3:].gt(0).sum() >= 2
        patterns['trend_down'] = closes.diff().iloc[-3:].lt(0).sum() >= 2

        # Breakout
        recent_high = highs.iloc[-5:].max()
        patterns['breakout'] = closes.iloc[-1] > recent_high

        return patterns