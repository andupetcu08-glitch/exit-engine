import json, urllib.request, time, csv, io, math

# Configurare header pentru stabilitate feed-uri
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req).read().decode()

def j(url): return json.loads(fetch(url))

def csv_last(url): 
    return list(csv.DictReader(io.StringIO(fetch(url))))[0]

def clamp(x): return max(0, min(1, x))
def norm(x, a, b): return clamp((x - a) / (b - a))

# ================= FEEDS =================
BINANCE="https://api.binance.com/api/v3/ticker/price"
CG_GLOBAL="https://api.coingecko.com/api/v3/global"
CG_MARKET="https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=250&page=1"

SP="https://stooq.pl/q/l/?s=^spx&f=sd2t2ohlcv&h&e=csv"
VIX="https://stooq.pl/q/l/?s=vix&f=sd2t2ohlcv&h&e=csv"
DXY="https://stooq.pl/q/l/?s=dxy&f=sd2t2ohlcv&h&e=csv"

TARGETS={
    "OPUSDT":4.8, "NOTUSDT":0.03, "ARBUSDT":3.5, "TIAUSDT":12,
    "JTOUSDT":8, "LDOUSDT":6, "CTSIUSDT":0.2, "IMXUSDT":4,
    "SONICUSDT":1, "SNXUSDT":7.8
}

# ================= STATE MANAGEMENT =================
history_total3 = []
btc_history = []

def ema(series, n=5):
    if not series: return 0
    k = 2 / (n + 1)
    e = series[0]
    for v in series[1:]: e = v * k + e * (1 - k)
    return e

def roc(series, period=3):
    if len(series) < period + 1: return 0
    return (series[-1] - series[-period-1]) / series[-period-1] * 100

# ================= CORE MODEL =================

def exit_probability(btc_d, total3, sp, vix, dxy, rot):
    # Crypto weights (60% of total)
    crypto = (1 - norm(btc_d, 42, 55)) * 0.45 + \
             norm(total3, 0.4, 1.8) * 0.35 + \
             norm(rot, 0, 15) * 0.2
    
    # Macro weights (40% of total)
    macro_liq = norm(sp, 5000, 6500) * 0.4 + \
                (1 - norm(vix, 12, 35)) * 0.35 + \
                (1 - norm(dxy, 98, 110)) * 0.25
    
    return round((crypto * 0.6 + macro_liq * 0.4) * 100, 1)

def coin_score(momentum, progress):
    # Scor mare = Momentum bun + Distanta mare fata de target
    return round(momentum * 0.6 + (100 - progress) * 0.4, 1)

# ================= ENGINE EXECUTION =================

def run():
    global history_total3, btc_history
    
    # Fetch data
    live = {i["symbol"]: float(i["price"]) for i in j(BINANCE)}
    g = j(CG_GLOBAL)["data"]
    strength = {i["symbol"].upper(): i["price_change_percentage_24h"] for i in j(CG_MARKET)}
    
    # Crypto Metrics
    btc_d = round(g["market_cap_percentage"]["btc"], 2)
    eth_d = g["market_cap_percentage"]["eth"]
    total3 = (g["total_market_cap"]["usd"] * (1 - (btc_d + eth_d) / 100)) / 1e12
    
    # Macro Metrics
    sp_val = float(csv_last(SP)["Close"])
    vix_val = float(csv_last(VIX)["Close"])
    dxy_val = float(csv_last(DXY)["Close"])
    
    # History tracking (keep last 50 points to save memory)
    history_total3.append(total3); history_total3 = history_total3[-50:]
    btc_history.append(btc_d); btc_history = btc_history[-50:]
    
    # Analytics
    rot_roc = roc(history_total3, 3)
    btc_trend = ema(btc_history[-6:]) - ema(btc_history[-12:]) if len(btc_history) > 12 else 0
    prob = exit_probability(btc_d, total3, sp_val, vix_val, dxy_val, rot_roc)
    
    print("\n" + "="*55)
    print(f" ALPHA ROTATION ENGINE | PROB: {prob}% | {time.strftime('%H:%M:%S')}")
    print("="*55)
    print(f" BTC.D: {btc_d}% (Trend: {btc_trend:.3f}) | TOTAL3: {total3:.3f}T$")
    print(f" S&P: {int(sp_val)} | VIX: {vix_val} | DXY: {dxy_val}")
    print(f" REGIME: {'🔴 SELL' if prob > 70 else '🟡 PREPARE' if prob > 45 else '🟢 HOLD'}")
    print("-" * 55)

    # Coins Processing
    results = []
    for c, t in TARGETS.items():
        if c in live:
            l = live[c]
            prog = (l / t) * 100
            up = ((t / l) - 1) * 100
            sym = c.replace("USDT", "")
            mom = strength.get(sym, 0)
            score = coin_score(mom, prog)
            results.append([sym, l, t, prog, up, mom, score])

    # Sortare dupa SCORE (cele mai bune oportunitati primele)
    results.sort(key=lambda x: x[6], reverse=True)

    print(f"{'COIN':<7}{'LIVE':>10}{'TARGET':>9}{'PROG%':>8}{'UP%':>9}{'MOM%':>8}{'SCORE':>8}")
    for r in results:
        print(f"{r[0]:<7}{r[1]:>10.4f}{r[2]:>9.2f}{r[3]:>7.1f}%{r[4]:>8.1f}%{r[5]:>8.1f}%{r[6]:>8.1f}")

# ================= LOOP =================
if __name__ == "__main__":
    while True:
        try:
            run()
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(20)
