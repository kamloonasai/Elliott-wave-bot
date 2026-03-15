import time
import urllib.request
import json
import os
from datetime import datetime

BOT_TOKEN = os.environ.get(“TELEGRAM_TOKEN”, “”)
CHAT_ID = os.environ.get(“CHAT_ID”, “”)
TWELVE_KEY = os.environ.get(“TWELVE_API_KEY”, “”)
CHECK_INTERVAL = 60

PAIRS = [
“EUR/USD”,“GBP/USD”,“USD/JPY”,“AUD/USD”,“USD/CAD”,
“USD/CHF”,“NZD/USD”,“EUR/GBP”,“EUR/JPY”,“GBP/JPY”,
“AUD/JPY”,“EUR/AUD”,“XAU/USD”,
]

last_signals = {}

def send_tg(msg):
url = “https://api.telegram.org/bot” + BOT_TOKEN + “/sendMessage”
data = json.dumps({“chat_id”: CHAT_ID, “text”: msg}).encode()
try:
req = urllib.request.Request(url, data, {“Content-Type”: “application/json”})
urllib.request.urlopen(req, timeout=10)
print(“TG sent OK”)
except Exception as e:
print(“TG error: “ + str(e))

def get_candles(symbol, n=60):
sym = symbol.replace(”/”, “”)
url = (“https://api.twelvedata.com/time_series?symbol=” + sym +
“&interval=1min&outputsize=” + str(n) +
“&apikey=” + TWELVE_KEY)
try:
res = urllib.request.urlopen(url, timeout=10)
data = json.loads(res.read())
if “values” not in data:
print(“No data “ + symbol)
return None
candles = []
for v in reversed(data[“values”]):
candles.append({
“o”: float(v[“open”]),
“h”: float(v[“high”]),
“l”: float(v[“low”]),
“c”: float(v[“close”]),
})
return candles
except Exception as e:
print(“API error “ + symbol + “: “ + str(e))
return None

def ema(prices, period):
k = 2.0 / (period + 1)
e = prices[0]
result = [e]
for p in prices[1:]:
e = p * k + e * (1 - k)
result.append(e)
return result

def calc_rsi(closes, period=14):
gains = 0.0
losses = 0.0
for i in range(1, period + 1):
d = closes[i] - closes[i-1]
if d > 0:
gains += d
else:
losses -= d
ag = gains / period
al = losses / period
for i in range(period + 1, len(closes)):
d = closes[i] - closes[i-1]
ag = (ag * (period - 1) + max(d, 0)) / period
al = (al * (period - 1) + max(-d, 0)) / period
rs = ag / (al if al > 0 else 1e-9)
return 100 - (100 / (1 + rs))

def find_pivots(candles, left=3, right=3):
highs = [c[“h”] for c in candles]
lows = [c[“l”] for c in candles]
ph = []
pl = []
for i in range(left, len(candles) - right):
if all(highs[i] >= highs[i-j] for j in range(1, left+1)) and all(highs[i] >= highs[i+j] for j in range(1, right+1)):
ph.append((i, highs[i]))
if all(lows[i] <= lows[i-j] for j in range(1, left+1)) and all(lows[i] <= lows[i+j] for j in range(1, right+1)):
pl.append((i, lows[i]))
return ph, pl

def detect_wave(candles):
closes = [c[“c”] for c in candles]
ph, pl = find_pivots(candles)
bull = 0
bear = 0
wave_pos = “No Pattern”

