import os
import sys
from twilio.rest import Client

def send_whatsapp_alert(error_msg):
    """Sovereign Failure Alert: Sends WhatsApp only on crash."""
    try:
        client = Client(os.getenv('USe35244c5f03cde210c3fe8cd9204f547'), os.getenv('7e157b97ff31fdf5eed33cf8de46eb94'))
        client.messages.create(
            from_=os.getenv(' +1 4155238886'),
            to=os.getenv('+91 9392352630'),
            body=f"🚨 ALERT: Your Trading Bot Failed.\nError: {error_msg}"
        )
    except Exception as e:
        print(f"Failed to send WhatsApp: {e}")

def run_trading_logic():
    # Your 5-year strategy goes here...
    # If something breaks, raise an exception
    pass

if __name__ == "__main__":
    try:
        run_trading_logic()
    except Exception as e:
        send_whatsapp_alert(str(e))
        sys.exit(1) # Ensures GitHub Actions shows a red 'Failure'
