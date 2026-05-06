import pandas as pd
import numpy as np

def apply_sma(df, close_col, fast_period, slow_period, only_buy, continuous_buy):
    df_res = df.copy()
    df_res['Fast_MA'] = df_res[close_col].rolling(window=fast_period).mean()
    df_res['Slow_MA'] = df_res[close_col].rolling(window=slow_period).mean()
    
    valid_idx = df_res.index[slow_period:]
    df_res['Signal'] = 0.0
    df_res.loc[valid_idx, 'Signal'] = np.where(
        df_res.loc[valid_idx, 'Fast_MA'] > df_res.loc[valid_idx, 'Slow_MA'], 1.0, -1.0)
    
    # 關鍵修正：在只買不賣模式下，只要已經買入，我們就不產生賣出訊號
    if only_buy:
        df_res['Signal'] = np.where(df_res['Signal'] == -1, 0, df_res['Signal'])
    
    if only_buy:
        if continuous_buy:
            df_res['Position'] = np.where(df_res['Signal'] == 1, 1, 0)
        else:
            df_res['Position'] = np.where((df_res['Signal'] == 1) & (df_res['Signal'].shift(1) != 1), 1, 0)
    else:
        pos_diff = df_res['Signal'].diff().fillna(0)
        if continuous_buy:
            sell_point = np.where((df_res['Signal'] == -1) & (df_res['Signal'].shift(1) != -1), -1, 0)
            buy_point = np.where(df_res['Signal'] == 1, 1, 0)
            df_res['Position'] = np.where(sell_point == -1, -1, buy_point)
        else:
            df_res['Position'] = np.where(pos_diff > 0, 1, np.where(pos_diff < 0, -1, 0))
            
    return df_res

def apply_rsi(df, close_col, rsi_period, oversold, overbought, only_buy, continuous_buy):
    df_res = df.copy()
    delta = df_res[close_col].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = gain / loss
    df_res['RSI'] = 100 - (100 / (1 + rs))
    
    df_res['Signal'] = np.nan
    df_res.loc[df_res['RSI'] < oversold, 'Signal'] = 1
    if not only_buy:
        df_res.loc[df_res['RSI'] > overbought, 'Signal'] = -1
        df_res['Signal'] = df_res['Signal'].ffill().fillna(0)
    else:
        # 只買不賣模式：不用 ffill，避免 Signal 被永久鎖在 1
        # 沒觸發買入條件時就維持 0，讓下次觸發能再產生新的買點
        df_res['Signal'] = df_res['Signal'].fillna(0)
    
    if only_buy:
        if continuous_buy:
            df_res['Position'] = np.where(df_res['Signal'] == 1, 1, 0)
        else:
            # 只有當 Signal 從非 1 (例如 0) 變成 1 時，才是唯一的買點
            df_res['Position'] = np.where((df_res['Signal'] == 1) & (df_res['Signal'].shift(1) != 1), 1, 0)
    else:
        pos_diff = df_res['Signal'].diff().fillna(0)
        if continuous_buy:
            # 連續加碼模式：直接使用原始條件，避免 ffill 讓訊號持續性影響買賣判斷
            raw_buy = df_res['RSI'] < oversold
            raw_sell = df_res['RSI'] > overbought
            sell_first = raw_sell & ~raw_sell.shift(1, fill_value=False)
            df_res['Position'] = np.where(sell_first, -1, np.where(raw_buy, 1, 0))
        else:
            df_res['Position'] = np.where(pos_diff > 0, 1, np.where(pos_diff < 0, -1, 0))

    return df_res

def apply_kd(df, close_col, high_col, low_col, kd_period, kd_buy, kd_sell, only_buy, continuous_buy):
    df_res = df.copy()
    min_low = df_res[low_col].rolling(window=kd_period).min()
    max_high = df_res[high_col].rolling(window=kd_period).max()
    df_res['RSV'] = (df_res[close_col] - min_low) / (max_high - min_low + 1e-8) * 100
    
    df_res['K'] = df_res['RSV'].ewm(com=2, adjust=False).mean()
    df_res['D'] = df_res['K'].ewm(com=2, adjust=False).mean()

    df_res['Signal'] = np.nan
    df_res.loc[df_res['K'] < kd_buy, 'Signal'] = 1
    if not only_buy:
        df_res.loc[df_res['K'] > kd_sell, 'Signal'] = -1
        df_res['Signal'] = df_res['Signal'].ffill().fillna(0)
    else:
        df_res['Signal'] = df_res['Signal'].fillna(0)
    
    if only_buy:
        if continuous_buy:
            df_res['Position'] = np.where(df_res['Signal'] == 1, 1, 0)
        else:
            # 只有當 Signal 從非 1 (例如 0) 變成 1 時，才是唯一的買點
            df_res['Position'] = np.where((df_res['Signal'] == 1) & (df_res['Signal'].shift(1) != 1), 1, 0)
    else:
        pos_diff = df_res['Signal'].diff().fillna(0)
        if continuous_buy:
            # 連續加碼模式：直接使用原始條件，避免 ffill 讓訊號持續性影響買賣判斷
            raw_buy = df_res['K'] < kd_buy
            raw_sell = df_res['K'] > kd_sell
            sell_first = raw_sell & ~raw_sell.shift(1, fill_value=False)
            df_res['Position'] = np.where(sell_first, -1, np.where(raw_buy, 1, 0))
        else:
            df_res['Position'] = np.where(pos_diff > 0, 1, np.where(pos_diff < 0, -1, 0))
            
    return df_res

def apply_dca(df, close_col, amount):
    df_res = df.copy()
    df_res['Month'] = df_res.index.to_period('M')
    first_days = df_res.groupby('Month').head(1).index
    df_res['Position'] = 0
    df_res.loc[first_days, 'Position'] = 1
    df_res['Shares_Bought'] = 0.0
    df_res.loc[first_days, 'Shares_Bought'] = amount / df_res.loc[first_days, close_col]
    df_res['Total_Shares'] = df_res['Shares_Bought'].cumsum()
    df_res['Total_Cost'] = (df_res['Position'] * amount).cumsum()
    df_res['Total_Value'] = df_res['Total_Shares'] * df_res[close_col]
    return df_res