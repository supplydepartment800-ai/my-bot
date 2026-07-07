from flask import Flask, jsonify
from flask_cors import CORS
import ccxt, threading, time

app = Flask(__name__)
CORS(app)
signals = []

def analyze():
    global signals
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            markets = exchange.load_markets()
            # Futures වලින් මුල් කොයින් 15 ස්කෑන් කරනවා
            symbols = [s for s in markets if '/USDT' in s][:15] 
            temp = []
            for s in symbols:
                ticker = exchange.fetch_ticker(s)
                price = ticker['last']
                change = ticker['change'] if ticker['change'] else 0
                
                # මිල වෙනස අනුව Buy/Sell තීරණය කිරීම
                side = "BUY" if change > 0 else "SELL"
                
                # TP සහ SL ගණනය කිරීම
                if side == "BUY":
                    tp1, tp2, tp3 = round(price * 1.01, 4), round(price * 1.02, 4), round(price * 1.03, 4)
                    sl = round(price * 0.98, 4)
                else:
                    tp1, tp2, tp3 = round(price * 0.99, 4), round(price * 0.98, 4), round(price * 0.97, 4)
                    sl = round(price * 1.02, 4)
                
                temp.append({
                    "coin": s, "price": price, "signal": side,
                    "entry": price, "leverage": "10x",
                    "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl
                })
            signals = temp
        except Exception as e:
            pass
        time.sleep(30)

threading.Thread(target=analyze, daemon=True).start()

@app.route('/signals')
def get_signals(): return jsonify(signals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
