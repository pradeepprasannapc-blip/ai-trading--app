import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Technical Indicators සහ 100% Live TradingView Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

# 💡 ජනප්‍රිය වෙළඳපොලවල් සහිත සජීවී ලැයිස්තුව
st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න (Select Market):")

category = st.radio(
    "ප්‍රවර්ගය තෝරන්න (Select Category):",
    ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ", "💱 ෆොරෙක්ස්", "✨ ලෝහ සහ තෙල්", "✏️ වෙනත් (Custom)"],
    horizontal=True
)

# --- 🔄 ජනප්‍රිය Top 30+ ක්‍රිප්ටෝ කාසි ලැයිස්තුව ---
if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ":
    market_options = {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD",
        "Solana (SOL/USD)": "SOL-USD",
        "Binance Coin (BNB/USD)": "BNB-USD",
        "Ripple (XRP/USD)": "XRP-USD",
        "Cardano (ADA/USD)": "ADA-USD",
        "Dogecoin (DOGE/USD)": "DOGE-USD",
        "Shiba Inu (SHIB/USD)": "SHIB-USD",
        "Pepe (PEPE/USD)": "PEPE-USD",
        "Avalanche (AVAX/USD)": "AVAX-USD",
        "Chainlink (LINK/USD)": "LINK-USD",
        "Polkadot (DOT/USD)": "DOT-USD",
        "Polygon (MATIC/USD)": "MATIC-USD",
        "Litecoin (LTC/USD)": "LTC-USD",
        "Bitcoin Cash (BCH/USD)": "BCH-USD",
        "Uniswap (UNI/USD)": "UNI-USD",
        "Cosmos (ATOM/USD)": "ATOM-USD",
        "Monero (XMR/USD)": "XMR-USD",
        "Stellar (XLM/USD)": "XLM-USD",
        "TRON (TRX/USD)": "TRX-USD",
        "VeChain (VET/USD)": "VET-USD",
        "Filecoin (FIL/USD)": "FIL-USD",
        "Aptos (APT/USD)": "APT-USD",
        "NEAR Protocol (NEAR/USD)": "NEAR-USD",
        "Arbitrum (ARB/USD)": "ARB-USD",
        "Optimism (OP/USD)": "OP-USD",
        "Injective (INJ/USD)": "INJ-USD",
        "Fetch.ai (FET/USD)": "FET-USD",
        "Gala (FTM/USD)": "FTM-USD",
        "Sui (SUI/USD)": "SUI-USD"
    }
    selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Coin/Pair):", list(market_options.keys()))
    ticker = market_options[selected_display_name]
    clean_symbol = ticker.replace('-USD', 'USDT')
    full_tv_ticker = f"BINANCE:{clean_symbol}"

elif category == "💱 ෆොරෙක්ස්":
    market_options = {
        "Euro / US Dollar (EUR/USD)": "EURUSD=X",
        "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X",
        "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X",
        "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X",
        "US Dollar / Canadian Dollar (USD/CAD)": "USDCAD=X",
        "US Dollar / Swiss Franc (USD/CHF)": "USDCHF=X"
    }
    selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Pair):", list(market_options.keys()))
    ticker = market_options[selected_display_name]
    clean_symbol = ticker.replace('=X', '')
    full_tv_ticker = f"FX_IDC:{clean_symbol}"

elif category == "✨ ලෝහ සහ තෙල්":
    market_options = {
        "රන් / Gold (XAU/USD)": "GC=F",
        "රීදි / Silver (XAG/USD)": "SI=F",
        "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F",
        "ස්වාභාවික වායු / Natural Gas": "NG=F"
    }
    selected_display_name = st.selectbox("කාසිය තෝරන්න (Select Commodity):", list(market_options.keys()))
    ticker = market_options[selected_display_name]
    clean_symbol = ticker.replace('=F', '')
    tv_exchange = "COMEX"
    if "CL" in ticker or "NG" in ticker:
        tv_exchange = "NYMEX"
    full_tv_ticker = f"{tv_exchange}:{clean_symbol}"

else:
    st.info("💡 **ඔබට අවශ්‍ය ඕනෑම කාසියක් මෙහි ඇතුළත් කළ හැක.**")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        ticker = st.text_input("Yahoo Finance Ticker (උදා: DOGE-USD, AAPL):", "DOGE-USD")
    with col_c2:
        full_tv_ticker = st.text_input("TradingView Symbol (උදා: BINANCE:DOGEUSDT):", "BINANCE:DOGEUSDT")
    selected_display_name = f"Custom Symbol ({ticker})"

# --- TIMEFRAME SELECTOR ---
tf_display = st.selectbox(
    "Timeframe එක තෝරන්න (Select Timeframe):", 
    ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"]
)

