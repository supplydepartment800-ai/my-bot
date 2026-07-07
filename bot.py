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
            symbols = [s for s in markets if '/USDT' in s][:10]
            new_signals = []
            for s in symbols:
                ticker = exchange.fetch_ticker(s)
                price = ticker['last']
                # මෙතන සරල RSI වගේ logic එකක් තියෙනවා කියලා හිතන්න (මෙය උදාහරණයක්)
                side = "BUY" if ticker['change'] > 0 else "SELL"
                new_signals.append({
                    "coin": s, "price": price, "signal": side,
                    "entry": price, "leverage": "10x",
                    "tp1": round(price * 1.01, 2), "tp2": round(price * 1.02, 2), 
                    "tp3": round(price * 1.03, 2), "sl": round(price * 0.98, 2)
                })
            signals = new_signals
        except: pass
        time.sleep(30)

@app.route('/signals')
def get_signals(): return jsonify(signals)

if __name__ == '__main__':
    threading.Thread(target=analyze, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
