Project Sentinel: Autonomous Market AI

![Status](https://github.com/kxrthk/my-sleeper-agent/actions/workflows/daily_schedule.yml/badge.svg)

**Project Sentinel** is a fully autonomous "Sleeper Agent" designed to observe the Indian Equity Markets (NSE) for 5 years without human intervention.

The Brain (Agent 5):
- **Strategy:** Technical Analysis (RSI + SMA 200) + Fundamental Context (News).
- **Architecture:** Python 3.11 running on GitHub Actions Cloud.
- **Resilience:** Self-healing code with "Stock Split" detection and "Zero-Cost" maintenance.
- **Targets:** Dynamic tracking of NIFTY 50 Leaders (Reliance, TCS, HDFC, etc.).

How it Works:
1.  **Wake Up:** Runs automatically every day at 4:00 PM IST.
2.  **Analyze:** Fetches prices from Yahoo Finance & News from Google RSS.
3.  **Decide:** Executes "Buy the Dip" logic only during Bull Markets.
4.  **Log:** Saves decision data to `trading_journal_YYYY.csv`.

Data Structure:
The AI maintains a yearly ledger:
| Date | Symbol | Price | Action | RSI | News Headline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-01-08 | TATASTEEL | 142.5 | BUY | 32.0 | "Steel exports rise..." |

---
*Started: Jan 2026 | Projected End: Jan 2031*
