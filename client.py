# frankelly_bot/core/client.py

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from coinbase.auth import JWTAuth

# Load environment variables from .env
load_dotenv()

# Get JWT credentials
API_KEY_ID = os.getenv("COINBASE_API_KEY_ID")
PRIVATE_KEY_PATH = os.getenv("COINBASE_PRIVATE_KEY_PATH")

if not API_KEY_ID or not PRIVATE_KEY_PATH:
    raise Exception("Missing COINBASE_API_KEY_ID or COINBASE_PRIVATE_KEY_PATH in .env")

# Setup JWT authentication
auth = JWTAuth(api_key_id=API_KEY_ID, private_key_path=PRIVATE_KEY_PATH)

# Create the Coinbase Advanced REST client
client = RESTClient(auth=auth)
