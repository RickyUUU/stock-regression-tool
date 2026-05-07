# 📈 Stock Backtest Tool 股票回測可視化工具

An interactive stock backtesting tool built with **Streamlit**, supporting multiple strategies with bilingual Chinese/English UI. Upload your own data and compare strategy performance visually.

The tool can be used directly from streamlit : https://ricky-stock-regression-tool.streamlit.app/

![Python](https://img.shields.io/badge/python-3.9+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red) ![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **5 Strategies in One View** — Compare Buy & Hold, DCA, RSI, KD, and SMA crossover side by side
- **Interactive Charts** — Candlestick charts with buy/sell signals, plus RSI / KD / DCA sub-charts
- **Customizable Parameters** — Adjust RSI period, KD thresholds, SMA windows via sliders
- **Accumulate Only Mode** — Toggle buy-and-hold accumulation without selling
- **Bilingual UI** — Switch between Chinese and English on the fly
- **Excel / CSV Support** — Drop in your own stock data
- **P&L Summary** — Total return, capital used, trade count, profit amount

## 🧩 Strategies

| Strategy | Description |
|----------|-------------|
| **Buy & Hold** | Buy on day 1, hold to the end (baseline) |
| **DCA** | Dollar-cost averaging — invest a fixed amount each month |
| **RSI** | Buy when RSI < oversold threshold, sell when > overbought |
| **KD (Stochastic)** | Buy when K < lower band, sell when > upper band |
| **SMA Crossover** | Buy when fast MA crosses above slow MA, sell on crossover below |

## 🚀 Quick Start

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud

1. Push this repo to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your repo and deploy — no extra config needed

## 📁 File Structure

```
Stock Regression Tool/v1.3/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .gitignore
├── .streamlit/
│   └── config.toml        # Streamlit theme & server config
└── modules/
    ├── core_math.py       # P&L calculation & IRR
    ├── strategies.py      # Signal generation (SMA, RSI, KD, DCA)
    └── plotter.py         # Chart rendering with i18n support
```

## 📊 Getting Stock Data

No built-in data source is included. The easiest free way to get historical data:

### Google Sheets + GOOGLEFINANCE

1. Create a new Google Sheet
2. Enter this formula in cell **A1** (example: S&P 500):
   ```
   =GOOGLEFINANCE(".INX", "all", TODAY()-10000, TODAY(), "DAILY")
   ```
3. **File → Download → Microsoft Excel (.xlsx)**

Replace `.INX` with any ticker GOOGLEFINANCE supports, e.g. `AAPL`, `TSM`, `2330.TW`.

The downloaded `.xlsx` works directly with this tool — just upload it from the sidebar.

---

## 📦 Dependencies

`streamlit`, `pandas`, `plotly`, `numpy`, `openpyxl`, `scipy`, `matplotlib`

---

## 🇹🇼 中文說明

### 功能簡介

股票回測可視化工具，上傳 Excel 或 CSV 格式的股價資料，快速比較五種交易策略的績效。

### 支援策略

| 策略 | 說明 |
|------|------|
| **長期持有 (Buy & Hold)** | 第一天買入抱到最後，作為基準線 |
| **定期定額 (DCA)** | 每月固定日期投入固定金額 |
| **RSI 超買超賣** | RSI 低於超賣線買進，高於超買線賣出 |
| **KD 隨機指標** | K 值低於超賣線買進，高於超買線賣出 |
| **SMA 雙均線交叉** | 短天期均線突破長天期均線買進，跌破賣出 |

### 操作方式

1. 從左側邊欄上傳 Excel (`.xlsx`) 或 CSV 檔案
2. 選擇測試區間與投入金額
3. 系統自動跑出五種策略的績效比較表
4. 點選單一策略檢視圖表（K 線、買賣訊號、指標副圖）
5. 可透過滑桿調整各策略參數

### 欄位對應

上傳的資料需包含以下欄位（名稱自動辨識，中英文皆可）：

- **日期**：`date` / `日期` / `time`
- **收盤價**：`close` / `收盤價` / `price` / `最後價格`
- **開盤價**（選擇性）：`open` / `開盤價` — 有提供才會畫 K 線
- **最高價 / 最低價**（選擇性，KD 策略需要）：`high` / `low`

### 部署到 Streamlit Cloud

1. 將此專案推到 GitHub
2. 登入 [streamlit.io/cloud](https://streamlit.io/cloud)
3. 選擇 repo → Deploy → 完成

### 語言切換

側邊欄最上方有 `語言 / Language` 切換按鈕，可即時切換中文與英文介面。

### 如何取得股價資料

本工具不內建資料源，最簡單的免費取得方式：

1. 新增一個 Google 試算表
2. 在 **A1** 儲存格貼上公式（以標普500為例）：
   ```
   =GOOGLEFINANCE(".INX", "all", TODAY()-10000, TODAY(), "DAILY")
   ```
3. **檔案 → 下載 → Microsoft Excel (.xlsx)**

將 `.INX` 換成其他代碼即可，例如 `AAPL`、`TSM`、`2330.TW`。

下載後的 `.xlsx` 直接從側邊欄上傳就能開始回測。

---

## 📄 License

MIT
