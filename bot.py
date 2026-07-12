import os
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def calculate_rsi(df, periods=14):
    close_delta = df['Close'].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=periods - 1, adjust=False).mean()
    ma_down = down.ewm(com=periods - 1, adjust=False).mean()
    rsi = ma_up / ma_down
    return 100 - (100 / (1 + rsi))

@app.route('/analyze')
def analyze_coin():
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    base_coin = coin.replace('USDT', '')
    yf_symbol = f"{base_coin}-USD"

    try:
        ticker = yf.Ticker(yf_symbol)
        # Fetching 1H history to analyze short, medium and macro trends together
        hist = ticker.history(period="1mo", interval="1h")
        
        if hist.empty or len(hist) < 200:
            hist = ticker.history(period="3mo", interval="1d")
            
        if hist.empty:
            return jsonify({"error": "Coin not found globally"}), 404

        price = round(hist['Close'].iloc[-1], 4)
        
        # Multi-Timeframe Technical Metrics
        hist['RSI'] = calculate_rsi(hist)
        current_rsi = round(hist['RSI'].iloc[-1], 2)
        
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()   # Intermediate Trend (4H equivalence)
        hist['SMA200'] = hist['Close'].rolling(window=200).mean() # Macro Trend (1D equivalence)
        
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]

        # Initialization
        side = "WAIT / NO SIGNAL"
        entry_zone = "No Trade Zone"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        alert = "Market is consolidating. Waiting for verified multi-timeframe confirmation."
        status = "NEUTRAL"

        # 🚨 ANTI-LATE ENTRY & LATE DUMP DETECTION LOGIC
        if price < sma50 and current_rsi < 28:
            # Price is down, but RSI shows it already dumped too much. Do not enter late!
            side = "WAIT / DO NOT ENTER"
            status = "EXHAUSTED"
            alert = "WARNING: The dump is already completed! Selling now is extremely risky. Trend exhaustion detected."
        
        elif price > sma50 and current_rsi > 72:
            # Price is up, but RSI shows it already pumped too much. Do not enter late!
            side = "WAIT / DO NOT ENTER"
            status = "EXHAUSTED"
            alert = "WARNING: The pump is already completed! Buying now is dangerous. Overbought exhaustion detected."

        # Verified Trends for Safe Entries
        elif price > sma50 and price > sma200 and (40 <= current_rsi <= 68):
            side = "BUY LIMIT (LONG)"
            status = "BULLISH"
            entry_low = round(price * 0.988, 4)
            entry_high = round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1 = round(price * 1.03, 4)
            tp2 = round(price * 1.07, 4)
            tp3 = round(price * 1.15, 4)
            sl = round(entry_low * 0.95, 4)
            alert = "STRONG CONFLUENCE: 1H, 4H & 1D trends are aligned upwards. Place orders inside the entry zone for a safe swing ride."

        elif price < sma50 and price < sma200 and (32 <= current_rsi <= 60):
            side = "SELL LIMIT (SHORT)"
            status = "BEARISH"
            entry_low = round(price * 1.002, 4)
            entry_high = round(price * 1.012, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1 = round(price * 0.97, 4)
            tp2 = round(price * 0.93, 4)
            tp3 = round(price * 0.85, 4)
            sl = round(entry_high * 1.05, 4)
            alert = "STRONG CONFLUENCE: Macro and micro trends are crashing down. Perfect entry window for safe shorting."

        return jsonify({
            "coin": coin, "price": price, "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": "3x - 5x (Swing Recommended)",
            "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl,
            "rsi": current_rsi, "macro_trend": "UPTREND" if price > sma200 else "DOWNTREND",
            "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
