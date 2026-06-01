import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components
import requests
import os
import time

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Technical Indicators සහ 100% Live TradingView Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

# Secrets හරහා Token ලබා ගැනීම
try:
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError:
    st.error("⚠️ රහස්‍ය දත්ත (Secrets) සොයාගත නොහැක. කරුණාකර Streamlit Cloud හි Secrets සකසන්න.")
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except:
        return False

HISTORY_FILE = "signal_history.csv"

# --- TABS සෑදීම (පිටු 2ක්) ---
tab1, tab2 = st.tabs(["⚡ Live AI Signals", "📂 Auto Signal History & Results"])

# ==========================================
# TAB 1: LIVE SIGNALS 
# ==========================================
with tab1:
    st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න:")

    category = st.radio(
        "ප්‍රවර්ගය තෝරන්න:",
        ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ", "💱 ෆොරෙක්ස්", "✨ ලෝහ සහ තෙල්", "✏️ වෙනත් (Custom)"],
        horizontal=True
    )

    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ":
        market_options = {
            "Bitcoin (BTC/USD)": "BTC-USD", "Ethereum (ETH/USD)": "ETH-USD",
            "Solana (SOL/USD)": "SOL-USD", "Binance Coin (BNB/USD)": "BNB-USD",
            "Ripple (XRP/USD)": "XRP-USD", "Cardano (ADA/USD)": "ADA-USD",
            "Dogecoin (DOGE/USD)": "DOGE-USD", "Shiba Inu (SHIB/USD)": "SHIB-USD",
            "Pepe (PEPE/USD)": "PEPE-USD", "Avalanche (AVAX/USD)": "AVAX-USD",
            "Chainlink (LINK/USD)": "LINK-USD", "Polkadot (DOT/USD)": "DOT-USD"
        }
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('-USD', 'USDT')
        full_tv_ticker = f"BINANCE:{clean_symbol}"

    elif category == "💱 ෆොරෙක්ස්":
        market_options = {
            "Euro / US Dollar (EUR/USD)": "EURUSD=X", "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X",
            "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X", "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X"
        }
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('=X', '')
        full_tv_ticker = f"FX_IDC:{clean_symbol}"

    elif category == "✨ ලෝහ සහ තෙල්":
        market_options = {
            "රන් / Gold (XAU/USD)": "GC=F", "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"
        }
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('=F', '')
        full_tv_ticker = f"COMEX:{clean_symbol}" if "GC" in ticker else f"NYMEX:{clean_symbol}"

    else:
        st.info("💡 **ඔබට අවශ්‍ය ඕනෑම කාසියක් මෙහි ඇතුළත් කළ හැක.**")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            ticker = st.text_input("Yahoo Finance Ticker:", "DOGE-USD")
        with col_c2:
            full_tv_ticker = st.text_input("TradingView Symbol:", "BINANCE:DOGEUSDT")
        selected_display_name = f"Custom Symbol ({ticker})"

    tf_display = st.selectbox(
        "Timeframe එක තෝරන්න:", 
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

    @st.cache_data
    def get_market_data(symbol, tf, prd):
        df = yf.download(symbol, period=prd, interval=tf, auto_adjust=True)
        return df

    df = get_market_data(ticker, selected_tf["yf"], selected_tf["period"])

    if not df.empty and len(df) > 35:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
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
        
        features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns']
        X = df[features]
        y = df['Target']
        
        split = int(0.85 * len(df))
        X_train, y_train = X[:split], y[:split]
        
        model = RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=3, random_state=42)
        model.fit(X_train, y_train)
        
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

        st.write("---")
        st.subheader(f"📊 {selected_display_name} ({tf_display}) PRO AI විශ්ලේෂණය:")
        
        has_valid_signal = False
        if ai_confidence < 60.0:
            st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI විශ්වාසය මදියි ({ai_confidence:.1f}%).")
        else:
            has_valid_signal = True
            if prediction == 1:
                st.success(f"🟢 **DIRECTION: BUY / LONG** 📈 ⬆️ (Confidence: {ai_confidence:.1f}%)")
            else:
                st.error(f"🔴 **DIRECTION: SELL / SHORT** 📉 ⬇️ (Confidence: {ai_confidence:.1f}%)")

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

        st.write("---")
        if has_valid_signal:
            dir_text = "🟢 BUY / LONG 📈 ⬆️" if prediction == 1 else "🔴 SELL / SHORT 📉 ⬇️"
            
            target_msg = f"📊 **ඇඳිය යුතු නිවැරදි මිල මට්ටම් (Visual Targets):** \n\n🔥 **Signal Direction:** {dir_text} \n\n🔵 **Entry Limit Price:** ${current_price:.4f} \n\n🎯 **Take Profit (TP) Target:** ${tp_price:.4f} \n\n🛑 **Stop Loss (SL) Target:** ${sl_price:.4f}"
            st.info(target_msg)
            
            st.write("### 📲 Telegram Group එකට Signal එක යවන්න")
            if st.button("Send Signal to Telegram 🚀"):
                
                telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n"
                telegram_text += f"🪙 *Coin/Pair:* {selected_display_name}\n"
                telegram_text += f"⏱ *Timeframe:* {tf_display}\n"
                telegram_text += f"🔥 *Direction:* {dir_text}\n\n"
                telegram_text += f"🔵 *Entry Price:* `${current_price:.4f}`\n"
                telegram_text += f"🎯 *Take Profit (TP):* `${tp_price:.4f}`\n"
                telegram_text += f"🛑 *Stop Loss (SL):* `${sl_price:.4f}`\n\n"
                telegram_text += f"📊 _Analyzed by PRO AI Trading System_"
                
                with st.spinner("Telegram වෙත යවමින් පවතී..."):
                    success = send_telegram_message(telegram_text)
                    
                if success:
                    st.success("✅ Signal එක සාර්ථකව යැව්වා! (History එකටත් Save වුණා)")
                    
                    # Auto History එකට දත්ත ඇතුළත් කිරීම (අලුත් Format එක)
                    date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                    data = {
                        "Date": [date_str], 
                        "Ticker": [ticker],
                        "Coin": [selected_display_name.split()[0]], 
                        "Direction": ["BUY" if prediction == 1 else "SELL"], 
                        "Entry": [current_price], 
                        "TP": [tp_price],
                        "SL": [sl_price],
                        "Status": ["⏳ Pending"]
                    }
                    df_new = pd.DataFrame(data)
                    if os.path.exists(HISTORY_FILE):
                        df_new.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
                    else:
                        df_new.to_csv(HISTORY_FILE, index=False)
                else:
                    st.error("❌ Signal එක යැවීම අසාර්ථකයි.")
    else:
        st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් දත්ත නොමැත.")

