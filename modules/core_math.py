import numpy as np
import pandas as pd
import scipy.optimize as optimize

def calc_fixed_amount_pnl(data, position_col, price_col, amount, only_buy=False, continuous_buy=False):
    """
    計算固定金額投資的回測損益、最大動用本金與年化報酬率 (IRR)
    """
    # 直接讀取已經算好的 Position 欄位 (1為買, -1為賣, 0為無動作)
    pos_series = data[position_col]
    
    held_shares = np.zeros(len(data))
    current_shares = 0.0
    cash_flow = np.zeros(len(data))
    trades = 0
    
    # 口袋需要準備的最大現金 (最大回撤資金)
    max_capital_needed = 0.0
    current_capital_used = 0.0
    
    irr_cash_flows = []
    irr_dates = []
    
    for i in range(len(data)):
        p = pos_series.iloc[i]
        price = data[price_col].iloc[i]
        current_date = data.index[i]
        
        # 判斷是否可以買入：
        # 如果是連續買入模式，只要有訊號(p==1)就買
        # 如果不是連續買入，且處於「只買不賣」模式，我們「仍然允許買入」(因為它代表加碼)；只有在「正常買賣且非連續」時才限制空手買。
        # 修正：在 only_buy 且 not continuous_buy 時，原本的 Position 已經幫我們過濾成「只有訊號翻正的第一天」才會有 1，
        # 所以只要 Position 是 1，我們就直接買入，不需要檢查 current_shares == 0。
        can_buy = (p == 1) and (continuous_buy or only_buy or current_shares == 0)
        
        if can_buy:
            shares_to_buy = amount / price
            current_shares += shares_to_buy
            cash_flow[i] = -amount
            current_capital_used += amount
            trades += 1
            irr_cash_flows.append(-amount)
            irr_dates.append(current_date)
            
        # 賣出邏輯 (如果不是 only_buy 模式，且出現賣出訊號，且手上有股票)
        elif not only_buy and p == -1 and current_shares > 0:
            cash_in = current_shares * price
            cash_flow[i] = cash_in
            # 賣出時收回全部部位，重置資本使用量
            current_capital_used = 0.0
            current_shares = 0.0
            trades += 1  # 買與賣各算一次交易動作
            irr_cash_flows.append(cash_in)
            irr_dates.append(current_date)
        
        # 紀錄歷史上口袋最深需要掏出多少錢
        if current_capital_used > max_capital_needed:
            max_capital_needed = current_capital_used
        
        held_shares[i] = current_shares
        
    cum_cash = np.sum(cash_flow)
    final_value = held_shares[-1] * data[price_col].iloc[-1]
    
    if current_shares > 0:
        irr_cash_flows.append(final_value)
        irr_dates.append(data.index[-1])
        
    total_profit = cum_cash + final_value
    
    actual_capital = max_capital_needed if max_capital_needed > 0 else amount
    ret_pct = (total_profit / actual_capital * 100) if actual_capital > 0 else 0
    
    def xnpv(rate, values, dates):
        if rate <= -1.0:
            return float('inf')
        d0 = dates[0]
        return sum([val / (1 + rate)**((d - d0).days / 365.25) for val, d in zip(values, dates)])
    
    annual_irr = 0.0
    if len(irr_cash_flows) >= 2 and actual_capital > 0:
        try:
            annual_irr = optimize.newton(lambda r: xnpv(r, irr_cash_flows, irr_dates), 0.0) * 100
        except:
            annual_irr = ret_pct / ((irr_dates[-1] - irr_dates[0]).days / 365.25) if (irr_dates[-1] - irr_dates[0]).days > 0 else 0

    return actual_capital, total_profit, ret_pct, annual_irr, trades
