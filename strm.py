import streamlit as st
import pandas as pd
import ccxt
import time
from datetime import datetime

# --- Dependency Check ---
try:
    import plotly.express as px
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly==5.15.0"])
    import plotly.express as px

# --- Exchange Initialization ---
@st.cache_resource
def init_exchange():
    try:
        if not st.secrets.get("PAPER_TRADING", True):
            return ccxt.binance({
                'apiKey': st.secrets["BINANCE_API_KEY"],
                'secret': st.secrets["BINANCE_SECRET"],
                'options': {'defaultType': 'future'},
                'enableRateLimit': True
            })
        return ccxt.binance()  # Public API for paper trading
    except Exception as e:
        st.error(f"🔴 Exchange Error: {str(e)}")
        st.stop()

exchange = init_exchange()

# --- UI Config ---
st.set_page_config(
    page_title="Binance Cloud Trader",
    layout="wide",
    page_icon="📈"
)

# --- Data Fetching ---
@st.cache_data(ttl=10)  # 10-second cache
def get_market_data(symbol='BTC/USDT', timeframe='1h', limit=100):
    try:
        # OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Order book data
        orderbook = exchange.fetch_order_book(symbol)
        return df, orderbook
    except Exception as e:
        st.warning(f"⚠️ Data Fetch Warning: {str(e)}")
        return pd.DataFrame(), None

# --- Main App ---
def main():
    st.title("🚀 Binance Live Trading Bot")
    
    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("⚙️ Trading Parameters")
        symbol = st.selectbox("Pair", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
        timeframe = st.selectbox("Interval", ['1m', '5m', '15m', '1h'])
        auto_refresh = st.checkbox("Auto Refresh", True)
        
        st.header("📉 Risk Management")
        trade_size = st.number_input("Trade Size (USDT)", 10, 10000, 100)
        stop_loss = st.slider("Stop Loss (%)", 0.1, 10.0, 2.0)
        take_profit = st.slider("Take Profit (%)", 0.1, 10.0, 4.0)
    
    # --- Data Display ---
    df, orderbook = get_market_data(symbol, timeframe)
    
    if not df.empty:
        current_price = df['close'].iloc[-1]
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"{current_price:.2f}")
        change_pct = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        col2.metric("Period Change", f"{change_pct:.2f}%", delta_color="off")
        col3.metric("Volume", f"{df['volume'].sum():.0f}")
        
        # Charts
        tab1, tab2 = st.tabs(["📈 Price Chart", "📊 Order Book"])
        
        with tab1:
            fig = px.line(df, x='timestamp', y='close', title=f"{symbol} Price")
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if orderbook:
                bids = pd.DataFrame(orderbook['bids'][:5], columns=['Price', 'Amount'])
                asks = pd.DataFrame(orderbook['asks'][:5], columns=['Price', 'Amount'])
                
                col1, col2 = st.columns(2)
                col1.dataframe(bids.style.format({'Price': '{:.4f}', 'Amount': '{:.2f}'}))
                col2.dataframe(asks.style.format({'Price': '{:.4f}', 'Amount': '{:.2f}'}))
    
    # --- Auto Refresh ---
    if auto_refresh:
        time.sleep(15)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
