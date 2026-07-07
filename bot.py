import ccxt
import time

# Public Data විතරක් ගන්න නිසා Keys ඕනේ නැහැ
exchange = ccxt.binance()

def scan():
    print("Scanning market...")
    try:
        # BTC සහ ETH වගේ ජනප්‍රිය කොයින්ස් ටිකක් බලමු
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        for s in symbols:
            ticker = exchange.fetch_ticker(s)
            print(f"{s}: {ticker['last']}")
    except Exception as e:
        print(f"Error: {e}")

while True:
    scan()
    time.sleep(60) # විනාඩියකට සැරයක් වැඩ කරනවා
