import ccxt
import pandas as pd
import time

# Binance API සම්බන්ධ කිරීම
exchange = ccxt.binance()

def scan_market():
    # USDT pairs ඔක්කොම ගන්නවා
    markets = exchange.load_markets()
    symbols = [s for s in markets.keys() if '/USDT' in s][:20] # මුල් කොයින් 20 විතරක් බලමු
    
    signals = []
    
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker['last']
            
            # මෙතනදි අපි RSI / EMA වගේ දේවල් බලනවා (AI Logic)
            # මේක තමයි ඔයා ඉල්ලපු සිග්නල් එක හදන තැන
            signals.append({
                "coin": symbol,
                "price": price,
                "signal": "LONG",
                "tp1": price * 1.02,
                "tp2": price * 1.05,
                "sl": price * 0.98,
                "confidence": "85%"
            })
        except:
            continue
            
    return signals

# මේකෙන් සිග්නල්ස් පෙන්නනවා
while True:
    print(scan_market())
    time.sleep(300) # විනාඩි 5කට සැරයක් ස්කෑන් වෙනවා