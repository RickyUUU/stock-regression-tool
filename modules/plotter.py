import plotly.graph_objects as go
import streamlit as st

_LABELS = {
    "zh": {
        "chart_title": lambda s: f"\U0001f4ca {s} 股價與交易訊號",
        "candle": "K線", "close": "收盤價",
        "buy_signal": "買入信號", "sell_signal": "賣出信號",
        "xaxis": "日期", "yaxis": "價格",
        "rsi_title": "RSI 指標", "rsi_yaxis": "RSI 值",
        "kd_title": "KD 指標", "kd_yaxis": "KD 值",
        "dca_value": "總資產價值", "dca_cost": "累積投入成本",
        "dca_title": "資產增長曲線", "dca_yaxis": "資產 ($)",
    },
    "en": {
        "chart_title": lambda s: f"\U0001f4ca {s} Price & Signals",
        "candle": "Candlestick", "close": "Close Price",
        "buy_signal": "Buy Signal", "sell_signal": "Sell Signal",
        "xaxis": "Date", "yaxis": "Price",
        "rsi_title": "RSI Indicator", "rsi_yaxis": "RSI Value",
        "kd_title": "KD Indicator", "kd_yaxis": "KD Value",
        "dca_value": "Portfolio Value", "dca_cost": "Total Cost",
        "dca_title": "Asset Growth", "dca_yaxis": "Value ($)",
    },
}

_STRAT_NAMES = {
    "sma": {"zh": "SMA 雙均線交叉", "en": "SMA Crossover"},
    "rsi": {"zh": "RSI 超買超賣", "en": "RSI Strategy"},
    "kd": {"zh": "KD 隨機指標", "en": "KD Stochastic"},
    "dca": {"zh": "定期定額 (DCA)", "en": "Dollar Cost Avg (DCA)"},
}


def _tl(key, lang, strat_id=None):
    t = _LABELS.get(lang, _LABELS["zh"])
    val = t.get(key, key)
    if callable(val):
        name = _ts(strat_id, lang) if strat_id else ""
        return val(name)
    return val


def _ts(strat_id, lang):
    s = _STRAT_NAMES.get(strat_id)
    return s.get(lang, strat_id) if s else strat_id


def plot_main_chart(df_backtest, strategy_id, col_map, close_col,
                    fast_period=None, slow_period=None, only_buy=False,
                    lang="zh"):
    st.subheader(_tl("chart_title", lang, strategy_id))
    fig = go.Figure()

    has_ohlc = all(c in col_map for c in ['open', 'high', 'low'])
    if has_ohlc:
        fig.add_trace(go.Candlestick(
            x=df_backtest.index, open=df_backtest[col_map['open']],
            high=df_backtest[col_map['high']],
            low=df_backtest[col_map['low']],
            close=df_backtest[close_col], name=_tl("candle", lang)
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest[close_col],
            mode='lines', name=_tl("close", lang),
            line=dict(color='gray', width=1.5)
        ))

    if strategy_id == "sma" and fast_period and slow_period:
        fig.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Fast_MA'],
                      mode='lines', name=f'MA {fast_period}',
                      line=dict(color='blue', width=1.5)))
        fig.add_trace(go.Scatter(x=df_backtest.index, y=df_backtest['Slow_MA'],
                      mode='lines', name=f'MA {slow_period}',
                      line=dict(color='orange', width=1.5)))

    buy_signals = df_backtest[df_backtest['Position'] == 1]
    sell_signals = df_backtest[df_backtest['Position'] == -1]

    fig.add_trace(go.Scatter(
        x=buy_signals.index, y=buy_signals[close_col],
        mode='markers', name=_tl("buy_signal", lang),
        marker=dict(symbol='triangle-up', size=15, color='green',
                    line=dict(width=1, color='darkgreen'))
    ))

    if strategy_id != "dca" and not only_buy:
        fig.add_trace(go.Scatter(
            x=sell_signals.index, y=sell_signals[close_col],
            mode='markers', name=_tl("sell_signal", lang),
            marker=dict(symbol='triangle-down', size=15, color='red',
                        line=dict(width=1, color='darkred'))
        ))

    fig.update_layout(
        height=600, template="plotly_white",
        xaxis_title=_tl("xaxis", lang),
        yaxis_title=_tl("yaxis", lang), hovermode="x unified"
    )
    fig.update_xaxes(rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    return buy_signals, sell_signals


def plot_sub_chart(df_backtest, strategy_id, overbought=None, oversold=None,
                   kd_buy=None, kd_sell=None, lang="zh"):
    if strategy_id == "rsi":
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest['RSI'],
            mode='lines', name='RSI', line=dict(color='purple')
        ))
        fig_rsi.add_hline(y=overbought, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=oversold, line_dash="dash", line_color="green")
        fig_rsi.update_layout(
            height=300, template="plotly_white",
            title=_tl("rsi_title", lang),
            yaxis_title=_tl("rsi_yaxis", lang)
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    elif strategy_id == "kd":
        fig_kd = go.Figure()
        fig_kd.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest['K'],
            mode='lines', name='K', line=dict(color='blue')
        ))
        fig_kd.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest['D'],
            mode='lines', name='D', line=dict(color='orange', dash='dot')
        ))
        fig_kd.add_hline(y=kd_sell, line_dash="dash", line_color="red")
        fig_kd.add_hline(y=kd_buy, line_dash="dash", line_color="green")
        fig_kd.update_layout(
            height=300, template="plotly_white",
            title=_tl("kd_title", lang),
            yaxis_title=_tl("kd_yaxis", lang)
        )
        st.plotly_chart(fig_kd, use_container_width=True)

    elif strategy_id == "dca":
        fig_dca = go.Figure()
        fig_dca.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest['Total_Value'],
            mode='lines', name=_tl("dca_value", lang),
            line=dict(color='green', width=2)
        ))
        fig_dca.add_trace(go.Scatter(
            x=df_backtest.index, y=df_backtest['Total_Cost'],
            mode='lines', name=_tl("dca_cost", lang),
            line=dict(color='gray', dash='dash')
        ))
        fig_dca.update_layout(
            height=300, template="plotly_white",
            title=_tl("dca_title", lang),
            yaxis_title=_tl("dca_yaxis", lang)
        )
        st.plotly_chart(fig_dca, use_container_width=True)
