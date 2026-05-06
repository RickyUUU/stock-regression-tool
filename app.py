import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import datetime

# 設定頁面
st.set_page_config(page_title="股票回測可視化工具", layout="wide")
st.title("📈 股票策略可視化回測工具")

# 1. 側邊欄：檔案上傳與策略選擇
st.sidebar.header("📁 資料載入")
uploaded_file = st.sidebar.file_uploader("📥 請載入 Excel 或 CSV 檔案", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # 讀取資料
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.sidebar.success(f"成功載入: {uploaded_file.name}")
        
        # 嘗試自動識別欄位名稱
        col_map = {str(c).lower().strip(): c for c in df.columns}
        
        # 尋找日期欄位並設為 Index
        date_col = next((col_map[c] for c in ['date', '日期', 'time'] if c in col_map), None)
        if date_col:
            df[date_col] = df[date_col].astype(str).str.split(' ').str[0]
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col])
            df = df.sort_values(date_col)
            df.set_index(date_col, inplace=True)
            
        close_col = next((col_map[c] for c in ['close', '收盤價', 'price', '最後價格'] if c in col_map), None)
        if not close_col:
            st.error("找不到收盤價 (Close) 欄位，請確認資料格式。")
            st.stop()

        # 取得資料起始與結束日期
        min_date = df.index.min().date()
        max_date = df.index.min().date() if pd.isna(df.index.max()) else df.index.max().date()

        # --- 新增功能：測試區間設定 ---
        st.sidebar.header("📅 測試區間設定")
        start_date = st.sidebar.date_input("開始日期", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("結束日期", max_date, min_value=min_date, max_value=max_date)

        # 根據區間過濾資料
        df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

        with st.expander("🔍 預覽過濾後的資料"):
            st.dataframe(df.tail())

        # 全局交易金額設定 (用於比較表與策略)
        st.sidebar.header("💰 資金設定")
        trade_amount = st.sidebar.number_input("每次交易固定投入金額 ($)", min_value=1000, value=100000, step=10000, help="設定每次買進訊號出現時，固定要買入的金額。定期定額則為每月投入金額。")

        # 載入 scipy 以計算 IRR
        import scipy.optimize as optimize

        # --- 共用固定金額計算函數 ---
        def calc_fixed_amount_pnl(data, signal_col, price_col, amount, only_buy=False):
            # 取得原始的訊號
            raw_signal = data[signal_col]
            
            # 處理「只買不賣」或「正常買賣」邏輯
            if only_buy:
                # 只看買進訊號 (1)，忽略賣出訊號 (0 或 -1)
                buy_points = np.where(raw_signal == 1, 1, 0)
                # 為了避免連續觸發買進，我們限制「同一天只能買一次」，但可以「無限累積庫存」
                pos = buy_points
            else:
                # 正常買賣：用 diff 找出狀態轉換點
                pos = raw_signal.diff().fillna(raw_signal)
                pos = np.where(pos == 1, 1, np.where(pos == -1, -1, 0))
            
            pos_series = pd.Series(pos, index=data.index)
            
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
                
                if only_buy:
                    # 只買不賣：只要有買進訊號就固定花 amount 買入 (無腦疊加)
                    if p == 1:
                        shares_to_buy = amount / price
                        current_shares += shares_to_buy
                        cash_flow[i] = -amount
                        current_capital_used += amount
                        trades += 1
                        irr_cash_flows.append(-amount)
                        irr_dates.append(current_date)
                else:
                    # 正常買賣：空手才買，有股票才賣
                    if p == 1 and current_shares == 0:
                        current_shares = amount / price
                        cash_flow[i] = -amount
                        current_capital_used += amount
                        trades += 1
                        irr_cash_flows.append(-amount)
                        irr_dates.append(current_date)
                    elif p == -1 and current_shares > 0:
                        cash_in = current_shares * price
                        cash_flow[i] = cash_in
                        current_capital_used -= amount # 賣出後本金回流
                        current_shares = 0.0
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
            
            # ★ 關鍵修改：報酬率分母改為「口袋需要準備的最大本金」
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

        # --- 新增功能：各策略績效大 PK 表格 ---
        st.subheader("🏆 策略績效大 PK (基於建議參數與固定投資額)")
        st.markdown(f"比較在所選區間內，每次交易投入 **${trade_amount:,}** 的整體表現：")
        
        # 新增全局「只買不賣」開關
        global_only_buy = st.checkbox("🔄 全局開啟「只買不賣」模式 (僅看買點，持續累積部位)", value=False, help="打勾後，SMA、RSI、KD 將忽略賣出訊號，每次觸發買點就固定加碼投入金額，直到期末。")
        
        results = []
        
        # 1. 買入持有 (基準)
        bh_cost = trade_amount
        bh_shares = trade_amount / df[close_col].iloc[0]
        bh_final_val = bh_shares * df[close_col].iloc[-1]
        bh_profit = bh_final_val - bh_cost
        bh_ret = (bh_profit / bh_cost) * 100
        days_held = (df.index[-1] - df.index[0]).days
        bh_cagr = ((bh_final_val / bh_cost) ** (365.25 / days_held) - 1) * 100 if days_held > 0 else 0
        results.append({"策略名稱": "長期持有 (Buy & Hold)", "實際動用最高本金": f"${bh_cost:,.0f}", "總獲利金額": f"${bh_profit:,.0f}", "總報酬率 (%)": bh_ret, "年化報酬率 (IRR %)": bh_cagr, "總交易次數": 1, "備註": "第一天買入後抱到期末"})
        
        # 2. SMA (10, 50)
        df_sma = df.copy()
        df_sma['Fast'] = df_sma[close_col].rolling(10).mean()
        df_sma['Slow'] = df_sma[close_col].rolling(50).mean()
        df_sma['Signal'] = np.where(df_sma['Fast'] > df_sma['Slow'], 1.0, 0.0)
        sma_cost, sma_prof, sma_ret, sma_irr, sma_trades = calc_fixed_amount_pnl(df_sma, 'Signal', close_col, trade_amount, only_buy=global_only_buy)
        results.append({"策略名稱": "SMA 雙均線交叉", "實際動用最高本金": f"${sma_cost:,.0f}", "總獲利金額": f"${sma_prof:,.0f}", "總報酬率 (%)": sma_ret, "年化報酬率 (IRR %)": sma_irr, "總交易次數": sma_trades, "備註": "短均線 10, 長均線 50"})
        
        # 3. RSI (14, 30, 70)
        df_rsi = df.copy()
        delta = df_rsi[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_rsi['RSI'] = 100 - (100 / (1 + rs))
        df_rsi['Signal'] = np.nan
        df_rsi.loc[df_rsi['RSI'] < 30, 'Signal'] = 1
        df_rsi.loc[df_rsi['RSI'] > 70, 'Signal'] = -1 if not global_only_buy else 0
        df_rsi['Signal'] = df_rsi['Signal'].ffill().fillna(0)
        
        rsi_cost, rsi_prof, rsi_ret, rsi_irr, rsi_trades = calc_fixed_amount_pnl(df_rsi, 'Signal', close_col, trade_amount, only_buy=global_only_buy)
        results.append({"策略名稱": "RSI 超買超賣", "實際動用最高本金": f"${rsi_cost:,.0f}", "總獲利金額": f"${rsi_prof:,.0f}", "總報酬率 (%)": rsi_ret, "年化報酬率 (IRR %)": rsi_irr, "總交易次數": rsi_trades, "備註": "週期 14, 買 <30, 賣 >70"})
        
        # 4. KD (9, 20, 80)
        df_kd = df.copy()
        high_col = col_map['high'] if 'high' in col_map else close_col
        low_col = col_map['low'] if 'low' in col_map else close_col
        min_low = df_kd[low_col].rolling(9).min()
        max_high = df_kd[high_col].rolling(9).max()
        df_kd['RSV'] = (df_kd[close_col] - min_low) / (max_high - min_low + 1e-8) * 100
        df_kd['K'] = df_kd['RSV'].ewm(com=2, adjust=False).mean()
        df_kd['Signal'] = np.nan
        df_kd.loc[df_kd['K'] < 20, 'Signal'] = 1
        df_kd.loc[df_kd['K'] > 80, 'Signal'] = -1 if not global_only_buy else 0
        df_kd['Signal'] = df_kd['Signal'].ffill().fillna(0)
        
        kd_cost, kd_prof, kd_ret, kd_irr, kd_trades = calc_fixed_amount_pnl(df_kd, 'Signal', close_col, trade_amount, only_buy=global_only_buy)
        results.append({"策略名稱": "KD 隨機指標", "實際動用最高本金": f"${kd_cost:,.0f}", "總獲利金額": f"${kd_prof:,.0f}", "總報酬率 (%)": kd_ret, "年化報酬率 (IRR %)": kd_irr, "總交易次數": kd_trades, "備註": "週期 9, 買 <20, 賣 >80"})
        
        # 5. DCA (定期定額)
        df_dca = df.copy()
        df_dca['Month'] = df_dca.index.to_period('M')
        first_days = df_dca.groupby('Month').head(1).index
        df_dca['Position'] = 0
        df_dca.loc[first_days, 'Position'] = 1
        df_dca['Shares'] = 0.0
        df_dca.loc[first_days, 'Shares'] = trade_amount / df_dca.loc[first_days, close_col]
        df_dca['Total_Shares'] = df_dca['Shares'].cumsum()
        df_dca['Total_Cost'] = (df_dca['Position'] * trade_amount).cumsum()
        df_dca['Total_Value'] = df_dca['Total_Shares'] * df_dca[close_col]
        
        dca_cost = df_dca['Total_Cost'].iloc[-1]
        dca_final = df_dca['Total_Value'].iloc[-1]
        dca_prof = dca_final - dca_cost
        dca_ret = (dca_prof / dca_cost * 100) if dca_cost > 0 else 0
        dca_trades = len(first_days)
        
        # DCA 計算 XIRR
        dca_cash_flows = [-trade_amount] * dca_trades + [dca_final]
        dca_dates = list(first_days) + [df.index[-1]]
        def xnpv_dca(rate, values, dates):
            if rate <= -1.0: return float('inf')
            d0 = dates[0]
            return sum([val / (1 + rate)**((d - d0).days / 365.25) for val, d in zip(values, dates)])
        
        dca_irr = 0.0
        if dca_cost > 0:
            try:
                dca_irr = optimize.newton(lambda r: xnpv_dca(r, dca_cash_flows, dca_dates), 0.0) * 100
            except:
                pass
                
        results.append({"策略名稱": "定期定額 (DCA)", "實際動用最高本金": f"${dca_cost:,.0f}", "總獲利金額": f"${dca_prof:,.0f}", "總報酬率 (%)": dca_ret, "年化報酬率 (IRR %)": dca_irr, "總交易次數": dca_trades, "備註": f"每月投入 ${trade_amount:,}"})
        
        # 產生表格並設定樣式
        comp_df = pd.DataFrame(results)
        st.dataframe(
            comp_df.style.format({
                "總報酬率 (%)": "{:.2f}",
                "年化報酬率 (IRR %)": "{:.2f}"
            }).background_gradient(subset=['年化報酬率 (IRR %)'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )
        st.divider()

        # 2. 側邊欄：策略設定
        st.sidebar.header("⚙️ 策略設定")
        strategy = st.sidebar.selectbox("選擇回測策略", [
            "SMA 雙均線交叉", 
            "RSI 超買超賣", 
            "KD 隨機指標", 
            "定期定額 (DCA)"
        ])

        # 3. 執行策略
        df_backtest = df.copy()
        
        # 預設一些共用欄位
        df_backtest['Signal'] = 0.0
        df_backtest['Position'] = 0.0
        
        if strategy == "SMA 雙均線交叉":
            fast_period = st.sidebar.slider("短天期均線 (Fast MA)", 5, 50, 10, help="建議數值：短期常看 5日或10日")
            slow_period = st.sidebar.slider("長天期均線 (Slow MA)", 20, 200, 50, help="建議數值：長期常看 20日(月線) 或 60日(季線)")
            only_buy = st.sidebar.checkbox("🔄 開啟「只買不賣」模式 (僅看買點持續累積)", value=global_only_buy)
            
            df_backtest['Fast_MA'] = df_backtest[close_col].rolling(window=fast_period).mean()
            df_backtest['Slow_MA'] = df_backtest[close_col].rolling(window=slow_period).mean()
            
            valid_idx = df_backtest.index[fast_period:]
            df_backtest.loc[valid_idx, 'Signal'] = np.where(
                df_backtest.loc[valid_idx, 'Fast_MA'] > df_backtest.loc[valid_idx, 'Slow_MA'], 1.0, 0.0)
            
            if only_buy:
                df_backtest['Position'] = np.where(df_backtest['Signal'] == 1, 1, 0)
            else:
                df_backtest['Position'] = df_backtest['Signal'].diff().fillna(df_backtest['Signal'])

        elif strategy == "RSI 超買超賣":
            rsi_period = st.sidebar.slider("RSI 週期", 5, 30, 14, help="建議數值：通常設定為 14")
            oversold = st.sidebar.slider("超賣線 (買進)", 10, 50, 30, help="建議數值：通常 RSI < 30 代表超賣，買進")
            overbought = st.sidebar.slider("超買線 (賣出)", 50, 90, 70, help="建議數值：通常 RSI > 70 代表超買，賣出")
            only_buy = st.sidebar.checkbox("🔄 開啟「只買不賣」模式 (僅看買點持續累積)", value=global_only_buy)
            
            delta = df_backtest[close_col].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df_backtest['RSI'] = 100 - (100 / (1 + rs))
            
            df_backtest['Signal'] = np.nan
            df_backtest.loc[df_backtest['RSI'] < oversold, 'Signal'] = 1
            df_backtest.loc[df_backtest['RSI'] > overbought, 'Signal'] = -1 if not only_buy else 0
            df_backtest['Signal'] = df_backtest['Signal'].ffill().fillna(0)
            
            if only_buy:
                df_backtest['Position'] = np.where(df_backtest['Signal'] == 1, 1, 0)
            else:
                df_backtest['Position'] = df_backtest['Signal'].diff().fillna(df_backtest['Signal'])

        elif strategy == "KD 隨機指標":
            kd_period = st.sidebar.slider("RSV 週期 (n)", 5, 30, 9, help="建議數值：通常設定為 9 天")
            kd_buy = st.sidebar.slider("超賣線 (K值買進)", 10, 50, 20, help="建議數值：K 值低於 20 準備買進")
            kd_sell = st.sidebar.slider("超買線 (K值賣出)", 50, 90, 80, help="建議數值：K 值高於 80 準備賣出")
            only_buy = st.sidebar.checkbox("🔄 開啟「只買不賣」模式 (僅看買點持續累積)", value=global_only_buy)
            
            high_col = col_map['high'] if 'high' in col_map else close_col
            low_col = col_map['low'] if 'low' in col_map else close_col

            min_low = df_backtest[low_col].rolling(window=kd_period).min()
            max_high = df_backtest[high_col].rolling(window=kd_period).max()
            df_backtest['RSV'] = (df_backtest[close_col] - min_low) / (max_high - min_low + 1e-8) * 100
            
            df_backtest['K'] = df_backtest['RSV'].ewm(com=2, adjust=False).mean()
            df_backtest['D'] = df_backtest['K'].ewm(com=2, adjust=False).mean()

            df_backtest['Signal'] = np.nan
            df_backtest.loc[df_backtest['K'] < kd_buy, 'Signal'] = 1
            df_backtest.loc[df_backtest['K'] > kd_sell, 'Signal'] = -1 if not only_buy else 0
            df_backtest['Signal'] = df_backtest['Signal'].ffill().fillna(0)
            
            if only_buy:
                df_backtest['Position'] = np.where(df_backtest['Signal'] == 1, 1, 0)
            else:
                df_backtest['Position'] = df_backtest['Signal'].diff().fillna(df_backtest['Signal'])

        elif strategy == "定期定額 (DCA)":
            df_backtest['Month'] = df_backtest.index.to_period('M')
            first_days = df_backtest.groupby('Month').head(1).index
            df_backtest['Position'] = 0
            df_backtest.loc[first_days, 'Position'] = 1
            df_backtest['Shares_Bought'] = 0.0
            df_backtest.loc[first_days, 'Shares_Bought'] = trade_amount / df_backtest.loc[first_days, close_col]
            df_backtest['Total_Shares'] = df_backtest['Shares_Bought'].cumsum()
            df_backtest['Total_Cost'] = (df_backtest['Position'] * trade_amount).cumsum()
            df_backtest['Total_Value'] = df_backtest['Total_Shares'] * df_backtest[close_col]

        # 清理 Position 使其只剩 1 (買) 與 -1 (賣)，0 為無動作
        if strategy != "定期定額 (DCA)":
            if not only_buy:
                df_backtest['Position'] = df_backtest['Position'].replace({-1.0: -1, 1.0: 1})
                df_backtest.loc[(df_backtest['Position'] != 1) & (df_backtest['Position'] != -1), 'Position'] = 0
            else:
                df_backtest['Position'] = df_backtest['Position'].replace({1.0: 1})
                df_backtest.loc[df_backtest['Position'] != 1, 'Position'] = 0

        # 4. 繪製圖表 (Plotly)
        st.subheader(f"📊 {strategy} 股價與交易訊號")
        fig = go.Figure()
        
        has_ohlc = all(c in col_map for c in ['open', 'high', 'low'])
        if has_ohlc:
            fig.add_trace(go.Candlestick(
                x=df_backtest.index, open=df_backtest[col_map['open']], high=df_backtest[col_map['high']],
                low=df_backtest[col_map['low']], close=df_backtest[close_col], name='K線'
            ))
        else:
            fig.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest[close_col], mode='lines', name='收盤價', line=dict(color='gray', width=1.5)))

        if strategy == "SMA 雙均線交叉":
            fig.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Fast_MA'], mode='lines', name=f'MA {fast_period}', line=dict(color='blue', width=1.5)))
            fig.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Slow_MA'], mode='lines', name=f'MA {slow_period}', line=dict(color='orange', width=1.5)))
            
        buy_signals = df_backtest[df_backtest['Position'] == 1]
        sell_signals = df_backtest[df_backtest['Position'] == -1]
        
        fig.add_trace(go.Scatter(
            x=buy_signals.index, y=buy_signals[close_col], mode='markers', name='買入信號',
            marker=dict(symbol='triangle-up', size=15, color='green', line=dict(width=1, color='darkgreen'))
        ))
        if strategy != "定期定額 (DCA)" and not only_buy:
            fig.add_trace(go.Scatter(
                x=sell_signals.index, y=sell_signals[close_col], mode='markers', name='賣出信號',
                marker=dict(symbol='triangle-down', size=15, color='red', line=dict(width=1, color='darkred'))
            ))

        fig.update_layout(height=600, template="plotly_white", xaxis_title="日期", yaxis_title="價格", hovermode="x unified")
        fig.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        if strategy == "RSI 超買超賣":
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['RSI'], mode='lines', name='RSI', line=dict(color='purple')))
            fig_rsi.add_hline(y=overbought, line_dash="dash", line_color="red")
            fig_rsi.add_hline(y=oversold, line_dash="dash", line_color="green")
            fig_rsi.update_layout(height=300, template="plotly_white", title="RSI 指標", yaxis_title="RSI 值")
            st.plotly_chart(fig_rsi, use_container_width=True)
            
        elif strategy == "KD 隨機指標":
            fig_kd = go.Figure()
            fig_kd.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['K'], mode='lines', name='K值', line=dict(color='blue')))
            fig_kd.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['D'], mode='lines', name='D值', line=dict(color='orange', dash='dot')))
            fig_kd.add_hline(y=kd_sell, line_dash="dash", line_color="red")
            fig_kd.add_hline(y=kd_buy, line_dash="dash", line_color="green")
            fig_kd.update_layout(height=300, template="plotly_white", title="KD 指標", yaxis_title="KD 值")
            st.plotly_chart(fig_kd, use_container_width=True)

        elif strategy == "定期定額 (DCA)":
            fig_dca = go.Figure()
            fig_dca.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Total_Value'], mode='lines', name='總資產價值', line=dict(color='green', width=2)))
            fig_dca.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Total_Cost'], mode='lines', name='累積投入成本', line=dict(color='gray', dash='dash')))
            fig_dca.update_layout(height=300, template="plotly_white", title="定期定額資產增長曲線", yaxis_title="資產 ($)")
            st.plotly_chart(fig_dca, use_container_width=True)

        # 5. 計算績效
        st.subheader("💰 實盤交易績效結算 (不含手續費)")
        
        if strategy == "定期定額 (DCA)":
            final_cost = df_backtest['Total_Cost'].iloc[-1]
            final_value = df_backtest['Total_Value'].iloc[-1]
            dca_prof = final_value - final_cost
            dca_return = (dca_prof / final_cost) * 100 if final_cost > 0 else 0
            
            # 使用前面算好的 dca_irr
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("總交易次數", f"{len(buy_signals)} 次買入")
            col2.metric("累積投入總成本", f"${final_cost:,.0f}")
            col3.metric("總獲利金額", f"${dca_prof:,.0f}")
            col4.metric("策略總報酬率", f"{dca_return:.2f}%")
            col5.metric("年化報酬率 (IRR)", f"{dca_irr:.2f}%")
        else:
            strat_cost, strat_prof, strat_ret, strat_irr, strat_trades = calc_fixed_amount_pnl(df_backtest, 'Signal', close_col, trade_amount)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("總交易次數", f"{strat_trades} 次買入")
            col2.metric("累積投入總成本", f"${strat_cost:,.0f}")
            col3.metric("總獲利金額", f"${strat_prof:,.0f}")
            col4.metric("策略總報酬率", f"{strat_ret:.2f}%")
            col5.metric("年化報酬率 (IRR)", f"{strat_irr:.2f}%")

    except Exception as e:
        st.error(f"處理檔案時發生錯誤：{e}")

else:
    st.info("👈 請從左側選單點擊 [Browse files] 載入您的 Excel 檔案以開始回測。")