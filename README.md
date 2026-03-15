# TON Crypto Trading Bot

An automated trading bot for Telegram that simulates trading TON (The Open Network) using RSI, EMA (50 and 200), and Bollinger Bands on Binance data.

## Features
- **Telegram Interface**: Easy to use interface through Telegram.
- **Virtual Balance**: Practice paper trading with a simulated balance without risking real funds. 
- **Indicator based Analysis**: Evaluates position entry using RSI, EMA, and Bollinger Bands with multi-timeframe capability (`15m`, `1h`).
- **Trailing Stop-Loss**: Dynamically updates stop-loss to protect profits depending on price movements.
- **Trade History & Portfolio**: Tracks open positions, calculates current profit/loss and stores trade history.

## Requirements
- Python 3.9+
- The dependencies listed in `requirements.txt`

## Installation & Setup

### For Windows Users (Automated setup)
You can double-click `install.bat` to automatically set up the virtual environment and install all necessary dependencies.

Alternatively, follow these steps manually:
1. Clone the repository.
2. Create python virtual environment:
   ```sh
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```sh
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Configuration
1. Rename `.env.example` to `.env` or just create `.env`.
2. Add your Telegram Bot Token and other settings:
   ```env
   BOT_TOKEN=YOUR_BOT_TOKEN_HERE
   INITIAL_BALANCE=1000
   TRADE_AMOUNT=100
   ```
   *You can get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.*

## Running the Bot
Once everything is set up, you can start the bot simply by double-clicking `run.bat` (if on Windows). Or you can run it via terminal:

```sh
python main.py
```

## Usage
In your Telegram chat with the bot, use the following commands:
- `/start` - Initial setup and welcome message. Resets the database and virtual balance if ran again.
- `/status` - Check your virtual portfolio balance, active trades, entry prices, and stop-loss levels.
- `/analyze` - Display the inline keyboard to run market analysis on either `15m` or `1h` timeframe and execute trades.
- `/history` - Display history of executed paper trades.

## Disclaimer
This project is for educational and entertainment purposes only (paper trading). It is not financial advice.
