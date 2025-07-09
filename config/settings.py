# config/settings.py

# --- Rotation Logic ---
ROTATION_INTERVAL_DAYS = 7  # Days between coin rotation
MAX_COINS = 15              # Max number of coins to hold

# --- Trading Logic ---
TRADE_PERCENTAGE = 0.7      # Use 70% of coin value when placing trades
CHECK_INTERVAL = 600        # Seconds between each check (10 minutes)

# --- Telegram Alert Timing ---
TELEGRAM_ALERT_START_HOUR = 6    # Start sending alerts at 6 AM
TELEGRAM_ALERT_END_HOUR = 23     # Stop sending alerts after 11 PM
