from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

def get_sentiment_score(text: str) -> float:
    """
    Returns a compound sentiment score in [-1, 1] for the given text.
    Positive values → bullish sentiment, negative → bearish.
    """
    vs = _analyzer.polarity_scores(text)
    return vs["compound"]
