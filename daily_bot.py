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

# --- SECRETS (These fetch the numbers from GitHub Settings automatically) ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    """Sends a message to your phone via Telegram."""
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
    else:
        print("Telegram keys missing. Check GitHub Secrets.")

def get_nifty50_leaders():
    """Returns the stocks we want to watch."""
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS"]

def fetch_latest_news(symbol_clean):
    """Fetches the latest news headline from Google RSS."""
    try:
        url = f"https://news.google.com/rss/search?q={symbol_clean}+stock+news&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        return root.find("./channel/item/title").text
    except:
        return "No News Found"

def analyze_stock(symbol):
    """Checks one stock for BUY/SELL signals."""
    try:
        # Download 1 Year of data (needed for SMA 200)
        df = yf.download(symbol, period="1y", progress=False)
        if df.empty: return None

        # Fix Column names (Critical for yfinance compatibility)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [c.capitalize() for c in df.columns]

        # 1. SPLIT GUARD: Check for suspicious 20% drops
        today_price = df['Close'].iloc[-1].item()
        yesterday_price = df['Close'].iloc[-2].item()
        drop_pct = (yesterday_price - today_price) / yesterday_price if yesterday_price != 0 else 0

        if drop_pct > 0.20:
            return {"Symbol": symbol, "Price": round(today_price, 2), "Action": "SUSPICIOUS (Split?)", "RSI": 0, "News": "CHECK SPLIT"}

        # 2. Calculate Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.sma(length=200, append=True)
        
        # Find the correct column names (Handles 'RSI_14' vs 'Rsi_14')
        rsi_col = 'RSI_14' if 'RSI_14' in df.columns else 'Rsi_14'
        sma_col = 'SMA_200' if 'SMA_200' in df.columns else 'Sma_200'
        
        if rsi_col not in df.columns or sma_col not in df.columns:
            return None

        rsi = round(df[rsi_col].iloc[-1], 2)
        sma = round(df[sma_col].iloc[-1], 2)

        # 3. The Strategy Logic
        action = "WAIT"
        # BUY: Price is above 200 SMA (Bull Trend) AND RSI is low (Dip)
        if today_price > sma and rsi < 35:
            action = "BUY (Dip)"
        # SELL: RSI is too high
        elif rsi > 75:
            action = "SELL (Overbought)"
        # AVOID: Price is below 200 SMA (Bear Trend)
        elif today_price < sma:
            action = "AVOID (Bear Market)"

        # 4. Fetch News
        symbol_clean = symbol.replace(".NS", "")
        news = fetch_latest_news(symbol_clean)

        return {"Symbol": symbol_clean, "Price": round(today_price, 2), "Action": action, "RSI": rsi, "News": news}

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def run_daily_task():
    """Main loop that checks all stocks."""
    watchlist = get_nifty50_leaders()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # Load or Create the Journal File
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        journal = pd.DataFrame(columns=["Date", "Symbol", "Price", "Action", "RSI", "News"])

    new_entries = []
    
    print("--- SENTINEL STARTED ---")
    for stock in watchlist:
        print(f"Checking {stock}...")
        data = analyze_stock(stock)
        
        if data:
            # Always add to the list
            new_entries.append({"Date": today_date, "Symbol": data['Symbol'], "Price": data['Price'], "Action": data['Action'], "RSI": data['RSI'], "News": data['News']})
            
            # Send Telegram Alert ONLY if it's a Signal (Buy/Sell/Suspicious)
            # We don't spam you for "WAIT" or "AVOID"
            if "BUY" in data['Action'] or "SELL" in data['Action'] or "SUSPICIOUS" in data['Action']:
                msg = f"🚨 {data['Action']}: {data['Symbol']}\nPrice: ₹{data['Price']}\nRSI: {data['RSI']}\nNews: {data['News']}"
                send_telegram(msg)
        
        # Polite delay
        time.sleep(2)

    # Save and Backup
    if new_entries:
        # Create Backup .bak file
        if os.path.exists(LOG_FILE):
            try:
                shutil.copy(LOG_FILE, f"{LOG_FILE}.bak")
            except:
                pass
        
        # Save to CSV
        new_df = pd.DataFrame(new_entries)
        journal = pd.concat([journal, new_df], ignore_index=True)
        journal.to_csv(LOG_FILE, index=False)
        print(f"✅ Saved data to {LOG_FILE}")
    else:
        print("No data to save.")

if __name__ == "__main__":
    run_daily_task()
