import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
from config import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, TRADE_AMOUNT
from database import get_portfolio, execute_trade, update_stop_loss

exchange = ccxt.binance({
    'enableRateLimit': True,
})

symbol = 'TON/USDT'
LIMIT = 300 

async def fetch_market_data(timeframe='1h'):
    try:
        loop = asyncio.get_event_loop()
        ohlcv = await loop.run_in_executor(None, lambda: exchange.fetch_ohlcv(symbol, timeframe, limit=LIMIT))
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Ошибка получения данных OHLCV: {e}")
        return None

async def check_trailing_stop():
    """Быстрая проверка только для трейлинг-стопа и стоп-лосса. Запускается часто."""
    portfolio = get_portfolio()
    if portfolio['ton'] == 0 or portfolio['entry_price'] == 0:
        return {"status": "success", "trade_executed": False, "message": ""}
        
    try:
        loop = asyncio.get_event_loop()
        # Скачиваем только одну текущую цену (тикер), это очень быстро и не расходует лимиты API
        ticker = await loop.run_in_executor(None, lambda: exchange.fetch_ticker(symbol))
        current_price = ticker['last']
    except Exception as e:
        print(f"Ошибка получения цены тикера: {e}")
        return {"status": "error", "message": "", "trade_executed": False}

    entry_price = portfolio['entry_price']
    stop_loss = portfolio['stop_loss']
    profit_pct = (current_price - entry_price) / entry_price
    
    trade_executed = False
    message = ""
    
    # === ТРЕЙЛИНГ-СТОП ===
    if profit_pct >= 0.01:
        new_sl = max(current_price * 0.99, entry_price)
        if new_sl > stop_loss:
            update_stop_loss(new_sl)
            stop_loss = new_sl
            message += f"🛡 *Трейлинг-стоп подтянут!*\n_Новый уровень защиты: ${new_sl:.4f} (в безубытке/профите)_\n"
            
    # === ВЫБИВАНИЕ ПО СТОПУ ===
    if current_price <= stop_loss and stop_loss > 0:
        usdt_to_receive = portfolio['ton'] * current_price
        ton_to_sell = portfolio['ton']
        execute_trade('SELL', current_price, ton_to_sell, usdt_to_receive)
        
        profit = usdt_to_receive - (ton_to_sell * entry_price)
        message += f"🔴 *СРАБОТАЛ СТОП-ЛОСС / ТРЕЙЛИНГ-СТОП!*\n_Цена упала до защитной линии, капитал спасен._\n"
        message += f"✅ *СДЕЛКА*: Продано {ton_to_sell:.2f} TON по {current_price:.4f}\n💰 _Итог: ${profit:.2f}_"
        trade_executed = True

    return {
        "status": "success",
        "trade_executed": trade_executed,
        "message": message,
        "price": current_price
    }

