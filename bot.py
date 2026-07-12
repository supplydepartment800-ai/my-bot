import os
import pandas as pd
import yfinance as yf
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
    rsi = 100 - (100 / (1 + (ma_up / ma_down)))
    df['RSI'] = rsi

    # 2 & 3. Moving Averages
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    # 4 & 5. MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 6 & 7. Bollinger Bands
    df['BB_mid'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_high'] = df['BB_mid'] + (df['BB_std'] * 2)
    df['BB_low'] = df['BB_mid'] - (df['BB_std'] * 2)

    # 8. ATR (Volatility)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['ATR'] = true_range.ewm(alpha=1/14, adjust=False).mean()

    # 9. Stochastic Oscillator (%K)
    low_14 = df['Low'].rolling(window=14).min()
    high_14 = df['High'].rolling(window=14).max()
    df['Stoch'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))

    # 10. Commodity Channel Index (CCI)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['CCI'] = (tp - tp.rolling(14).mean()) / (0.015 * tp.rolling(14).std())

    return df

@app.route('/analyze')
def analyze_coin():
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    mode = request.args.get('mode', 'FUTURE').upper().strip()
    
    base_coin = coin.replace('USDT', '').replace('.P', '')
    yf_symbol = f"{base_coin}-USD"

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="1mo", interval="1h")
        
        if hist.empty or len(hist) < 200:
            hist = ticker.history(period="3mo", interval="1d")
            
        if hist.empty:
            return jsonify({"error": "Coin asset not found globally"}), 404

        hist = calculate_indicators(hist)
        
        # Latest Values
        price = round(hist['Close'].iloc[-1], 4)
        rsi = round(hist['RSI'].iloc[-1], 2)
        macd = hist['MACD'].iloc[-1]
        signal_line = hist['Signal_Line'].iloc[-1]
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]
        bb_high = hist['BB_high'].iloc[-1]
        bb_low = hist['BB_low'].iloc[-1]
        stoch = round(hist['Stoch'].iloc[-1], 2)
        cci = round(hist['CCI'].iloc[-1], 2)

        # Indicators 10 Voting System
        bullish_votes = 0
        bearish_votes = 0

        if rsi > 50: bullish_votes += 1
        else: bearish_votes += 1

        if price > sma50: bullish_votes += 1
        else: bearish_votes += 1

        if price > sma200: bullish_votes += 1
        else: bearish_votes += 1

        if macd > signal_line: bullish_votes += 1
        else: bearish_votes += 1

        if macd > 0: bullish_votes += 1
        else: bearish_votes += 1

        if price > hist['SMA20'].iloc[-1]: bullish_votes += 1
        else: bearish_votes += 1

        if cci > 0: bullish_votes += 1
        else: bearish_votes += 1

        if stoch > 50: bullish_votes += 1
        else: bearish_votes += 1

        if price > ((bb_high + bb_low) / 2): bullish_votes += 1
        else: bearish_votes += 1

        if hist['Close'].iloc[-1] > hist['Close'].iloc[-2]: bullish_votes += 1
        else: bearish_votes += 1

        # Decision Matrix
        status = "NEUTRAL"
        side = "WAIT / NO SIGNAL"
        entry_zone = "No Trade Zone"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        leverage = "1x (Spot)" if mode == "SPOT" else "3x - 5x (Swing)"
        alert = "Market is consolidating. All 10 indicators are fighting for direction."

        # Safety Override Rules (Anti-loss)
        if rsi < 28 or stoch < 15:
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 LOSS PREVENTION: Asset is extremely oversold. Entering a short or panic selling here will cause massive losses."
        elif rsi > 72 or stoch > 85:
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 OVERBOUGHT PROTECTION: Price pumped too high. Buying right now is dangerous. Rejection imminent."
        
        # Valid Signals Based on 10 Indicators Score
        elif bullish_votes >= 7:
            status = "BULLISH"
            if mode == "FUTURE":
                side = "BUY LIMIT (LONG)"
                alert = f"🔥 AI SCANNED ({bullish_votes}/10 Bullish): Macro and micro trends are aligned upwards. Safe to enter Long position."
            else:
                side = "BUY (SPOT)"
                alert = f"🟢 AI SPOT SCANNED ({bullish_votes}/10 Bullish): Strong organic structure. Perfect accumulation window."
            
            entry_low = round(price * 0.988, 4)
            entry_high = round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1 = round(price * 1.03, 4)
            tp2 = round(price * 1.07, 4)
            tp3 = round(price * 1.15, 4)
            sl = round(entry_low * 0.96, 4)

        elif bearish_votes >= 7:
            status = "BEARISH"
            if mode == "FUTURE":
                side = "SELL LIMIT (SHORT)"
                alert = f"🔴 AI SCANNED ({bearish_votes}/10 Bearish): Matrix is collapsing down. Safe to deploy short protection grid."
                entry_low = round(price * 1.002, 4)
                entry_high = round(price * 1.012, 4)
                entry_zone = f"{entry_low} - {entry_high}"
                tp1 = round(price * 0.97, 4)
                tp2 = round(price * 0.93, 4)
                tp3 = round(price * 0.85, 4)
                sl = round(entry_high * 1.04, 4)
            else:
                side = "WAIT / CASH ONLY"
                entry_zone = "Bear Downtrend - Avoid Buying"
                alert = f"⚠️ SPOT WARNING ({bearish_votes}/10 Bearish): Downtrend phase active. Do NOT buy spot coins."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": leverage,
            "tp1": f"{tp1:,.4f}" if tp1 > 0 else "0.00", 
            "tp2": f"{tp2:,.4f}" if tp2 > 0 else "0.00", 
            "tp3": f"{tp3:,.4f}" if tp3 > 0 else "0.00", 
            "sl": f"{sl:,.4f}" if sl > 0 else "0.00",
            "rsi": rsi, "stoch": stoch, "cci": cci,
            "score": f"BULL: {bullish_votes} | BEAR: {bearish_votes}",
            "macro_trend": "UPTREND" if price > sma200 else "DOWNTREND",
            "alert": alert, "mode": mode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def ai_chat():
    data = request.json or {}
    msg = data.get('message', '').lower()
    coin = data.get('coin', 'BTCUSDT').upper()
    signal_data = data.get('signalData', {})

    # Advanced Rule-Based Sinhala Generative Engine for Crypto
    if not signal_data or "price" not in signal_data:
        return jsonify({"reply": "කරුණාකර ප්‍රථමයෙන් 'AI SCAN' බොත්තම ඔබා දත්ත ලබාගන්න."})

    price = signal_data.get('price')
    status = signal_data.get('status')
    signal = signal_data.get('signal')
    score = signal_data.get('score')
    entry = signal_data.get('entry_zone')
    tp1 = signal_data.get('tp1')
    sl = signal_data.get('sl')
    lev = signal_data.get('leverage')

    if "pump" in msg or "up" in msg or "yada" in msg:
        if status == "BULLISH":
            reply = f"✅ ඔව්, {coin} කාසිය මේ වෙලාවේ හොඳටම Bullish මට්ටමක තියෙන්නේ ({score}). Indicators 10න් වැඩි ප්‍රමාණයක් ඉහළට යාමට සංඥා කරනවා. Entry සෝන් එකෙන් බලාගෙන Long එකක් දාන්න පුළුවන්. හැබැයි ලොකුවටම Pump වෙනකම් ඉන්න එපා, TP1 සහ TP2 වලදී ලාභය ගන්න!"
        elif status == "EXHAUSTED":
            reply = f"⚠️ පිස්සුද! {coin} දැනටමත් ගොඩක් Pump වෙලා ඉවරයි (Overbought). දැන් අලුතෙන් බයි කරන්න යන්න එපා, ලොකු ඩම්ප් එකක් (Drop එකක්) ඕනෑම වෙලාවක එන්න පුළුවන්. ප්‍රවේශම් වන්න!"
        else:
            reply = f"❌ නැහැ, {coin} එකට මේ වෙලාවේ ලොකු Pump එකක් යාමේ හැකියාවක් නැහැ. මාකට් එක තියෙන්නේ සයිඩ්වේස් (Consolidating) මට්ටමකයි. Trade එකකට යන්න එපා."

    elif "dump" in msg or "down" in msg or "weteida" in msg:
        if status == "BEARISH":
            reply = f"🚨 ඔව් ප්‍රවේශම් වන්න! {coin} කාසිය Indicators 10න්ම පෙන්වන්නේ Bearish තත්වයක් ({score}). මිල තවත් පහළට කඩාගෙන වැටෙන්න පුළුවන්. Future කරනවා නම් හොඳම Entry එකක් බලාගෙන Short එකක් සෙට් කරන්න පුළුවන්."
        elif status == "EXHAUSTED":
            reply = f"⚠️ නැහැ, {coin} දැනටමත් උපරිමයටම ඩම්ප් වෙලා තියෙන්නේ (Oversold). මේ වෙලාවේ අලුතෙන් Short දාන්න හෝ බයට විකුණන්න යන්න එපා. ඕනෑම වෙලාවක මාකට් එක ආපහු හැරෙන්න (Bounce back) පුළුවන්."
        else:
            reply = f"📉 {coin} දැනට ස්ථාවර මට්ටමක තියෙනවා. ලොකු කඩා වැටීමක් පෙන්වන්නේ නැහැ, හැබැයි Indicators 10න් පැහැදිලි Trend එකක් එනකම් ඉවසන්න."

    elif "entry" in msg or "sl" in msg or "target" in msg or "koheda" in msg:
        if "TRADE" in signal or "WAIT" in signal:
            reply = f"🚫 මේ වෙලාවේ {coin} එකට කිසිම ආරක්ෂිත Entry එකක් නැහැ! AI එකෙන් මේ වෙලාවේ Trade කරන්න එපා කියලා කියනවා. කරුණාකර ඉවසන්න."
        else:
            reply = f"📊 මෙන්න {coin} සඳහා AI එකෙන් ගණනය කරපු ආරක්ෂිතම කලාපය:\n• Entry සෝන් එක: {entry}\n• Leverage එක: {lev}\n• Stop Loss (SL): {sl}\n• පළමු ඉලක්කය (TP1): {tp1}\nකරුණාකර Risk එක කළමනාකරණය කරගෙන Trade කරන්න."

    else:
        reply = f"வணக்கம்/ආයුබෝවන්! මම Nexus AI සහායකයා. {coin} දැනට පවතින්නේ {status} මට්ටමකයි ({score}). ඔබට මෙහි ඉදිරි ගමන (Pump/Dump), Entry සෝන් එක හෝ Stop Loss පිළිබඳව ඕනෑම දෙයක් Singlish වලින් අසා දැනගත හැක!"

    return jsonify({"reply": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
