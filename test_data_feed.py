from coinbase.rest import RESTClient
from core.data_feed import fetch_live_candles
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINBASE_API_KEY_ID")
API_SECRET = os.getenv("COINBASE_PRIVATE_KEY_CONTENT")

client = RESTClient(api_key=API_KEY, api_secret=API_SECRET)
df = fetch_live_candles(client, symbol="BTC-USD", granularity="ONE_HOUR", limit=300)
print(df)
