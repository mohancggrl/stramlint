import streamlit as st
import pandas as pd
import ccxt
import plotly.express as px
from datetime import datetime
import time

# Initialize Binance connection
@st.cache_resource
def init_exchange():
    try:
        if not st.secrets.get("PAPER_TRADING", True):
            return ccxt.binance({
                'apiKey': st.secrets["BINANCE_API_KEY"],
                'secret': st.secrets["BINANCE_SECRET"],
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
        return ccxt.binance()  # Public API for paper trading
    except Exception as e:
        st.error(f"🚨 Exchange connection failed: {str(e)}")
        st.stop()

exchange = init_exchange()

# Page Config
st.set_page_config(
    page_title="Binance Cloud Trader",
    layout="wide",
    page_icon="📊"
)

# UI Styling
st.markdown("""
<style>
    .green { color: #00ffaa; }
    .red { color: #ff4b4b; }
    .metric-card {
        border-radius: 5px;
        padding: 15px;
        background-color: #0e1117;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Live Data Fetching
@st.cache_data(ttl=5)  # 5-second cache
def get_market_data(symbol, timeframe='1h', limit=100):
    try:
        # OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Order book data
        orderbook = exchange.fetch_order_book(symbol)
        bids = pd.DataFrame(orderbook['bids'][:5], columns=['Price', 'Amount'])
        asks = pd.DataFrame(orderbook['asks'][:5], columns=['Price', 'Amount'])
        
        return df, bids, asks
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Main App
def main():
    st.title("🚀 Binance Live Trading Bot")
    
    # Sidebar Controls
    with st.sidebar:
        st.header("⚙️ Trading Parameters")
        symbol = st.selectbox("Pair", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT'])
        timeframe = st.selectbox("Interval", ['1m', '5m', '15m', '1h', '4h'])
        auto_trade = st.checkbox("Enable Auto-Trading", False)
        
        st.header("📉 Risk Management")
        trade_size = st.number_input("Trade Size (USDT)", 10, 10000, 100)
        stop_loss = st.slider("Stop Loss (%)", 0.1, 10.0, 2.0)
        take_profit = st.slider("Take Profit (%)", 0.1, 10.0, 4.0)
    
    # Get data
    df, bids, asks = get_market_data(symbol, timeframe)
    
    if not df.empty:
        current_price = df['close'].iloc[-1]
        
        # Metrics Dashboard
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>Current Price</h3>
                <h2>{current_price:.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            change_pct = ((current_price - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
            st.markdown(f"""
            <div class="metric-card">
                <h3>Period Change</h3>
                <h2 class="{'green' if change_pct >= 0 else 'red'}">{change_pct:.2f}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>24h Volume</h3>
                <h2>{df['volume'].sum():.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Charts
        tab1, tab2 = st.tabs(["📈 Price Chart", "📊 Order Book"])
        
        with tab1:
            fig = px.line(df, x='timestamp', y='close', title=f"{symbol} Price")
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Bids")
                st.dataframe(bids.style.format({'Price': '{:.4f}', 'Amount': '{:.2f}'}))
            with col2:
                st.subheader("Asks")
                st.dataframe(asks.sort_values('Price', ascending=False)
                           .style.format({'Price': '{:.4f}', 'Amount': '{:.2f}'}))
        
        # Trading Logic
        if auto_trade and not st.secrets.get("PAPER_TRADING", True):
            try:
                # Example strategy: Buy when price > 5-period average
                ma5 = df['close'].rolling(5).mean().iloc[-1]
                if current_price > ma5:
                    amount = trade_size / current_price
                    exchange.create_market_buy_order(symbol, amount)
                    st.success(f"Executed BUY: {amount:.4f} {symbol}")
            except Exception as e:
                st.error(f"Trade failed: {str(e)}")
    else:
        st.warning("No market data available")

if __name__ == "__main__":
    main()
    # Auto-refresh every 60 seconds
    time.sleep(60)
    st.experimental_rerun()
