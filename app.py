import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# App Interface එක සිංහලෙන්
st.title("🤖 AI Trading Signal App")
st.write("Real-time AI තාක්ෂණයෙන් ක්‍රිප්ටෝ සහ ස්ටොක් Signal ලබාගන්න.")

# පරිශීලකයාට කැමති Coin එකක් තෝරාගත හැක
ticker = st.text_input("කාසිය ඇතුලත් කරන්න (उदा: BTC-USD, SOL-USD, ETH-USD):", "BTC-USD")
timeframe = st.selectbox("Timeframe එක තෝරන්න:", ["1h", "4h", "1d"])

# 1. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf):
    # auto_adjust=True සහ group_by='column' දමා 2D array එරර් එක නැති කිරීම
    df = yf.download(symbol, period="60d", interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, timeframe)

if not df.empty:
    # Multi-index columns තියෙනවා නම් ඒවා තනි මට්ටමකට පත් කිරීම (Error Fix)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 2. Indicators සැකසීම (RSI සහ SMA)
    df['Returns'] = df['Close'].pct_change()
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_30'] = df['Close'].rolling(window=30).mean()
    
    # RSI Indicator එක හැදීම
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ඊළඟ කැන්ඩල් එක උඩ යයිද පහළ යයිද කියා Target එක සෙටප් කිරීම
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    df.dropna(inplace=True)
    
    # 3. Machine Learning (AI) මාදිලිය පුහුණු කිරීම
    features = ['SMA_10', 'SMA_30', 'RSI', 'Returns']
    X = df[features]
    y = df['Target']
    
    # දත්ත බෙදීම
    split = int(0.8 * len(df))
    X_train, y_train = X[:split], y[:split]
    
    # Random Forest Classifier AI එක ක්‍රියාත්මක කිරීම
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 4. අනාවැකිය ලබාගැනීම
    last_market_state = X.iloc[[-1]]
    prediction = model.predict(last_market_state)[0]
    probability = model.predict_proba(last_market_state)[0]
    
    # පේළි තනි අගයන් බවට පත් කරගැනීම (float conversion fix)
    current_price = float(df['Close'].to_numpy()[-1])
    current_high = float(df['High'].to_numpy()[-1])
    current_low = float(df['Low'].to_numpy()[-1])
    volatility = current_high - current_low
    
    # 5. ප්‍රතිඵල Screen එක මත පෙන්වීම
    st.subheader(f"📊 {ticker} සඳහා වත්මන් තත්ත්වය:")
    st.metric(label="දැනට පවතින මිල (Current Price)", value=f"${current_price:.4f}")
    
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
    # දර්ශනය සඳහා සරල දත්ත පුවරුවක් සැකසීම
    display_df = pd.DataFrame({
        'Close Price': df['Close'],
        'RSI (14)': df['RSI'],
        'SMA (10)': df['SMA_10']
    })
    st.dataframe(display_df.tail(5))
else:
    st.error("දත්ත ලබාගැනීමට අපොහොසත් විය. කරුණාකර Ticker එක නිවැරදිදැයි බලන්න.")
