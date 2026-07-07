from flask import Flask, jsonify
import ccxt
import threading, time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
final_signals = []

def scan_market():
    global final_signals
    # Binance Futures සම්බන්ධ කිරීම
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    while True:
        try:
            markets = exchange.load_markets()
            # USDT වලින් තියෙන සියලුම Futures pairs තෝරා ගැනීම
            symbols = [s for s in markets if '/USDT' in s]
            temp_signals = []
            
            # සියලුම කොයින්ස් පරීක්ෂා කර මිල ගණන් ගැනීම
            for s in symbols[:20]: # ඕන නම් මෙතන 20 වෙනුවට 50 දාන්න පුළුවන්
                ticker = exchange.fetch_ticker(s)
                temp_signals.append({
                    "coin": s, 
                    "price": ticker['last'], 
                    "signal": "WATCH"
                })
            
            final_signals = temp_signals
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60) # විනාඩියකට සැරයක් අලුත් වෙනවා

@app.route('/signals')
def get_signals(): return jsonify(final_signals)

if __name__ == '__main__':
    threading.Thread(target=scan_market, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
