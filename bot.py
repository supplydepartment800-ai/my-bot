from flask import Flask, jsonify
from flask_cors import CORS
import ccxt, threading, time

app = Flask(__name__)
CORS(app)
final_signals = []

def get_signals():
    global final_signals
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            markets = exchange.load_markets()
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT']
            temp = []
            for s in symbols:
                ticker = exchange.fetch_ticker(s)
                # සරල සිග්නල් ලොජික්
                side = "BUY" if ticker['change'] and ticker['change'] > 0 else "SELL"
                temp.append({"coin": s, "price": ticker['last'], "signal": side})
            final_signals = temp
        except: pass
        time.sleep(20)

threading.Thread(target=get_signals, daemon=True).start()

@app.route('/signals')
def signals(): return jsonify(final_signals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
