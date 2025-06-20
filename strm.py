import streamlit as st
import pandas as pd
import numpy as np
import datetime
import ccxt
from ta.trend import EMAIndicator, MACD

# ===== CONFIGURATION =====
PAPER_TRADING = True  # Set to False for real trading
SYMBOL = "BTC/USDT"
INITIAL_BALANCE = 1000  # USDT

# ===== SETUP =====
st.set_page_config(
    page_title="Crypto Trading Bot",
    page_icon="🤖",
    layout="wide"
)

# Initialize exchange (with error handling)
@st.cache_resource
def init_exchange():
    try:
        if not PAPER_TRADING:
            exchange = ccxt.binance({
                'apiKey': st.secrets["BINANCE_API_KEY"],
                'secret': st.secrets["BINANCE_SECRET"],
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            exchange.load_markets()
            return exchange
        return None  # Paper trading mode
    except Exception as e:
        st.error(f"Exchange initialization failed: {str(e)}")
        st.stop()

exchange = init_exchange()

# ===== DATA LOADING =====
@st.cache_data(ttl=60)  # 1 minute cache
def load_data(symbol, timeframe='1h', limit=100):
    try:
        if exchange and not PAPER_TRADING:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df.set_index('timestamp')
        else:
            # Fallback to CCXT public API
            temp_exchange = ccxt.binance()
            ohlcv = temp_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df.set_index('timestamp')
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame()

# ===== TRADING STRATEGY =====
def calculate_signals(df):
    df = df.copy()
    close = df['close']
    
    # Indicators
    ema_fast = EMAIndicator(close, window=9).ema_indicator()
    ema_slow = EMAIndicator(close, window=21).ema_indicator()
    macd = MACD(close)
    
    # Signals
    df['signal'] = np.where(
        (ema_fast > ema_slow) & (macd.macd() > macd.macd_signal()),
        'BUY',
        np.where(
            (ema_fast < ema_slow) & (macd.macd() < macd.macd_signal()),
            'SELL',
            'HOLD'
        )
    )
    return df

# ===== TRADING ENGINE =====
class TradingBot:
    def __init__(self):
        self.balance = INITIAL_BALANCE
        self.position = 0
        self.entry_price = 0
        self.trade_history = []
    
    def execute_trade(self, signal, current_price):
        if PAPER_TRADING:
            if signal == 'BUY' and self.balance > 10:
                self.position = self.balance / current_price
                self.entry_price = current_price
                self.balance = 0
                self.trade_history.append({
                    'type': 'BUY',
                    'price': current_price,
                    'amount': self.position,
                    'time': datetime.datetime.now()
                })
                return f"📈 Paper BUY: {self.position:.6f} {SYMBOL.split('/')[0]} at {current_price:.2f}"
            
            elif signal == 'SELL' and self.position > 0:
                self.balance = self.position * current_price
                profit_pct = ((current_price - self.entry_price) / self.entry_price) * 100
                self.trade_history.append({
                    'type': 'SELL',
                    'price': current_price,
                    'amount': self.position,
                    'profit': profit_pct,
                    'time': datetime.datetime.now()
                })
                position = self.position
                self.position = 0
                return f"📉 Paper SELL: {position:.6f} {SYMBOL.split('/')[0]} at {current_price:.2f} ({profit_pct:.2f}%)"
            
            return "No paper trade executed"
        else:
            try:
                if signal == 'BUY' and exchange:
                    amount = self.balance / current_price
                    order = exchange.create_market_buy_order(SYMBOL, amount)
                    return f"📈 Real BUY executed: {order['amount']} {SYMBOL.split('/')[0]}"
                elif signal == 'SELL' and exchange:
                    order = exchange.create_market_sell_order(SYMBOL, self.position)
                    return f"📉 Real SELL executed: {order['amount']} {SYMBOL.split('/')[0]}"
            except Exception as e:
                return f"❌ Trade failed: {str(e)}"
        return "No action taken"

# ===== STREAMLIT UI =====
st.title(f"💰 Crypto Trading Bot: {SYMBOL}")
st.caption(f"Mode: {'PAPER TRADING' if PAPER_TRADING else 'LIVE TRADING'}")

# Load data
timeframe = st.sidebar.selectbox("Timeframe", ['15m', '1h', '4h', '1d'])
data = load_data(SYMBOL, timeframe)
if not data.empty:
    data = calculate_signals(data)
    current_price = data['close'].iloc[-1]
    last_signal = data['signal'].iloc[-1]

    # Initialize bot
    if 'bot' not in st.session_state:
        st.session_state.bot = TradingBot()
    bot = st.session_state.bot

    # Display charts
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Price Chart")
        st.line_chart(data['close'])
    with col2:
        st.metric("Current Price", f"{current_price:.2f}")
        st.metric("Position", f"{bot.position:.6f}" if bot.position > 0 else "No position")
        st.metric("Balance", f"{bot.balance:.2f} USDT")

    # Trading execution
    st.subheader("Trading Controls")
    if st.button("🔄 Check Signal"):
        result = bot.execute_trade(last_signal, current_price)
        st.info(f"Last Signal: {last_signal}")
        st.success(result)

    # Trade history
    if bot.trade_history:
        st.subheader("Trade History")
        st.table(pd.DataFrame(bot.trade_history))
else:
    st.warning("No data loaded - check your connection")

# ===== FOOTER =====
st.sidebar.markdown("---")
st.sidebar.info("""
**Safety Features:**
- Paper trading by default
- Rate limiting enabled
- No leverage used
""")
