import pandas as pd
import matplotlib.pyplot as plt
import talib
import numpy as np

def get_OHLCV(df, symbol):
    df = df.iloc[:,df.columns.get_level_values(1)==symbol]
    df.columns = df.columns.droplevel(1)
    return(df)

def get_sp500(path = '../sp500_daily_2017_2020_8_16.csv'):
    return pd.read_csv(path, header=[0, 1], index_col=0, parse_dates=True)

def plot_signals(close, positions, chart_title, color):
    plt.figure(figsize=(12,8))
    ax = close.plot(figsize=(12,8))
    ax2 = positions.plot(secondary_y=True, figsize=(12,8), color=color, ax=ax)
    
    ax.set_ylabel('Price', fontsize=14)
    ax.set_xlabel('Time', fontsize=14)
    ax2.set_ylabel('Signal', fontsize=14)
    ax2.set_title(chart_title, fontsize=16)

    # Add legend to the axis
    plt.legend()

    # Define the tick size for x-axis and y-axis
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid()
    plt.show()
    
    # Calculate the PnL for exit of a long position
def long_exit(stock, time, entry_time, entry_price):
    pnl = round(stock.loc[time, 'Adj Close'] - entry_price, 2)
    # Calculate trading cost. Feel free to change the trading cost to a value that suits your local markets and broker
    trading_cost = stock.loc[time, 'Adj Close'] * 0.0002 * 2
    pnl = pnl - trading_cost
    return pd.DataFrame([('Long',entry_time,entry_price,time,stock.loc[time, 'Adj Close'],pnl)])
    
# Calculate the PnL for exit of a short position
def short_exit(stock, time, entry_time, entry_price):
    pnl = round(entry_price - stock.loc[time, 'Adj Close'], 2) 
    trading_cost = stock.loc[time, 'Adj Close'] * 0.0002 * 2
    pnl = pnl - trading_cost
    return pd.DataFrame([('Short',entry_time,entry_price,time,stock.loc[time, 'Adj Close'],pnl)])

def scalping_strategy(data, stop_loss_threshold, take_profit_threshold):
    # Calculate the Average True Range(ATR)
    data['ATR'] = talib.ATR(data['High'], data['Low'],
                            data['Close'], timeperiod=30)
    # Calculate the rolling mean of ATR
    data['ATR_MA_5'] = data['ATR'].rolling(5).mean()
    
    # Calculate the first minute where ATR breaks out its rolling mean
    data['ATR_breakout'] = np.where((data['ATR'] > data['ATR_MA_5']), True, False)    
    
    # Calculate the three-candle rolling high
    data['three_candle_high'] = data['High'].rolling(3).max()
    # Check if the fourth candle is higher than the highest of the previous 3 candles
    data['four_candle_high'] = np.where( data['High'] >
        data['three_candle_high'].shift(1), True, False)
    # Flag the long position signal
    data['long_positions'] = np.where(data['ATR_breakout'] & data['four_candle_high'], 1, 0)
    
    # Calculate the three-candle rolling low
    data['three_candle_low'] = data['Low'].rolling(3).min()
    # Check if the fourth candle is lower than the lowest of the previous 3 candles
    data['four_candle_low'] = np.where( data['Low'] <
        data['three_candle_low'].shift(1), True, False) 
    # Flag the short position signal    
    data['short_positions'] = np.where(data['ATR_breakout'] & data['four_candle_low'], -1, 0)
    # Combine the long and short flags
    data['positions'] = data['long_positions'] + data['short_positions']
    
    
    current_position = 0
    stop_loss = ''
    take_profit = ''
    entry_price = np.nan
    data['pnl'] = np.nan

    # Calculate the PnL for exit of a long position
    def long_exit(data, time, entry_price):
        pnl = round(data.loc[time, 'Close'] - entry_price, 2)
        data.loc[time, 'pnl'] = pnl
        
    # Calculate the PnL for exit of a short position
    def short_exit(data, time, entry_price):
        pnl = round(entry_price - data.loc[time, 'Close'], 2)
        data.loc[time, 'pnl'] = pnl

    for time in data.index:
        # ---------------------------------------------------------------------------------
        # Long Position
        if (current_position == 0) and (data.loc[time, 'positions'] == 1):
            current_position = 1
            entry_price = data.loc[time, 'Close']
            stop_loss = data.loc[time, 'Close'] * (1-stop_loss_threshold)
            take_profit = data.loc[time, 'Close'] * (1+take_profit_threshold)

        # ---------------------------------------------------------------------------------
        # Long Exit
        elif (current_position == 1):
            # Check for sl and tp
            if data.loc[time, 'Close'] < stop_loss or data.loc[time, 'Close'] > take_profit:
                long_exit(data, time, entry_price)
                current_position = 0

        # ---------------------------------------------------------------------------------
        # Short Position
        if (current_position == 0) and (data.loc[time, 'positions'] == -1):
            current_position = data.loc[time, 'positions']
            entry_price = data.loc[time, 'Close']
            stop_loss = data.loc[time, 'Close'] * (1+stop_loss_threshold)
            take_profit = data.loc[time, 'Close'] * (1-take_profit_threshold)

        # ---------------------------------------------------------------------------------
        # Short Exit
        elif (current_position == -1):
            # Check for sl and tp
            if data.loc[time, 'Close'] > stop_loss or data.loc[time, 'Close'] < take_profit:
                short_exit(data, time, entry_price)
                current_position = 0

        # ---------------------------------------------------------------------------------
        # Close Open Position at EOD
        if time.hour == 15 and time.minute == 59:
            if current_position == 1:
                long_exit(data, time, entry_price)
                current_position = 0

            elif current_position == -1:
                short_exit(data, time, entry_price)
                current_position = 0
                
    return data.pnl.sum()