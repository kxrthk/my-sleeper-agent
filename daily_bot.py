import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import os
import shutil

# --- CONFIGURATION ---
current_year = datetime.now().year
LOG_FILE = f"trading_journal_{current_year}.csv"
# SECRETS (From GitHub)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    else:
        print("Telegram keys missing. Check GitHub Secrets.")

def get_nifty50_leaders():
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS"]

def fetch_latest_news(symbol_clean):
    try:
        url = f"https://news.google.com/rss/search?q={symbol_clean}+stock+news&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        return root.find("./channel/item/title").text
    except:
        return "No News Found"

def analyze_stock(symbol):
    try:
        # Download 1 Year of data for SMA 200
        df = yf.download(symbol, period="1y", progress=False)
        if df.empty: return None

        # Fix Column names
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [c.capitalize() for c in df.columns]

        # 1. SPLIT GUARD
        today_price = df['Close'].iloc[-1].item()
        yesterday_price = df['Close'].iloc[-2].item()
        drop_pct = (yesterday_price - today_price) / yesterday_price if yesterday_price != 0 else 0

        if drop_pct > 0.20:
            return {"Symbol": symbol, "Price": round(today_price, 2), "Action": "SUSPICIOUS (Split?)", "RSI": 0, "News": "CHECK SPLIT"}

        # 2. Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.sma(length=200, append=True)
        
        # Safe Fetch
        rsi_col = 'RSI_14' if 'RSI_14' in df.columns else 'Rsi_14'
        sma_col = 'SMA_200' if 'SMA_200' in df.columns else 'Sma_200'
        
        rsi = round(df[rsi_col].iloc[-1], 2)
        sma = round(df[sma_col].iloc[-1], 2)

        # 3. Strategy
        action = "WAIT"
        if today_price > sma and rsi < 35:
            action = "BUY (Dip)"
        elif rsi > 75:
            action = "SELL (Overbought)"
        elif today_price < sma:
            action = "AVOID (Bear Market)"

        # 4. News
        symbol_clean = symbol.replace(".NS", "")
        news = fetch_latest_news(symbol_clean)

        return {"Symbol": symbol_clean, "Price": round(today_price, 2), "Action": action, "RSI": rsi, "News": news}

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def run_daily_task():
    watchlist = get_nifty50_leaders()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # Load Journal
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        journal = pd.DataFrame(columns=["Date", "Symbol", "Price", "Action", "RSI", "News"])

    new_entries = []
    
    for stock in watchlist:
        print(f"Analyzing {stock}...")
        data = analyze_stock(stock)
        
        if data:
            # Add to list
            new_entries.append({"Date": today_date, "Symbol": data['Symbol'], "Price": data['Price'], "Action": data['Action'], "RSI": data['RSI'], "News": data['News']})
            
            # TELEGRAM ALERT (Only if interesting)
            if "BUY" in data['Action'] or "SELL" in data['Action'] or "SUSPICIOUS" in data['Action']:
                msg = f"🚨 {data['Action']}: {data['Symbol']}\nPrice: {data['Price']}\nRSI: {data['RSI']}\nNews: {data['News']}"
                send_telegram(msg)
        
        time.sleep(2)

    # Save and Backup
    if new_entries:
        if os.path.exists(LOG_FILE):
            shutil.copy(LOG_FILE, f"{LOG_FILE}.bak")
        
        # Append new data
        new_df = pd.DataFrame(new_entries)
        journal = pd.concat([journal, new_df], ignore_index=True)
        journal.to_csv(LOG_FILE, index=False)
        print(f"✅ Saved to {LOG_FILE}")
    else:
        print("No data to save.")

if __name__ == "__main__":
    run_daily_task()
