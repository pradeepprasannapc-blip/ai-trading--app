import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components
import requests
import os
import time
import plotly.graph_objects as go
import io

# --- 1. App පෙනුම සහ Title සැකසීම ---
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="wide")

st.title("⚡ PRO AI Trading Signal App (Institutional VIP Edition)")
st.write("SMC (FVG & Order Blocks), ATR දර්ශකය සහ ලෝකයේ හොඳම Technical Indicators එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

try:
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_GROUP_ID = st.secrets["TELEGRAM_GROUP_ID"]
    TELEGRAM_CHANNEL_ID = st.secrets["TELEGRAM_CHANNEL_ID"]
except KeyError:
    st.error("⚠️ රහස්‍ය දත්ත (Secrets) සොයාගත නොහැක. කරුණාකර Streamlit Cloud හි Secrets සකසන්න.")
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_GROUP_ID = ""
    TELEGRAM_CHANNEL_ID = ""

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_GROUP_ID or not TELEGRAM_CHANNEL_ID:
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_group = {"chat_id": TELEGRAM_GROUP_ID, "text": message, "parse_mode": "Markdown"}
    payload_channel = {"chat_id": TELEGRAM_CHANNEL_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        res_group = requests.post(url, json=payload_group)
        res_channel = requests.post(url, json=payload_channel)
        return res_group.status_code == 200 and res_channel.status_code == 200
    except:
        return False

# 🟢 අලුත් Function එක: URL වෙනුවට Image Bytes කෙලින්ම යැවීම
def send_telegram_photo_bytes(caption, photo_bytes):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_GROUP_ID or not TELEGRAM_CHANNEL_ID:
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    success = True
    
    for chat_id in [TELEGRAM_GROUP_ID, TELEGRAM_CHANNEL_ID]:
        payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
        files = {"photo": ("chart.png", photo_bytes, "image/png")}
        try:
            res = requests.post(url, data=payload, files=files)
            if res.status_code != 200:
                success = False
        except:
            success = False
            
    return success

# 🟢 අලුත් Function එක: Candlestick සහ Risk/Reward Zone Chart එක සෑදීම
def generate_candlestick_image_bytes(df, coin_name, direction, entry, tp3, sl):
    df_plot = df.tail(60).copy() # අවසාන කෑන්ඩල් 60 පෙන්වමු
    
    fig = go.Figure()

    # Candlestick chart එක එකතු කිරීම
    fig.add_trace(go.Candlestick(
        x=df_plot.index,
        open=df_plot['Open'],
        high=df_plot['High'],
        low=df_plot['Low'],
        close=df_plot['Close'],
        name='Price'
    ))

    x_start = df_plot.index[0]
    x_end = df_plot.index[-1] + pd.Timedelta(minutes=60) # Zone එක ඉස්සරහට දික් කරන්න

    # 🟢 Profit Zone (Green Box)
    fig.add_shape(
        type="rect",
        x0=x_start, y0=entry, x1=x_end, y1=tp3,
        fillcolor="rgba(46, 204, 113, 0.2)",
        line=dict(color="rgba(46, 204, 113, 0.8)", width=2),
        layer="below"
    )

    # 🔴 Stop Loss Zone (Red Box)
    fig.add_shape(
        type="rect",
        x0=x_start, y0=sl, x1=x_end, y1=entry,
        fillcolor="rgba(231, 76, 60, 0.2)",
        line=dict(color="rgba(231, 76, 60, 0.8)", width=2),
        layer="below"
    )

    # Entry, TP, සහ SL රේඛා
    fig.add_hline(y=entry, line_dash="dash", line_color="blue", annotation_text="Entry", annotation_position="top right")
    fig.add_hline(y=tp3, line_dash="dash", line_color="green", annotation_text="TP 3", annotation_position="top right")
    fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="Stop Loss", annotation_position="bottom right")

    fig.update_layout(
        title=f"✨ {coin_name} - {direction} SETUP 🚀",
        yaxis_title="Price",
        xaxis_title="Time",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        width=800,
        height=500,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    img_bytes = fig.to_image(format="png")
    return img_bytes


HISTORY_FILE = "signal_history.csv"

tab1, tab2 = st.tabs(["⚡ Live AI Signals", "📂 Auto Signal History & Live Tracker"])

with tab1:
    st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න:")
    category = st.radio("ප්‍රවර්ගය තෝරන්න:", ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ", "💱 ෆොරෙක්ස්", "✨ ලෝහ සහ තෙල්", "✏️ වෙනත් (Custom)"], horizontal=True)

    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ":
        market_options = {
            "Bitcoin (BTC/USD)": "BTC-USD", "Ethereum (ETH/USD)": "ETH-USD",
            "Solana (SOL/USD)": "SOL-USD", "Binance Coin (BNB/USD)": "BNB-USD",
            "Ripple (XRP/USD)": "XRP-USD", "Cardano (ADA/USD)": "ADA-USD",
            "Dogwifhat (WIF/USD)": "WIF-USD", "Shiba Inu (SHIB/USD)": "SHIB-USD",
            "Pepe (PEPE/USD)": "PEPE-USD", "Avalanche (AVAX/USD)": "AVAX-USD",
            "Chainlink (LINK/USD)": "LINK-USD", "Polkadot (DOT/USD)": "DOT-USD",
            "Fantom (FTM/USD)": "FTM-USD", "Polygon (MATIC/USD)": "MATIC-USD",
            "Injective (INJ/USD)": "INJ-USD"
        }
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('-USD', 'USDT')
        full_tv_ticker = f"BINANCE:{clean_symbol}"

    elif category == "💱 ෆොරෙක්ස්":
        market_options = {"Euro / US Dollar (EUR/USD)": "EURUSD=X", "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X", "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X", "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X"}
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('=X', '')
        full_tv_ticker = f"FX_IDC:{clean_symbol}"

    elif category == "✨ ලෝහ සහ තෙල්":
        market_options = {"රන් / Gold (XAU/USD)": "GC=F", "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"}
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('=F', '')
        full_tv_ticker = f"COMEX:{clean_symbol}" if "GC" in ticker else f"NYMEX:{clean_symbol}"

    else:
        st.info("💡 **ඔබට අවශ්‍ය ඕනෑම කාසියක් මෙහි ඇතුළත් කළ හැක.**")
        col_c1, col_c2 = st.columns(2)
        with col_c1: ticker = st.text_input("Yahoo Finance Ticker:", "DOGE-USD")
        with col_c2: full_tv_ticker = st.text_input("TradingView Symbol:", "BINANCE:DOGEUSDT")
        selected_display_name = f"Custom Symbol ({ticker})"

    tf_display = st.selectbox("Timeframe එක තෝරන්න:", ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"])
    tf_mapping = {
        "5 min": {"yf": "5m", "tv": "5", "period": "7d"}, "15 min": {"yf": "15m", "tv": "15", "period": "7d"},
        "30 min": {"yf": "30m", "tv": "30", "period": "30d"}, "1 hour": {"yf": "1h", "tv": "60", "period": "60d"},
        "4 hour": {"yf": "4h", "tv": "240", "period": "90d"}, "1 day": {"yf": "1d", "tv": "D", "period": "max"}
    }
    selected_tf = tf_mapping[tf_display]

    @st.cache_data
    def get_market_data(symbol, tf, prd):
        df = yf.download(symbol, period=prd, interval=tf, auto_adjust=True)
        return df

    df = get_market_data(ticker, selected_tf["yf"], selected_tf["period"])

    if not df.empty and len(df) > 35:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
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
        
        df['High-Low'] = df['High'] - df['Low']
        df['High-PrevClose'] = np.abs(df['High'] - df['Close'].shift(1))
        df['Low-PrevClose'] = np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
        df.dropna(inplace=True) 
        
        if len(df) < 20:
            st.warning("⚠️ ප්‍රමාණවත් දත්ත නොමැත.")
        else:
            try:
                features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns', 'ATR']
                X = df[features]
                y = df['Target']
                
                split = int(0.85 * len(df))
                X_train, y_train = X[:split], y[:split]
                
                model = RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=3, random_state=42)
                model.fit(X_train, y_train)
                
                last_market_state = X.iloc[[-1]]
                prediction = model.predict(last_market_state)[0]
                probability = model.predict_proba(last_market_state)[0]
                
                try:
                    tkr_live = yf.Ticker(ticker)
                    current_price = float(tkr_live.fast_info['lastPrice'])
                except Exception:
                    current_price = float(df['Close'].to_numpy()[-1])
                    
                atr_val = float(df['ATR'].to_numpy()[-1])
                ai_confidence = max(probability) * 100
                dp = 8 if current_price < 0.01 else 4
                
                pullback_amount = atr_val * 0.2  
                
                if prediction == 1: 
                    entry_price = current_price - pullback_amount 
                    tp1_price = entry_price + (atr_val * 1.2)
                    tp2_price = entry_price + (atr_val * 2.2)
                    tp3_price = entry_price + (atr_val * 3.5)
                    sl_price = entry_price - (atr_val * 1.5) 
                else: 
                    entry_price = current_price + pullback_amount 
                    tp1_price = entry_price - (atr_val * 1.2)
                    tp2_price = entry_price - (atr_val * 2.2)
                    tp3_price = entry_price - (atr_val * 3.5)
                    sl_price = entry_price + (atr_val * 1.5) 
        
                st.write("---")
                st.subheader(f"📊 {selected_display_name} PRO AI විශ්ලේෂණය:")
                
                has_valid_signal = False
                if ai_confidence < 60.0:
                    st.warning(f"⚠️ NO SIGNAL (මාකට් එක පැහැදිලි නැත)")
                else:
                    has_valid_signal = True
                    if prediction == 1:
                        st.success(f"🟢 **BUY / LONG** 📈 ⬆️ ({ai_confidence:.1f}%)")
                    else:
                        st.error(f"🔴 **SELL / SHORT** 📉 ⬇️ ({ai_confidence:.1f}%)")
        
                if has_valid_signal:
                    dir_text = "🟢 BUY / LONG" if prediction == 1 else "🔴 SELL / SHORT"
                    direction = "BUY" if prediction == 1 else "SELL"
                    
                    st.write("### 📸 Signal Visualizer Preview (Telegram වෙත යැවෙන ප්‍රස්ථාරය)")
                    
                    try:
                        chart_image_bytes = generate_candlestick_image_bytes(df, selected_display_name.split()[0], direction, entry_price, tp3_price, sl_price)
                        st.image(chart_image_bytes, caption="Generated Candlestick setup")
                        image_generated_successfully = True
                    except Exception as img_err:
                        st.error(f"⚠️ ප්‍රස්ථාරය සැකසීමේදී දෝෂයක්. kaleido package එක නිවැරදිව ස්ථාපනය වී ඇතිදැයි බලන්න. ({img_err})")
                        image_generated_successfully = False

                    if st.button("Send Signal & Chart to Telegram 🚀"):
                        telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n🪙 *Coin:* {selected_display_name}\n🔥 *Direction:* {dir_text}\n\n🔵 *Entry:* `${entry_price:.{dp}f}`\n🎯 *TP 1:* `${tp1_price:.{dp}f}`\n🎯 *TP 2:* `${tp2_price:.{dp}f}`\n🎯 *TP 3:* `${tp3_price:.{dp}f}`\n🛑 *SL:* `${sl_price:.{dp}f}`"
                        
                        with st.spinner("Telegram වෙත යවමින් පවතී... ⏳"):
                            success = False
                            if image_generated_successfully:
                                success = send_telegram_photo_bytes(telegram_text, chart_image_bytes)
                            
                            if success:
                                st.success("✅ සාර්ථකව යැව්වා!")
                            else:
                                st.error("❌ යැවීම අසාර්ථකයි.")
            except Exception as e:
                st.error(f"⚠️ විශ්ලේෂණයේදී ගැටලුවක්. ({e})")
