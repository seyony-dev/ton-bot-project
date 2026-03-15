import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, INITIAL_BALANCE
from database import init_db, get_portfolio, get_trade_history
from trading_engine import analyze_market, check_trailing_stop

if not BOT_TOKEN:
    print("ВНИМАНИЕ: Токен бота не найден! Добавьте его в файл .env")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
USER_CHAT_ID = None 

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    global USER_CHAT_ID
    USER_CHAT_ID = message.from_user.id
    init_db(INITIAL_BALANCE)
    
    welcome_text = (
        f"Привет, {message.from_user.full_name}! 🚀\n"
        f"Я твой обновленный бот для торговли TON.\n\n"
        f"Я анализирую: *RSI, EMA 50, EMA 200 и уровни поддержки*.\n"
        f"У тебя виртуальный баланс: *${INITIAL_BALANCE}*.\n\n"
        f"Доступные команды:\n"
        f"/status - Посмотреть баланс\n"
        f"/analyze - Выбрать таймфрейм и запустить анализ\n"
        f"/history - История сделок\n"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    portfolio = get_portfolio()
    text = (
        f"💼 *ТВОЙ ВИРТУАЛЬНЫЙ ПОРТФЕЛЬ:*\n\n"
        f"💵 USDT: *${portfolio['usdt']:.2f}*\n"
        f"💎 TON: *{portfolio['ton']:.2f}*\n"
    )
    
    if portfolio['ton'] > 0:
        text += (
            f"\n📊 *ОТКРЫТАЯ ПОЗИЦИЯ:*\n"
            f"🎯 Цена покупки: *${portfolio['entry_price']:.4f}*\n"
            f"🛡 Стоп-лосс / Трейлинг: *${portfolio['stop_loss']:.4f}*\n"
        )
        
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("history"))
async def history_handler(message: types.Message):
    history = get_trade_history()
    if not history:
        await message.answer("История сделок пока пуста. Ждем подходящего момента для торговли!")
        return
    text = "📜 *ИСТОРИЯ СДЕЛОК:*\n\n"
    for trade in history:
        timestamp, action, price, amount_ton, amount_usdt = trade
        emoji = "🟢" if action == 'BUY' else "🔴"
        text += f"{emoji} *{action}* | Цена: ${price:.3f}\n🕒 {timestamp}\n💰 TON: {amount_ton:.2f} | USDT: {amount_usdt:.2f}\n\n"
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# === ИНТЕРАКТИВНОЕ МЕНЮ ДЛЯ ANALYZE ===
@dp.message(Command("analyze"))
async def analyze_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡️ 15 минут", callback_data="analyze_15m"),
            InlineKeyboardButton(text="⏳ 1 час", callback_data="analyze_1h")
        ]
    ])
    await message.answer("🔄 Выбери таймфрейм для анализа графика TON:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("analyze_"))
async def process_analyze_callback(callback_query: CallbackQuery):
    timeframe = callback_query.data.split('_')[1] # получим '15m' или '1h'
    await bot.answer_callback_query(callback_query.id)
    
    # Редактируем сообщение, чтобы показать что мы думаем
    await bot.edit_message_text(
        text=f"🔄 Анализирую график ({'15 мин' if timeframe == '15m' else '1 час'})...",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    
    result = await analyze_market(timeframe)
    await bot.edit_message_text(
        text=result['message'],
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN
    )
# =======================================


# Планировщик будет проверять рынок каждые 15 минут
async def scheduled_market_check():
    global USER_CHAT_ID
    if USER_CHAT_ID:
        # Для авто-торговли используем 15-минутный таймфрейм, чтобы быстрее реагировать
        result = await analyze_market('15m')
        if result.get('trade_executed'):
            await bot.send_message(USER_CHAT_ID, f"🔔 *АВТОМАТИЧЕСКАЯ СДЕЛКА!*\n\n{result['message']}", parse_mode=ParseMode.MARKDOWN)
        else:
            print("Рынок (15m) проверен. Сделок нет.")

async def scheduled_trailing_stop_check():
    global USER_CHAT_ID
    if USER_CHAT_ID:
        result = await check_trailing_stop()
        if result.get('message'):
            await bot.send_message(USER_CHAT_ID, result['message'], parse_mode=ParseMode.MARKDOWN)

async def main() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_market_check, "interval", minutes=15)
    scheduler.add_job(scheduled_trailing_stop_check, "interval", minutes=2)
    scheduler.start()
    init_db(INITIAL_BALANCE)

    print("Бот запущен! Жду сообщений (нажми Ctrl+C в этом окне, чтобы остановить)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
