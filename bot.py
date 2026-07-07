import os
import requests
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def calculate_indicators(df):
    # 1. RSI (14)
    close_delta = df['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=13, adjust=False).mean()
    ma_down = down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (ma_up / ma_down)))
    
    # 2. MACD (12, 26, 9)
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 3. Bollinger Bands
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    
    # 4. Moving Averages for Swing Filtration
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

@app.route('/analyze')
def analyze_coin():
    raw_coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    clean_coin = raw_coin.replace('-', '').replace('/', '')
    if not clean_coin.endswith('USDT'):
        clean_coin += 'USDT'

    # Real-browser headers to bypass cloud hosting firewall blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    data = None
    # 5 Global Binance Mirrors Array to defeat 403/451 errors
    endpoints = [
        f"https://api.binance.com/api/v3/klines?symbol={clean_coin}&interval=1h&limit=200",
        f"https://api1.binance.com/api/v3/klines?symbol={clean_coin}&interval=1h&limit=200",
        f"https://api2.binance.com/api/v3/klines?symbol={clean_coin}&interval=1h&limit=200",
        f"https://api3.binance.com/api/v3/klines?symbol={clean_coin}&interval=1h&limit=200",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={clean_coin}&interval=1h&limit=200"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and isinstance(data, list):
                    break
        except:
            continue

    if not data or 'code' in str(data):
        return jsonify({"error": f"Token symbol '{raw_coin}' not recognized globally."}), 404

    try:
        df = pd.DataFrame(data, columns=[
            'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_time', 'Quote_asset_volume', 'Number_of_trades',
            'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
        ])
        
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)

        df = calculate_indicators(df)
        
        price = round(df['Close'].iloc[-1], 6)
        rsi = round(df['RSI'].iloc[-1], 2)
        macd = df['MACD'].iloc[-1]
        macd_signal = df['Signal_Line'].iloc[-1]
        ema50 = df['EMA50'].iloc[-1]
        ema200 = df['EMA200'].iloc[-1]

        bullish_signals = 0
        bearish_signals = 0
        
        if price > ema50: bullish_signals += 1
        else: bearish_signals += 1
        
        if price > ema200: bullish_signals += 1
        else: bearish_signals += 1
        
        if macd > macd_signal: bullish_signals += 1
        else: bearish_signals += 1

        # Pro Strategy Logic (1-7 Days Hold)
        if bullish_signals >= 3 and (42 <= rsi <= 68):
            side = "BUY / LONG SETUP"
            status = "STRONG_BULLISH"
            entry_zone = f"{round(price * 0.985, 5)} - {round(price * 0.998, 5)}"
            tp1 = round(price * 1.05, 5)
            tp2 = round(price * 1.10, 5)
            tp3 = round(price * 1.18, 5)
            sl = round(price * 0.94, 5)
            alert = "PRO CRITERIA MATCHED: Structural 1-7 Days Swing Long activated. Safe parameters set for small accounts."
        elif bearish_signals >= 3 and (32 <= rsi <= 58):
            side = "SELL / SHORT SETUP"
            status = "STRONG_BEARISH"
            entry_zone = f"{round(price * 1.002, 5)} - {round(price * 1.015, 5)}"
            tp1 = round(price * 0.95, 5)
            tp2 = round(price * 0.90, 5)
            tp3 = round(price * 0.82, 5)
            sl = round(price * 1.06, 5)
            alert = "PRO CRITERIA MATCHED: Macro distribution confirms a clear multi-day Short window."
        else:
            side = "DO NOT ENTER NOW"
            status = "RISKY_WAIT"
            entry_zone = "STAY OUT / NO SETUP"
            tp1, tp2, tp3, sl = "N/A", "N/A", "N/A", "N/A"
            if rsi > 70:
                alert = "DO NOT ENTER: Asset is massively Overbought (RSI > 70). Entering now will trap your small wallet at the top."
            elif rsi < 30:
                alert = "DO NOT ENTER: Asset is deeply Oversold (RSI < 30). Late dumping risk is extreme. Wait for a recovery pattern."
            else:
                alert = "DO NOT ENTER: Consolidation / Choppy price action detected. Trend has no direction. Protect capital and wait."

        return jsonify({
            "coin": clean_coin, "price": price, "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": "2x - 3x (Strict Small Wallet Rule)",
            "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl, "rsi": rsi,
            "macd": "BULLISH" if macd > macd_signal else "BEARISH",
            "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
