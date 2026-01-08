import yfinance as yf
from nselib import capital_market
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION ---
STOCK_SYMBOL = "TATASTEEL"   # For NSE Library
YF_SYMBOL = "TATASTEEL.NS"   # For Yahoo Library
LOG_FILE = "trading_journal.csv"

def get_verified_price():
    """
    Asks two different servers for the price.
    Returns the price ONLY if they agree (or if one fails).
    """
    price_yahoo = None
    price_nse = None

    print(f"--- Checking Price for {STOCK_SYMBOL} ---")

    # 1. Ask Yahoo Finance
    try:
        data = yf.download(YF_SYMBOL, period="1d", progress=False)
        if not data.empty:
            price_yahoo = round(data['Close'].iloc[-1].item(), 2)
            print(f"Server 1 (Yahoo): {price_yahoo}")
    except Exception as e:
        print(f"Yahoo Failed: {e}")

    # 2. Ask NSE Official (Backup)
    try:
        # Fetches today's live data directly from NSE
        data_nse = capital_market.price_volume_and_delivery_position_data(symbol=STOCK_SYMBOL, period='1D')
        if not data_nse.empty:
            # NSE returns price as string with commas (e.g., "1,200.50")
            price_nse = float(data_nse['ClosePrice'].iloc[-1].replace(',', ''))
            print(f"Server 2 (NSE):   {price_nse}")
    except Exception as e:
        print(f"NSE Failed: {e}")

    # 3. The "Judge" Logic
    if price_yahoo and price_nse:
        # If difference is huge (> 2%), trust NSE (Official)
        diff = abs(price_yahoo - price_nse)
        if diff > (price_yahoo * 0.02): 
            print("⚠️ DISCREPANCY! Servers disagree. Trusting NSE.")
            return price_nse
        else:
            print("✅ Data Verified. Prices match.")
            return price_yahoo # Return Yahoo as it's usually cleaner
            
    elif price_nse:
        return price_nse # Fallback to NSE
    elif price_yahoo:
        return price_yahoo # Fallback to Yahoo
    else:
        return None # Both failed

def run_daily_task():
    # 1. Get the Reliable Price
    current_price = get_verified_price()
    
    if current_price is None:
        print("❌ CRITICAL: All servers down. No action taken.")
        return

    today_date = datetime.now().strftime("%Y-%m-%d")

    # 2. Load the Journal (Memory)
    if os.path.exists(LOG_FILE):
        journal = pd.read_csv(LOG_FILE)
    else:
        journal = pd.DataFrame(columns=["Date", "Price", "Action", "Result"])

    # 3. The "Brain" (Trading Logic)
    # Compare Current Price vs Last Recorded Price in Journal
    action = "WAIT"
    
    if not journal.empty:
        last_price = journal.iloc[-1]['Price']
        
        # Simple Logic: Buy if price dropped compared to last entry (Buy the dip)
        if current_price < last_price:
            action = "BUY"
        elif current_price > last_price:
            action = "SELL"
        else:
            action = "HOLD"
    else:
        # First day ever? Just Buy to start tracking.
        action = "BUY (First Entry)"

    # 4. Log the Entry
    new_entry = pd.DataFrame([{
        "Date": today_date, 
        "Price": current_price, 
        "Action": action, 
        "Result": "Pending"
    }])
    
    journal = pd.concat([journal, new_entry], ignore_index=True)
    
    # 5. Save back to file
    journal.to_csv(LOG_FILE, index=False)
    print(f"✍️ Journal updated. Action: {action} @ {current_price}")

if __name__ == "__main__":
    run_daily_task()
