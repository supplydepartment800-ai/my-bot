import os
import numpy as np
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

def calculate_indicators(hist):
    hist['RSI'] = calculate_rsi(hist)
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    
    exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
    exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
    hist['MACD'] = exp1 - exp2
    hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
    
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['BB_Std'] = hist['Close'].rolling(window=20).std()
    hist['BB_Upper'] = hist['MA20'] + (hist['BB_Std'] * 2)
    hist['BB_Lower'] = hist['MA20'] - (hist['BB_Std'] * 2)
    
    low_14 = hist['Low'].rolling(window=14).min()
    high_14 = hist['High'].rolling(window=14).max()
    hist['Stoch_K'] = 100 * ((hist['Close'] - low_14) / (high_14 - low_14))
    
    tp = (hist['High'] + hist['Low'] + hist['Close']) / 3
    ma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    hist['CCI'] = (tp - ma_tp) / (0.015 * mad_tp)
    
    hist['TR'] = pd.concat([hist['High'] - hist['Low'], (hist['High'] - hist['Close'].shift()).abs(), (hist['Low'] - hist['Close'].shift()).abs()], axis=1).max(axis=1)
    hist['ATR'] = hist['TR'].rolling(window=14).mean()
    hist['ADX'] = (hist['Close'].diff().abs().rolling(window=14).mean() / hist['ATR']) * 100
    return hist

@app.route('/analyze')
def analyze_coin():
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    mode = request.args.get('mode', 'FUTURE').upper().strip()
    base_coin = coin.replace('USDT', '')

    try:
        ticker = yf.Ticker(f"{base_coin}-USD")
        hist = ticker.history(period="1mo", interval="1h")
        if hist.empty: return jsonify({"error": "Not Found"}), 404

        price = round(hist['Close'].iloc[-1], 4)
        hist = calculate_indicators(hist)
        
        # Latest Matrix Values
        rsi = round(hist['RSI'].iloc[-1], 2)
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]
        macd = hist['MACD'].iloc[-1]
        macd_sig = hist['MACD_Signal'].iloc[-1]
        stoch_k = round(hist['Stoch_K'].iloc[-1], 2)
        cci = round(hist['CCI'].iloc[-1], 2)
        adx = round(hist['ADX'].iloc[-1], 2)
        bb_upper = hist['BB_Upper'].iloc[-1]
        bb_lower = hist['BB_Lower'].iloc[-1]

        # 10-INDICATOR MATRIX CONFLUENCE COUNTER
        bullish_score = 0
        bearish_score = 0
        
        if price > sma50: bullish_score += 1
        else: bearish_score += 1
        
        if price > sma200: bullish_score += 1
        else: bearish_score += 1
        
        if rsi > 50: bullish_score += 1
        else: bearish_score += 1
        
        if macd > macd_sig: bullish_score += 1
        else: bearish_score += 1
        
        if stoch_k > 50: bullish_score += 1
        else: bearish_score += 1
        
        if cci > 0: bullish_score += 1
        else: bearish_score += 1
        
        if price > ((bb_upper + bb_lower)/2): bullish_score += 1
        else: bearish_score += 1
        
        if adx > 25 and bullish_score > bearish_score: bullish_score += 1
        elif adx > 25 and bearish_score > bullish_score: bearish_score += 1

        # Calculate Dynamic Strategy Output
        leverage = "1x (SPOT)" if mode == "SPOT" else "3x - 5x"
        
        # Targets Calculation
        tp1 = round(price * 1.025, 4)
        tp2 = round(price * 1.05, 4)
        tp3 = round(price * 1.10, 4)
        sl = round(price * 0.965, 4)
        
        # Default Action Settings
        side = "WAIT / ACCUMULATION FLOW"
        status = "NEUTRAL"
        strategy = "📊 No Position: Wait for Matrix confirmation before entry."
        alert = "🔍 Market is building volume. Do not force entries now."

        # High Volatility or Breakout Scenarios (Big Buy / Big Sell Flow)
        if adx > 35:
            alert = "🚀 HIGH VOLUME FLOW DETECTED: Strong trend momentum is currently active!"

        if bullish_score >= 5:
            status = "BULLISH"
            side = "STRONG BUY (LONG)" if mode == "FUTURE" else "BUY (SPOT)"
            strategy = "🔥 In a Buy Trade? HOLD ACTIVE. Strong buying flow. You can target higher targets (TP2/TP3)."
            alert = "🎯 CONFLUENCE PASSED: Bulls are dominant. Trailing Stop Loss is highly recommended."
        elif bearish_score >= 5:
            status = "BEARISH"
            side = "STRONG SELL (SHORT)" if mode == "FUTURE" else "REDUCE / SPOT HOLD"
            strategy = "⚠️ In a Buy Trade? EXIT / SECURE PROFIT NOW. Bearish trend building. In a Short? Hold for TP1."
            alert = "📉 DOWNWARD MOMENTUM: High pressure from sellers. Avoid spot buying."
            
        if rsi > 75:
            status = "EXHAUSTED"
            side = "RISK ALERT / OVERBOUGHT"
            strategy = "🚨 Already in Profit? CLOSE POSITION NOW. Market is extremely overbought. Expect a drop."
            alert = "⛔ EXTREME RISK: RSI Exhaustion triggered. Protected flow active."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "leverage": leverage, "rsi": rsi, "adx": adx, "score": f"{bullish_score}/8 Bulls Active",
            "tp1": f"{tp1:,.4f}", "tp2": f"{tp2:,.4f}", "tp3": f"{tp3:,.4f}", "sl": f"{sl:,.4f}",
            "strategy": strategy, "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
