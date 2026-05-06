import plotly.graph_objects as go
import streamlit as st

def plot_main_chart(df_backtest, strategy, col_map, close_col, fast_period=None, slow_period=None, only_buy=False):
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

    if strategy == "SMA 雙均線交叉" and fast_period and slow_period:
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
    return buy_signals, sell_signals

def plot_sub_chart(df_backtest, strategy, overbought=None, oversold=None, kd_buy=None, kd_sell=None):
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