from flask import Flask, jsonify
import threading
import time
import ccxt

app = Flask(__name__)
import yfinance as yf # මේක අලුතෙන් දාන්න

def run_bot():
    global current_signals
    while True:
        try:
            # BTC එකේ මිල ගන්නවා
            ticker = yf.Ticker("BTC-USD")
            price = ticker.history(period="1d")['Close'].iloc[-1]
            current_signals = [{"coin": "BTC/USDT", "price": round(price, 2), "signal": "BUY"}]
            print(f"Signals updated: {price}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)
current_signals = []

@app.route('/signals')
def get_signals():
    return jsonify(current_signals)

def run_bot():
    global current_signals
    while True:
        try:
            # සිග්නල් එකක් හදනවා
            ticker = exchange.fetch_ticker('BTC/USDT')
            price = ticker['last']
            current_signals = [{"coin": "BTC/USDT", "price": price, "signal": "BUY"}]
            print("Signals updated")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
