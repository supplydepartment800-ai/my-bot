from flask import Flask, jsonify
from flask_cors import CORS # මේක අනිවාර්යයි
import ccxt, threading, time

app = Flask(__name__)
CORS(app) # මේක තමයි ඔයාගේ බ්‍රව්සරයට දත්ත එන්න ඉඩ දෙන්නේ
signals = []

def analyze():
    global signals
    try:
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker('BTC/USDT')
        signals = [{
            "coin": "BTC/USDT", 
            "price": ticker['last'], 
            "signal": "BUY",
            "entry": ticker['last'],
            "tp1": round(ticker['last'] * 1.01, 2),
            "sl": round(ticker['last'] * 0.99, 2)
        }]
    except: pass
    time.sleep(10)

threading.Thread(target=analyze, daemon=True).start()

@app.route('/signals')
def get_signals(): return jsonify(signals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