# ==========================================
# TAB 2: SIGNAL HISTORY & RESULTS (AUTO CHECKER)
# ==========================================
with tab2:
    st.subheader("📂 ගත්තු Signals වල History එක (Auto Check)")
    st.write("ඔයා යවපු සිග්නල් TP එකට හරි SL එකට හරි ගියාම මෙතන Status එක ස්වයංක්‍රීයව වෙනස් වෙනවා!")
    
    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)
            # පැරණි Format එක නම් Auto Delete කර අලුත් එකට ඉඩ හැදීම
            if "Status" not in history_df.columns:
                os.remove(HISTORY_FILE)
                st.warning("🔄 පද්ධතිය යාවත්කාලීන විය. කරුණාකර අලුතින් Signal එකක් ලබා දෙන්න.")
                st.stop()
        except Exception:
            pass
            
        # 1. පෙන්ඩින් (Pending) ට්‍රේඩ්ස් චෙක් කිරීම
        updated = False
        with st.spinner('සජීවීව මාකට් එක පරීක්ෂා කරමින් පවතී... 🔍'):
            for index, row in history_df.iterrows():
                if row['Status'] == "⏳ Pending":
                    # අදාළ කාසියේ අද දවසේ මිල ගණන් ගැනීම
                    df_hist = yf.download(row['Ticker'], period="1d", interval="5m", progress=False)
                    if not df_hist.empty:
                        if isinstance(df_hist.columns, pd.MultiIndex):
                            df_hist.columns = df_hist.columns.get_level_values(0)
                        
                        max_price = float(df_hist['High'].max())
                        min_price = float(df_hist['Low'].min())
                        tp_val = float(row['TP'])
                        sl_val = float(row['SL'])
                        
                        if row['Direction'] == 'BUY':
                            if max_price >= tp_val:
                                history_df.at[index, 'Status'] = "✅ TP HIT"
                                updated = True
                            elif min_price <= sl_val:
                                history_df.at[index, 'Status'] = "🛑 SL HIT"
                                updated = True
                        else: # SELL
                            if min_price <= tp_val:
                                history_df.at[index, 'Status'] = "✅ TP HIT"
                                updated = True
                            elif max_price >= sl_val:
                                history_df.at[index, 'Status'] = "🛑 SL HIT"
                                updated = True
        
        # 2. අලුත් Status ටික CSV එකට Save කිරීම
        if updated:
            history_df.to_csv(HISTORY_FILE, index=False)
            
        # 3. ලස්සනට පෙන්වීම සඳහා දත්ත සකස් කිරීම
        display_df = history_df.copy()
        display_df['Entry'] = display_df['Entry'].apply(lambda x: f"${float(x):.4f}")
        display_df['TP'] = display_df['TP'].apply(lambda x: f"${float(x):.4f}")
        display_df['SL'] = display_df['SL'].apply(lambda x: f"${float(x):.4f}")
        # Ticker column එක User ට පෙන්නන්න අවශ්‍ය නැති නිසා අයින් කරනවා
        display_df.drop(columns=['Ticker'], inplace=True)
        
        # Table එක පෙන්වීම
        st.dataframe(display_df, use_container_width=True)
        
        # --- TELEGRAM යැවීම ---
        st.write("---")
        st.subheader("📢 Result එක Telegram යවන්න")
        
        # ✅ TP HIT වුණු ඒවා පමණක් තේරීමට දීම
        completed_signals = history_df[history_df['Status'] != "⏳ Pending"]
        
        if not completed_signals.empty:
            options = []
            for index, row in completed_signals.iterrows():
                options.append(f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})")
                
            selected_sig = st.selectbox("Update කරන්න අවශ්‍ය Signal එක තෝරන්න:", options)
            
            if selected_sig:
                selected_idx = options.index(selected_sig)
                sel_row = completed_signals.iloc[selected_idx]
                
                if "TP HIT" in sel_row['Status']:
                    if st.button("✅ Profit මැසේජ් එක යවන්න 🚀"):
                        msg = f"✅ *PROFIT TARGET HIT!* 🎉\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {sel_row['Direction']}\n🎯 *Target Reached:* {sel_row['TP']}\n\n🤑 _PRO AI Trading Signal එක 100% සාර්ථකයි!_"
                        if send_telegram_message(msg):
                            st.success("✅ Profit මැසේජ් එක සාර්ථකව යැව්වා!")
                else:
                    if st.button("🛑 Loss මැසේජ් එක යවන්න"):
                        msg = f"🛑 *STOP LOSS HIT* 📉\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {sel_row['Direction']}\n\nමාකට් එක වෙනස් වුණා. Risk Management අනුගමනය කරන්න. ඊළඟ Trade එකෙන් අපි අල්ලමු! 💪"
                        if send_telegram_message(msg):
                            st.success("🛑 Stop Loss මැසේජ් එක යැව්වා!")
        else:
            st.info("තවම TP හෝ SL වුණු සිග්නල් කිසිවක් නැත.")
                        
        st.write("---")
        if st.button("🗑️ History එක මකන්න (Clear All)"):
            os.remove(HISTORY_FILE)
            st.success("History එක සම්පූර්ණයෙන්ම මකා දැමුවා! කරුණාකර App එක Refresh කරන්න.")
    else:
        st.info("දැනට කිසිම Signal එකක් Save වෙලා නෑ. අලුත් Signal එකක් Telegram එකට යැව්වම මෙතනට වැටෙයි.")
