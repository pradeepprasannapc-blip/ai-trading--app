import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Technical Indicators සහ Live Analysis Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

# 💡 ජනප්‍රිය වෙළඳපොලවල් සහිත සජීවී ලැයිස්තුව
st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න (Select Market):")

category = st.radio(
    "ප්‍රවර්ගය තෝරන්න (Select Category):",
    ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)", "💱 ෆොරෙක්ස් (Forex)", "✨ වටිනා ලෝහ සහ තෙල් (Metals & Energies)"],
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
    tv_exchange = "BINANCE"
elif category == "💱 ෆොරෙක්ස් (Forex)":
    market_options = {
        "Euro / US Dollar (EUR/USD)": "EURUSD=X",
        "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X",
        "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X"
    }
    tv_exchange = "FX_IDC"
else:
    market_options = {
        "රන් / Gold (XAU/USD)": "GC=F",
        "රීදි / Silver (XAG/USD)": "SI=F",
        "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"
    }
    tv_exchange = "COMEX"

selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Coin/Pair):", list(market_options.keys()))
ticker = market_options[selected_display_name]

# --- TIMEFRAME SELECTOR ---
tf_display = st.selectbox(
    "Timeframe එක තෝරන්න (Select Timeframe):", 
    ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"]
)

tf_mapping = {
    "5 min": {"yf": "5m", "tv": "5", "period": "60d"},
    "15 min": {"yf": "15m", "tv": "15", "period": "60d"},
    "30 min": {"yf": "30m", "tv": "30", "period": "60d"},
    "1 hour": {"yf": "1h", "tv": "60", "period": "90d"},
    "4 hour": {"yf": "4h", "tv": "240", "period": "90d"},
    "1 day": {"yf": "1d", "tv": "D", "period": "max"}
}

selected_tf = tf_mapping[tf_display]

# TradingView සඳහා Symbol එක සකස් කිරීම
if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)":
    clean_symbol = ticker.replace('-USD', 'USDT')
elif category == "💱 ෆොරෙක්ස් (Forex)":
    clean_symbol = ticker.replace('=X', '')
