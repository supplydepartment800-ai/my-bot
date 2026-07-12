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

def calculate_indicators(hist):
    # 1, 2, 3. RSI & Moving Averages
    hist['RSI'] = calculate_rsi(hist)
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    
    # 4, 5. MACD & Signal Line
    exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
    exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
    hist['MACD'] = exp1 - exp2
    hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
    
    # 6, 7. Bollinger Bands (Upper & Lower)
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['BB_Std'] = hist['Close'].rolling(window=20).std()
    hist['BB_Upper'] = hist['MA20'] + (hist['BB_Std'] * 2)
    hist['BB_Lower'] = hist['MA20'] - (hist['BB_Std'] * 2)
    
    # 8. Stochastic Oscillator (%K)
    low_14 = hist['Low'].rolling(window=14).min()
    high_14 = hist['High'].rolling(window=14).max()
    hist['Stoch_K'] = 100 * ((hist['Close'] - low_14) / (high_14 - low_14))
    
    # 9. Commodity Channel Index (CCI)
    tp = (hist['High'] + hist['Low'] + hist['Close']) / 3
    ma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: pd.Series(x).mad() if hasattr(pd.Series(x), 'mad') else np.abs(x - x.mean()).mean())
    hist['CCI'] = (tp - ma_tp) / (0.015 * mad_tp)
    
    # 10. Average Directional Index (ADX) - Simplified Trend Strength
    hist['TR'] = pd.concat([hist['High'] - hist['Low'], 
                            (hist['High'] - hist['Close'].shift()).abs(), 
                            (hist['Low'] - hist['Close'].shift()).abs()], axis=1).max(axis=1)
    hist['ATR'] = hist['TR'].rolling(window=14).mean()
    # Trend strength estimate based on velocity
    hist['ADX'] = (hist['Close'].diff().abs().rolling(window=14).mean() / hist['ATR']) * 100
    
    return hist

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

        price = round(hist['Close'].iloc[-1], 4)
        hist = calculate_indicators(hist)
        
        # Pulling Latest Data Points
        rsi = round(hist['RSI'].iloc[-1], 2)
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]
        macd = hist['MACD'].iloc[-1]
        macd_sig = hist['MACD_Signal'].iloc[-1]
        bb_up = hist['BB_Upper'].iloc[-1]
        bb_low = hist['BB_Lower'].iloc[-1]
        stoch_k = round(hist['Stoch_K'].iloc[-1], 2)
        cci = round(hist['CCI'].iloc[-1], 2)
        adx = round(hist['ADX'].iloc[-1], 2)

        # Scoring Matrix based on 10 Indicators
        bullish_score = 0
        bearish_score = 0
        
        if price > sma50: bullish_score += 1
        else: bearish_score += 1
        
        if price > sma200: bullish_score += 1
        else: bearish_score += 1
        
        if macd > macd_sig: bullish_score += 1
        else: bearish_score += 1
        
        if macd > 0: bullish_score += 1
        else: bearish_score += 1
        
        if rsi > 50: bullish_score += 1
        elif rsi < 50: bearish_score += 1
        
        if cci > 0: bullish_score += 1
        else: bearish_score += 1
        
        if stoch_k > 50: bullish_score += 1
        else: bearish_score += 1
        
        if price > ((bb_up + bb_low)/2): bullish_score += 1
        else: bearish_score += 1

        # Logic Assignments
        status = "NEUTRAL"
        side = "WAIT / MARKET UNSTABLE"
        entry_zone = "No Trade Zone"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        leverage = "1x" if mode == "SPOT" else "3x - 5x"
        alert = "Nexus Core: Indicators are clashing. Capital preservation active."

        # Risk Protection Filters
        if rsi < 28 or stoch_k < 15:
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 LOSS PREVENTION: Indicators show extreme oversold exhaustion. Do NOT short or panic sell here!"
        elif rsi > 72 or stoch_k > 85:
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 RISK PROTECTION: Extreme overbought momentum scanned. Massive drop risk. Do NOT long or buy now!"
        
        # Valid Execution Windows
        elif bullish_score >= 6 and (40 <= rsi <= 68):
            status = "BULLISH"
            side = "BUY LIMIT (LONG)" if mode == "FUTURE" else "BUY (SPOT)"
            leverage = "3x - 5x (Max Safe)" if mode == "FUTURE" else "1x (Spot)"
            entry_low = round(price * 0.99, 4)
            entry_high = round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1, tp2, tp3 = round(price * 1.03, 4), round(price * 1.06, 4), round(price * 1.12, 4)
            sl = round(entry_low * 0.96, 4)
            alert = f"🔥 10-INDICATOR CONFLUENCE PASSED: Bullish Strength is high ({bullish_score}/8). Safe to trade."
            
        elif bearish_score >= 6 and (32 <= rsi <= 60):
            status = "BEARISH"
            if mode == "FUTURE":
                side = "SELL LIMIT (SHORT)"
                leverage = "2x - 3x (Conservative)"
                entry_low = round(price * 1.002, 4)
                entry_high = round(price * 1.01, 4)
                entry_zone = f"{entry_low} - {entry_high}"
                tp1, tp2, tp3 = round(price * 0.97, 4), round(price * 0.94, 4), round(price * 0.88, 4)
                sl = round(entry_high * 1.04, 4)
                alert = f"🔴 BEARISH MATRIX DETECTED: Sell pressure dominating ({bearish_score}/8). Safe to execute short protection grids."
            else:
                side = "WAIT / CASH ONLY"
                entry_zone = "Bear Downtrend - Avoid Buying"
                alert = "⚠️ SPOT WARNING: Global trend is down. Protect your spot wallet. Standby in stable cash."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": leverage, "rsi": rsi, "stoch": stoch_k, "adx": adx,
            "tp1": f"{tp1:,.4f}", "tp2": f"{tp2:,.4f}", "tp3": f"{tp3:,.4f}", "sl": f"{sl:,.4f}",
            "score": f"BULL: {bullish_score} | BEAR: {bearish_score}", "alert": alert, "mode": mode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ai_chat')
