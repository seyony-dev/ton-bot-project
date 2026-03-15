import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", 1000.0))
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", 100.0)) # Сколько USDT тратить на 1 сделку

# Настройки индикатора RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 30 # Ниже 30 - пора покупать
RSI_OVERBOUGHT = 70 # Выше 70 - пора продавать
