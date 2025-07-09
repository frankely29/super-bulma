import os
import praw
from sentiment.sentiment_score import get_sentiment_score

class SentimentAnalyzer:
    def __init__(self):
        # Reddit credentials in .env: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "frankelly-bot-sentiment")
        )

    def fetch_reddit_posts(self, subreddit: str, limit: int = 20) -> list[str]:
        """
        Fetches the titles + selftexts of the top `limit` hot posts from a subreddit.
        """
        posts = []
        try:
            for submission in self.reddit.subreddit(subreddit).hot(limit=limit):
                content = submission.title
                if submission.selftext:
                    content += " " + submission.selftext
                posts.append(content)
        except Exception as e:
            print(f"❌ Reddit fetch error: {e}")
        return posts

    def analyze_reddit_sentiment(self, coin: str, limit: int = 20) -> float:
        """
        Returns the average sentiment score for recent posts mentioning `coin`.
        """
        posts = self.fetch_reddit_posts("CryptoCurrency", limit=limit)
        # only keep posts that mention the coin symbol
        mentions = [p for p in posts if coin.split("-")[0].upper() in p.upper()]
        if not mentions:
            return 0.0
        scores = [get_sentiment_score(text) for text in mentions]
        return sum(scores) / len(scores)