```
if len(pl) >= 3 and len(ph) >= 2:
    w1s = pl[-3][1]
    w1e = ph[-2][1]
    w2e = pl[-2][1]
    w3e = ph[-1][1]
    w4e = pl[-1][1] if len(pl) >= 1 else None
    w1 = w1e - w1s
    w2 = w1e - w2e
    w3 = w3e - w2e
    if w2e > w1s:
        bull += 2
    if w3 > w1:
        bull += 2
    if w3 > w2:
        bull += 1
    if w4e and w4e > w1e:
        bull += 2
    if closes[-1] > w3e:
        bull += 1
        wave_pos = "Wave 5 UP"
    elif w4e and closes[-1] > w4e:
        bull += 1
        wave_pos = "Wave 4-5 UP"

if len(ph) >= 3 and len(pl) >= 2:
    w1s = ph[-3][1]
    w1e = pl[-2][1]
    w2e = ph[-2][1]
    w3e = pl[-1][1]
    w4e = ph[-1][1] if len(ph) >= 1 else None
    w1 = w1s - w1e
    w2 = w2e - w1e
    w3 = w2e - w3e
    if w2e < w1s:
        bear += 2
    if w3 > w1:
        bear += 2
    if w3 > w2:
        bear += 1
    if w4e and w4e < w1e:
        bear += 2
    if closes[-1] < w3e:
        bear += 1
        wave_pos = "Wave 5 DN"
    elif w4e and closes[-1] < w4e:
        bear += 1
        wave_pos = "Wave 4-5 DN"

return bull, bear, wave_pos
```

def analyze(candles):
n = len(candles) - 1
closes = [c[“c”] for c in candles]
highs = [c[“h”] for c in candles]
lows = [c[“l”] for c in candles]

```
e8 = ema(closes, 8)
e21 = ema(closes, 21)
t_up = e8[n] > e21[n] and closes[n] > e8[n]
t_dn = e8[n] < e21[n] and closes[n] < e8[n]

rv = calc_rsi(closes, 14)
r_up = rv > 52
r_dn = rv < 48
r_ob = rv > 78
r_os = rv < 22

wb, wbe, wave_pos = detect_wave(candles)

call_ok = t_up and r_up and not r_ob and wb >= 4
put_ok = t_dn and r_dn and not r_os and wbe >= 4

return call_ok, put_ok, wb, wbe, rv, wave_pos
```

def run():
print(“Elliott Wave Bot started!”)
send_tg(
“ELLIOTT WAVE BOT started!

“
“Real-Time from Twelve Data
“
“Scanning “ + str(len(PAIRS)) + “ pairs every 60s”
)

```
while True:
    now = datetime.now().strftime("%H:%M:%S")
    print(now + " Scanning...")

    for symbol in PAIRS:
        try:
            candles = get_candles(symbol, 60)
            if not candles or len(candles) < 30:
                time.sleep(1)
                continue

            price = candles[-1]["c"]
            call_ok, put_ok, wb, wbe, rv, wave_pos = analyze(candles)
            dp = 3 if "JPY" in symbol else (1 if "XAU" in symbol else 5)
            key = symbol.replace("/", "")

            if call_ok and last_signals.get(key) != "CALL":
                msg = (
                    "ELLIOTT WAVE - CALL UP
```

“
“Pair: “ + symbol + “
“
“Price: “ + str(round(price, dp)) + “
“
“Wave: “ + wave_pos + “
“
“Wave Score: “ + str(wb) + “/8
“
“RSI: “ + str(round(rv, 1)) + “
“
“Time: “ + now + “

“
“Enter next candle!”
)
send_tg(msg)
last_signals[key] = “CALL”
print(“CALL: “ + symbol)

```
            elif put_ok and last_signals.get(key) != "PUT":
                msg = (
                    "ELLIOTT WAVE - PUT DOWN
```

“
“Pair: “ + symbol + “
“
“Price: “ + str(round(price, dp)) + “
“
“Wave: “ + wave_pos + “
“
“Wave Score: “ + str(wbe) + “/8
“
“RSI: “ + str(round(rv, 1)) + “
“
“Time: “ + now + “

“
“Enter next candle!”
)
send_tg(msg)
last_signals[key] = “PUT”
print(“PUT: “ + symbol)

```
            elif not call_ok and not put_ok:
                last_signals[key] = ""

            time.sleep(2)

        except Exception as e:
            print("Error " + symbol + ": " + str(e))
            continue

    print("Next scan in " + str(CHECK_INTERVAL) + "s")
    time.sleep(CHECK_INTERVAL)
```

if **name** == “**main**”:
run()
