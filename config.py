from dotenv import load_dotenv
import os

load_dotenv()

KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")
PAPER_TRADE = os.getenv("PAPER_TRADE", "true").lower() == "true"

DATA_DIR   = os.getenv("DATA_DIR",   "./data/cache")
MODELS_DIR = os.getenv("MODELS_DIR", "./models/saved")

# Create dirs on startup (needed on Railway where /data may not pre-exist)
os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# NSE watchlist — large caps + mid caps + penny/volatile stocks
WATCHLIST = [
    # Large cap blue chips
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "TATAMOTORS.NS", "ADANIENT.NS", "AXISBANK.NS", "WIPRO.NS",
    "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "KOTAKBANK.NS", "LT.NS",
    "NTPC.NS", "POWERGRID.NS", "ONGC.NS", "COALINDIA.NS", "HINDALCO.NS",
    # Mid cap / growth
    "ZOMATO.NS", "PAYTM.NS", "IRFC.NS", "NHPC.NS", "BHEL.NS",
    "SAIL.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS", "BANKBARODA.NS",
    "IRCTC.NS", "LODHA.NS", "NYKAA.NS", "DELHIVERY.NS", "POLICYBZR.NS",
    "TATAPOWER.NS", "ADANIPORTS.NS", "GAIL.NS", "IOC.NS", "BPCL.NS",
    # Volatile / momentum
    "SUZLON.NS", "YESBANK.NS", "IDEA.NS", "RPOWER.NS", "JPPOWER.NS",
    "TRIDENT.NS", "HFCL.NS", "RVNL.NS", "IRB.NS", "ZEEL.NS",
    "GMRINFRA.NS", "JSWENERGY.NS", "RECLTD.NS", "PFC.NS", "CESC.NS",
]

# Smaller focused list for daily dashboard scan (faster)
WATCHLIST_CORE = WATCHLIST[:20]

# Signal thresholds
MIN_SIGNALS_TO_BUY = 4      # out of 6 signals must agree
STOP_LOSS_PCT = 0.02        # 2% stop loss
TARGET_PCT = 0.04           # 4% target
TRAILING_STOP_PCT = 0.015   # 1.5% trailing stop

# Risk per trade as % of portfolio
RISK_PER_TRADE_PCT = 0.02
