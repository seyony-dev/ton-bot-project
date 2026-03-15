import sqlite3
import datetime

DB_FILE = 'paper_trading.db'

def init_db(initial_balance=1000.0):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            usdt_balance REAL,
            ton_balance REAL,
            avg_entry_price REAL DEFAULT 0.0,
            stop_loss_price REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action TEXT, -- BUY или SELL
            price REAL,
            amount_ton REAL,
            amount_usdt REAL
        )
    ''')
    
    # Добавляем новые колонки для старой базы данных безопасно
    try:
        cursor.execute("ALTER TABLE portfolio ADD COLUMN avg_entry_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE portfolio ADD COLUMN stop_loss_price REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('SELECT COUNT(*) FROM portfolio')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO portfolio (id, usdt_balance, ton_balance, avg_entry_price, stop_loss_price) VALUES (1, ?, 0, 0.0, 0.0)', (initial_balance,))
        
    conn.commit()
    conn.close()

def get_portfolio():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT usdt_balance, ton_balance, avg_entry_price, stop_loss_price FROM portfolio WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'usdt': result[0], 
            'ton': result[1], 
            'entry_price': result[2] if result[2] else 0.0, 
            'stop_loss': result[3] if result[3] else 0.0
        }
    return {'usdt': 0.0, 'ton': 0.0, 'entry_price': 0.0, 'stop_loss': 0.0}

def update_stop_loss(new_stop_loss):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE portfolio SET stop_loss_price = ? WHERE id = 1', (new_stop_loss,))
    conn.commit()
    conn.close()

def execute_trade(action, price, amount_ton, amount_usdt):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO trades (timestamp, action, price, amount_ton, amount_usdt)
        VALUES (?, ?, ?, ?, ?)
    ''', (now, action, price, amount_ton, amount_usdt))
    
    portfolio = get_portfolio()
    if action == 'BUY':
        new_usdt = portfolio['usdt'] - amount_usdt
        new_ton = portfolio['ton'] + amount_ton
        
        # Считаем среднюю цену входа
        total_value_before = portfolio['ton'] * portfolio['entry_price']
        new_entry_price = (total_value_before + amount_usdt) / new_ton if new_ton > 0 else 0
        new_stop_loss = price * 0.95 # Первичный страховочный стоп на -5% при покупке
        
        cursor.execute('''
            UPDATE portfolio SET usdt_balance = ?, ton_balance = ?, avg_entry_price = ?, stop_loss_price = ? WHERE id = 1
        ''', (new_usdt, new_ton, new_entry_price, new_stop_loss))
        
    elif action == 'SELL':
        new_usdt = portfolio['usdt'] + amount_usdt
        new_ton = portfolio['ton'] - amount_ton
        
        # Если продали всё, обнуляем стопы и цену входа
        new_entry_price = portfolio['entry_price'] if new_ton > 0.0001 else 0.0
        new_stop_loss = portfolio['stop_loss'] if new_ton > 0.0001 else 0.0
        
        cursor.execute('''
            UPDATE portfolio SET usdt_balance = ?, ton_balance = ?, avg_entry_price = ?, stop_loss_price = ? WHERE id = 1
        ''', (new_usdt, new_ton, new_entry_price, new_stop_loss))
        
    conn.commit()
    conn.close()
    return True

def get_trade_history(limit=5):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, action, price, amount_ton, amount_usdt FROM trades ORDER BY id DESC LIMIT ?', (limit,))
    result = cursor.fetchall()
    conn.close()
    return result
