from flask import Flask, jsonify
import ccxt
import threading, time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
final_signals = []

def analyze_market():
    global final_signals
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            markets = exchange.load_markets()
            symbols = [s for s in markets if '/USDT' in s][:10] # ප්‍රධාන කොයින් 10
            temp = []
            for s in symbols:
                ticker = exchange.fetch_ticker(s)
                price = ticker['last']
                # සරල Logic: මිල වැඩි නම් BUY, අඩු නම් SELL (මෙය ඔයාට අවශ්‍ය පරිදි සංකීර්ණ කළ හැක)
                signal = "BUY" if ticker['change'] > 0 else "SELL"
                temp.append({
                    "coin": s,
                    "price": price,
                    "signal": signal,
                    "entry": price,
                    "tp1": round(price * 1.01, 2),
                    "tp2": round(price * 1.02, 2),
                    "tp3": round(price * 1.03, 2),
                    "sl": round(price * 0.98, 2),
                    "leverage": "10x"
                })
            final_signals = temp
        except: pass
        time.sleep(30)

@app.route('/signals')
def get_signals(): return jsonify(final_signals)

if __name__ == '__main__':
    threading.Thread(target=analyze_market, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