else:
    clean_symbol = ticker.replace('=F', '1!')
    if "CL" in ticker:
        tv_exchange = "NYMEX"

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
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['StdDev'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (df['StdDev'] * 2)
    df['BB_Lower'] = df['MA20'] - (df['StdDev'] * 2)
    
    # --- 4. SMART MONEY CONCEPTS (SMC) DETECTION ---
    df['Bearish_FVG'] = (df['High'].shift(2) < df['Low']) & (df['Close'].shift(1) < df['Open'].shift(1))
    df['Bullish_FVG'] = (df['Low'].shift(2) > df['High']) & (df['Close'].shift(1) > df['Open'].shift(1))
    
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    df.dropna(inplace=True)
    
    # 5. Machine Learning (AI) Model Training
    features = ['EMA_9', 'EMA_21', 'RSI', 'MACD', 'Signal_Line', 'BB_Upper', 'BB_Lower', 'Returns']
    X = df[features]
    y = df['Target']
    
    split = int(0.85 * len(df))
    X_train, y_train = X[:split], y[:split]
    
    model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # 6. Prediction & Probabilities
    last_market_state = X.iloc[[-1]]
    prediction = model.predict(last_market_state)[0]
    probability = model.predict_proba(last_market_state)[0]
    
    current_price = float(df['Close'].to_numpy()[-1])
    is_bull_fvg_present = bool(df['Bullish_FVG'].to_numpy()[-1])
    is_bear_fvg_present = bool(df['Bearish_FVG'].to_numpy()[-1])
    
    volatility = float((df['High'] - df['Low']).rolling(window=14).mean().to_numpy()[-1])
    
    # 7. Screen එක මත පෙන්වීම
    st.write("---")
    st.subheader(f"📊 {selected_display_name} ({tf_display}) සඳහා PRO AI විශ්ලේෂණය:")
    
    ai_confidence = max(probability) * 100
    
    # TP / SL Math Calculations
    if prediction == 1:
        tp_price = current_price + (volatility * 2.0)
        sl_price = current_price - (volatility * 1.5)
    else:
        tp_price = current_price - (volatility * 2.0)
        sl_price = current_price + (volatility * 1.5)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.metric(label="📊 සජීවී වෙළඳපොල මිල (Live Price)", value=f"${current_price:.4f}")
        st.write("### 🚨 AI Analysis Target Levels:")
        
        if ai_confidence < 58.0:
            st.warning(f"⚠️ **NO SIGNAL** \n\nAI විශ්වාසය මදියි ({ai_confidence:.1f}%).")
        else:
            if prediction == 1:
                st.markdown(f"### 🟩 **DIRECTION: BUY / LONG**")
                st.markdown(f"🔹 **Entry Zone:** `${current_price:.4f}`")
                st.markdown(f"🟩 **Take Profit (TP):** `${tp_price:.4f}`")
                st.markdown(f"🟥 **Stop Loss (SL):** `${sl_price:.4f}`")
                st.info(f"🔥 AI Confidence: {ai_confidence:.1f}%")
                if is_bull_fvg_present: st.success("💡 Bullish FVG Detected!")
            else:
                st.markdown(f"### 🟥 **DIRECTION: SELL / SHORT**")
                st.markdown(f"🔹 **Entry Zone:** `${current_price:.4f}`")
                st.markdown(f"🟩 **Take Profit (TP):** `${tp_price:.4f}`")
                st.markdown(f"🟥 **Stop Loss (SL):** `${sl_price:.4f}`")
                st.info(f"🔥 AI Confidence: {ai_confidence:.1f}%")
                if is_bear_fvg_present: st.error("💡 Bearish OB/FVG Detected!")

    with col2:
        st.write("### 📈 Live Technical Summary:")
        tv_summary_html = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
          {{
          "interval": "{selected_tf['tv'] if selected_tf['tv'] != '5' else '1m'}",
          "width": "100%",
          "isTransparent": false,
          "height": 280,
          "symbol": "{tv_exchange}:{clean_symbol}",
          "showHeading": false,
          "screenMode": "normal",
          "locale": "en",
          "theme": "dark"
          }}
          </script>
        </div>
        """
        components.html(tv_summary_html, height=290)
                
    # --- 8. LIVE TRADINGVIEW CHART ---
    st.write("---")
    st.subheader(f"📈 සජීවී ස්වයංක්‍රීය ප්‍රස්ථාරය (Live Technical Chart):")
    st.write("💡 *ඉහත AI ලෙවල්ස් බලාගෙන වම්පස ඇති Long/Short Position Tool එකෙන් චාර්ට් එක මත කෙලින්ම ඇනලයිස් එක දමා බලන්න.*")
    
    chart_studies = '["MASimple@tv-basicstudies", "BBands@tv-basicstudies"]'
    
    tradingview_html = f"""
    <div class="tradingview-widget-container" style="height:550px; width:100%;">
      <div id="tradingview_chart" style="height:550px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "height": 550,
        "symbol": "{tv_exchange}:{clean_symbol}",
        "interval": "{selected_tf['tv']}",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "studies": {chart_studies},
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(tradingview_html, height=560)

    # Visual Target Sync Panel
    st.info(f"🎯 **ප්‍රස්ථාරයේ ඇඳී ඇති නිවැරදි මිල මට්ටම් (Visual Target Sync):**\n\n"
            f"🔵 **Entry Price:** ${current_price:.4f} | "
            f"🟩 **Take Profit (TP):** ${tp_price:.4f} | "
            f"🟥 **Stop Loss (SL):** ${sl_price:.4f}")

    # --- 9. DATA TABLE ---
    st.write("---")
    st.subheader("📊 TAක්ෂණික දර්ශක දත්ත පුවරුව (Technical Indicators Data Table):")
    table_df = df[['Close', 'RSI', 'MACD', 'BB_Upper', 'BB_Lower']].copy()
    table_df.columns = ['Close Price', 'RSI (14)', 'MACD Trend', 'BB Upper (Res)', 'BB Lower (Sup)']
    st.dataframe(table_df.tail(5))
else:
    st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් සජීවී දත්ත නොමැත. කරුණාකර වෙනත් කාසියක් හෝ වෙනත් Timeframe එකක් තෝරන්න.")
