import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import plotly.graph_objects as go  # චාර්ට් එක උඩම ඉරි ඇඳීම සඳහා

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Indicators සහ Auto-Draw Levels ප්‍රස්ථාරය මුසු වූ ස්මාර්ට් ඇනලයිසර් එක.")

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
    "5 min": {"yf": "5m", "period": "60d"},
    "15 min": {"yf": "15m", "period": "60d"},
    "30 min": {"yf": "30m", "period": "60d"},
    "1 hour": {"yf": "1h", "period": "90d"},
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
    st.metric(label="සජීවී වෙළඳපොල මිල (Current Entry Price)", value=f"${current_price:.4f}")
    
    ai_confidence = max(probability) * 100
    
    st.write("### 🚨 AI තීරණය (AI Signal Output):")
    
    has_signal = False
    if ai_confidence < 58.0:
        st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI එකට මෙම Timeframe එකේ ({tf_display}) දිශාව ගැන ලොකු විශ්වාසයක් නැහැ ({ai_confidence:.1f}%). කරුණාකර වෙනත් Timeframe එකක් හෝ වෙනත් කාසියක් තෝරා බලන්න.")
    else:
        has_signal = True
        if prediction == 1:
            st.success(f"🔥 **HIGH-CONFIDENCE SIGNAL: BUY / LONG** (සුවර් එක: {ai_confidence:.1f}%)")
            tp_price = current_price + (volatility * 2)
            sl_price = current_price - (volatility * 1.5)
            trade_type = "BUY"
            
            st.write(f"🟩 **Entry ගන්න ඕන මිල (Entry Price):** `${current_price:.4f}`")
            st.write(f"🎯 **Take Profit (TP / ටාගට් එක):** `${tp_price:.4f}`")
            st.write(f"🛑 **Stop Loss (SL / අලාභ සීමාව):** `${sl_price:.4f}`")
            if is_bull_fvg_present: st.info("💡 **SMC Confluence:** Bullish Fair Value Gap එකක් තියෙනවා!")
        else:
            st.error(f"🚨 **HIGH-CONFIDENCE SIGNAL: SELL / SHORT** (සුවර් එක: {ai_confidence:.1f}%)")
            tp_price = current_price - (volatility * 2)
            sl_price = current_price + (volatility * 1.5)
            trade_type = "SELL"
            
            st.write(f"🟥 **Entry ගන්න ඕන මිල (Entry Price):** `${current_price:.4f}`")
            st.write(f"🎯 **Take Profit (TP / ටාගට් එක):** `${tp_price:.4f}`")
            st.write(f"🛑 **Stop Loss (SL / අලාභ සීමාව):** `${sl_price:.4f}`")
            if is_bear_fvg_present: st.info("💡 **SMC Confluence:** Bearish Order Block/FVG එකක් තියෙනවා!")
                
    # --- 8. 🔥 CUSTOM AUTO-DRAW LEVELS CANDLESTICK CHART ---
    st.write("---")
    st.subheader(f"📈 ස්වයංක්‍රීය ඇනලයිස් ප්‍රස්ථාරය (Auto-Analysis Chart):")
    
    # මෑතකාලීන කැන්ඩල්ස් 40ක් පමණක් ලස්සනට පෙන්වීමට වෙන් කිරීම
    plot_df = df.tail(40)
    
    fig = go.Figure()
    
    # 1. Candlestick Chart එක ඇඳීම
    fig.add_trace(go.Candlestick(
        x=plot_df.index,
        open=plot_df['Open'], high=plot_df['High'],
        low=plot_df['Low'], close=plot_df['Close'],
        name="Market Price"
    ))
    
    # 2. Bollinger Bands (BB) ඉරි දෙක ඇඳීම
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['BB_Upper'], line=dict(color='rgba(173, 216, 230, 0.6)', width=1), name="BB Upper (Res)"))
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['BB_Lower'], line=dict(color='rgba(173, 216, 230, 0.6)', width=1), name="BB Lower (Sup)"))
    
    # 3. සිග්නල් එකක් තිබේ නම් පමණක් Entry/TP/SL ඉරි චාර්ට් එක මත කෙලින්ම ඇඳීම
    if has_signal:
        # Entry Line (🔵 නිල් පාට)
        fig.add_hline(y=current_price, line_dash="dash", line_color="#00E5FF", line_width=2, 
                      annotation_text=f"ENTRY: ${current_price:.4f}", annotation_position="top left")
        # Take Profit Line (🟢 කොළ පාට)
        fig.add_hline(y=tp_price, line_dash="solid", line_color="#00E676", line_width=2.5, 
                      annotation_text=f"🎯 TAKE PROFIT: ${tp_price:.4f}", annotation_position="top left")
        # Stop Loss Line (🔴 රතු පාට)
        fig.add_hline(y=sl_price, line_dash="solid", line_color="#FF1744", line_width=2.5, 
                      annotation_text=f"🛑 STOP LOSS: ${sl_price:.4f}", annotation_position="top left")
    
    # චාර්ට් එකේ පෙනුම (Dark Theme Layout) සැකසීම
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # චාර්ට් එක ස්ක්‍රීන් එක මත පෙන්වීම
    st.plotly_chart(fig, use_container_width=True)

    # --- 9. DATA TABLE ---
    st.write("---")
    st.subheader("📊 තාක්ෂණික දර්ශක දත්ත පුවරුව (Technical Indicators Data Table):")
    
    table_df = df[['Close', 'RSI', 'MACD', 'BB_Upper', 'BB_Lower']].copy()
    table_df.columns = ['Close Price', 'RSI (14)', 'MACD Trend', 'BB Upper (Res)', 'BB Lower (Sup)']
    
    st.dataframe(table_df.tail(5))
else:
    st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් සජීවී දත්ත නොමැත. කරුණාකර වෙනත් කාසියක් හෝ වෙනත් Timeframe එකක් තෝරන්න.")
