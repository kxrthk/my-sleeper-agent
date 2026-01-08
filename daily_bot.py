import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# --- CONFIGURATION ---
STOCK = "TATASTEEL.NS"
LOG_FILE = "trading_journal.csv"

def run_daily_task():
    # 1. Get Today's Data
    print(f"Fetching data for {STOCK}...")
    # Fetch last 5 days to ensure we get the latest closed candle
    data = yf.download(STOCK, period="5d") 
    
    if data.empty:
        print("No data found. Market might be closed.")
        return

    today_price = data['Close'].iloc[-1].item()
    today_date = datetime.now().strftime("%Y-%m-%d")

    # 2. Load the Journal (Memory)
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        # Create new journal if none exists
        journal = pd.DataFrame(columns=["Date", "Price", "Action", "Result"])

    # 3. The "Mock" Decision (Placeholder for your AI Brain)
    # logic: If price is lower than yesterday, Buy. (Simple 'Buy the Dip')
    action = "HOLD"
    if len(data) >= 2:
        yesterday_price = data['Close'].iloc[-2].item()
        if today_price < yesterday_price:
            action = "BUY"
        else:
            action = "SELL"

    # 4. Log the Entry
    new_entry = {
        "Date": today_date,
        "Price": round(today_price, 2),
        "Action": action,
        "Result": "Pending" # We will check this tomorrow
    }
    
    # Add to journal using pd.concat (modern method)
    new_row = pd.DataFrame([new_entry])
    journal = pd.concat([journal, new_row], ignore_index=True)

    # 5. Save back to file
    journal.to_csv(LOG_FILE, index=False)
    print(f"Journal updated for {today_date}. Action: {action}")

if __name__ == "__main__":
    run_daily_task()
