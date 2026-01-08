import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import os
import sys
import shutil  # For the Backup Protocol

# --- CONFIGURATION ---
# Dynamic Filename: "trading_journal_2026.csv" -> New file every year
current_year = datetime.now().year
LOG_FILE = f"trading_journal_{current_year}.csv"

def get_nifty50_leaders():
    """Returns top stocks to track (Basket Strategy)."""
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS"]

def fetch_latest_news(symbol_clean):
    """Fetches Google News headlines."""
    try:
        url = f"https://news.google.com/rss/search?q={symbol_clean}+stock+news&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        return root.find("./channel/item/title").text
    except:
        return "No News Found"

def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", progress=False)
        if df.empty: return None

        # 1. SPLIT GUARD: Check if price dropped > 20% in one day without explanation
        today_price = df['Close'].iloc[-1].item()
        yesterday_price = df['Close'].iloc[-2].item()
        
        # Avoid division by zero
        if yesterday_price == 0: 
            drop_pct = 0
        else:
            drop_pct = (yesterday_price - today_price) / yesterday_price

        if drop_pct > 0.20:
            return {
                "Symbol": symbol, "Price": round(today_price, 2),
                "Action": "SUSPICIOUS (Possible Split)", 
                "RSI": 0, "News_Headline": "CHECK FOR SPLIT"
            }

        # 2. Indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['SMA_200'] = ta.sma(df['Close'], length=200)

        rsi = round(df['RSI'].iloc[-1], 2)
        sma = round(df['SMA_200'].iloc[-1], 2)
        
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

        return {
            "Symbol": symbol_clean,
            "Price": round(today_price, 2),
            "Action": action,
            "RSI": rsi,
            "News_Headline": news
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def run_daily_task():
    watchlist = get_nifty50_leaders()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Load correct yearly file
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        journal = pd.DataFrame(columns=["Date", "Symbol", "Price", "Action", "RSI", "News_Headline"])

    new_entries = []
    
    # 2. LOOP: Analyze all stocks
    for stock in watchlist:
        print(f"Analyzing {stock}...")
        data = analyze_stock(stock)
        
        if data:
            new_entries.append({
                "Date": today_date,
                "Symbol": data['Symbol'],
                "Price": data['Price'],
                "Action": data['Action'],
                "RSI": data['RSI'],
                "News_Headline": data['News_Headline']
            })
        
        # Sleep inside the loop to be polite to Google
        time.sleep(2)

    # 3. SAVE BLOCK (Happens once, AFTER the loop finishes)
    if new_entries:
        # --- BACKUP PROTOCOL: Safety First ---
        if os.path.exists(LOG_FILE):
            try:
                shutil.copy(LOG_FILE, f"{LOG_FILE}.bak") # Creates .bak file
                print("🛡️ Backup created.")
            except Exception as e:
                print(f"⚠️ Backup failed (continuing anyway): {e}")

        # Save the new data
        journal = pd.concat([journal, pd.DataFrame(new_entries)], ignore_index=True)
        journal.to_csv(LOG_FILE, index=False)
        print(f"✅ Saved to {LOG_FILE}")

if __name__ == "__main__":
    run_daily_task()
