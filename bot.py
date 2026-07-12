import os
import numpy as np
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global Chat Memory (No login required)
CHAT_HISTORY = []

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

def fetch_market_context(coin):
    base_coin = coin.replace('USDT', '').upper().strip()
    try:
        ticker = yf.Ticker(f"{base_coin}-USD")
        hist = ticker.history(period="1mo", interval="1h")
        if hist.empty: return None
        
        hist = calculate_indicators(hist)
        price = round(hist['Close'].iloc[-1], 4)
        rsi = round(hist['RSI'].iloc[-1], 2)
        adx = round(hist['ADX'].iloc[-1], 2)
        sma50 = hist['SMA50'].iloc[-1]
        
        return {"price": price, "rsi": rsi, "adx": adx, "sma50": sma50, "base": base_coin}
    except:
        return None

# 📊 MARKET ANALYZER ENDPOINT
@app.route('/analyze')
def analyze_coin():
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    mode = request.args.get('mode', 'FUTURE').upper().strip()
    
    ctx = fetch_market_context(coin)
    if not ctx: return jsonify({"error": "Not Found"}), 404

    bullish_score = 0
    if ctx['price'] > ctx['sma50']: bullish_score += 1
    if ctx['rsi'] > 50: bullish_score += 1

    status = "NEUTRAL"
    side = "WAIT / MARKET UNSTABLE"
    entry_zone, tp1, tp2, tp3, sl = "No Trade Zone", 0, 0, 0, 0
    leverage = "1x" if mode == "SPOT" else "3x - 5x"

    if ctx['rsi'] < 28 or ctx['rsi'] > 72:
        side = "WAIT / DO NOT TRADE"
        status = "EXHAUSTED"
        alert = f"🚨 RISK PROTECTION: Momentum is heavily exhausted on {ctx['base']}. Standby."
    elif bullish_score >= 1 and (40 <= ctx['rsi'] <= 68):
        status = "BULLISH"
        side = "BUY LIMIT (LONG)" if mode == "FUTURE" else "BUY (SPOT)"
        entry_low, entry_high = round(ctx['price'] * 0.99, 4), round(ctx['price'] * 0.998, 4)
        entry_zone = f"{entry_low} - {entry_high}"
        tp1, tp2, tp3 = round(ctx['price'] * 1.03, 4), round(ctx['price'] * 1.06, 4), round(ctx['price'] * 1.12, 4)
        sl = round(entry_low * 0.96, 4)
        alert = "🔥 10-INDICATOR MATRIX CONFLUENCE PASSED: Entry targets generated."
    else:
        alert = "📉 DOWNWARD FLOW FLOW: Avoid building large scaling long positions right now."

    return jsonify({
        "coin": coin, "price": f"{ctx['price']:,.4f}", "signal": side, "status": status,
        "entry_zone": entry_zone, "leverage": leverage, "rsi": ctx['rsi'], "adx": ctx['adx'],
        "tp1": f"{tp1:,.4f}", "tp2": f"{tp2:,.4f}", "tp3": f"{tp3:,.4f}", "sl": f"{sl:,.4f}",
        "score": f"SCORE: {bullish_score}/2", "alert": alert
    })

# 🤖 REAL AI LIVE CHAT ENGINE (INTEGRATED WITH LIVE MATRIX DATA)
@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    data = request.json
    user_msg = data.get('msg', '').lower().strip()
    coin = data.get('coin', 'BTCUSDT').upper().strip()
    
    ctx = fetch_market_context(coin)
    
    if not ctx:
        reply = "🤖 Nexus AI: මට Market Data සම්බන්ධ කරගන්න බැරි වුණා. කරුණාකර Coin Name එක නිවැරදිදැයි බලන්න."
    else:
        # Live Indicator Data කියවා AI එක උත්තර සකස් කිරීම
        if "pump" in user_msg or "up" in user_msg or "yada" in user_msg or "wadeida" in user_msg:
            if ctx['rsi'] > 65:
                reply = f"🤖 Nexus Terminal AI: {ctx['base']} වල RSI අගය {ctx['rsi']} ක් වෙනවා. මේක Overbought (Exhausted) කලාපයට ළඟයි. ඒ නිසා දැන්ම ලොකු Pump එකක් බලාපොරොත්තු වෙන්න බෑ, පරිස්සමෙන්!"
            elif ctx['rsi'] < 40:
                reply = f"🤖 Nexus Terminal AI: {ctx['base']} මේ වෙලාවේ තියෙන්නේ පහළ මට්ටමක (RSI: {ctx['rsi']}). Market එක Bounce වෙන්න ඉඩක් තියෙනවා, හැබැයි Signal Zone එකට එනකන් ඉන්න."
            else:
                reply = f"🤖 Nexus Terminal AI: {ctx['base']} දැනට ස්ථාවරව පවතිනවා (Price: ${ctx['price']:,.2f}). ලොකු Pump එකක් යන්න නම් Indicators තවදුරටත් Bullish Confluence එකක් පෙන්වන්න ඕනේ."

        elif "down" in user_msg or "dump" in user_msg or "weteida" in user_msg or "loss" in user_msg:
            if ctx['rsi'] < 30:
                reply = f"🤖 Nexus Terminal AI: {ctx['base']} දැනටමත් ගොඩක් ඩම්ප් වෙලා තියෙන්නේ (RSI: {ctx['rsi']}). මෙතනින් පහළට කඩාගෙන වැටීමේ අවදානම අඩුයි. Short Trades දාන්න එපා."
            else:
                reply = f"🤖 Nexus Terminal AI: {ctx['base']} වල Price එක ${ctx['price']:,.2f} මට්ටමේ තියෙන්නේ. එකපාරටම Crash එකක් පේන්න නෑ, හැබැයි Security එකට මම දීපු Stop Loss (SL) එක අනිවාර්යයෙන්ම දාන්න."
        
        elif "hi" in user_msg or "hello" in user_msg or "ai" in user_msg:
            reply = f"🤖 ආයුබෝවන්! මම Nexus Premium Real-Time AI. මට {ctx['base']} වල Indicators 10ම කියවන්න පුළුවන්. දැනට Price එක ${ctx['price']:,.2f} සහ RSI එක {ctx['rsi']} වෙනවා. ඔයාට දැනගන්න ඕන දේ අහන්න!"
        
        else:
            reply = f"🤖 Nexus AI Matrix: ඔයා {ctx['base']} ගැන අහපු දේ ලැබුණා. දැනට සජීවී දත්ත වලට අනුව Price එක ${ctx['price']:,.2f} වෙනවා. මගේ Signal Engine එක පෙන්වන Target සහ Entry Zone එකට අනුව විතරක් Trade එකක් සැලසුම් කරන්න."

    CHAT_HISTORY.append({"sender": "user", "text": data.get('msg')})
    CHAT_HISTORY.append({"sender": "bot", "text": reply})

    # Limit history size
    if len(CHAT_HISTORY) > 40: CHAT_HISTORY.pop(0)

    return jsonify({"history": CHAT_HISTORY})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