tf_mapping = {
    "5 min": {"yf": "5m", "tv": "5", "period": "7d"},
    "15 min": {"yf": "15m", "tv": "15", "period": "7d"},
    "30 min": {"yf": "30m", "tv": "30", "period": "30d"},
    "1 hour": {"yf": "1h", "tv": "60", "period": "60d"},
    "4 hour": {"yf": "4h", "tv": "240", "period": "90d"},
    "1 day": {"yf": "1d", "tv": "D", "period": "max"}
}

selected_tf = tf_mapping[tf_display]

# 2. Data Download කිරීම
@st.cache_data
def get_market_data(symbol, tf, prd):
    df = yf.download(symbol, period=prd, interval=tf, auto_adjust=True)
    return df

df = get_market_data(ticker, selected_tf["yf"], selected_tf["period"])

if not df.empty and len(df) > 35:
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
    
    # 4. Machine Learning Model Training
    features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns']
    X = df[features]
    y = df['Target']
    
    split = int(0.85 * len(df))
    X_train, y_train = X[:split], y[:split]
    
    model = RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=3, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. Prediction & Probabilities
    last_market_state = X.iloc[[-1]]
    prediction = model.predict(last_market_state)[0]
    probability = model.predict_proba(last_market_state)[0]
    
    current_price = float(df['Close'].to_numpy()[-1])
    volatility = float((df['High'] - df['Low']).rolling(window=14).mean().to_numpy()[-1])
    ai_confidence = max(probability) * 100
    
    if prediction == 1:
        tp_price = current_price + (volatility * 2.0)
        sl_price = current_price - (volatility * 1.5)
    else:
        tp_price = current_price - (volatility * 2.0)
        sl_price = current_price + (volatility * 1.5)

    # --- 6. SCREEN OUTPUT DISPLAY ---
    st.write("---")
    st.subheader(f"📊 {selected_display_name} ({tf_display}) PRO AI විශ්ලේෂණය:")
    
    st.metric(label="🎯 AI නිර්දේශිත Limit Entry මිල (AI Evaluated Entry Price)", value=f"${current_price:.4f}")
    
    st.write("### 🚨 AI තීරණය (AI Signal Output):")
    
    has_valid_signal = False
    
    if ai_confidence < 60.0:
        st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI විශ්වාසය මදියි ({ai_confidence:.1f}%). කරුණාකර වෙනත් Timeframe එකක් බලන්න.")
    else:
        has_valid_signal = True
        if prediction == 1:
            st.success(f"🟢 **DIRECTION: BUY / LONG** 📈 ⬆️ (Confidence: {ai_confidence:.1f}%)")
        else:
            st.error(f"🔴 **DIRECTION: SELL / SHORT** 📉 ⬇️ (Confidence: {ai_confidence:.1f}%)")

    st.info("💡 **සටහන:** පහත ප්‍රස්ථාරයේ (Chart) පෙන්වන්නේ තත්පරයෙන් තත්පරයට වෙනස් වන සජීවී මිලයි. AI විසින් ඉහළින් නිර්දේශ කර ඇති Entry මිලට **Limit Order** එකක් සකසා වෙළඳපොල එම මිලට එනතුරු රැඳී සිටින්න.")

    # --- 7. 100% LIVE TRADINGVIEW CHART ---
    st.write("---")
    st.subheader("📈 සජීවී ප්‍රස්ථාර ඇනලයිසර් (Live Analysis Chart):")
    
    chart_studies = '["MASimple@tv-basicstudies", "BBands@tv-basicstudies"]'
    
    tradingview_html = f"""
    <div class="tradingview-widget-container" style="height:500px; width:100%;">
      <div id="tradingview_chart" style="height:500px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "height": 500,
        "symbol": "{full_tv_ticker}",
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
    components.html(tradingview_html, height=510)

    # --- 8. VISUAL TARGET SYNC PANEL ---
    if has_valid_signal:
        target_msg = f"📊 **ප්‍රස්ථාරයේ ඇඳිය යුතු නිවැරදි මිල මට්ටම් (Visual Targets):** \n\n🔵 **Entry Limit Price:** ${current_price:.4f} \n\n🎯 **Take Profit (TP) Target:** ${tp_price:.4f} \n\n🛑 **Stop Loss (SL) Target:** ${sl_price:.4f}"
        st.info(target_msg)
    else:
        st.info("ℹ️ **AI එකට මාකට් එක සුවර් නැති නිසා (NO SIGNAL), අලාභ වළක්වා ගැනීමට Entry, TP, සහ SL මට්ටම් මෙහි ලබා දී නොමැත.**")

else:
    st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් සජීවී දත්ත නොමැත. කරුණාකර වෙනත් Timeframe එකක් තෝරන්න.")
