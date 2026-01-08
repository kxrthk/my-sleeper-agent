import yfinance as yf
import pandas as pd
import pandas_ta_classic as ta
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import os
import shutil
import json

# --- CONFIGURATION ---
# We use the static name to match your existing file
LOG_FILE = "trading_journal.csv" 
BRAIN_FILE = "bot_brain.json"    # Stores the Karma Score

# --- SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        except: pass

def get_brain():
    """Reads the bot's Karma Score. Starts at 0."""
    if os.path.exists(BRAIN_FILE):
        with open(BRAIN_FILE, 'r') as f:
            return json.load(f)
    return {"karma_score": 0, "wins": 0, "losses": 0}

def update_brain(new_karma, result):
    """Updates the score based on +10 or -20."""
    brain = get_brain()
    brain["karma_score"] += new_karma
    if result == "WIN": brain["wins"] += 1
    elif result == "LOSS": brain["losses"] += 1
    
    with open(BRAIN_FILE, 'w') as f:
        json.dump(brain, f)
    return brain

def review_past_decisions(journal):
    """The 'Enforcement Learning' Step."""
    if journal.empty: return journal
    
    # Check trades from 3-5 days ago that are still 'Pending'
    # Realistically, for hourly, we check trades older than 24 hours
    mask = (journal['Result'].isna()) | (journal['Result'] == 'Pending')
    pending_trades = journal[mask]
    
    if pending_trades.empty: return journal

    print("🎓 Reviewing past homework...")
    
    for index, row in pending_trades.iterrows():
        try:
            symbol = row['Symbol'] + ".NS" # Restore .NS for lookup
            buy_price = float(row['Price'])
            action = row['Action']
            date_logged = row['Date'] # e.g., 2026-01-08
            
            # Fetch current price
            curr_df = yf.download(symbol, period="1d", progress=False)
            if curr_df.empty: continue
            curr_price = curr_df['Close'].iloc[-1].item()
            
            # --- SCORING RULES (+10 / -20) ---
            outcome = "Pending"
            points = 0
            
            if "BUY" in action:
                # Win: Price rose > 2% | Loss: Price fell > 2%
                if curr_price > buy_price * 1.02:
                    outcome = "WIN"
                    points = 10
                elif curr_price < buy_price * 0.98:
                    outcome = "LOSS"
                    points = -20
            
            if outcome != "Pending":
                print(f"   > Trade Review: {symbol} ({action}) -> {outcome} ({points} pts)")
                journal.at[index, 'Result'] = outcome
                
                # Update the Brain
                new_stats = update_brain(points, outcome)
                send_telegram(f"🧠 LEARNING UPDATE:\nTrade: {symbol} was a {outcome}.\nKarma Change: {points}\nTotal Score: {new_stats['karma_score']}")
                
        except Exception as e:
            print(f"Error reviewing {row['Symbol']}: {e}")
            
    return journal

def get_smart_thresholds(karma):
    """Adjusts strategy based on Confidence Score."""
    # BASELINE: RSI 35 is Buy, 75 is Sell
    buy_limit = 35
    sell_limit = 75
    
    if karma > 50:
        # Confident: Buy earlier (Aggressive)
        buy_limit = 40 
    elif karma < -20:
        # Scared: Buy only on deep crashes (Conservative)
        buy_limit = 25
        
    return buy_limit, sell_limit

def analyze_stock(symbol, karma):
    buy_limit, sell_limit = get_smart_thresholds(karma)
    
    try:
        df = yf.download(symbol, period="1y", progress=False)
        if df.empty: return None

        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [c.capitalize() for c in df.columns]

        today_price = df['Close'].iloc[-1].item()
        
        # Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.sma(length=200, append=True)
        
        rsi_col = 'RSI_14' if 'RSI_14' in df.columns else 'Rsi_14'
        sma_col = 'SMA_200' if 'SMA_200' in df.columns else 'Sma_200'
        
        rsi = round(df[rsi_col].iloc[-1], 2)
        sma = round(df[sma_col].iloc[-1], 2)

        action = "WAIT"
        # Smart Logic using Dynamic Thresholds
        if today_price > sma and rsi < buy_limit:
            action = "BUY (Dip)"
        elif rsi > sell_limit:
            action = "SELL (Overbought)"
        elif today_price < sma:
            action = "AVOID (Bear Market)"

        return {"Symbol": symbol.replace(".NS",""), "Price": round(today_price, 2), "Action": action, "RSI": rsi}

    except: return None

def run_task():
    brain = get_brain()
    print(f"--- SENTINEL STARTED (Karma: {brain['karma_score']}) ---")
    
    # 1. Load Journal
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        journal = pd.DataFrame(columns=["Date", "Symbol", "Price", "Action", "RSI", "Result"])

    # 2. Enforcement Learning (Grade Homework)
    journal = review_past_decisions(journal)
    
    # 3. Analyze New Market
    watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS"]
    new_entries = []
    today_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    for stock in watchlist:
        data = analyze_stock(stock, brain['karma_score'])
        if data:
            new_entries.append({
                "Date": today_date, "Symbol": data['Symbol'], 
                "Price": data['Price'], "Action": data['Action'], 
                "RSI": data['RSI'], "Result": "Pending"
            })
            if "BUY" in data['Action'] or "SELL" in data['Action']:
                send_telegram(f"🚨 {data['Action']} [{brain['karma_score']} pts]\n{data['Symbol']} @ ₹{data['Price']}\nRSI: {data['RSI']}")
        time.sleep(1)

    # 4. Save Everything
    if new_entries or not journal.empty:
        new_df = pd.DataFrame(new_entries)
        journal = pd.concat([journal, new_df], ignore_index=True)
        journal.to_csv(LOG_FILE, index=False)
        print("✅ Journal Updated")

if __name__ == "__main__":
    run_task()
