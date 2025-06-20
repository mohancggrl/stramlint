import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import time

# Initialize Binance connection
@st.cache_resource
def init_binance():
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}  # or 'spot'
    })

exchange = init_binance()

# Page Config
st.set_page_config(layout="wide", page_title="Binance Live Trader")

# CSS Styling
st.markdown("""
<style>
    .metric-box {
        border: 1px solid #2e4a7a;
        border-radius: 5px;
        padding: 10px;
        background-color: #0e1117;
        margin-bottom: 10px;
    }
    .positive { color: #00ffaa; }
    .negative { color: #ff4b4b; }
    .dataframe { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.header("Trading Parameters")
    symbol = st.selectbox("Symbol", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT'])
    timeframe = st.selectbox("Timeframe", ['1m', '5m', '15m', '1h', '4h', '1d'])
    st.markdown("---")
    st.header("Risk Management")
    trade_amount = st.number_input("Trade Size (USDT)", 100, 10000, 1000)
    stop_loss = st.number_input("Stop Loss (%)", 0.1, 20.0, 2.0)
    take_profit = st.number_input("Take Profit (%)", 0.1, 20.0, 4.0)

# Function to fetch live data
@st.cache_data(ttl=5)  # Cache for 5 seconds
def get_live_data(symbol, timeframe, limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol.split('/')[0]
        
        # Calculate order book imbalance (simplified example)
        orderbook = exchange.fetch_order_book(symbol)
        bids = orderbook['bids']
        asks = orderbook['asks']
        bid_vol = sum([bid[1] for bid in bids[:5]])
        ask_vol = sum([ask[1] for ask in asks[:5]])
        imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0
        
        return df, imbalance, orderbook
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), 0, {}

# Main Dashboard
st.title(f"Binance Live Trading: {symbol}")

# Control Panel
col1, col2, col3 = st.columns([1,1,2])
with col1:
    auto_trade = st.checkbox("🟢 Auto Trading", False)
with col2:
    if st.button("🔄 Refresh Data"):
        st.experimental_rerun()
with col3:
    st.markdown(f"**Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Get live data
df, imbalance, orderbook = get_live_data(symbol, timeframe)

if not df.empty:
    current_price = df['close'].iloc[-1]
    
    # Portfolio Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><h4>Current Price</h4><h2>{current_price:.2f}</h2></div>', 
                   unsafe_allow_html=True)
    with col2:
        imbalance_color = "positive" if imbalance > 0 else "negative"
        st.markdown(f'<div class="metric-box"><h4>Order Book Imbalance</h4><h2 class="{imbalance_color}">{imbalance:.4f}</h2></div>', 
                   unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><h4>24h Volume</h4><h2>{df["volume"].sum():.2f}</h2></div>', 
                   unsafe_allow_html=True)
    with col4:
        change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        change_color = "positive" if change >= 0 else "negative"
        st.markdown(f'<div class="metric-box"><h4>Period Change</h4><h2 class="{change_color}">{change:.2f}%</h2></div>', 
                   unsafe_allow_html=True)

    # Display charts
    tab1, tab2 = st.tabs(["Price Chart", "Order Book"])
    
    with tab1:
        st.line_chart(df.set_index('timestamp')['close'])
    
    with tab2:
        bids = pd.DataFrame(orderbook['bids'][:10], columns=['Price', 'Amount'])
        asks = pd.DataFrame(orderbook['asks'][:10], columns=['Price', 'Amount'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Bids")
            st.dataframe(bids.style.format({'Price': '{:.4f}', 'Amount': '{:.4f}'}))
        with col2:
            st.subheader("Asks")
            st.dataframe(asks.sort_values('Price', ascending=False)
                        .style.format({'Price': '{:.4f}', 'Amount': '{:.4f}'}))

    # Trading Signals Table
    st.subheader("Trading Opportunities")
    
    # Create signals dataframe
    signals = []
    for i in range(1, len(df)):
        pct_change = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1] * 100
        signals.append({
            'timestamp': df['timestamp'].iloc[i],
            'symbol': symbol,
            'side': 'BUY' if pct_change > 0 else 'SELL',
            'price': df['close'].iloc[i],
            'change%': pct_change,
            'volume': df['volume'].iloc[i]
        })
    
    signals_df = pd.DataFrame(signals[-10:])  # Show last 10 signals
    
    # Color formatting
    def color_signal(val):
        color = 'green' if val == 'BUY' else 'red'
        return f'color: {color}'
    
    st.dataframe(
        signals_df.style.applymap(color_signal, subset=['side'])
                  .format({'price': '{:.4f}', 'change%': '{:.2f}%', 'volume': '{:.2f}'}),
        hide_index=True
    )
    
    # Trading logic
    if auto_trade and imbalance > 0.2:  # Example threshold
        try:
            amount = trade_amount / current_price
            order = exchange.create_market_buy_order(symbol, amount)
            st.success(f"Executed BUY order: {amount:.4f} {symbol} at {current_price:.2f}")
        except Exception as e:
            st.error(f"Trade failed: {e}")
else:
    st.warning("No data available - check your connection")

# Run continuously
st_autorefresh = st.empty()
while True:
    time.sleep(5)  # Refresh every 5 seconds
    st_autorefresh.experimental_rerun()
