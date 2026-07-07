import os
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import threading
import time

app = Flask(__name__)
CORS(app)
signals = []

def analyze_market():
    global signals
    # ස්කෑන් කරන ප්‍රධාන Future Coins ලැයිස්තුව
    coin_map = {
        "BTC-USD": "BTC/USDT",
        "ETH-USD": "ETH/USDT",
        "SOL-USD": "SOL/USDT",
        "XRP-USD": "XRP/USDT",
        "BNB-USD": "BNB/USDT",
        "DOGE-USD": "DOGE/USDT",
        "ADA-USD": "ADA/USDT"
    }
    
    while True:
        try:
            temp = []
            for yf_symbol, display_name in coin_map.items():
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period="1d")
                
                if not hist.empty:
                    price = round(hist['Close'].iloc[-1], 4)
                    open_p = hist['Open'].iloc[-1]
                    
                    # මිල උඩ යනවා නම් BUY, පල්ලෙහාට නම් SELL
                    side = "BUY" if price >= open_p else "SELL"
                    
                    # TP සහ SL නිවැරදිව ගණනය කිරීම
                    if side == "BUY":
                        tp1 = round(price * 1.01, 2) if price > 10 else round(price * 1.01, 4)
                        tp2 = round(price * 1.02, 2) if price > 10 else round(price * 1.02, 4)
                        tp3 = round(price * 1.03, 2) if price > 10 else round(price * 1.03, 4)
                        sl = round(price * 0.98, 2) if price > 10 else round(price * 0.98, 4)
                    else:
                        tp1 = round(price * 0.99, 2) if price > 10 else round(price * 0.99, 4)
                        tp2 = round(price * 0.98, 2) if price > 10 else round(price * 0.98, 4)
                        tp3 = round(price * 0.97, 2) if price > 10 else round(price * 0.97, 4)
                        sl = round(price * 1.02, 2) if price > 10 else round(price * 1.02, 4)
                    
                    temp.append({
                        "coin": display_name, "price": price, "signal": side,
                        "entry": price, "leverage": "10x",
                        "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl
                    })
            signals = temp
            print("Signals updated successfully!")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(15) # තත්පර 15කින් නැවත අලුත් වේ

threading.Thread(target=analyze_market, daemon=True).start()

@app.route('/signals')
def get_signals():
    return jsonify(signals)

if __name__ == '__main__':
    # Railway එකට අවශ්‍ය Port එක ලබා ගැනීම
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
