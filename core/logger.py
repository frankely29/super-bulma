import logging
import os
from datetime import datetime

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Daily rotating log file
log_filename = datetime.now().strftime("logs/%Y-%m-%d.log")

logger = logging.getLogger("frankelly-bot")
logger.setLevel(logging.DEBUG)

# File handler (DEBUG+)
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# Console handler (INFO+)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
