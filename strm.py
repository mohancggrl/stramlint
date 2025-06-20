import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime
import ccxt
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange

# Initialize Binance exchange (synchronous mode)
def init_exchange():
    return ccxt.binance({
        'apiKey': 'your_api_key',
        'secret': 'your_api_secret',
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True,
        }
    })

exchange = init_exchange()

# Sidebar Inputs
st.sidebar.header("Trading Parameters")
symbol = st.sidebar.text_input("Symbol (e.g. BTC/USDT)", "BTC/USDT")
symbol_yf = symbol.replace("/", "") + "-USD"
interval = st.sidebar.selectbox("Interval", ['5m', '15m', '1h', '1d'])
lookback = st.sidebar.slider("Lookback (days)", 1, 30, 2)
trade_amount = st.sidebar.number_input("Trade Amount (USDT)", value=20.0)

# Load Price Data
@st.cache_data(ttl=60)
def load_data(symbol, interval, lookback):
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=lookback)
    df = yf.download(tickers=symbol, start=start, end=end, interval=interval)
    df.dropna(inplace=True)
    return df

try:
    data = load_data(symbol_yf, interval, lookback)
    
    # Calculate indicators
    close = data['Close']
    hl2 = (data['High'] + data['Low']) / 2
    
    ema_fast = EMAIndicator(close, window=9).ema_indicator()
    ema_slow = EMAIndicator(close, window=18).ema_indicator()
    
    macd = MACD(close)
    macd_line = macd.macd()
    macd_signal = macd.macd_signal()
    
    atr = AverageTrueRange(data['High'], data['Low'], close, window=10).average_true_range() * 3
    long_stop = hl2 - atr
    short_stop = hl2 + atr
    
    dir_ = pd.Series(
        np.where(close > short_stop.shift(1), 1,
        np.where(close < long_stop.shift(1), -1, np.nan)),
        index=close.index
    ).ffill().fillna(1)
    
    long_signal = (ema_fast > ema_slow) & (macd_line > macd_signal) & (dir_ == 1)
    short_signal = (ema_fast < ema_slow) & (macd_line < macd_signal) & (dir_ == -1)
    
    data['Signal'] = np.where(long_signal, 'Buy', np.where(short_signal, 'Sell', ''))

    # Display
    st.title("📈 Binance Live Trading Bot")
    st.line_chart(close)
    st.dataframe(data[['Close', 'Signal']].tail(20))

    # Trading execution
    def place_order(signal, symbol, amount):
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker['last']
            qty = amount / price
            
            if signal == "Buy":
                exchange.create_market_buy_order(symbol, qty)
                return f"✅ Bought {qty:.6f} {symbol.split('/')[0]} at {price:.2f}"
            elif signal == "Sell":
                exchange.create_market_sell_order(symbol, qty)
                return f"🔴 Sold {qty:.6f} {symbol.split('/')[0]} at {price:.2f}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    if len(data) > 1:
        current_signal = data['Signal'].iloc[-1]
        previous_signal = data['Signal'].iloc[-2]
        
        if current_signal != previous_signal and current_signal in ["Buy", "Sell"]:
            result = place_order(current_signal, symbol, trade_amount)
            st.warning(f"New signal detected: {current_signal}")
            st.success(result)
        else:
            st.info("No new trading signals")

    # Manual controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Force Buy"):
            st.success(place_order("Buy", symbol, trade_amount))
    with col2:
        if st.button("🔴 Force Sell"):
            st.error(place_order("Sell", symbol, trade_amount))

except Exception as e:
    st.error(f"Application error: {str(e)}")