async def analyze_market(timeframe='1h'):
    df = await fetch_market_data(timeframe)
    if df is None or len(df) < 200:
        return {"status": "error", "message": "Недостаточно данных для анализа"}

    df.ta.rsi(length=RSI_PERIOD, append=True)
    rsi_col = f"RSI_{RSI_PERIOD}"
    
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    ema_50_col = "EMA_50"
    ema_200_col = "EMA_200"
    
    # Добавляем Полосы Боллинджера для торговли во флэте
    df.ta.bbands(length=20, std=2, append=True)
    bb_lower_col = [c for c in df.columns if c.startswith('BBL')][0]
    bb_upper_col = [c for c in df.columns if c.startswith('BBU')][0]

    support_level = df['low'].tail(20).min()
    resist_level = df['high'].tail(20).max()

    current_price = df['close'].iloc[-1]
    current_rsi = df[rsi_col].iloc[-1]
    current_ema_50 = df[ema_50_col].iloc[-1]
    current_ema_200 = df[ema_200_col].iloc[-1]
    current_bb_lower = df[bb_lower_col].iloc[-1]
    current_bb_upper = df[bb_upper_col].iloc[-1]
    
    # Более агрессивная (скальперская) логика для боковика
    # Мы убираем жесткую привязку к EMA 50/200, чтобы бот мог ловить "отскоки" внутри коридора.
    signal = "NEUTRAL"
    if current_rsi < 40 or current_price <= current_bb_lower * 1.002: # +0.2% погрешности для касания
        signal = "BUY"
    elif current_rsi > 65 or current_price >= current_bb_upper * 0.998:
        signal = "SELL"

    tf_label = "15 мин" if timeframe == '15m' else "1 час"
    message = (
        f"📊 *Анализ TON/USDT ({tf_label})*\n\n"
        f"💵 Текущая цена: *${current_price:.4f}*\n"
        f"📈 RSI: *{current_rsi:.2f}*\n"
        f"🌐 Боллинджер: Низ ${current_bb_lower:.4f} | Верх ${current_bb_upper:.4f}\n"
        f"🟡 EMA 50: ${current_ema_50:.4f} | 🔴 EMA 200: ${current_ema_200:.4f}\n"
        f"🛡 Поддержка: ${support_level:.4f} | ⚔️ Сопротивление: ${resist_level:.4f}\n\n"
    )

    trade_executed = False
    portfolio = get_portfolio()
    
    # Перед анализом проведем быструю проверку стоп-лоссов на всякий случай
    # (Но вообще это будет делать отдельная функция раз в 2 минуты)
    trailing_res = await check_trailing_stop()
    if trailing_res.get('message'):
        message += trailing_res['message'] + "\n\n"
        # Обновим порфолио, вдруг нас сейчас выбило
        portfolio = get_portfolio()

    # === ИСПОЛНЕНИЕ СИГНАЛОВ ПО СТРАТЕГИИ ===
    if signal == "BUY" and portfolio['ton'] == 0: 
        message += "🟢 *Сигнал: ПОКУПАТЬ*\n_Сработала агрессивная логика ('отскок' от нижней границы Боллинджера или RSI < 40). Ищем быструю прибыль._"
        if portfolio['usdt'] >= TRADE_AMOUNT:
            ton_to_buy = TRADE_AMOUNT / current_price
            execute_trade('BUY', current_price, ton_to_buy, TRADE_AMOUNT)
            
            new_portfolio = get_portfolio()
            message += f"\n✅ *СДЕЛКА*: Куплено {ton_to_buy:.2f} TON за ${TRADE_AMOUNT}\n_Страховочный Стоп-Лосс установлен на ${new_portfolio['stop_loss']:.4f}_"
            trade_executed = True
        else:
             message += "\n⚠️ Недостаточно USDT для покупки."

    elif signal == "SELL" and portfolio['ton'] > 0:
        message += "🔴 *Сигнал: ПРОДАВАТЬ*\n_Рынок перекуплен, фиксируем прибыль по индикатору RSI._"
        usdt_to_receive = portfolio['ton'] * current_price
        ton_to_sell = portfolio['ton']
        execute_trade('SELL', current_price, ton_to_sell, usdt_to_receive)
        
        profit = usdt_to_receive - (ton_to_sell * portfolio['entry_price'])
        message += f"\n✅ *СДЕЛКА*: Продано {ton_to_sell:.2f} TON за ${usdt_to_receive:.2f}\n💰 _Чистая прибыль от сделки: ${profit:.2f}_"
        trade_executed = True
            
    else:
        if portfolio['ton'] > 0:
            diff = ((current_price / portfolio['entry_price']) - 1) * 100
            diff_str = f"+{diff:.2f}%" if diff >= 0 else f"{diff:.2f}%"
            message += f"⏳ *Позиция открыта*\n_Текущий профит: {diff_str}_\n_Ждем сигнал на продажу или срабатывание стопа._"
        else:
            message += "⏳ *Сигнал: ОЖИДАНИЕ*\n_Нет явных возможностей. Сидим ровно._"

    return {
        "status": "success",
        "signal": signal,
        "price": current_price,
        "rsi": current_rsi,
        "message": message,
        "trade_executed": trade_executed
    }

if __name__ == "__main__":
    res = asyncio.run(analyze_market('15m'))
    print(res['message'])
