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
    mode = request.args.get('mode', 'FUTURE').upper().strip() # FUTURE or SPOT
    
    base_coin = coin.replace('USDT', '').replace('.P', '')
    yf_symbol = f"{base_coin}-USD"

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="1mo", interval="1h")
        
        if hist.empty or len(hist) < 200:
            hist = ticker.history(period="3mo", interval="1d")
            
        if hist.empty:
            return jsonify({"error": "Coin asset not found globally"}), 404

        price = round(hist['Close'].iloc[-1], 4)
        
        # Tech Indicators Data Layer
        hist['RSI'] = calculate_rsi(hist)
        current_rsi = round(hist['RSI'].iloc[-1], 2)
        
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()
        hist['SMA200'] = hist['Close'].rolling(window=200).mean()
        
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]

        # Standard Default Clean System
        side = "WAIT / MARKET UNSTABLE"
        entry_zone = "No Trade Zone"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        leverage = "1x (No Leverage)" if mode == "SPOT" else "3x - 5x (Swing Mode)"
        alert = "Nexus Core: Matrix is consolidating. Avoid early entries."
        status = "NEUTRAL"

        # STRICT CAPITAL PROTECTION MATRIX (LOSS prevention logic)
        if price < sma50 and current_rsi < 28:
            # Oversold Market Phase
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 LOSS PREVENTION ALERT: Asset already crashed into heavy oversold zone! Dynamic shorting or late panic selling here will cause massive losses. Keep waiting."
        
        elif price > sma50 and current_rsi > 72:
            # Overbought Market Phase
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 OVERBOUGHT PROTECTION: Market pumped too high! Do NOT enter long now. Institutional liquidation imminent. Standby in cash."

        # VERIFIED TRADING PHASES
        elif price > sma50 and price > sma200 and (40 <= current_rsi <= 68):
            # Bullish Trend Alignment
            status = "BULLISH"
            if mode == "FUTURE":
                side = "BUY LIMIT (LONG)"
                leverage = "3x - 5x Maximum (Safe Margin)"
                alert = "🔥 AI FUTURE ENGINE: Trend is strongly aligned upwards on 1H/4H framework. Safe to build Long grid orders inside the entry window."
            else:
                side = "BUY (SPOT ACCUMULATION)"
                leverage = "1x (Spot Architecture)"
                alert = "🟢 AI SPOT SCANNED: Strong organic macro demand. Excellent window to load spot portfolio for maximum hold upside."

            entry_low = round(price * 0.988, 4)
            entry_high = round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1 = round(price * 1.03, 4)
            tp2 = round(price * 1.07, 4)
            tp3 = round(price * 1.15, 4)
            sl = round(entry_low * 0.96, 4) # Tight protective stop loss

        elif price < sma50 and price < sma200 and (32 <= current_rsi <= 60):
            # Bearish Trend Alignment
            status = "BEARISH"
            if mode == "FUTURE":
                side = "SELL LIMIT (SHORT)"
                leverage = "2x - 3x (High Risk Downtrend)"
                entry_low = round(price * 1.002, 4)
                entry_high = round(price * 1.012, 4)
                entry_zone = f"{entry_low} - {entry_high}"
                tp1 = round(price * 0.97, 4)
                tp2 = round(price * 0.93, 4)
                tp3 = round(price * 0.85, 4)
                sl = round(entry_high * 1.04, 4)
                alert = "🔴 AI FUTURE ENGINE: Market structures are collapsing down. Safe to deploy short protection grid inside the entry zone."
            else:
                side = "WAIT / CASH ONLY"
                entry_zone = "Bear Downtrend - Avoid Buying"
                alert = "⚠️ SPOT WARNING: Global downtrend phase active. Do NOT buy spot coins. Wait for an accumulation floor to trigger."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": leverage,
            "tp1": f"{tp1:,.4f}" if tp1 > 0 else "0.00", 
            "tp2": f"{tp2:,.4f}" if tp2 > 0 else "0.00", 
            "tp3": f"{tp3:,.4f}" if tp3 > 0 else "0.00", 
            "sl": f"{sl:,.4f}" if sl > 0 else "0.00",
            "rsi": current_rsi, "macro_trend": "UPTREND" if price > sma200 else "DOWNTREND",
            "alert": alert, "mode": mode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
