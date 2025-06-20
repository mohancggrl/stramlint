import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# Initialize session state
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'balance' not in st.session_state:
    st.session_state.balance = 1000.00
if 'auto_trading' not in st.session_state:
    st.session_state.auto_trading = False
if 'order_book_data' not in st.session_state:
    st.session_state.order_book_data = pd.DataFrame()

# Default trading parameters
DEFAULT_PARAMS = {
    'INITIAL_INVESTMENT': 1000.00,
    'AMOUNT_PER_TRADE': 100.00,
    'STOP_LOSS_PCT': 5.0,
    'TAKE_PROFIT_PCT': 10.0,
    'BUY_THRESHOLD': 0.20,
    'SELL_THRESHOLD': -0.20
}

@st.cache_data(ttl=60)
def get_market_data(symbol):
    """Get market data for a stock symbol using Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        
        if data.empty:
            return None
            
        last_price = data['Close'].iloc[-1]
        spread_pct = (data['High'].iloc[-1] - data['Low'].iloc[-1]) / last_price
        
        # Simulate order book data (since Yahoo Finance doesn't provide real order book)
        imbalance = np.random.uniform(-0.3, 0.3)
        total_bid = (1 + imbalance) * 1000  # Simulated volume
        total_ask = (1 - imbalance) * 1000  # Simulated volume
        
        return {
            'symbol': symbol,
            'imbalance': imbalance,
            'spread_pct': spread_pct * 100,
            'bid_volume': total_bid,
            'ask_volume': total_ask,
            'liquidity': (total_bid + total_ask) * last_price,
            'last_price': last_price,
            'company': stock.info.get('longName', symbol)
        }
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def get_trading_opportunities(symbols, buy_threshold, sell_threshold):
    """Get trading opportunities based on order book imbalance"""
    opportunities = []
    for symbol in symbols:
        data = get_market_data(symbol)
        if data:
            side = None
            if data['imbalance'] >= buy_threshold:
                side = 'BUY'
            elif data['imbalance'] <= sell_threshold:
                side = 'SELL'
                
            if side:
                opportunities.append({
                    'timestamp': pd.Timestamp.now(),
                    'symbol': symbol,
                    'company': data['company'],
                    'side': side,
                    'price': data['last_price'],
                    'imbalance': data['imbalance'],
                    'volume': data['bid_volume'] if side == 'BUY' else data['ask_volume'],
                    'spread_pct': data['spread_pct'],
                    'liquidity': data['liquidity']
                })
    return pd.DataFrame(opportunities)

def execute_trade(symbol, side, price, company, amount, stop_loss_pct, take_profit_pct):
    """Execute a simulated trade"""
    if amount <= 0 or amount > st.session_state.balance:
        return None
    
    shares = amount / price
    stop_loss = price * (1 - stop_loss_pct/100) if side == 'BUY' else price * (1 + stop_loss_pct/100)
    take_profit = price * (1 + take_profit_pct/100) if side == 'BUY' else price * (1 - take_profit_pct/100)
    
    trade = {
        'timestamp': datetime.now(),
        'symbol': symbol,
        'company': company,
        'side': side,
        'entry_price': price,
        'shares': shares,
        'amount': amount,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'status': 'OPEN',
        'pnl': None,
        'exit_price': None
    }
    
    st.session_state.trades.append(trade)
    st.session_state.balance -= amount
    return trade

def close_trade(trade_index):
    """Close a simulated trade"""
    if 0 <= trade_index < len(st.session_state.trades):
        trade = st.session_state.trades[trade_index]
        if trade['status'] == 'OPEN':
            current_data = get_market_data(trade['symbol'])
            if current_data:
                current_price = current_data['last_price']
                if trade['side'] == 'BUY':
                    pnl = (current_price - trade['entry_price']) * trade['shares']
                else:
                    pnl = (trade['entry_price'] - current_price) * trade['shares']
                
                trade['exit_price'] = current_price
                trade['pnl'] = pnl
                trade['status'] = 'CLOSED'
                trade['exit_time'] = datetime.now()
                st.session_state.balance += trade['amount'] + pnl
                return trade
    return None

def main():
    st.set_page_config(layout="wide", page_title="Stock Market Trader")
    
    # Sidebar controls
    with st.sidebar:
        st.title("Trading Parameters")
        params = {
            'initial_investment': st.number_input("Initial Investment ($)", 
                                                value=DEFAULT_PARAMS['INITIAL_INVESTMENT'], 
                                                step=100.0),
            'amount_per_trade': st.number_input("Amount per Trade ($)", 
                                             value=DEFAULT_PARAMS['AMOUNT_PER_TRADE'], 
                                             step=10.0),
            'stop_loss_pct': st.number_input("Stop Loss (%)", 
                                          value=DEFAULT_PARAMS['STOP_LOSS_PCT'], 
                                          step=0.5),
            'take_profit_pct': st.number_input("Take Profit (%)", 
                                            value=DEFAULT_PARAMS['TAKE_PROFIT_PCT'], 
                                            step=0.5),
            'buy_threshold': st.number_input("Buy Threshold", 
                                          value=DEFAULT_PARAMS['BUY_THRESHOLD'], 
                                          step=0.05),
            'sell_threshold': st.number_input("Sell Threshold", 
                                           value=DEFAULT_PARAMS['SELL_THRESHOLD'], 
                                           step=0.05)
        }
        
        if st.button("Reset Portfolio"):
            st.session_state.balance = params['initial_investment']
            st.session_state.trades = []
            st.success("Portfolio reset!")
    
    # Main dashboard
    st.title("📈 Stock Market Order Book Imbalance Trader")
    
    # Auto trading toggle
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Auto Trading" if not st.session_state.auto_trading else "Stop Auto Trading"):
            st.session_state.auto_trading = not st.session_state.auto_trading
            st.rerun()
    with col2:
        if st.button("Refresh Data"):
            st.rerun()
    
    st.subheader(f"Auto Trading Status: {'🟢 ACTIVE' if st.session_state.auto_trading else '🔴 INACTIVE'}")
    
    # Portfolio summary
    st.subheader("💰 Portfolio Summary")
    total_pnl = sum(t.get('pnl', 0) for t in st.session_state.trades)
    pnl_percent = (total_pnl / params['initial_investment']) * 100 if params['initial_investment'] > 0 else 0
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("Current Balance", f"${st.session_state.balance:,.2f}")
    with metric_col2:
        st.metric("Total PnL", f"${total_pnl:,.2f}", f"{pnl_percent:.2f}%")
    with metric_col3:
        open_trades = len([t for t in st.session_state.trades if t['status'] == 'OPEN'])
        st.metric("Open Positions", open_trades)
    
    # Trading opportunities
    st.subheader("🔍 Trading Opportunities")
    stock_symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'WMT']
    
    try:
        with st.spinner("Loading market data..."):
            opportunities = get_trading_opportunities(
                stock_symbols, 
                params['buy_threshold'], 
                params['sell_threshold']
            )
            st.session_state.order_book_data = opportunities
    except Exception as e:
        st.error(f"Error loading market data: {str(e)}")
        st.session_state.order_book_data = pd.DataFrame()
    
    if not st.session_state.order_book_data.empty:
        st.dataframe(
            st.session_state.order_book_data,
            column_config={
                "price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "imbalance": st.column_config.NumberColumn("Imbalance", format="%.3f"),
                "spread_pct": st.column_config.NumberColumn("Spread %", format="%.2f%%"),
                "liquidity": st.column_config.NumberColumn("Liquidity", format="$%.0f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Trade execution
        for idx, row in st.session_state.order_book_data.iterrows():
            if st.button(
                f"{row['side']} {row['symbol']} @ {row['price']:.2f}", 
                key=f"trade_{idx}",
                type="primary" if row['side'] == 'BUY' else "secondary"
            ):
                trade = execute_trade(
                    row['symbol'],
                    row['side'],
                    row['price'],
                    row['company'],
                    params['amount_per_trade'],
                    params['stop_loss_pct'],
                    params['take_profit_pct']
                )
                if trade:
                    st.success(f"Trade executed: {trade['side']} {trade['symbol']} ({trade['company']})")
                else:
                    st.error("Failed to execute trade - check your balance")
    
    # Open positions
    st.subheader("📊 Open Positions")
    open_trades = [t for t in st.session_state.trades if t['status'] == 'OPEN']
    
    if open_trades:
        for idx, trade in enumerate(open_trades):
            cols = st.columns([3, 2, 2, 1])
            with cols[0]:
                st.write(f"**{trade['symbol']}** ({trade['company']})")
                st.write(f"{trade['side']} {trade['shares']:.2f} shares @ ${trade['entry_price']:.2f}")
            with cols[1]:
                st.write("**SL/TP**")
                st.write(f"${trade['stop_loss']:.2f} / ${trade['take_profit']:.2f}")
            with cols[2]:
                current_price = get_market_data(trade['symbol'])['last_price']
                pnl = (current_price - trade['entry_price']) * trade['shares'] if trade['side'] == 'BUY' \
                      else (trade['entry_price'] - current_price) * trade['shares']
                st.write("**Current PnL**")
                st.write(f"${pnl:.2f}")
            with cols[3]:
                if st.button("Close", key=f"close_{idx}"):
                    closed_trade = close_trade(idx)
                    if closed_trade:
                        st.success(f"Closed with PnL: ${closed_trade['pnl']:.2f}")
                    st.rerun()
    else:
        st.info("No open positions")
    
    # Trade history
    st.subheader("📋 Trade History")
    closed_trades = [t for t in st.session_state.trades if t['status'] == 'CLOSED']
    
    if closed_trades:
        st.dataframe(
            pd.DataFrame(closed_trades)[[
                'timestamp', 'symbol', 'company', 'side', 
                'entry_price', 'exit_price', 'amount', 'pnl'
            ]],
            column_config={
                "timestamp": "Time",
                "entry_price": st.column_config.NumberColumn("Entry", format="$%.2f"),
                "exit_price": st.column_config.NumberColumn("Exit", format="$%.2f"),
                "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "pnl": st.column_config.NumberColumn("PnL", format="$%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No trade history yet")

if __name__ == "__main__":
    main()
