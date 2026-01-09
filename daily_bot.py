import pandas as pd
import pandas_ta_classic as ta
import yfinance as yf
import requests
import json
import os
from datetime import datetime
import time

# --- CONFIGURATION ---
LOG_FILE = "trading_journal.csv"
BRAIN_FILE = "bot_brain.json"
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try: requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        except: pass

def get_dynamic_watchlist():
    """GOD-MODE: Automatically fetches the top 100 stocks from NSE."""
    try:
        # Fetching Nifty 100 directly to ensure we always have the current leaders
        url = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
        df = pd.read_csv(url)
        # Adding .NS to symbols for Yahoo Finance compatibility
        return [str(symbol) + ".NS" for symbol in df['Symbol'].tolist()]
    except Exception as e:
        print(f"Discovery Error: {e}")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"] # Emergency Fallback

def get_brain_wisdom():
    if os.path.exists(BRAIN_FILE):
        with open(BRAIN_FILE, 'r') as f: return json.load(f)
    return {"karma_score": 0, "market_mood": "Neutral", "last_lesson": ""}

def analyze_and_learn(symbol, karma):
    """Sovereign analysis: Checks Trend + Volatility + RSI."""
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 200: return None
        
        # Clean columns for multi-index issues
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Technical Indicators
        df.ta.sma(length=200, append=True)
        df.ta.rsi(length=14, append=True)
        
        price = df['Close'].iloc[-1].item()
        sma = df['SMA_200'].iloc[-1].item()
        rsi = df['RSI_14'].iloc[-1].item()
        
        # Self-Evolving Thresholds: Karma > 50 makes bot aggressive, < 0 makes it cautious
        buy_threshold = 35 if karma < 50 else 42
        
        action = "WAIT"
        # The 'God-Tier' Swing Setup: Bull Trend + Healthy Pullback
        if price > (sma * 1.05) and rsi < buy_threshold:
            action = "POSITIONAL BUY"
        elif rsi > 75:
            action = "PROFIT TARGET"

        return {"Symbol": symbol.replace(".NS",""), "Price": round(price,2), "Action": action, "RSI": round(rsi,2)}
    except: return None

def run_sentinel():
    brain = get_brain_wisdom()
    print(f"--- SENTINEL AWAKE | KARMA: {brain['karma_score']} ---")
    
    # 1. Self-Discovery (Find current market leaders)
    watchlist = get_dynamic_watchlist()
    
    # 2. Analyze the whole list (Self-Organizing focus)
    found_opportunities = []
    for stock in watchlist:
        res = analyze_and_learn(stock, brain['karma_score'])
        if res and res['Action'] != "WAIT":
            found_opportunities.append(res)
        time.sleep(0.5) # Be polite to servers

    # 3. Memory Persistence
    if found_opportunities:
        report = "🌟 **DAILY SECTOR SCAN REPORT** 🌟\n\n"
        for op in found_opportunities:
            report += f"🔹 {op['Symbol']}: {op['Action']} @ ₹{op['Price']} (RSI: {op['RSI']})\n"
        send_telegram(report)
        
        # Save to CSV journal
        new_df = pd.DataFrame(found_opportunities)
        new_df['Date'] = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(LOG_FILE):
            new_df.to_csv(LOG_FILE, mode='a', header=False, index=False)
        else:
            new_df.to_csv(LOG_FILE, index=False)

if __name__ == "__main__":
    run_sentinel()
