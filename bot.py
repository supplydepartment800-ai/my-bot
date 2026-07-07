from flask import Flask, jsonify
import threading
import time
import yfinance as yf

app = Flask(__name__)
current_signals = []

@app.route('/signals')
def get_signals():
    return jsonify(current_signals)

def run_bot():
    global current_signals
    while True:
        try:
            # BTC මිල ගැනීම
            ticker = yf.Ticker("BTC-USD")
            data = ticker.history(period="1d")
            if not data.empty:
                price = data['Close'].iloc[-1]
                current_signals = [{"coin": "BTC/USDT", "price": round(price, 2), "signal": "BUY"}]
                print(f"Signals updated: {price}")
            else:
                print("No data received")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(60)

if __name__ == '__main__':
    # Thread එක ආරම්භ කිරීම
    threading.Thread(target=run_bot, daemon=True).start()
    # Flask app එක run කිරීම
    app.run(host='0.0.0.0', port=8080)
