import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# Trading parameters
INITIAL_INVESTMENT = 1000.00
AMOUNT_PER_TRADE = 100.00
STOP_LOSS = 0.05  # 5% for stocks
TAKE_PROFIT = 0.10  # 10% for stocks
LEVERAGE = 1  # Typically 1 for stocks (no leverage)
BUY_IMBALANCE_THRESHOLD = 0.20
SELL_IMBALANCE_THRESHOLD = -0.20

# Initialize session state
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'balance' not in st.session_state:
    st.session_state.balance = INITIAL_INVESTMENT
if 'auto_trading' not in st.session_state:
    st.session_state.auto_trading = False
if 'order_book_data' not in st.session_state:
    st.session_state.order_book_data = pd.DataFrame()

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_market_data(symbol):
    """Get market data for a stock symbol using Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if data.empty:
            return None
            
        # Get order book data (simulated since Yahoo Finance doesn't provide real order book)
        last_price = data['Close'].iloc[-1]
        spread_pct = 0.001  # Simulated spread (0.1%)
        
        # Simulate order book imbalance
        imbalance = np.random.uniform(-0.3, 0.3)
        total_bid = (1 + imbalance) * 1000  # Simulated volume
        total_ask = (1 - imbalance) * 1000  # Simulated volume
        
        return {
            'symbol': symbol,
            'imbalance': imbalance,
            'spread%': spread_pct * 100,
            'bid_volume': total_bid,
            'ask_volume': total_ask,
            'liquidity': (total_bid + total_ask) * last_price,
            'last_price': last_price,
            'company': stock.info.get('longName', symbol)
        }
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

def get_trading_opportunities(symbols):
    """Get trading opportunities based on order book imbalance"""
    opportunities = []
    for symbol in symbols:
        data = get_market_data(symbol)
        if data:
            side = 'BUY' if data['imbalance'] >= BUY_IMBALANCE_THRESHOLD else 'SELL' if data['imbalance'] <= SELL_IMBALANCE_THRESHOLD else None
            if side:
                opportunities.append({
                    'timestamp': pd.Timestamp.now(),
                    'symbol': symbol,
                    'company': data['company'],
                    'side': side,
                    'price': data['last_price'],
                    'imbalance': data['imbalance'],
                    'volume_data': data['bid_volume'] if side == 'BUY' else -data['ask_volume'],
                    'spread%': data['spread%'],
                    'liquidity_rad': data['liquidity']
                })
    return pd.DataFrame(opportunities)

def execute_trade(symbol, side, price, company):
    """Execute a trade (simulated for demo)"""
    trade_amount = min(AMOUNT_PER_TRADE, st.session_state.balance)
    if trade_amount <= 0:
        return None
    
    # Calculate number of shares (fractional shares allowed)
    shares = trade_amount / price
    
    trade = {
        'timestamp': pd.Timestamp.now(),
        'symbol': symbol,
        'company': company,
        'side': side,
        'entry_price': price,
        'shares': shares,
        'amount': trade_amount,
        'leverage': LEVERAGE,
        'stop_loss': price * (1 - STOP_LOSS) if side == 'BUY' else price * (1 + STOP_LOSS),
        'take_profit': price * (1 + TAKE_PROFIT) if side == 'BUY' else price * (1 - TAKE_PROFIT),
        'status': 'OPEN'
    }
    
    st.session_state.trades.append(trade)
    st.session_state.balance -= trade_amount
    return trade

def close_trade(trade_index):
    """Close a trade (simulated for demo)"""
    if 0 <= trade_index < len(st.session_state.trades):
        trade = st.session_state.trades[trade_index]
        if trade['status'] == 'OPEN':
            # Get current price
            current_data = get_market_data(trade['symbol'])
            if current_data:
                current_price = current_data['last_price']
                if trade['side'] == 'BUY':
                    pnl = (current_price - trade['entry_price']) * trade['shares']
                else:  # SELL (short position)
                    pnl = (trade['entry_price'] - current_price) * trade['shares']
                
                trade['exit_price'] = current_price
                trade['pnl'] = pnl
                trade['exit_time'] = pd.Timestamp.now()
                trade['status'] = 'CLOSED'
                st.session_state.balance += trade['amount'] + pnl
                return trade
    return None

def main():
    st.set_page_config(layout="wide")
    
    # Sidebar with trading parameters
    with st.sidebar:
        st.title("Trading Parameters")
        INITIAL_INVESTMENT = st.number_input("Initial Investment ($)", value=1000.00, step=100.0)
        AMOUNT_PER_TRADE = st.number_input("Amount per Trade ($)", value=100.00, step=10.0)
        STOP_LOSS = st.number_input("Stop Loss (%)", value=5.0, step=0.5) / 100
        TAKE_PROFIT = st.number_input("Take Profit (%)", value=10.0, step=0.5) / 100
        BUY_IMBALANCE_THRESHOLD = st.number_input("Buy Imbalance Threshold", value=0.20, step=0.05)
        SELL_IMBALANCE_THRESHOLD = st.number_input("Sell Imbalance Threshold", value=-0.20, step=0.05)
        
        if st.button("Reset Portfolio"):
            st.session_state.balance = INITIAL_INVESTMENT
            st.session_state.trades = []
    
    # Main dashboard
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.title("Stock Market Orderbook Imbalance Trader")
        
        # Auto trading toggle
        auto_col1, auto_col2 = st.columns(2)
        with auto_col1:
            if st.button("Start Auto Trading" if not st.session_state.auto_trading else "Stop Auto Trading"):
                st.session_state.auto_trading = not st.session_state.auto_trading
        with auto_col2:
            if st.button("Manual Refresh"):
                pass  # Refresh handled in main loop
        
        st.markdown(f"### Auto Trading Status: *{'ACTIVE' if st.session_state.auto_trading else 'INACTIVE'}*")
        
        # Portfolio balance
        st.markdown("### Portfolio Balance")
        total_pnl = sum(t.get('pnl', 0) for t in st.session_state.trades)
        pnl_percent = (total_pnl / INITIAL_INVESTMENT) * 100 if INITIAL_INVESTMENT > 0 else 0
        st.metric("Total PnL", 
                 f"${st.session_state.balance:.2f}", 
                 f"{total_pnl:.2f} ({pnl_percent:.2f}%)")
        
        # Trades summary
        st.markdown("### Trades Summary")
        open_trades = len([t for t in st.session_state.trades if t['status'] == 'OPEN'])
        closed_trades = len([t for t in st.session_state.trades if t['status'] == 'CLOSED'])
        st.metric("Open Trades", open_trades)
        st.metric("Closed Trades", closed_trades)
    
    with col2:
        # Trading opportunities table
        st.markdown("### Trading Opportunities")
        
        # Popular US stocks
        stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
                        'META', 'NVDA', 'JPM', 'V', 'WMT']
        
        try:
            if st.session_state.auto_trading or st.button("Refresh Opportunities"):
                with st.spinner('Fetching market data...'):
                    opportunities = get_trading_opportunities(stock_symbols)
                    st.session_state.order_book_data = opportunities
        except Exception as e:
            st.error(f"Failed to fetch market data: {str(e)}")
            st.session_state.order_book_data = pd.DataFrame()
        
        if not st.session_state.order_book_data.empty:
            st.dataframe(st.session_state.order_book_data.style.format({
                'price': '{:.2f}',
                'imbalance': '{:.4f}',
                'volume_data': '{:.2f}',
                'spread%': '{:.4f}',
                'liquidity_rad': '{:.2f}'
            }))
            
            # Execute trades from opportunities
            for idx, row in st.session_state.order_book_data.iterrows():
                if st.button(f"{row['side']} {row['symbol']} @ {row['price']:.2f}", key=f"trade_{idx}"):
                    trade = execute_trade(row['symbol'], row['side'], row['price'], row['company'])
                    if trade:
                        st.success(f"Trade executed: {trade['side']} {trade['symbol']} ({trade['company']}) @ {trade['entry_price']:.2f}")
                    else:
                        st.error("Not enough balance to execute trade")
        
        # Open trades table
        st.markdown("### Open Trades")
        open_trades_df = pd.DataFrame([t for t in st.session_state.trades if t['status'] == 'OPEN'])
        if not open_trades_df.empty:
            st.dataframe(open_trades_df[['timestamp', 'symbol', 'company', 'side', 'entry_price', 'shares', 'amount']])
            
            # Close trades
            for idx, trade in enumerate([t for t in st.session_state.trades if t['status'] == 'OPEN']):
                if st.button(f"Close {trade['symbol']} {trade['side']}", key=f"close_{idx}"):
                    closed_trade = close_trade(idx)
                    if closed_trade:
                        st.success(f"Trade closed with PnL: ${closed_trade['pnl']:.2f}")
        
        # Closed trades history
        st.markdown("### Trade History")
        closed_trades_df = pd.DataFrame([t for t in st.session_state.trades if t['status'] == 'CLOSED'])
        if not closed_trades_df.empty:
            st.dataframe(closed_trades_df[['timestamp', 'symbol', 'company', 'side', 'entry_price', 'exit_price', 'amount', 'pnl']])

if __name__ == "__main__":
    main()
