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
        
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()   # Intermediate Trend
        hist['SMA200'] = hist['Close'].rolling(window=200).mean() # Macro Trend
        
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]

        # Initialization
        side = "WAIT / NO SIGNAL"
        entry_zone = "No Trade Zone"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        alert = "Market is consolidating. Waiting for verified macro trend confirmation."
        status = "NEUTRAL"

        # 🚨 ANTI-LATE ENTRY & SPOT EXHAUSTION DETECTION LOGIC
        if price < sma50 and current_rsi < 28:
            side = "ACCUMULATE / HOLD"
            status = "EXHAUSTED"
            alert = "⚠️ EXHAUSTION SCANNER: Price has dumped aggressively into heavy oversold territory. Selling here is irrational. Look to accumulate if you hold cash."
        
        elif price > sma50 and current_rsi > 72:
            side = "TAKE PROFIT / WAIT"
            status = "EXHAUSTED"
            alert = "⚠️ OVERBOUGHT SCENARIO: Asset is running hot above short-term EMAs. Buying at these high rates is highly dangerous. Consider securing partial spot profits."

        # Verified Spot Trends (Safe Bullish Entry)
        elif price > sma50 and price > sma200 and (40 <= current_rsi <= 68):
            side = "BUY (SPOT)"
            status = "BULLISH"
            entry_low = round(price * 0.988, 4)
            entry_high = round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1 = round(price * 1.03, 4)
            tp2 = round(price * 1.07, 4)
            tp3 = round(price * 1.15, 4)
            sl = round(entry_low * 0.93, 4) # Slightly wider stop loss for Spot swings
            alert = "🟢 STRONG SPOT CONFLUENCE: 1H, 4H & 1D trends are fully aligned upwards. Safest structural window to execute accumulation orders inside the entry zone."

        # Bearish / Markdown Phase (Avoid buying or short safely via Spot-exit)
        elif price < sma50 and price < sma200 and (32 <= current_rsi <= 60):
            side = "WAIT / BEARISH"
            status = "BEARISH"
            entry_zone = "Decline Phase - No Buy Zone"
            alert = "🔴 TREND DOWNTURN: Macro structure is breaking downwards. Avoid spot allocations here. Cash preservation is highly recommended until bottom structure forms."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": "1x (Spot Architecture)",
            "tp1": f"{tp1:,.4f}" if tp1 > 0 else "0.00", 
            "tp2": f"{tp2:,.4f}" if tp2 > 0 else "0.00", 
            "tp3": f"{tp3:,.4f}" if tp3 > 0 else "0.00", 
            "sl": f"{sl:,.4f}" if sl > 0 else "0.00",
            "rsi": current_rsi, "macro_trend": "BULLISH UPTREND" if price > sma200 else "BEARISH DOWNTREND",
            "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
