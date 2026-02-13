import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import zscore

# --- CONFIGURARE ---
BINANCE = "https://api.binance.com/api/v3/ticker/price"
CG_BASE = "https://api.coingecko.com/api/v3"
headers = {"Accept": "application/json"}

# TARGETS: Poți ajusta prețurile aici
TARGETS = {
    "SNXUSDT":7.8, "OPUSDT":4.8, "LDOUSDT":6, "JTOUSDT":8,
    "TIAUSDT":12, "IMXUSDT":4, "SONICUSDT":1, "CTSIUSDT":0.2, "NOTUSDT":0.03
}

@st.cache_data(ttl=600)
def get_market_data():
    try:
        g_resp = requests.get(f"{CG_BASE}/global", headers=headers).json()
        btc_d = g_resp['data']['market_cap_percentage']['btc']
        h_resp = requests.get(f"{CG_BASE}/coins/bitcoin/market_chart?vs_currency=usd&days=30&interval=daily", headers=headers).json()
        caps = [x[1] for x in h_resp['market_caps']]
        return btc_d, caps
    except:
        return 52.0, [1e12] * 30

def get_prices():
    try:
        return {i["symbol"]: float(i["price"]) for i in requests.get(BINANCE).json()}
    except:
        return {}

# --- LOGICĂ ---
btc_d, btc_caps = get_market_data()
prices = get_prices()
btc_z = zscore(btc_caps)[-1]
p_exit = (1 / (1 + np.exp(-((48 - btc_d) * 0.3 + btc_z * 1.5)))) * 100

# --- UI ---
st.set_page_config(layout="wide", page_title="Institutional Exit Engine")
st.title("🚦 Institutional Exit Engine")

# Tabel procesare date
rows = []
total_progress = []

for c, t in TARGETS.items():
    if c in prices:
        pr = prices[c]
        prog = (pr / t) * 100
        total_progress.append(min(prog, 100)) # Limitam la 100 pt medie
        
        if p_exit > 70 and prog > 85: status = "🟩 SELL"
        elif p_exit > 45 and prog > 55: status = "🟨 PREPARE"
        else: status = "🟥 HOLD"
        
        rows.append({
            "Coin": c.replace("USDT",""),
            "Live Price": round(pr, 4),
            "Target": t,
            "Progress %": round(prog, 1),
            "Action": status
        })

df = pd.DataFrame(rows)
avg_exit_progress = sum(total_progress) / len(total_progress) if total_progress else 0

# --- DASHBOARD METRICS ---
m1, m2, m3 = st.columns(3)
m1.metric("Market Rotation Prob.", f"{p_exit:.1f}%")
m2.metric("Portfolio Exit Progress", f"{avg_exit_progress:.1f}%")
m3.metric("BTC Dominance", f"{btc_d:.1f}%")

st.markdown("### 🎯 Portfolio Global Exit Status")
st.progress(avg_exit_progress / 100)

def style_row(val):
    if "🟩" in str(val): return 'background-color: #00c853; color: white'
    if "🟨" in str(val): return 'background-color: #ffeb3b; color: black'
    if "🟥" in str(val): return 'background-color: #d32f2f; color: white'
    return ''

st.subheader("Individual Asset Strategy")
st.dataframe(df.style.applymap(style_row, subset=['Action']), use_container_width=True)

st.divider()
st.info("💡 **Hold (Roșu)**: Rămâi poziționat. **Prepare (Galben)**: Fii gata de exit. **Sell (Verde)**: Target atins în condiții de rotație favorabilă.")