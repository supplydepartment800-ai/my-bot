import os
import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# RSI දර්ශකය ගණනය කිරීමේ ශ්‍රිතය
def calculate_rsi(df, periods=14):
    close_delta = df["Close"].diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    ma_up = up.ewm(com=periods - 1, adjust=False).mean()
    ma_down = down.ewm(com=periods - 1, adjust=False).mean()
    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))
    return rsi


@app.route("/analyze")
def analyze_coin():
    coin = request.args.get("coin", "BTCUSDT").upper().strip()

    # TradingView ටෝකන් එක Yahoo Finance එකට ගැලපෙන සේ සැකසීම
    base_coin = coin.replace("USDT", "")
    yf_symbol = f"{base_coin}-USD"

    try:
        ticker = yf.Ticker(yf_symbol)
        # දින ගණන් හෝල්ඩ් කරන සිග්නල් සඳහා පැයක (1h) දත්ත ලබා ගැනීම
        hist = ticker.history(period="1mo", interval="1h")

        if hist.empty or len(hist) < 50:
            hist = ticker.history(period="3mo", interval="1d")

        if hist.empty:
            return (
                jsonify(
                    {
                        "error": "Coin not found. Please use standard symbols like BTCUSDT"
                    }
                ),
                404,
            )

        price = round(hist["Close"].iloc[-1], 4)

        # --- තාක්ෂණික දර්ශක ගණනය කිරීම (Technical Indicators) ---
        hist["RSI"] = calculate_rsi(hist)
        current_rsi = round(hist["RSI"].iloc[-1], 2)

        hist["SMA20"] = hist["Close"].rolling(window=20).mean()
        hist["SMA50"] = hist["Close"].rolling(window=50).mean()
        sma20 = hist["SMA20"].iloc[-1]
        sma50 = hist["SMA50"].iloc[-1]

        # මුලින්ම Default Signals සකස් කිරීම
        side = "WAIT / NO SIGNAL"
        entry_zone = "පැහැදිලි රටාවක් නොමැත"
        tp1, tp2, tp3, sl = 0, 0, 0, 0
        alert = "📊 දර්ශක විශ්ලේෂණය කරමින් පවතී... ස්ථාවර Trend එකක් එනකන් ඉවසන්න."

        # --- MULTI-INDICATOR SWING LOGIC ---
        # 1. strong BUY LIMIT Logic (රේට් එක පොඩ්ඩක් පල්ලෙහාට ආවම ගන්න)
        if price > sma50 and current_rsi > 45:
            side = "BUY LIMIT (LONG)"
            # දැන් යන මිලට වඩා 0.5% - 1.5% ක් අතර අඩුවෙන් එන්ට්‍රි කලාපය හැදීම
            entry_low = round(price * 0.985, 4)
            entry_high = round(price * 0.995, 4)
            entry_zone = f"{entry_low} - {entry_high}"

            # දවස් ගණන් හෝල්ඩ් කර ලොකු ප්‍රොෆිට් ගන්නා Target Points (3%, 6%, 12%)
            tp1 = round(price * 1.03, 4)
            tp2 = round(price * 1.06, 4)
            tp3 = round(price * 1.12, 4)
            sl = round(entry_low * 0.96, 4)  # Safe SL
            alert = "🔥 <b>STRONG BULLISH TREND:</b> දින කිහිපයක් හෝල්ඩ් කර ලොකු ප්‍රොෆිට් එකක් ගත හැක. දැන්ම මාකට් ප්‍රයිස් එකෙන් ගන්න එපා, Entry Zone එකට එනකන් ඉන්න."

        # 2. strong SELL LIMIT Logic
        elif price < sma50 and current_rsi < 55:
            side = "SELL LIMIT (SHORT)"
            entry_low = round(price * 1.005, 4)
            entry_high = round(price * 1.015, 4)
            entry_zone = f"{entry_low} - {entry_high}"

            tp1 = round(price * 0.97, 4)
            tp2 = round(price * 0.94, 4)
            tp3 = round(price * 0.88, 4)
            sl = round(entry_high * 1.04, 4)
            alert = "📉 <b>BEARISH TREND DETECTED:</b> මාකට් එක පහළට යාමට වැඩි ඉඩක් ඇත. Entry Zone එකෙන් Short ඕඩරයක් සෙට් කරගන්න."

        # Indicators එකිනෙකට පටහැනි නම් (No clear trend)
        if pd.isna(current_rsi) or side == "WAIT / NO SIGNAL":
            side = "WAIT / NO SIGNAL"
            entry_zone = "No Trade Zone"
            alert = "⚠️ <b>අවදානම වැඩියි:</b> Indicators පටලැවිලි සහගතයි. පොඩි වොලට් එකක් ඇති අය මේ මොහොතේ ට්‍රේඩ් එකකට යාමෙන් වළකින්න!"

        return jsonify(
            {
                "coin": coin,
                "price": price,
                "signal": side,
                "entry_zone": entry_zone,
                "leverage": "3x - 5x (Safe For Small Wallets)",
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "rsi": current_rsi,
                "sma": "UP TREND" if price > sma50 else "DOWN TREND",
                "alert": alert,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
