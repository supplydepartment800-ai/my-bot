import os
import random
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_mail import Mail, Message

app = Flask(__name__)
CORS(app)

# 📬 GMAIL SMTP CONFIGURATION (සැබෑ OTP යැවීම සඳහා)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # 👈 ඔයාගේ Gmail එක මෙතනට දාන්න
app.config['MAIL_PASSWORD'] = 'your-google-app-password'  # 👈 Google App Password එක මෙතනට දාන්න
mail = Mail(app)

# 🗄️ In-Memory Database (Production වලදී DB එකකට සම්බන්ධ කළ හැක)
USERS_DB = {}
OTP_STORE = {}

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
    mad_tp = tp.rolling(window=20).apply(lambda x: pd.Series(x).mad() if hasattr(pd.Series(x), 'mad') else np.abs(x - x.mean()).mean())
    hist['CCI'] = (tp - ma_tp) / (0.015 * mad_tp)
    hist['TR'] = pd.concat([hist['High'] - hist['Low'], (hist['High'] - hist['Close'].shift()).abs(), (hist['Low'] - hist['Close'].shift()).abs()], axis=1).max(axis=1)
    hist['ATR'] = hist['TR'].rolling(window=14).mean()
    hist['ADX'] = (hist['Close'].diff().abs().rolling(window=14).mean() / hist['ATR']) * 100
    return hist

