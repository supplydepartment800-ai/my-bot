import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

@app.route('/analyze')
def analyze_coin():
    # Frontend එකෙන් එවන කොයින් එක ගන්නවා (Default: BTCUSDT)
    coin = request.args.get('coin', 'BTCUSDT').upper().strip()
    
    # Yahoo Finance වලට ගැලපෙන සේ සකස් කිරීම
    yf_symbol = coin.replace('USDT', '-USD')
    if not yf_symbol.endswith('-USD'):
        yf_symbol += '-USD'

    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="1d", interval="15m") # මිනිත්තු 15ක දත්ත
        
        if hist.empty:
            hist = ticker.history(period="1d")
        if hist.empty:
            return jsonify({"error": "Coin not found"}), 404

        price = round(hist['Close'].iloc[-1], 4)
        open_p = hist['Open'].iloc[-1]
        
        # BUY හෝ SELL තීරණය කිරීම
        side = "BUY" if price >= open_p else "SELL"
        
        # 🚨 Dynamic Close Alerts (මිල වෙනස්වීම් මත ක්ලෝස් කරන්න ඇලර්ට් දීම)
        alert = "HOLDING: ට්‍රෙන්ඩ් එක ස්ථාවරයි. Target එක එනකන් ඉන්න."
        if len(hist) > 2:
            prev_price = hist['Close'].iloc[-2]
            if side == "BUY" and price < prev_price:
                alert = "⚠️ ALERT: මිල පොඩ්ඩක් බහිනවා! ලාභයක් තියෙනවා නම් දැන්ම CLOSE කරන්න, නැත්නම් SL බලාගන්න!"
            elif side == "SELL" and price > prev_price:
                alert = "⚠️ ALERT: මිල පොඩ්ඩක් ඉහළ යනවා! Reversal අවදානමක්, දැන්ම CLOSE කරන්න!"

        # TP සහ SL ගණනය කිරීම
        if side == "BUY":
            tp1 = round(price * 1.01, 2 if price > 10 else 4)
            tp2 = round(price * 1.02, 2 if price > 10 else 4)
            tp3 = round(price * 1.03, 2 if price > 10 else 4)
            sl = round(price * 0.98, 2 if price > 10 else 4)
        else:
            tp1 = round(price * 0.99, 2 if price > 10 else 4)
            tp2 = round(price * 0.98, 2 if price > 10 else 4)
            tp3 = round(price * 0.97, 2 if price > 10 else 4)
            sl = round(price * 1.02, 2 if price > 10 else 4)

        return jsonify({
            "coin": coin, "price": price, "signal": side, "entry": price,
            "leverage": "10x - 20x Max", "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "sl": sl, "alert": alert
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
