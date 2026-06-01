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
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="wide")

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

# --- TABS සෑදීම ---
tab1, tab2 = st.tabs(["⚡ Live AI Signals", "📂 Auto Signal History & Live Tracker"])

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
        
        dp = 8 if current_price < 0.01 else 4
        
        if prediction == 1:
            tp1_price = current_price + (volatility * 1.2)
            tp2_price = current_price + (volatility * 2.0)
            tp3_price = current_price + (volatility * 3.0)
            sl_price = current_price - (volatility * 1.5)
        else:
            tp1_price = current_price - (volatility * 1.2)
            tp2_price = current_price - (volatility * 2.0)
            tp3_price = current_price - (volatility * 3.0)
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
            
            target_msg = (
                f"📊 **ඇඳිය යුතු නිවැරදි මිල මට්ටම් (Visual Targets):**\n\n"
                f"🪙 **Coin:** {selected_display_name}\n\n"
                f"🔥 **Signal Direction:** {dir_text}\n\n"
                f"🔵 **Entry Limit Price:** ${current_price:.{dp}f}\n\n"
                f"🎯 **TP 1:** ${tp1_price:.{dp}f}\n\n"
                f"🎯 **TP 2:** ${tp2_price:.{dp}f}\n\n"
                f"🎯 **TP 3:** ${tp3_price:.{dp}f}\n\n"
                f"🛑 **Stop Loss (SL):** ${sl_price:.{dp}f}"
            )
            st.info(target_msg)
            
            st.write("### 📲 Telegram Group එකට Signal එක යවන්න")
            if st.button("Send Signal to Telegram 🚀"):
                
                telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n"
                telegram_text += f"🪙 *Coin/Pair:* {selected_display_name}\n"
                telegram_text += f"⏱ *Timeframe:* {tf_display}\n"
                telegram_text += f"🔥 *Direction:* {dir_text}\n\n"
                telegram_text += f"🔵 *Entry Price:* `${current_price:.{dp}f}`\n"
                telegram_text += f"🎯 *TP 1:* `${tp1_price:.{dp}f}`\n"
                telegram_text += f"🎯 *TP 2:* `${tp2_price:.{dp}f}`\n"
                telegram_text += f"🎯 *TP 3:* `${tp3_price:.{dp}f}`\n"
                telegram_text += f"🛑 *Stop Loss (SL):* `${sl_price:.{dp}f}`\n\n"
                telegram_text += f"📊 _Analyzed by PRO AI Trading System_"
                
                with st.spinner("Telegram වෙත යවමින් පවතී..."):
                    success = send_telegram_message(telegram_text)
                    
                if success:
                    st.success("✅ Signal එක සාර්ථකව යැව්වා! (History එකටත් Save වුණා)")
                    
                    date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                    data = {
                        "Date": [date_str], 
                        "Ticker": [ticker],
                        "Coin": [selected_display_name.split()[0]], 
                        "Direction": ["BUY" if prediction == 1 else "SELL"], 
                        "Entry": [current_price], 
                        "TP1": [tp1_price],
                        "TP2": [tp2_price],
                        "TP3": [tp3_price],
                        "SL": [sl_price],
                        "Status": ["⏳ Pending Entry"] # අලුත් Pending Entry Status එක
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
# TAB 2: SIGNAL HISTORY & RESULTS (AUTO CHECKER & LIVE TRACKER)
# ==========================================
with tab2:
    st.subheader("📂 ගත්තු Signals වල History එක සහ Live Price")
    st.write("මාකට් එකේ සජීවී මිල මෙහි යාවත්කාලීන වේ. TP 1, 2, හෝ 3 Hit වූ විට Status එක Auto වෙනස් වෙනවා!")
    
    auto_refresh = st.checkbox("🔄 Auto Refresh (සෑම තත්පර 15කට වරක් සජීවී මිල සහ Status පමණක් යාවත්කාලීන වීමට මෙහි ටික් එකක් දාන්න)")

    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)
            if "TP1" not in history_df.columns:
                os.remove(HISTORY_FILE)
                st.warning("🔄 පද්ධතිය යාවත්කාලීන විය. කරුණාකර අලුතින් Signal එකක් ලබා දෙන්න.")
                st.stop()
        except Exception:
            pass
            
        updated = False
        live_prices_dict = {}
        
        with st.spinner('සජීවීව මාකට් එක පරීක්ෂා කරමින් පවතී... 🔍'):
            for index, row in history_df.iterrows():
                try:
                    df_hist = yf.download(row['Ticker'], period="1d", progress=False)
                    if not df_hist.empty:
                        if isinstance(df_hist.columns, pd.MultiIndex):
                            df_hist.columns = df_hist.columns.get_level_values(0)
                        
                        current_live_price = float(df_hist['Close'].dropna().iloc[-1])
                        live_prices_dict[index] = current_live_price
                        
                        # --- අලුත් Auto Status Checker Logic එක ---
                        
                        entry_val = float(row['Entry'])
                        tp1_val = float(row['TP1'])
                        tp2_val = float(row['TP2'])
                        tp3_val = float(row['TP3'])
                        sl_val = float(row['SL'])
                        
                        new_status = row['Status']
                        
                        # 1. Pending Entry එකක් නම්, Entry එකට ආවද බලනවා
                        if new_status == "⏳ Pending Entry":
                            if row['Direction'] == 'BUY':
                                # BUY එකකට Limit Price එකට එන්න නම් මිල අඩුවෙන්න ඕනේ
                                if current_live_price <= entry_val:
                                    new_status = "🟢 Active"
                            else: # SELL
                                # SELL එකකට Limit Price එකට එන්න නම් මිල වැඩිවෙන්න ඕනේ
                                if current_live_price >= entry_val:
                                    new_status = "🟢 Active"
                                    
                        # 2. Active වෙලා නම්, TP හෝ SL වැදුනද බලනවා
                        if new_status == "🟢 Active":
                            if row['Direction'] == 'BUY':
                                if current_live_price <= sl_val:
                                    new_status = "🛑 SL HIT"
                                elif current_live_price >= tp3_val:
                                    new_status = "✅ TP3 HIT"
                                elif current_live_price >= tp2_val:
                                    new_status = "✅ TP2 HIT"
                                elif current_live_price >= tp1_val:
                                    new_status = "✅ TP1 HIT"
                                    
                            else: # SELL
                                if current_live_price >= sl_val:
                                    new_status = "🛑 SL HIT"
                                elif current_live_price <= tp3_val:
                                    new_status = "✅ TP3 HIT"
                                elif current_live_price <= tp2_val:
                                    new_status = "✅ TP2 HIT"
                                elif current_live_price <= tp1_val:
                                    new_status = "✅ TP1 HIT"
                                    
                        if new_status != row['Status']:
                            history_df.at[index, 'Status'] = new_status
                            updated = True
                            
                    else:
                        live_prices_dict[index] = np.nan
                except Exception:
                    live_prices_dict[index] = np.nan
        
        if updated:
            history_df.to_csv(HISTORY_FILE, index=False)
            
        display_df = history_df.copy()
        display_df['Live Price'] = display_df.index.map(live_prices_dict)
        
        def format_price(x):
            if pd.isnull(x): return "N/A"
            val = float(x)
            return f"${val:.8f}" if val < 0.01 else f"${val:.4f}"

        cols_to_format = ['Entry', 'TP1', 'TP2', 'TP3', 'SL', 'Live Price']
        for col in cols_to_format:
            display_df[col] = display_df[col].apply(format_price)
            
        display_df.drop(columns=['Ticker'], inplace=True)
        
        # Table එක පෙන්වීම
        st.dataframe(display_df, use_container_width=True)
        
        # --- TELEGRAM යැවීම ---
        st.write("---")
        st.subheader("📢 Result එක Telegram යවන්න")
        
        # Pending හෝ Active ඒවා අයින් කර, Result එක ආපු (TP/SL) ඒවා විතරක් තේරීම
        completed_signals = history_df[~history_df['Status'].isin(["⏳ Pending Entry", "🟢 Active"])]
        
        if not completed_signals.empty:
            options = []
            for index, row in completed_signals.iterrows():
                options.append(f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})")
                
            selected_sig = st.selectbox("Update කරන්න අවශ්‍ය Signal එක තෝරන්න:", options)
            
            if selected_sig:
                selected_idx = options.index(selected_sig)
                sel_row = completed_signals.iloc[selected_idx]
                
                if "TP" in sel_row['Status']:
                    hit_level = sel_row['Status'].split()[1]
                    tp_val = float(sel_row[hit_level])
                    tp_dp = 8 if tp_val < 0.01 else 4
                    
                    if st.button(f"✅ {hit_level} Profit මැසේජ් එක යවන්න 🚀"):
                        msg = f"✅ *PROFIT TARGET HIT!* 🎉\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {sel_row['Direction']}\n🎯 *{hit_level} Reached:* `${tp_val:.{tp_dp}f}`\n\n🤑 _PRO AI Trading Signal එක 100% සාර්ථකයි!_"
                        if send_telegram_message(msg):
                            st.success(f"✅ {hit_level} Profit මැසේජ් එක සාර්ථකව යැව්වා!")
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
            
        # Streamlit Soft Refresh Logic
        if auto_refresh:
            time.sleep(15)
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()
    else:
        st.info("දැනට කිසිම Signal එකක් Save වෙලා නෑ. අලුත් Signal එකක් Telegram එකට යැව්වම මෙතනට වැටෙයි.")