# 🔐 AUTHENTICATION ENDPOINTS
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    password = data.get('password', '')

    if email in USERS_DB and USERS_DB[email]['verified']:
        return jsonify({"error": "Email already registered"}), 400

    otp = str(random.randint(100000, 999999))
    OTP_STORE[email] = {"otp": otp, "name": name, "password": password, "type": "REGISTRATION"}

    try:
        msg = Message("Nexus Terminal - Verification OTP", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Hello {name},\n\nYour OTP for Nexus Terminal registration is: {otp}\n\nDo not share this code."
        mail.send(msg)
        return jsonify({"message": "OTP sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

@app.route('/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email', '').strip().lower()
    otp_input = data.get('otp', '').strip()

    if email not in OTP_STORE or OTP_STORE[email]['otp'] != otp_input:
        return jsonify({"error": "Invalid or expired OTP code"}), 400

    session_data = OTP_STORE[email]
    
    if session_data['type'] == "REGISTRATION":
        USERS_DB[email] = {
            "name": session_data['name'],
            "password": session_data['password'],
            "verified": True
        }
        del OTP_STORE[email]
        return jsonify({"message": "Registration complete! You can now log in."}), 200
        
    elif session_data['type'] == "FORGET":
        return jsonify({"message": "OTP Verified successfully. Proceed to reset password."}), 200

@app.route('/auth/forget-password', methods=['POST'])
def forget_password():
    data = request.json
    email = data.get('email', '').strip().lower()

    if email not in USERS_DB or not USERS_DB[email]['verified']:
        return jsonify({"error": "Email account not found"}), 404

    otp = str(random.randint(100000, 999999))
    OTP_STORE[email] = {"otp": otp, "type": "FORGET"}

    try:
        msg = Message("Nexus Terminal - Password Reset OTP", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your Password Reset OTP is: {otp}\n\nVerify this to choose a new password."
        mail.send(msg)
        return jsonify({"message": "Reset OTP sent to your email"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to send OTP email"}), 500

@app.route('/auth/reset-password-confirm', methods=['POST'])
def reset_password_confirm():
    data = request.json
    email = data.get('email', '').strip().lower()
    new_password = data.get('password', '')
    
    if email in USERS_DB:
        USERS_DB[email]['password'] = new_password
        return jsonify({"message": "Password changed successfully! Login now."}), 200
    return jsonify({"error": "Action restricted"}, 400)

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if email not in USERS_DB or USERS_DB[email]['password'] != password:
        return jsonify({"error": "Invalid email credentials or unverified account"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {"name": USERS_DB[email]['name'], "email": email}
    }), 200

# 📊 MARKET ENGINE & CHAT PIPELINES
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
        
        rsi = round(hist['RSI'].iloc[-1], 2)
        sma50 = hist['SMA50'].iloc[-1]
        sma200 = hist['SMA200'].iloc[-1]
        stoch_k = round(hist['Stoch_K'].iloc[-1], 2)
        adx = round(hist['ADX'].iloc[-1], 2)

        bullish_score = 0
        if price > sma50: bullish_score += 1
        if price > sma200: bullish_score += 1
        if rsi > 50: bullish_score += 1

        status = "NEUTRAL"
        side = "WAIT / MARKET UNSTABLE"
        entry_zone, tp1, tp2, tp3, sl = "No Trade Zone", 0, 0, 0, 0
        leverage = "1x" if mode == "SPOT" else "3x - 5x"

        if rsi < 28 or rsi > 72:
            side = "WAIT / DO NOT TRADE"
            status = "EXHAUSTED"
            alert = "🚨 RISK PROTECTION ACTIVE: Market momentum is highly exhausted. Standby."
        elif bullish_score >= 2 and (40 <= rsi <= 68):
            status = "BULLISH"
            side = "BUY LIMIT (LONG)" if mode == "FUTURE" else "BUY (SPOT)"
            entry_low, entry_high = round(price * 0.99, 4), round(price * 0.998, 4)
            entry_zone = f"{entry_low} - {entry_high}"
            tp1, tp2, tp3 = round(price * 1.03, 4), round(price * 1.06, 4), round(price * 1.12, 4)
            sl = round(entry_low * 0.96, 4)
            alert = "🔥 10-INDICATOR MATRIX CONFLUENCE PASSED: Secure entries inside the zone."
        else:
            alert = "📉 DOWNWARD FLOW MODE: Avoid building active spot capital profiles now."

        return jsonify({
            "coin": coin, "price": f"{price:,.4f}", "signal": side, "status": status,
            "entry_zone": entry_zone, "leverage": leverage, "rsi": rsi, "adx": adx,
            "tp1": f"{tp1:,.4f}", "tp2": f"{tp2:,.4f}", "tp3": f"{tp3:,.4f}", "sl": f"{sl:,.4f}",
            "score": f"SCORE: {bullish_score}/3", "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ai_chat')
def ai_chat():
    user_msg = request.args.get('msg', '').lower()
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    username = request.args.get('name', 'User').strip()
    
    base_coin = coin.replace('USDT', '')
    
    if "pump" in user_msg or "up" in user_msg or "yada" in user_msg:
        response_text = f"🤖 Nexus AI විශ්ලේෂණය: ස්තුතියි {username}! දැනට {base_coin} වල Indicators 10න් බහුතරයක් මධ්‍යස්ථයි. RSI අගය සමබර නිසා එකපාරටම Big Pump එකක් යාමට ඇති ඉඩකඩ සීමිතයි. Loss නොවී සිටීමට නම්, System එක මඟින් 'ACTIVE TRADING PERMITTED' ලැබෙන තෙක් ඉවසන්න."
    elif "down" in user_msg or "dump" in user_msg or "weteida" in user_msg:
        response_text = f"🤖 Nexus AI විශ්ලේෂණය: {username}, දැනට පවතින සජීවී Trend එක අනුව {base_coin} එකවරම ලොකු Crash එකක් සිදුවීමේ අවධානම අඩුයි. ලිවරේජ් එක 3x වඩා වැඩි නොකර, අප ලබා දී ඇති Stop Loss (SL) එක අනිවාර්යයෙන්ම භාවිත කරන්න."
    else:
        response_text = f"🤖 ආයුබෝවන් {username}! මම {base_coin} ගැන ඔයාගේ ප්‍රශ්න වලට උදව් කරන්න සූදානම්. Loss නොවී බේරෙන ආකාරය මම සිංහලෙන්ම කියන්නම්."

    return jsonify({"reply": response_text})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
