import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from streamlit_lightweight_charts import renderLightweightCharts

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Technical Indicators සහ Live Auto-Draw Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

# 💡 ජනප්‍රිය වෙළඳපොලවල් සහිත සජීවී ලැයිස්තුව
st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න (Select Market):")

category = st.radio(
    "ප්‍රවර්ගය තෝරන්න (Select Category):",
    ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)", "💱 ෆොරෙක්ස් (Forex)", "✨ වටිනา ලෝහ සහ තෙල් (Metals & Energies)"],
    horizontal=True
)

if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)":
    market_options = {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD",
        "Solana (SOL/USD)": "SOL-USD",
        "Ripple (XRP/USD)": "XRP-USD",
        "Binance Coin (BNB/USD)": "BNB-USD"
    }
elif category == "💱 ෆොරෙක්ස් (Forex)":
    market_options = {
        "Euro / US Dollar (EUR/USD)": "EURUSD=X",
        "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X",
        "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X"
    }
else:
    market_options = {
        "රන් / Gold (XAU/USD)": "GC=F",
        "රීදි / Silver (XAG/USD)": "SI=F",
        "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"
    }

selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Coin/Pair):", list(market_options.keys()))
ticker = market_options[selected_display_name]

# --- TIMEFRAME SELECTOR ---
tf_display = st.selectbox(
    "Timeframe එක තෝරන්න (Select Timeframe):", 
    ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"]
)

tf_mapping = {
    "5 min": {"yf": "5m", "period": "7d"},
    "15 min": {"yf": "15m", "period": "7d"},
    "30 min": {"yf": "30m", "period": "30d"},
    "1 hour": {"yf": "1h", "period": "60d"},
    "4 hour": {"yf": "4h", "period": "90d"},
    "1 day": {"yf": "1d", "period": "max"}
}

selected_tf = tf_mapping[tf_display]

# 2. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf, prd):
    df = yf.download(symbol, period=prd, interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, selected_tf["yf"], selected_tf["period"])

if not df.empty and len(df) > 30:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # --- 3. ADVANCED INDICATORS ENGINEERING ---
    df['Returns'] = df['Close'].pct_change()
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['StdDev'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (df['StdDev'] * 2)
    df['BB_Lower'] = df['MA20'] - (df['StdDev'] * 2)
    
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    df.dropna(inplace=True)
    
    # 4. Machine Learning Model
    features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns']
    X = df[features]
    y = df['Target']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    prediction = model.predict(X.iloc[[-1]])[0]
    probability = model.predict_proba(X.iloc[[-1]])[0]
    
    current_price = float(df['Close'].to_numpy()[-1])
    volatility = float((df['High'] - df['Low']).rolling(window=14).mean().to_numpy()[-1])
    ai_confidence = max(probability) * 100
    
    if prediction == 1:
        tp_price = current_price + (volatility * 2.0)
        sl_price = current_price - (volatility * 1.5)
    else:
        tp_price = current_price - (volatility * 2.0)
        sl_price = current_price + (volatility * 1.5)

    # --- 5. SCREEN OUTPUT DISPLAY ---
    st.write("---")
    st.subheader(f"📊 {selected_display_name} ({tf_display}) PRO AI විශ්ලේෂණය:")
    st.metric(label="📊 සජීවී වෙළඳපොල මිල (Live Price)", value=f"${current_price:.4f}")
    
    st.write("### 🚨 AI තීරණය (AI Signal Output):")
    
    # --- 🔄 ඔයා ඉල්ලපු විදිහට හරියටම ⬆️ GREEN සහ ⬇️ RED ඊතල සකසා ඇත ---
    if prediction == 1:
        st.markdown("### 🟢 **DIRECTION: BUY / LONG** ⬆️")
        st.info(f"🔥 AI Confidence: {ai_confidence:.1f}%")
    else:
        st.markdown("### 🔴 **DIRECTION: SELL / SHORT** ⬇️")
        st.info(f"🔥 AI Confidence: {ai_confidence:.1f}%")

    # --- 6. 🔥 FIX DATETIME KEYERROR & FORMAT DATA ---
    st.write("---")
    st.subheader("📈 සජීවී ප්‍රස්ථාර ඇනලයිසර් (Live Analysis Chart):")
    st.write("💡 *AI දෙන Entry (🔵), Take Profit (🟢), සහ Stop Loss (🔴) මට්ටම් සජීවීව චාර්ට් එක මතම ඇඳී ඇත.*")
    
    # මෙතනින් තමයි Datetime / Index ප්‍රශ්නය 100% ක්ම විසඳුවේ
    chart_df = df.tail(50).copy()
    chart_df = chart_df.reset_index()
    
    # Column වල නම් කුමක් වුවත් නිවැරදිව Time එක සකස් කිරීම
    time_col = 'Date' if 'Date' in chart_df.columns else ('Datetime' if 'Datetime' in chart_df.columns else chart_df.columns[0])
    chart_df['time'] = pd.to_datetime(chart_df[time_col]).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    candles = []
    for _, row in chart_df.iterrows():
        candles.append({
            'time': row['time'], 'open': float(row['Open']), 'high': float(row['High']), 'low': float(row['Low']), 'close': float(row['Close'])
        })
        
    # Chart Options Settings
    chart_options = {
        "width": 700, "height": 450,
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#242832"}, "horzLines": {"color": "#242832"}},
        "priceScale": {"autoScale": True}
    }
    
    # චාර්ට් එක ඇතුලටම නිවැරදිව ඉරි ඇඳීම
    price_lines = [
        {"price": current_price, "color": "#00E5FF", "lineWidth": 2, "lineStyle": 1, "axisLabelVisible": True, "title": "ENTRY"},
        {"price": tp_price, "color": "#00E676", "lineWidth": 2.5, "lineStyle": 0, "axisLabelVisible": True, "title": "TAKE PROFIT (TP)"},
        {"price": sl_price, "color": "#FF1744", "lineWidth": 2.5, "lineStyle": 0, "axisLabelVisible": True, "title": "STOP LOSS (SL)"}
    ]
    
    series_chart = [{
        "type": "Candlestick",
        "data": candles,
        "options": {"upColor": "#26a69a", "downColor": "#ef5350", "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"},
        "priceLines": price_lines
    }]
    
    renderLightweightCharts(series=series_chart, options=chart_options)

    # --- 7. VISUAL TARGET SYNC PANEL ---
    st.info(f"📊 **ප්‍රස්ථාරයේ ඇඳී ඇති නිවැරදි මිල මට්ටම් (Visual Targets):**\n\n"
            f"🔵 **Entry Price Level:** ${current_price:.4f}\n\n"
            f"🎯 **Take Profit (TP) Target:** ${tp_price:.4f}\n\n"
            f"🛑 **Stop Loss (SL) Target:** ${sl_price:.4f}")
else:
    st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් සජීවී දත්ත නොමැත. කරුණාකර වෙනත් Timeframe එකක් තෝරන්න.")
