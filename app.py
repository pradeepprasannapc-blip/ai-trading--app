import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="AI Trading Signal App", page_icon="🤖", layout="centered")

st.title("🤖 AI Trading Signal App")
st.write("Binance සහ TradingView වගේ සජීවී තේරීම් ලැයිස්තුවෙන් පහසුවෙන්ම Signals ලබාගන්න.")

# 💡 ජනප්‍රිය වෙළඳපොලවල් සහිත සජීවී ලැයිස්තුව (Watchlist Category)
st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න (Select Market):")

category = st.radio(
    "ප්‍රවර්ගය තෝරන්න (Select Category):",
    ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)", "💱 ෆොරෙක්ස් (Forex)", "✨ වටිනා ලෝහ සහ තෙල් (Metals & Energies)"],
    horizontal=True
)

# ප්‍රවර්ගය අනුව පෙන්විය යුතු කාසි නියම කිරීම
if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Popular Crypto)":
    market_options = {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD",
        "Solana (SOL/USD)": "SOL-USD",
        "Ripple (XRP/USD)": "XRP-USD",
        "Cardano (ADA/USD)": "ADA-USD",
        "Dogecoin (DOGE/USD)": "DOGE-USD",
        "Binance Coin (BNB/USD)": "BNB-USD"
    }
elif category == "💱 ෆොරෙක්ස් (Forex)":
    market_options = {
        "Euro / US Dollar (EUR/USD)": "EURUSD=X",
        "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X",
        "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X",
        "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X"
    }
else:
    market_options = {
        "රන් / Gold (XAU/USD)": "GC=F",
        "රීදි / Silver (XAG/USD)": "SI=F",
        "कෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"
    }

# Dropdown එකක් මඟින් ලේසියෙන්ම කාසිය තෝරාගැනීම
selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Coin/Pair):", list(market_options.keys()))
ticker = market_options[selected_display_name]

# සෙවුම් කොටුවක් (Optional Search) - ලැයිස්තුවේ නැති එකක් ඕනෙ නම් විතරක් ටයිප් කරන්න
st.write("---")
with st.expander("🔍 ලැයිස්තුවේ නැති වෙනත් කාසියක් සෙවීමට (Optional Custom Search)"):
    custom_input = st.text_input("කාසියේ කේතය කෙලින්ම ඇතුලත් කරන්න (උදා: MATIC-USD):", "")
    if custom_input:
        ticker = custom_input.strip().upper()

timeframe = st.selectbox("Timeframe එක තෝරන්න (Select Timeframe):", ["1h", "4h", "1d"])

# 2. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf):
    df = yf.download(symbol, period="60d", interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, timeframe)

if not df.empty:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 3. Indicators සැකසීම (RSI සහ SMA)
    df['Returns'] = df['Close'].pct_change()
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_30'] = df['Close'].rolling(window=30).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    df.dropna(inplace=True)
    
    # 4. Machine Learning (AI) මාදිලිය පුහුණු කිරීම
    features = ['SMA_10', 'SMA_30', 'RSI', 'Returns']
    X = df[features]
    y = df['Target']
    
    split = int(0.8 * len(df))
    X_train, y_train = X[:split], y[:split]
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. අනාවැකිය ලබාගැනීම
    last_market_state = X.iloc[[-1]]
    prediction = model.predict(last_market_state)[0]
    probability = model.predict_proba(last_market_state)[0]
    
    current_price = float(df['Close'].to_numpy()[-1])
    current_high = float(df['High'].to_numpy()[-1])
    current_low = float(df['Low'].to_numpy()[-1])
    volatility = current_high - current_low
    
    # 6. ප්‍රතිඵල Screen එක මත පෙන්වීම
    st.subheader(f"📊 {selected_display_name} සඳහා වත්මන් AI තත්ත්වය:")
    st.metric(label="දැනට පවතින සජීවී මිල (Current Start Entry)", value=f"${current_price:.4f}")
    
    st.write("---")
    if prediction == 1:
        st.success(f"🟢 AI SIGNAL: BUY / LONG (විශ්වාසවන්තභාවය: {probability[1]*100:.1f}%)")
        st.write(f"🎯 **Take Profit (TP):** ${(current_price + (volatility * 1.5)):.4f}")
        st.write(f"🛑 **Stop Loss (SL):** ${(current_price - volatility):.4f}")
    else:
        st.error(f"🔴 AI SIGNAL: SELL / SHORT (විශ්වාසවන්තභාවය: {probability[0]*100:.1f}%)")
        st.write(f"🎯 **Take Profit (TP):** ${(current_price - (volatility * 1.5)):.4f}")
        st.write(f"🛑 **Stop Loss (SL):** ${(current_price + volatility):.4f}")
        
    st.write("📈 මෑතකාලීන දත්ත සටහන (Historical Data View):")
    display_df = pd.DataFrame({
        'Close Price': df['Close'],
        'RSI (14)': df['RSI'],
        'SMA (10)': df['SMA_10']
    })
    st.dataframe(display_df.tail(5))
else:
    st.error("දත්ත ලබාගැනීමට අපොහොසත් විය. කරුණාකර තේරීම නිවැරදිදැයි හෝ ඉන්ටර්නෙට් සම්බන්ධතාවය පරීක්ෂා කරන්න.")
