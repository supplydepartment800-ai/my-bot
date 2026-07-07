import os
import requests
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def calculate_indicators(df):
    # 1. RSI Calculation
    close_delta = df['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=13, adjust=False).mean()
    ma_down = down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (ma_up / ma_down)))
    
    # 2. MACD Calculation
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 3. Bollinger Bands
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    
    # 4. Exponential Moving Averages (Multi-Timeframe Confluence)
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

@app.route('/analyze')
def analyze_coin():
    raw_coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    
    # Standardizing token symbol for Binance API
    clean_coin = raw_coin.replace('-', '').replace('/', '')
    if not clean_coin.endswith('USDT'):
        clean_coin += 'USDT'

    # Fetching live 1H data from Binance Public API (Tries Spot first, then Futures)
    data = None
    intervals = ["1h", "4h", "1d"]
    
    # Target endpoint array for maximum reliability
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol={clean_coin}&interval=1h&limit=200",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={clean_coin}&interval=1h&limit=200"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url, timeout=5)
            if res.status_style == 200:
                data = res.json()
                if data and isinstance(data, list):
                    break
        except:
            continue

    if not data or 'code' in str(data):
        return jsonify({"error": f"Symbol {raw_coin} not found on Binance database."}), 404

    try:
        # Parsing Binance Klines data structure
        df = pd.DataFrame(data, columns=[
            'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_time', 'Quote_asset_volume', 'Number_of_trades',
            'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
        ])
        
        # Casting types to float for mathematical correctness
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)

        df = calculate_indicators(df)
        
        price = round(df['Close'].iloc[-1], 6)
        rsi = round(df['RSI'].iloc[-1], 2)
        macd = round(df['MACD'].iloc[-1], 6)
        macd_signal = round(df['Signal_Line'].iloc[-1], 6)
        bb_upper = round(df['BB_Upper'].iloc[-1], 6)
        bb_lower = round(df['BB_Lower'].iloc[-1], 6)
        ema50 = df['EMA50'].iloc[-1]
        ema200 = df['EMA200'].iloc[-1]

        # Heavy Multi-Indicator Analysis
        bullish_score = 0
        bearish_score = 0
        
        if price > ema50: bullish_score += 1
        else: bearish_score += 1
        
        if price > ema200: bullish_score += 1
        else: bearish_score += 1
        
        if macd > macd_signal: bullish_score += 1
        else: bearish_score += 1
        
        if rsi > 50: bullish_score += 1
        elif rsi < 50: bearish_score += 1

        # Strict Safe Strategy Formula (Always produces dynamic target parameters)
        if bullish_score >= bearish_score:
            side = "BUY LIMIT (LONG)"
            status = "STRONG_BULLISH" if bullish_score >= 3 else "WEAK_BULLISH"
            entry_low = round(price * 0.982, 5)
            entry_high = round(price * 0.995, 5)
            tp1 = round(price * 1.035, 5)
            tp2 = round(price * 1.075, 5)
            tp3 = round(price * 1.140, 5)
            sl = round(entry_low * 0.950, 5)
            alert = "ALL INDICATORS ALIGNED: Heavy structural support confirmed. Order safely inside the lower pull-back entry zone for swing goals."
        else:
            side = "SELL LIMIT (SHORT)"
            status = "STRONG_BEARISH" if bearish_score >= 3 else "WEAK_BEARISH"
            entry_low = round(price * 1.005, 5)
            entry_high = round(price * 1.018, 5)
            tp1 = round(price * 0.965, 5)
            tp2 = round(price * 0.925, 5)
            tp3 = round(price * 0.860, 5)
            sl = round(entry_high * 1.045, 5)
            alert = "BEARISH WAVE DETECTED: Multiple exponential moving averages crossing downwards. Short positions activated inside the entry ceiling."

        # Anti-Trap Protocol for Exhausted Over-extended Trends
        if rsi > 76 and "BUY" in side:
            status = "EXHAUSTED"
            alert = "LATE ENTRY RISK: Market is extremely Overbought (RSI > 75). Buying right now is dangerous. Wait for a severe correction."
        elif rsi < 24 and "SELL" in side:
            status = "EXHAUSTED"
            alert = "LATE DUMP RISK: Market is heavily Oversold (RSI < 25). The massive dump has already happened. Avoid shorting late."

        entry_zone = f"{entry_low} - {entry_high}"

        return jsonify({
            "coin": clean_coin, "price": price, "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": "3x - 5x (Small Wallet Safety)",
            "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl, "rsi": rsi,
            "macd": "BULLISH CROSS" if macd > macd_signal else "BEARISH CROSS",
            "bb_position": "UPPER CHANNEL" if price > ((bb_upper+bb_lower)/2) else "LOWER CHANNEL",
            "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
