import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# App Interface එක සිංහලෙන්
st.title("🤖 AI Trading Signal App")
st.write("Real-time AI TA ශබ්දකෝෂයෙන් ක්‍රිප්ටෝ, ෆොරෙක්ස් සහ රන් Signal ලබාගන්න.")

# 💡 සාමාන්‍ය නම හඳුනාගැනීමේ ශබ්දකෝෂය (Smart Dictionary)
COIN_DICTIONARY = {
    # ක්‍රිප්ටෝ (Crypto)
    "bitcoin": "BTC-USD", "බිට්කොයින්": "BTC-USD", "btc": "BTC-USD",
    "ethereum": "ETH-USD", "ඉතීරියම්": "ETH-USD", "eth": "ETH-USD",
    "solana": "SOL-USD", "සොලානා": "SOL-USD", "sol": "SOL-USD",
    "ripple": "XRP-USD", "රිපල්": "XRP-USD", "xrp": "XRP-USD",
    "cardano": "ADA-USD", "කාඩානോ": "ADA-USD", "ada": "ADA-USD",
    "dogecoin": "DOGE-USD", "ඩොජ්කොයින්": "DOGE-USD", "doge": "DOGE-USD",
    "binance coin": "BNB-USD", "බයිනෑන්ස්": "BNB-USD", "bnb": "BNB-USD",
    
    # රන් සහ වෙනත් (Commodities)
    "gold": "GC=F", "රන්": "GC=F", "රත්තරන්": "GC=F", "xau": "GC=F",
    "oil": "CL=F", "තෙල්": "CL=F", "crude oil": "CL=F",
    
    # ෆොරෙක්ස් (Forex)
    "eurusd": "EURUSD=X", "යුරෝ": "EURUSD=X",
    "gbpusd": "GBPUSD=X", "පවුම්": "GBPUSD=X",
    "audusd": "AUDUSD=X"
}

# පරිශීලකයාගෙන් සාමාන්‍ය නම ලබාගැනීම
user_input = st.text_input("ඔයාට අවශ්‍ය කාසියේ හෝ වෙළඳපොලේ නම ඇතුලත් කරන්න (සිංහලෙන් හෝ ඉංග්‍රීසියෙන්):", "Bitcoin")

# නම පිරිසිදු කර ශබ්දකෝෂය හරහා සෙවීම
clean_input = user_input.strip().lower()

if clean_input in COIN_DICTIONARY:
    ticker = COIN_DICTIONARY[clean_input]
    st.info(f"🔍 AI විසින් හඳුනාගත් කේතය: **{ticker}** ({user_input})")
else:
    # ලැයිස්තුවේ නැති එකක් නම් කෙලින්ම ගහපු එක ගන්නවා
    ticker = user_input.strip().upper()

timeframe = st.selectbox("Timeframe එක තෝරන්න:", ["1h", "4h", "1d"])

# 1. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf):
    df = yf.download(symbol, period="60d", interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, timeframe)

if not df.empty:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 2. Indicators සැකසීම (RSI සහ SMA)
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
    
    # 3. Machine Learning (AI) මාදිලිය පුහුණු කිරීම
    features = ['SMA_10', 'SMA_30', 'RSI', 'Returns']
    X = df[features]
    y = df['Target']
    
    split = int(0.8 * len(df))
    X_train, y_train = X[:split], y[:split]
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 4. අනාවැකිය ලබාගැනීම
    last_market_state = X.iloc[[-1]]
    prediction = model.predict(last_market_state)[0]
    probability = model.predict_proba(last_market_state)[0]
    
    current_price = float(df['Close'].to_numpy()[-1])
    current_high = float(df['High'].to_numpy()[-1])
    current_low = float(df['Low'].to_numpy()[-1])
    volatility = current_high - current_low
    
    # 5. ප්‍රතිඵල Screen එක මත පෙන්වීම
    st.subheader(f"📊 {ticker} සඳහා වත්මන් තත්ත්වය:")
    st.metric(label="දැනට පවතින මිල (Current Start Entry)", value=f"${current_price:.4f}")
    
    st.write("---")
    if prediction == 1:
        st.success(f"🟢 AI SIGNAL: BUY / LONG (විශ්වාසවන්තභාවය: {probability[1]*100:.1f}%)")
        st.write(f"🎯 **Take Profit (TP):** ${(current_price + (volatility * 1.5)):.4f}")
        st.write(f"🛑 **Stop Loss (SL):** ${(current_price - volatility):.4f}")
    else:
        st.error(f"🔴 AI SIGNAL: SELL / SHORT (විශ්වාසවන්තභාවය: {probability[0]*100:.1f}%)")
        st.write(f"🎯 **Take Profit (TP):** ${(current_price - (volatility * 1.5)):.4f}")
        st.write(f"🛑 **Stop Loss (SL):** ${(current_price + volatility):.4f}")
        
    st.write("📈 මෑතකාලීන දත්ත සටහන:")
    display_df = pd.DataFrame({
        'Close Price': df['Close'],
        'RSI (14)': df['RSI'],
        'SMA (10)': df['SMA_10']
    })
    st.dataframe(display_df.tail(5))
else:
    st.error("දත්ත ලබාගැනීමට අපොහොසත් විය. කරුණාකර නම නිවැරදිදැයි හෝ ඉන්ටර්නෙට් සම්බන්ධතාවය පරීක්ෂා කරන්න.")
