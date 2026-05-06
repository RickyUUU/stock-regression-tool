import streamlit as st
import pandas as pd
import numpy as np

from modules.core_math import calc_fixed_amount_pnl
from modules.strategies import apply_sma, apply_rsi, apply_kd, apply_dca
from modules.plotter import plot_main_chart, plot_sub_chart

st.set_page_config(page_title="Stock Backtest Tool v1.3", layout="wide")

# ===== I18N =====

STRATEGIES = {
    "sma": {"zh": "SMA 雙均線交叉", "en": "SMA Crossover"},
    "rsi": {"zh": "RSI 超買超賣", "en": "RSI Strategy"},
    "kd": {"zh": "KD 隨機指標", "en": "KD Stochastic"},
    "dca": {"zh": "定期定額 (DCA)", "en": "Dollar Cost Avg (DCA)"},
}

_T = {
    "zh": {
        "title": "📈 股票回測工具 v1.3",
        "data_load": "📁 資料載入",
        "file_uploader": "📥 載入 Excel 或 CSV",
        "load_success": lambda n: f"成功載入: {n}",
        "no_close_col": "找不到收盤價 (Close) 欄位，請確認資料格式。",
        "test_period": "📅 測試區間設定",
        "start_date": "開始日期",
        "end_date": "結束日期",
        "data_preview": "🔍 預覽過濾後的資料",
        "fund_setting": "💰 資金設定",
        "trade_amount": "每次交易固定投入金額 ($)",
        "pk_title": "🏆 策略績效比較",
        "pk_per_trade": lambda amt: f"每次投入 **${amt:,}** ：",
        "only_buy_global": "🔄 只買不賣 (持續累積)",
        "only_buy": "🔄 只買不賣",
        "strategy_select": "選擇策略",
        "strat_setting": "⚙️ 策略設定",
        "result_title": "💰 績效結算",
        "lang_label": "語言 / Language",
        # PK table columns
        "col_strategy": "策略名稱",
        "col_capital": "實際動用最高本金",
        "col_profit": "總獲利金額",
        "col_return": "總報酬率 (%)",
        "col_trades": "總交易次數",
        "col_note": "備註",
        # Buy & Hold
        "bh_name": "長期持有 (Buy & Hold)",
        "bh_note": "第一天買入後抱到期末",
        # Notes
        "sma_note": "短 10, 長 50",
        "rsi_note": "RSI 14, <30 買, >70 賣",
        "kd_note": "RSV 9, K<20 買, K>80 賣",
        "dca_note": lambda amt: f"每月投入 ${amt:,}",
        # Metrics
        "metric_trades": lambda n: f"{n} 次操作",
        "metric_cost": "累積投入總成本",
        "metric_profit": "總獲利金額",
        "metric_return": "策略總報酬率",
        "metric_capital": "實際動用最高本金",
        # Slider labels
        "fast_ma": "短天期均線",
        "slow_ma": "長天期均線",
        "rsi_period": "RSI 週期",
        "oversold": "超賣線 (買進)",
        "overbought": "超買線 (賣出)",
        "rsv_period": "RSV 週期",
        "kd_buy_line": "K值買進線",
        "kd_sell_line": "K值賣出線",
        # Upload prompt
        "upload_prompt": "👈 從左側上傳 Excel 或 CSV 開始",
        # Error
        "process_error": lambda e: f"處理檔案時發生錯誤：{e}",
    },
    "en": {
        "title": "📈 Stock Backtest Tool v1.3",
        "data_load": "📁 Data Load",
        "file_uploader": "📥 Load Excel or CSV",
        "load_success": lambda n: f"Loaded: {n}",
        "no_close_col": "Cannot find Close column. Please check your data format.",
        "test_period": "📅 Test Period",
        "start_date": "Start Date",
        "end_date": "End Date",
        "data_preview": "🔍 Preview Filtered Data",
        "fund_setting": "💰 Fund Settings",
        "trade_amount": "Fixed Investment per Trade ($)",
        "pk_title": "🏆 Strategy Comparison",
        "pk_per_trade": lambda amt: f"Fixed **${amt:,}** per trade:",
        "only_buy_global": "🔄 Accumulate Only (No Sell)",
        "only_buy": "🔄 Accumulate Only",
        "strategy_select": "Select Strategy",
        "strat_setting": "⚙️ Strategy Settings",
        "result_title": "💰 P&L Summary",
        "lang_label": "語言 / Language",
        # PK table columns
        "col_strategy": "Strategy",
        "col_capital": "Max Capital Used",
        "col_profit": "Total Profit",
        "col_return": "Total Return (%)",
        "col_trades": "Total Trades",
        "col_note": "Notes",
        # Buy & Hold
        "bh_name": "Buy & Hold",
        "bh_note": "Buy on day 1 and hold to the end",
        # Notes
        "sma_note": "Fast 10, Slow 50",
        "rsi_note": "RSI 14, <30 buy, >70 sell",
        "kd_note": "RSV 9, K<20 buy, K>80 sell",
        "dca_note": lambda amt: f"Monthly ${amt:,}",
        # Metrics
        "metric_trades": lambda n: f"{n} trades",
        "metric_cost": "Total Cost Invested",
        "metric_profit": "Total Profit",
        "metric_return": "Strategy Return",
        "metric_capital": "Max Capital Used",
        # Slider labels
        "fast_ma": "Fast MA",
        "slow_ma": "Slow MA",
        "rsi_period": "RSI Period",
        "oversold": "Oversold (Buy)",
        "overbought": "Overbought (Sell)",
        "rsv_period": "RSV Period",
        "kd_buy_line": "K Buy Line",
        "kd_sell_line": "K Sell Line",
        # Upload prompt
        "upload_prompt": "👈 Upload Excel or CSV from the sidebar",
        # Error
        "process_error": lambda e: f"Error processing file: {e}",
    },
}


