#!/bin/bash

# Upgrade pip (optional)
pip install --upgrade pip

# Force install the correct Coinbase Advanced SDK
pip install coinbase-advanced-py==1.8.2

# Run the trading bot
python main.py