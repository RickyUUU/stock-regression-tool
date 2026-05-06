import streamlit as st
import pandas as pd
import numpy as np
import scipy.optimize as optimize

# 匯入我們自建的模組
from modules.core_math import calc_fixed_amount_pnl
from modules.strategies import apply_sma, apply_rsi, apply_kd, apply_dca
from modules.plotter import plot_main_chart, plot_sub_chart

# 設定頁面
st.set_page_config(page_title="股票回測可視化工具", layout="wide")
st.title("📈 股票策略可視化回測工具 (v1.2 穩定版)")

# 1. 側邊欄：檔案上傳
st.sidebar.header("📁 資料載入")
uploaded_file = st.sidebar.file_uploader("📥 請載入 Excel 或 CSV 檔案", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # 資料讀取與前處理
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.sidebar.success(f"成功載入: {uploaded_file.name}")
        
        col_map = {str(c).lower().strip(): c for c in df.columns}
        
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

        min_date = df.index.min().date()
        max_date = df.index.min().date() if pd.isna(df.index.max()) else df.index.max().date()

        # 測試區間與資金設定
        st.sidebar.header("📅 測試區間設定")
        start_date = st.sidebar.date_input("開始日期", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("結束日期", max_date, min_value=min_date, max_value=max_date)
        
        df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

        with st.expander("🔍 預覽過濾後的資料"):
            st.dataframe(df.tail())

        st.sidebar.header("💰 資金設定")
        trade_amount = st.sidebar.number_input("每次交易固定投入金額 ($)", min_value=1000, value=100000, step=10000)

        # --- 策略績效大 PK 表格 ---
        st.subheader("🏆 策略績效大 PK (基於建議參數與固定投資額)")
        st.markdown(f"比較在所選區間內，每次交易投入 **${trade_amount:,}** 的整體表現：")
        
        col_cb1, col_cb2 = st.columns(2)
        with col_cb1:
            global_only_buy = st.checkbox("🔄 全局「只買不賣」模式 (僅看買點，持續累積部位)", value=False)
        with col_cb2:
            global_continuous_buy = st.checkbox("🔄 全局「連續訊號加碼」模式 (只要符合條件就一直買)", value=False)
        
        results = []
        
        # 1. 買入持有
        bh_cost = trade_amount
        bh_shares = trade_amount / df[close_col].iloc[0]
        bh_final_val = bh_shares * df[close_col].iloc[-1]
        bh_profit = bh_final_val - bh_cost
        bh_ret = (bh_profit / bh_cost) * 100
        days_held = (df.index[-1] - df.index[0]).days
        bh_cagr = ((bh_final_val / bh_cost) ** (365.25 / days_held) - 1) * 100 if days_held > 0 else 0
        results.append({"策略名稱": "長期持有 (Buy & Hold)", "實際動用最高本金": f"${bh_cost:,.0f}", "總獲利金額": f"${bh_profit:,.0f}", "總報酬率 (%)": bh_ret, "年化報酬率 (IRR %)": bh_cagr, "總交易次數": 1, "備註": "第一天買入後抱到期末"})
        
        # 2. SMA PK
        df_sma_pk = apply_sma(df, close_col, 10, 50, global_only_buy, global_continuous_buy)
        sma_cost, sma_prof, sma_ret, sma_irr, sma_trades = calc_fixed_amount_pnl(df_sma_pk, 'Position', close_col, trade_amount, global_only_buy, global_continuous_buy)
        results.append({"策略名稱": "SMA 雙均線交叉", "實際動用最高本金": f"${sma_cost:,.0f}", "總獲利金額": f"${sma_prof:,.0f}", "總報酬率 (%)": sma_ret, "年化報酬率 (IRR %)": sma_irr, "總交易次數": sma_trades, "備註": "短 10, 長 50"})
        
        # 3. RSI PK
        df_rsi_pk = apply_rsi(df, close_col, 14, 30, 70, global_only_buy, global_continuous_buy)
        rsi_cost, rsi_prof, rsi_ret, rsi_irr, rsi_trades = calc_fixed_amount_pnl(df_rsi_pk, 'Position', close_col, trade_amount, global_only_buy, global_continuous_buy)
        results.append({"策略名稱": "RSI 超買超賣", "實際動用最高本金": f"${rsi_cost:,.0f}", "總獲利金額": f"${rsi_prof:,.0f}", "總報酬率 (%)": rsi_ret, "年化報酬率 (IRR %)": rsi_irr, "總交易次數": rsi_trades, "備註": "RSI 14, <30 買, >70 賣"})
        
        # 4. KD PK
        high_col = col_map.get('high', close_col)
        low_col = col_map.get('low', close_col)
        df_kd_pk = apply_kd(df, close_col, high_col, low_col, 9, 20, 80, global_only_buy, global_continuous_buy)
        kd_cost, kd_prof, kd_ret, kd_irr, kd_trades = calc_fixed_amount_pnl(df_kd_pk, 'Position', close_col, trade_amount, global_only_buy, global_continuous_buy)
        results.append({"策略名稱": "KD 隨機指標", "實際動用最高本金": f"${kd_cost:,.0f}", "總獲利金額": f"${kd_prof:,.0f}", "總報酬率 (%)": kd_ret, "年化報酬率 (IRR %)": kd_irr, "總交易次數": kd_trades, "備註": "RSV 9, K<20 買, K>80 賣"})
        
        # 5. DCA PK
        df_dca_pk = apply_dca(df, close_col, trade_amount)
        dca_cost = df_dca_pk['Total_Cost'].iloc[-1]
        dca_final = df_dca_pk['Total_Value'].iloc[-1]
        dca_prof = dca_final - dca_cost
        dca_ret = (dca_prof / dca_cost * 100) if dca_cost > 0 else 0
        dca_trades = (df_dca_pk['Position'] == 1).sum()
        dca_cash_flows = [-trade_amount] * dca_trades + [dca_final]
        first_days = df_dca_pk[df_dca_pk['Position'] == 1].index
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
        
        # 顯示 PK 表格
        comp_df = pd.DataFrame(results)
        st.dataframe(
            comp_df.style.format({"總報酬率 (%)": "{:.2f}", "年化報酬率 (IRR %)": "{:.2f}"})
                   .background_gradient(subset=['年化報酬率 (IRR %)'], cmap='RdYlGn'),
            use_container_width=True, hide_index=True
        )
        st.divider()

        # --- 側邊欄：單一策略設定 ---
        st.sidebar.header("⚙️ 單一策略分析")
        strategy = st.sidebar.selectbox("選擇回測策略", ["SMA 雙均線交叉", "RSI 超買超賣", "KD 隨機指標", "定期定額 (DCA)"])
        
        col_sc1, col_sc2 = st.sidebar.columns(2)
        with col_sc1:
            only_buy = st.checkbox("🔄 只買不賣", value=global_only_buy)
        with col_sc2:
            continuous_buy = st.checkbox("🔄 連續加碼", value=global_continuous_buy)

        df_backtest = None
        
        # 產生單一策略訊號與持倉
        if strategy == "SMA 雙均線交叉":
            fast_p = st.sidebar.slider("短天期均線 (Fast MA)", 5, 50, 10)
            slow_p = st.sidebar.slider("長天期均線 (Slow MA)", 20, 200, 50)
            df_backtest = apply_sma(df, close_col, fast_p, slow_p, only_buy, continuous_buy)
            buy_signals, sell_signals = plot_main_chart(df_backtest, strategy, col_map, close_col, fast_p, slow_p, only_buy)

        elif strategy == "RSI 超買超賣":
            rsi_p = st.sidebar.slider("RSI 週期", 5, 30, 14)
            oversold = st.sidebar.slider("超賣線 (買進)", 10, 50, 30)
            overbought = st.sidebar.slider("超買線 (賣出)", 50, 90, 70)
            df_backtest = apply_rsi(df, close_col, rsi_p, oversold, overbought, only_buy, continuous_buy)
            buy_signals, sell_signals = plot_main_chart(df_backtest, strategy, col_map, close_col, only_buy=only_buy)
            plot_sub_chart(df_backtest, strategy, overbought=overbought, oversold=oversold)

        elif strategy == "KD 隨機指標":
            kd_p = st.sidebar.slider("RSV 週期 (n)", 5, 30, 9)
            kd_buy = st.sidebar.slider("超賣線 (K值買進)", 10, 50, 20)
            kd_sell = st.sidebar.slider("超買線 (K值賣出)", 50, 90, 80)
            df_backtest = apply_kd(df, close_col, high_col, low_col, kd_p, kd_buy, kd_sell, only_buy, continuous_buy)
            buy_signals, sell_signals = plot_main_chart(df_backtest, strategy, col_map, close_col, only_buy=only_buy)
            plot_sub_chart(df_backtest, strategy, kd_buy=kd_buy, kd_sell=kd_sell)

        elif strategy == "定期定額 (DCA)":
            df_backtest = apply_dca(df, close_col, trade_amount)
            buy_signals, sell_signals = plot_main_chart(df_backtest, strategy, col_map, close_col)
            plot_sub_chart(df_backtest, strategy)

        # 清理圖表繪製用的 Position 殘留 (若有需要)，但模組內已經清理乾淨，這部分繪圖邏輯整合在 plotter 中
        
        # --- 單一策略實盤績效結算 ---
        st.subheader("💰 實盤交易績效結算 (不含手續費)")
        
        if strategy == "定期定額 (DCA)":
            d_cost = df_backtest['Total_Cost'].iloc[-1]
            d_final = df_backtest['Total_Value'].iloc[-1]
            d_prof = d_final - d_cost
            d_ret = (d_prof / d_cost) * 100 if d_cost > 0 else 0
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("總交易次數", f"{len(buy_signals)} 次操作")
            c2.metric("累積投入總成本", f"${d_cost:,.0f}")
            c3.metric("總獲利金額", f"${d_prof:,.0f}")
            c4.metric("策略總報酬率", f"{d_ret:.2f}%")
            c5.metric("年化報酬率 (IRR)", f"{dca_irr:.2f}%") # 這裡簡化使用上方算好的 dca_irr
        else:
            strat_cost, strat_prof, strat_ret, strat_irr, strat_trades = calc_fixed_amount_pnl(
                df_backtest, 'Position', close_col, trade_amount, only_buy=only_buy, continuous_buy=continuous_buy)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("總交易次數", f"{strat_trades} 次操作")
            c2.metric("實際動用最高本金", f"${strat_cost:,.0f}")
            c3.metric("總獲利金額", f"${strat_prof:,.0f}")
            c4.metric("策略總報酬率", f"{strat_ret:.2f}%")
            c5.metric("年化報酬率 (IRR)", f"{strat_irr:.2f}%")

    except Exception as e:
        st.error(f"處理檔案時發生錯誤：{e}")

else:
    st.info("👈 請從左側選單點擊 [Browse files] 載入您的 Excel 檔案以開始回測。")