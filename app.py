import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components  # Live Chart එක Embed කිරීමට

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Indicators සහ Live TradingView Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

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
    tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}" if 'ticker' in locals() else "BINANCE:BTCUSDT"
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

# TradingView සජීවී චාර්ට් එක සඳහා නිවැරදි Symbol එක සැකසීම
if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)":
    tv_symbol = f"BINANCE:{ticker.replace('-USD', 'USDT')}"
elif category == "💱 ෆොරෙක්ස් (Forex)":
    tv_symbol = f"FX_IDC:{ticker.replace('=X', '')}"
else:
    tv_symbol = f"COMEX:{ticker.replace('=F', '1!')}" if "GC" in ticker or "SI" in ticker else f"NYMEX:{ticker.replace('=F', '1!')}"

timeframe = st.selectbox("Timeframe එක තෝරන්න (SMC සඳහා 1h හෝ 4h වඩාත් සුදුසුයි):", ["1h", "4h", "1d"])

# 2. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf):
    df = yf.download(symbol, period="90d", interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, timeframe)

if not df.empty:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # --- 3. ADVANCED INDICATORS ENGINEERING ---
    df['Returns'] = df['Close'].pct_change()
    
    # Moving Averages
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands
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
    st.subheader(f"📊 {selected_display_name} සඳහා PRO AI විශ්ලේෂණය:")
    st.metric(label="සජීවී වෙළඳපොල මිල (Current Entry Price)", value=f"${current_price:.4f}")
    
    # සුවර් සිග්නල් Filter එක (Probability එක බැලීම)
    ai_confidence = max(probability) * 100
    
    st.write("### 🚨 AI තීරණය (AI Signal Output):")
    if ai_confidence < 58.0:
        st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI එකට මේ වෙලාවේ දිශාව ගැන ලොකු විශ්වාසයක් නැහැ ({ai_confidence:.1f}%). අවදානම අඩු කිරීමට කරුණාකර වෙනත් Timeframe එකක් හෝ වෙනත් කාසියක් (Coin) තෝරා බලන්න.")
    else:
        if prediction == 1:
            st.success(f"🔥 **HIGH-CONFIDENCE SIGNAL: BUY / LONG** (සුවර් එක: {ai_confidence:.1f}%)")
            
            tp_price = current_price + (volatility * 2)
            sl_price = current_price - (volatility * 1.5)
            
            st.write(f"🟩 **Entry ගන්න ඕන මිල (Entry Price):** `${current_price:.4f}`")
            st.write(f"🎯 **Take Profit (TP / ටාගට් එක):** `${tp_price:.4f}`")
            st.write(f"🛑 **Stop Loss (SL / අලාභ සීමාව):** `${sl_price:.4f}`")
            
            if is_bull_fvg_present:
                st.info("💡 **SMC Confluence:** Bullish Fair Value Gap එකක් තියෙනවා. මිල තවත් ඉහළට යන්න ලොකු ඉඩක් තියෙනවා.")
        else:
            st.error(f"🚨 **HIGH-CONFIDENCE SIGNAL: SELL / SHORT** (සුවර් එක: {ai_confidence:.1f}%)")
            
            tp_price = current_price - (volatility * 2)
            sl_price = current_price + (volatility * 1.5)
            
            st.write(f"🟥 **Entry ගන්න ඕන මිල (Entry Price):** `${current_price:.4f}`")
            st.write(f"🎯 **Take Profit (TP / ටාගට් එක):** `${tp_price:.4f}`")
            st.write(f"🛑 **Stop Loss (SL / අලාභ සීමාව):** `${sl_price:.4f}`")
            
            if is_bear_fvg_present:
                st.info("💡 **SMC Confluence:** Bearish Order Block/FVG එකක් තියෙනවා. විකිණුම්කරුවන් (Sellers) ප්‍රබලයි.")
                
    # --- 8. LIVE INTERACTIVE CHART EMBEDDING ---
    st.write("---")
    st.subheader(f"📈 සජීවී තාක්ෂණික ප්‍රස්ථාරය (Live Technical Chart):")
    
    # Timeframe එක TradingView එකට ගැළපෙන සේ හැඩගැස්වීම
    tv_tf = "60" if timeframe == "1h" else "240" if timeframe == "4h" else "D"
    
    tradingview_html = f"""
    <div class="tradingview-widget-container" style="height:450px;">
      <div id="tradingview_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": 450,
        "symbol": "{tv_symbol}",
        "interval": "{tv_tf}",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    # HTML Component එක ඇප් එක ඇතුලට දැමීම
    components.html(tradingview_html, height=460)

    st.write("---")
    st.write("📊 **තාක්ෂණික දර්ශක දත්ත පුවරුව (Technical Indicators Data Table):**")
    display_df = pd.DataFrame({
        'Close Price': df['Close'],
        'RSI (Momentum)': df['RSI'],
        'MACD': df['MACD'],
        'BB Upper (Resistance)': df['BB_Upper'],
        'BB Lower (Support)': df['BB_Lower']
    })
    st.dataframe(display_df.tail(5))
else:
    st.error("දත්ත ලබාගැනීමට අපොහොසත් විය. කරුණාකර ඉන්ටර්නෙට් සම්බන්ධතාවය පරීක්ෂා කරන්න.")
