import time
import urllib.request
import json
from datetime import datetime

BOT_TOKEN = ‘8590098793:AAGTbi0G8PQHvaIgQJgeQbaF8rTKiw7Ayow’
CHAT_ID = ‘8028512511’
TWELVE_KEY = ‘6aa3f263137b4734ab26435c88146036’
CHECK_INTERVAL = 60

PAIRS = [
‘EUR/USD’,‘GBP/USD’,‘USD/JPY’,‘AUD/USD’,‘USD/CAD’,
‘USD/CHF’,‘NZD/USD’,‘EUR/GBP’,‘EUR/JPY’,‘GBP/JPY’,
‘AUD/JPY’,‘EUR/AUD’,‘XAU/USD’,
]

last_signals = {}

def send_tg(msg):
url = ‘https://api.telegram.org/bot’ + BOT_TOKEN + ‘/sendMessage’
data = json.dumps({‘chat_id’: CHAT_ID, ‘text’: msg}).encode()
try:
req = urllib.request.Request(url, data, {‘Content-Type’: ‘application/json’})
urllib.request.urlopen(req, timeout=10)
print(’TG sent: ’ + msg[:50])
except Exception as e:
print(’TG error: ’ + str(e))

def get_candles(symbol, n=60):
sym = symbol.replace(’/’, ‘’)
url = (‘https://api.twelvedata.com/time_series?symbol=’ + sym +
‘&interval=1min&outputsize=’ + str(n) +
‘&apikey=’ + TWELVE_KEY)
try:
res = urllib.request.urlopen(url, timeout=10)
data = json.loads(res.read())
if ‘values’ not in data:
print(’No data ’ + symbol + ’: ’ + str(data.get(‘message’, ‘’)))
return None
candles = []
for v in reversed(data[‘values’]):
candles.append({
‘o’: float(v[‘open’]),
‘h’: float(v[‘high’]),
‘l’: float(v[‘low’]),
‘c’: float(v[‘close’]),
})
return candles
except Exception as e:
print(’API error ’ + symbol + ’: ’ + str(e))
return None

def ema(prices, period):
k = 2.0 / (period + 1)
e = prices[0]
result = [e]
for p in prices[1:]:
e = p * k + e * (1 - k)
result.append(e)
return result

def sma(prices, period):
result = []
for i in range(len(prices)):
if i < period - 1:
result.append(None)
else:
result.append(sum(prices[i-period+1:i+1]) / period)
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

def calc_macd(closes):
fast = ema(closes, 12)
slow = ema(closes, 26)
line = [fast[i] - slow[i] for i in range(len(fast))]
sig = ema(line, 9)
hist = [line[i] - sig[i] for i in range(len(line))]
return line, sig, hist

def find_pivots(candles, left=3, right=3):
highs = [c[‘h’] for c in candles]
lows = [c[‘l’] for c in candles]
ph, pl = [], []
for i in range(left, len(candles) - right):
if all(highs[i] >= highs[i-j] for j in range(1, left+1)) and   
all(highs[i] >= highs[i+j] for j in range(1, right+1)):
ph.append((i, highs[i]))
if all(lows[i] <= lows[i-j] for j in range(1, left+1)) and   
all(lows[i] <= lows[i+j] for j in range(1, right+1)):
pl.append((i, lows[i]))
return ph, pl

def analyze(candles):
n = len(candles) - 1
closes = [c[‘c’] for c in candles]
highs = [c[‘h’] for c in candles]
lows = [c[‘l’] for c in candles]

