import time
import urllib.request
import json
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
TWELVE_KEY = os.environ.get("TWELVE_API_KEY", "")
CHECK_INTERVAL = 60

PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
    "USD/CHF","NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY",
    "AUD/JPY","EUR/AUD","EUR/CHF","GBP/CHF","CAD/JPY",
    "AUD/CAD","AUD/CHF","AUD/NZD","CAD/CHF","CHF/JPY",
    "EUR/NZD","GBP/AUD","GBP/CAD","GBP/NZD","NZD/CAD",
    "NZD/CHF","NZD/JPY","EUR/CAD","XAU/USD","XAG/USD",
]

last_signals = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode()
    try:
        req = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_candles(symbol, outputsize=100):
    sym = symbol.replace("/", "")
    url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1min&outputsize={outputsize}&apikey={TWELVE_KEY}"
    try:
        res = urllib.request.urlopen(url, timeout=10)
        data = json.loads(res.read())
        if "values" not in data:
            print(f"No data {symbol}: {data.get('message','')}")
            return None
        candles = []
        for v in reversed(data["values"]):
            candles.append({
                "o": float(v["open"]),
                "h": float(v["high"]),
                "l": float(v["low"]),
                "c": float(v["close"]),
            })
        return candles
    except Exception as e:
        print(f"API Error {symbol}: {e}")
        return None

def ema(prices, period):
    k = 2 / (period + 1)
    e = prices[0]
    result = [e]
    for p in prices[1:]:
        e = p * k + e * (1 - k)
        result.append(e)
    return result

def calc_rsi(closes, period=14):
    gains, losses = 0, 0
    for i in range(1, period + 1):
        d = closes[i] - closes[i-1]
        if d > 0: gains += d
        else: losses -= d
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i-1]
        avg_gain = (avg_gain * (period-1) + max(d, 0)) / period
        avg_loss = (avg_loss * (period-1) + max(-d, 0)) / period
    rs = avg_gain / (avg_loss if avg_loss > 0 else 1e-9)
    return 100 - (100 / (1 + rs))

def find_pivots(candles, left=3, right=3):
    highs = [c["h"] for c in candles]
    lows  = [c["l"] for c in candles]
    pivot_highs, pivot_lows = [], []
    for i in range(left, len(candles) - right):
        if all(highs[i] >= highs[i-j] for j in range(1, left+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, right+1)):
            pivot_highs.append((i, highs[i]))
        if all(lows[i] <= lows[i-j] for j in range(1, left+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, right+1)):
            pivot_lows.append((i, lows[i]))
    return pivot_highs, pivot_lows

def detect_elliott_wave(candles):
    ph, pl = find_pivots(candles)
    closes = [c["c"] for c in candles]
    n = len(candles) - 1
    bull_score, bear_score, wave_pos = 0, 0, "No Pattern"

    if len(pl) >= 3 and len(ph) >= 2:
        w1_start = pl[-3][1]; w1_end = ph[-2][1]
        w2_end = pl[-2][1];   w3_end = ph[-1][1]
        w4_end = pl[-1][1] if len(pl) >= 1 else None
        w1 = w1_end - w1_start; w2 = w1_end - w2_end; w3 = w3_end - w2_end
        if w2_end > w1_start: bull_score += 2
        if w3 > w1:           bull_score += 2
        if w3 > w2:           bull_score += 1
        if w4_end and w4_end > w1_end: bull_score += 2
        if closes[n] > w3_end:
            bull_score += 1; wave_pos = "Wave 5 🚀"
        elif w4_end and closes[n] > w4_end:
            bull_score += 1; wave_pos = "Wave 4→5 📈"

    if len(ph) >= 3 and len(pl) >= 2:
        w1_start = ph[-3][1]; w1_end = pl[-2][1]
        w2_end = ph[-2][1];   w3_end = pl[-1][1]
        w4_end = ph[-1][1] if len(ph) >= 1 else None
        w1 = w1_start - w1_end; w2 = w2_end - w1_end; w3 = w2_end - w3_end
        if w2_end < w1_start: bear_score += 2
        if w3 > w1:           bear_score += 2
        if w3 > w2:           bear_score += 1
        if w4_end and w4_end < w1_end: bear_score += 2
        if closes[n] < w3_end:
            bear_score += 1; wave_pos = "Wave 5 📉"
        elif w4_end and closes[n] < w4_end:
            bear_score += 1; wave_pos = "Wave 4→5 🔻"

    return bull_score, bear_score, wave_pos

def run():
    print("Elliott Wave Bot started!")
    send_telegram("🌊 *ELLIOTT WAVE BOT* เริ่มทำงานแล้ว!\n\n📊 ราคาเรียลไทม์จาก Twelve Data\n🔍 สแกน 30 คู่เงิน ทุก 60 วินาที")
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        for symbol in PAIRS:
            try:
                candles = get_candles(symbol)
                if not candles or len(candles) < 30:
                    time.sleep(1)
                    continue
                closes = [c["c"] for c in candles]
                price = closes[-1]
                bull_score, bear_score, wave_pos = detect_elliott_wave(candles)
                rsi = calc_rsi(closes)
                e8  = ema(closes, 8)
                e21 = ema(closes, 21)
                trend_up = e8[-1] > e21[-1]
                trend_dn = e8[-1] < e21[-1]
                dp = 3 if "JPY" in symbol else (1 if "XAU" in symbol else 5)
                key = symbol.replace("/", "")

                if bull_score >= 5 and trend_up and rsi < 75 and last_signals.get(key) != "CALL":
                    msg = (f"🌊 *ELLIOTT WAVE — BUY* ▲\n\n"
                           f"💱 *{symbol}*\n"
                           f"💰 ราคา: `{price:.{dp}f}`\n"
                           f"📍 ตำแหน่ง: *{wave_pos}*\n"
                           f"📊 Wave Score: *{bull_score}/8*\n"
                           f"📈 RSI: `{rsi:.1f}`\n"
                           f"⏰ {now}\n\n"
                           f"⚡ *เข้า BUY ได้เลย!*\n\n"
                           f"_Elliott Wave Real-Time Bot_")
                    send_telegram(msg)
                    last_signals[key] = "CALL"

                elif bear_score >= 5 and trend_dn and rsi > 25 and last_signals.get(key) != "PUT":
                    msg = (f"🌊 *ELLIOTT WAVE — SELL* ▼\n\n"
                           f"💱 *{symbol}*\n"
                           f"💰 ราคา: `{price:.{dp}f}`\n"
                           f"📍 ตำแหน่ง: *{wave_pos}*\n"
                           f"📊 Wave Score: *{bear_score}/8*\n"
                           f"📉 RSI: `{rsi:.1f}`\n"
                           f"⏰ {now}\n\n"
                           f"⚡ *เข้า SELL ได้เลย!*\n\n"
                           f"_Elliott Wave Real-Time Bot_")
                    send_telegram(msg)
                    last_signals[key] = "PUT"

                elif bull_score < 5 and bear_score < 5:
                    last_signals[key] = ""

                time.sleep(2)

            except Exception as e:
                print(f"Error {symbol}: {e}")
                continue

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run()