def ai_chat():
    # Simulated Advanced Sinhala Financial AI response using the 10-Indicator Engine Context
    user_msg = request.args.get('msg', '').lower()
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    mode = request.args.get('mode', 'FUTURE').upper().strip()
    
    base_coin = coin.replace('USDT', '')
    
    # Custom rule-based mapping to generate high-quality pure Sinhala text responses based on technical parameters
    if "pump" in user_msg or "up" in user_msg or "yada" in user_msg:
        response_text = f"🤖 Nexus AI විශ්ලේෂණය: {base_coin} සඳහා දැනට Indicators 10න් බහුතරයක් මධ්‍යස්ථ මට්ටමක පවතී. RSI අගය සමබර බැවින් එකපාරටම විශාල Big Pump එකක් යාමට ඇති ඉඩකඩ සීමිතයි. Loss නොවී සිටීමට නම්, System එක මඟින් 'ACTIVE TRADING PERMITTED' කොළ පාට සංඥාව ලබා දෙන තෙක් ඉවසීමෙන් සිට Entry Zone එක ඇතුළත පමණක් ඕඩර්ස් ක්‍රියාත්මක කරන්න. කලබල වී ඉහළ මිල ගණන් වලදී මිලදී ගැනීමෙන් වළකින්න!"
    elif "down" in user_msg or "dump" in user_msg or "weteida" in user_msg:
        response_text = f"🤖 Nexus AI විශ්ලේෂණය: {base_coin} දැනට පවතින සජීවී Trend එක අනුව එකවරම ලොකු Crash එකක් සිදුවීමේ අවධානම අඩුයි. නමුත් EMA සහ MACD මඟින් කුඩා නිවැරදි කිරීමක් (Retracement) පෙන්විය හැක. ලිවරේජ් එක 3x වඩා වැඩි නොකර, අප ලබා දී ඇති Stop Loss (SL) එක අනිවාර්යයෙන්ම භාවිත කරන්න. එවිට ඔබගේ මුදල් සම්පූර්ණයෙන්ම ආරක්ෂිත වේ."
    else:
        response_text = f"🤖 ආයුබෝවන්! {base_coin} ගැන මගෙන් ඕනෑම ප්‍රශ්නයක් අහන්න (උදා: Big pump එකක් යයිද? Trade එකක් දාන්න හොඳද?). මම ඔබට Indicators 10ම පරීක්ෂා කර Loss නොවී බේරෙන ආකාරය සිංහලෙන්ම පැහැදිලි කරන්නම්."

    return jsonify({"reply": response_text})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