```
e8 = ema(closes, 8)
e21 = ema(closes, 21)
e50 = ema(closes, 50)
t_up = e8[n] > e21[n] and e21[n] > e50[n] and closes[n] > e8[n]
t_dn = e8[n] < e21[n] and e21[n] < e50[n] and closes[n] < e8[n]

rv = calc_rsi(closes, 14)
r_up = rv > 52
r_dn = rv < 48
r_ob = rv > 78
r_os = rv < 22

line, sig, hist = calc_macd(closes)
m_up = line[n] > sig[n] and hist[n] > hist[n-1]
m_dn = line[n] < sig[n] and hist[n] < hist[n-1]

bb_mid = sma(closes, 20)
bm = bb_mid[n] if bb_mid[n] is not None else closes[n]
b_up = closes[n] > bm
b_dn = closes[n] < bm

cur = candles[n]
prv = candles[n-1]
body = abs(cur['c'] - cur['o'])
uw = cur['h'] - max(cur['c'], cur['o'])
dw = min(cur['c'], cur['o']) - cur['l']
eg_up = cur['c'] > cur['o'] and cur['c'] > prv['h'] and cur['o'] < prv['l']
eg_dn = cur['c'] < cur['o'] and cur['c'] < prv['l'] and cur['o'] > prv['h']
pin_up = dw > body * 2 and dw > uw * 2
pin_dn = uw > body * 2 and uw > dw * 2

pv_up = lows[n] > lows[n-1] and lows[n-1] > lows[n-2] and cur['c'] > cur['o']
pv_dn = highs[n] < highs[n-1] and highs[n-1] < highs[n-2] and cur['c'] < cur['o']

hi9 = max(highs[n-8:n+1])
lo9 = min(lows[n-8:n+1])
hi26 = max(highs[max(0, n-25):n+1])
lo26 = min(lows[max(0, n-25):n+1])
tk = (hi9 + lo9) / 2
kj = (hi26 + lo26) / 2
i_up = closes[n] > tk and tk > kj
i_dn = closes[n] < tk and tk < kj

ph, pl = find_pivots(candles)
w_bull = 0
w_bear = 0
wave_pos = 'No Pattern'

if len(pl) >= 3 and len(ph) >= 2:
    w1s = pl[-3][1]; w1e = ph[-2][1]
    w2e = pl[-2][1]; w3e = ph[-1][1]
    w4e = pl[-1][1] if len(pl) >= 1 else None
    w1 = w1e - w1s; w2 = w1e - w2e; w3 = w3e - w2e
    if w2e > w1s: w_bull += 2
    if w3 > w1: w_bull += 2
    if w3 > w2: w_bull += 1
    if w4e and w4e > w1e: w_bull += 2
    if closes[n] > w3e:
        w_bull += 1; wave_pos = 'Wave 5 UP'
    elif w4e and closes[n] > w4e:
        w_bull += 1; wave_pos = 'Wave 4to5 UP'

if len(ph) >= 3 and len(pl) >= 2:
    w1s = ph[-3][1]; w1e = pl[-2][1]
    w2e = ph[-2][1]; w3e = pl[-1][1]
    w4e = ph[-1][1] if len(ph) >= 1 else None
    w1 = w1s - w1e; w2 = w2e - w1e; w3 = w2e - w3e
    if w2e < w1s: w_bear += 2
    if w3 > w1: w_bear += 2
    if w3 > w2: w_bear += 1
    if w4e and w4e < w1e: w_bear += 2
    if closes[n] < w3e:
        w_bear += 1; wave_pos = 'Wave 5 DN'
    elif w4e and closes[n] < w4e:
        w_bear += 1; wave_pos = 'Wave 4to5 DN'

bs = 0
bes = 0
if t_up: bs += 2
if t_dn: bes += 2
if r_up: bs += 1
if r_dn: bes += 1
if m_up: bs += 1
if m_dn: bes += 1
if b_up: bs += 1
if b_dn: bes += 1
if eg_up: bs += 1
if eg_dn: bes += 1
if pin_up: bs += 1
if pin_dn: bes += 1
if pv_up: bs += 1
if pv_dn: bes += 1
if i_up: bs += 2
if i_dn: bes += 2
if w_bull >= 4: bs += 2
if w_bear >= 4: bes += 2

call_ok = bs >= 6 and t_up and r_up and m_up and not r_ob
put_ok = bes >= 6 and t_dn and r_dn and m_dn and not r_os

return call_ok, put_ok, bs, bes, rv, wave_pos
```

def run():
print(‘Elliott Wave + Binary Pro Max BOT started!’)
send_tg(
‘ELLIOTT WAVE + BINARY PRO MAX BOT started!\n\n’
‘Real-Time price from Twelve Data\n’
‘Scanning every 60 seconds\n’
‘Pairs: ’ + str(len(PAIRS)) + ’ pairs’
)

```
while True:
    now = datetime.now().strftime('%H:%M:%S')
    print(now + ' Scanning...')

    for symbol in PAIRS:
        try:
            candles = get_candles(symbol, 60)
            if not candles or len(candles) < 30:
                time.sleep(1)
                continue

            price = candles[-1]['c']
            call_ok, put_ok, bs, bes, rv, wave_pos = analyze(candles)
            dp = 3 if 'JPY' in symbol else (1 if 'XAU' in symbol else 5)
            key = symbol.replace('/', '')

            if call_ok and last_signals.get(key) != 'CALL':
                msg = (
                    'CALL SIGNAL UP\n\n'
                    'Pair: ' + symbol + '\n'
                    'Price: ' + str(round(price, dp)) + '\n'
                    'Score: ' + str(bs) + '/16\n'
                    'RSI: ' + str(round(rv, 1)) + '\n'
                    'Wave: ' + wave_pos + '\n'
                    'Time: ' + now + '\n\n'
                    'Enter next candle!\n'
                    'ELLIOTT WAVE + BINARY PRO MAX V4'
                )
                send_tg(msg)
                last_signals[key] = 'CALL'

            elif put_ok and last_signals.get(key) != 'PUT':
                msg = (
                    'PUT SIGNAL DOWN\n\n'
                    'Pair: ' + symbol + '\n'
                    'Price: ' + str(round(price, dp)) + '\n'
                    'Score: ' + str(bes) + '/16\n'
                    'RSI: ' + str(round(rv, 1)) + '\n'
                    'Wave: ' + wave_pos + '\n'
                    'Time: ' + now + '\n\n'
                    'Enter next candle!\n'
                    'ELLIOTT WAVE + BINARY PRO MAX V4'
                )
                send_tg(msg)
                last_signals[key] = 'PUT'

            elif not call_ok and not put_ok:
                last_signals[key] = ''

            time.sleep(2)

        except Exception as e:
            print('Error ' + symbol + ': ' + str(e))
            continue

    print('Next scan in ' + str(CHECK_INTERVAL) + 's')
    time.sleep(CHECK_INTERVAL)
```

if **name** == ‘**main**’:
run()