def _tl(key, lang="zh"):
    t = _T.get(lang, _T["zh"])
    return t.get(key, key)


def _ts(strat_id, lang="zh"):
    s = STRATEGIES.get(strat_id)
    return s.get(lang, strat_id) if s else strat_id


# ===== Language selector =====
lang_option = st.sidebar.radio("語言 / Language", ["中文", "English"], index=0)
lang = "en" if lang_option == "English" else "zh"

st.title(_tl("title", lang))

# ===== Sidebar: File Upload =====
st.sidebar.header(_tl("data_load", lang))
uploaded_file = st.sidebar.file_uploader(_tl("file_uploader", lang), type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        # Data loading
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.sidebar.success(_tl("load_success", lang)(uploaded_file.name))

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
            st.error(_tl("no_close_col", lang))
            st.stop()

        min_date = df.index.min().date()
        max_date = df.index.max().date()

        # Test period
        st.sidebar.header(_tl("test_period", lang))
        start_date = st.sidebar.date_input(_tl("start_date", lang), min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input(_tl("end_date", lang), max_date, min_value=min_date, max_value=max_date)

        df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

        with st.expander(_tl("data_preview", lang)):
            st.dataframe(df.tail())

        # Fund settings
        st.sidebar.header(_tl("fund_setting", lang))
        trade_amount = st.sidebar.number_input(_tl("trade_amount", lang), min_value=1000, value=100000, step=10000)

        # ===== Strategy PK Table =====
        st.subheader(_tl("pk_title", lang))
        st.markdown(_tl("pk_per_trade", lang)(trade_amount))

        global_only_buy = st.checkbox(_tl("only_buy_global", lang), value=True)

        results = []

        # 1. Buy & Hold
        bh_cost = trade_amount
        bh_shares = trade_amount / df[close_col].iloc[0]
        bh_final_val = bh_shares * df[close_col].iloc[-1]
        bh_profit = bh_final_val - bh_cost
        bh_ret = (bh_profit / bh_cost) * 100
        results.append({
            _tl("col_strategy", lang): _tl("bh_name", lang),
            _tl("col_capital", lang): f"${bh_cost:,.0f}",
            _tl("col_profit", lang): f"${bh_profit:,.0f}",
            _tl("col_return", lang): bh_ret,
            _tl("col_trades", lang): 1,
            _tl("col_note", lang): _tl("bh_note", lang),
        })

        # 2. DCA
        df_dca_pk = apply_dca(df, close_col, trade_amount)
        dca_cost = df_dca_pk['Total_Cost'].iloc[-1]
        dca_final = df_dca_pk['Total_Value'].iloc[-1]
        dca_prof = dca_final - dca_cost
        dca_ret = (dca_prof / dca_cost * 100) if dca_cost > 0 else 0
        dca_trades = (df_dca_pk['Position'] == 1).sum()
        results.append({
            _tl("col_strategy", lang): _ts("dca", lang),
            _tl("col_capital", lang): f"${dca_cost:,.0f}",
            _tl("col_profit", lang): f"${dca_prof:,.0f}",
            _tl("col_return", lang): dca_ret,
            _tl("col_trades", lang): dca_trades,
            _tl("col_note", lang): _tl("dca_note", lang)(trade_amount),
        })

        # 3. RSI
        df_rsi_pk = apply_rsi(df, close_col, 14, 30, 70, only_buy=global_only_buy)
        rsi_cost, rsi_prof, rsi_ret, _, rsi_trades = calc_fixed_amount_pnl(
            df_rsi_pk, 'Position', close_col, trade_amount, only_buy=global_only_buy)
        results.append({
            _tl("col_strategy", lang): _ts("rsi", lang),
            _tl("col_capital", lang): f"${rsi_cost:,.0f}",
            _tl("col_profit", lang): f"${rsi_prof:,.0f}",
            _tl("col_return", lang): rsi_ret,
            _tl("col_trades", lang): rsi_trades,
            _tl("col_note", lang): _tl("rsi_note", lang),
        })

        # 4. KD
        high_col = col_map.get('high', close_col)
        low_col = col_map.get('low', close_col)
        df_kd_pk = apply_kd(df, close_col, high_col, low_col, 9, 20, 80, only_buy=global_only_buy)
        kd_cost, kd_prof, kd_ret, _, kd_trades = calc_fixed_amount_pnl(
            df_kd_pk, 'Position', close_col, trade_amount, only_buy=global_only_buy)
        results.append({
            _tl("col_strategy", lang): _ts("kd", lang),
            _tl("col_capital", lang): f"${kd_cost:,.0f}",
            _tl("col_profit", lang): f"${kd_prof:,.0f}",
            _tl("col_return", lang): kd_ret,
            _tl("col_trades", lang): kd_trades,
            _tl("col_note", lang): _tl("kd_note", lang),
        })

        # 5. SMA
        df_sma_pk = apply_sma(df, close_col, 10, 50, only_buy=global_only_buy)
        sma_cost, sma_prof, sma_ret, _, sma_trades = calc_fixed_amount_pnl(
            df_sma_pk, 'Position', close_col, trade_amount, only_buy=global_only_buy)
        results.append({
            _tl("col_strategy", lang): _ts("sma", lang),
            _tl("col_capital", lang): f"${sma_cost:,.0f}",
            _tl("col_profit", lang): f"${sma_prof:,.0f}",
            _tl("col_return", lang): sma_ret,
            _tl("col_trades", lang): sma_trades,
            _tl("col_note", lang): _tl("sma_note", lang),
        })

        # Display PK table
        comp_df = pd.DataFrame(results)
        ret_col = _tl("col_return", lang)

        def _clr(val):
            if pd.isna(val) or val == 0:
                return ''
            if val > 0:
                g = max(100, 255 - int(min(val / 50, 1) * 155))
                return f'background-color: rgb({g}, 255, {g})'
            else:
                r = max(100, 255 - int(min(abs(val) / 50, 1) * 155))
                return f'background-color: rgb(255, {r}, {r})'

        st.dataframe(
            comp_df.style
                   .format({ret_col: "{:.2f}"})
                   .map(_clr, subset=[ret_col]),
            use_container_width=True, hide_index=True
        )
        st.divider()

        # ===== Sidebar: Single Strategy =====
        st.sidebar.header(_tl("strat_setting", lang))
        display_options = {_ts(sid, lang): sid for sid in ["dca", "rsi", "kd", "sma"]}
        selected_display = st.sidebar.selectbox(_tl("strategy_select", lang), list(display_options.keys()))
        strategy_id = display_options[selected_display]

        only_buy = st.checkbox(_tl("only_buy", lang), value=global_only_buy)

        df_backtest = None

        # Generate strategy signals
        if strategy_id == "sma":
            fast_p = st.sidebar.slider(_tl("fast_ma", lang), 5, 50, 10)
            slow_p = st.sidebar.slider(_tl("slow_ma", lang), 20, 200, 50)
            df_backtest = apply_sma(df, close_col, fast_p, slow_p, only_buy)
            buy_signals, sell_signals = plot_main_chart(
                df_backtest, strategy_id, col_map, close_col,
                fast_p, slow_p, only_buy, lang=lang)

        elif strategy_id == "rsi":
            rsi_p = st.sidebar.slider(_tl("rsi_period", lang), 5, 30, 14)
            oversold = st.sidebar.slider(_tl("oversold", lang), 10, 50, 30)
            overbought = st.sidebar.slider(_tl("overbought", lang), 50, 90, 70)
            df_backtest = apply_rsi(df, close_col, rsi_p, oversold, overbought, only_buy)
            buy_signals, sell_signals = plot_main_chart(
                df_backtest, strategy_id, col_map, close_col,
                only_buy=only_buy, lang=lang)
            plot_sub_chart(df_backtest, strategy_id, overbought=overbought,
                           oversold=oversold, lang=lang)

        elif strategy_id == "kd":
            kd_p = st.sidebar.slider(_tl("rsv_period", lang), 5, 30, 9)
            kd_buy = st.sidebar.slider(_tl("kd_buy_line", lang), 10, 50, 20)
            kd_sell = st.sidebar.slider(_tl("kd_sell_line", lang), 50, 90, 80)
            df_backtest = apply_kd(df, close_col, high_col, low_col, kd_p, kd_buy, kd_sell, only_buy)
            buy_signals, sell_signals = plot_main_chart(
                df_backtest, strategy_id, col_map, close_col,
                only_buy=only_buy, lang=lang)
            plot_sub_chart(df_backtest, strategy_id, kd_buy=kd_buy,
                           kd_sell=kd_sell, lang=lang)

        elif strategy_id == "dca":
            df_backtest = apply_dca(df, close_col, trade_amount)
            buy_signals, sell_signals = plot_main_chart(
                df_backtest, strategy_id, col_map, close_col, lang=lang)
            plot_sub_chart(df_backtest, strategy_id, lang=lang)

        # ===== Single Strategy P&L =====
        st.subheader(_tl("result_title", lang))

        if strategy_id == "dca":
            d_cost = df_backtest['Total_Cost'].iloc[-1]
            d_final = df_backtest['Total_Value'].iloc[-1]
            d_prof = d_final - d_cost
            d_ret = (d_prof / d_cost) * 100 if d_cost > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(_tl("col_trades", lang), _tl("metric_trades", lang)(len(buy_signals)))
            c2.metric(_tl("metric_cost", lang), f"${d_cost:,.0f}")
            c3.metric(_tl("metric_profit", lang), f"${d_prof:,.0f}")
            c4.metric(_tl("metric_return", lang), f"{d_ret:.2f}%")
        else:
            strat_cost, strat_prof, strat_ret, _, strat_trades = calc_fixed_amount_pnl(
                df_backtest, 'Position', close_col, trade_amount, only_buy=only_buy)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(_tl("col_trades", lang), _tl("metric_trades", lang)(strat_trades))
            c2.metric(_tl("metric_capital", lang), f"${strat_cost:,.0f}")
            c3.metric(_tl("metric_profit", lang), f"${strat_prof:,.0f}")
            c4.metric(_tl("metric_return", lang), f"{strat_ret:.2f}%")

    except Exception as e:
        st.error(_tl("process_error", lang)(e))

else:
    st.info(_tl("upload_prompt", lang))
