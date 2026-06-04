import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components
import requests
import os
import time
import io
import mplfinance as mpf

# --- 1. App පෙනුම සහ Title සැකසීම ---
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="wide")

st.title("⚡ PRO AI Trading Signal App (Institutional VIP Edition)")
st.write("SMC (FVG & Order Blocks), ATR, VWAP, Supertrend සහ Market Sentiment (Fear & Greed) එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

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

# --- Global Fear & Greed Fetcher (Cached) ---
@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        data = res.json()
        return int(data['data'][0]['value']), data['data'][0]['value_classification']
    except:
        return 50, "Neutral"

# 🟢 Candlestick Pattern Detection Function 
def detect_candlestick_pattern(df):
    try:
        if len(df) < 3:
            return "Not Enough Data"
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        last_body = abs(last['Close'] - last['Open'])
        last_is_green = last['Close'] > last['Open']
        prev_is_green = prev['Close'] > prev['Open']
        
        last_upper_wick = last['High'] - max(last['Open'], last['Close'])
        last_lower_wick = min(last['Open'], last['Close']) - last['Low']
        
        # 1. Bullish Engulfing
        if not prev_is_green and last_is_green and (last['Close'] > prev['Open']) and (last['Open'] < prev['Close']):
            return "Bullish Engulfing 📈"
            
        # 2. Bearish Engulfing
        if prev_is_green and not last_is_green and (last['Close'] < prev['Open']) and (last['Open'] > prev['Close']):
            return "Bearish Engulfing 📉"
            
        # 3. Hammer (Bullish Reversal)
        if last_lower_wick > (2 * last_body) and last_upper_wick < (0.2 * last_body):
            return "Hammer (Bullish) 🔨"
            
        # 4. Shooting Star (Bearish Reversal)
        if last_upper_wick > (2 * last_body) and last_lower_wick < (0.2 * last_body):
            return "Shooting Star (Bearish) 🌠"
            
        # 5. Doji
        if last_body < (0.01 * last['Open']):
            return "Doji (Indecision) ⚖️"
            
        # 6. Fair Value Gap (FVG)
        prev3 = df.iloc[-3]
        if last['Low'] > prev3['High']:
            return "Bullish FVG 🟢"
        if last['High'] < prev3['Low']:
            return "Bearish FVG 🔴"
            
        return "Standard Price Action"
    except:
        return "Standard Price Action"

# 🟢 Manual Supertrend Calculation for AI Features
def add_supertrend(df, period=10, multiplier=3):
    hl2 = (df['High'] + df['Low']) / 2
    atr = df['TR'].rolling(window=period).mean()
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    in_uptrend = True
    supertrend = [0.0] * len(df)
    st_dir = [1] * len(df)
    
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > upper_band.iloc[i-1]:
            in_uptrend = True
        elif df['Close'].iloc[i] < lower_band.iloc[i-1]:
            in_uptrend = False
        else:
            in_uptrend = in_uptrend 
            if in_uptrend and lower_band.iloc[i] < lower_band.iloc[i-1]:
                lower_band.iloc[i] = lower_band.iloc[i-1]
            if not in_uptrend and upper_band.iloc[i] > upper_band.iloc[i-1]:
                upper_band.iloc[i] = upper_band.iloc[i-1]
        
        st_dir[i] = 1 if in_uptrend else -1
        supertrend[i] = lower_band.iloc[i] if in_uptrend else upper_band.iloc[i]
        
    df['Supertrend'] = supertrend
    df['ST_DIR'] = st_dir
    return df

# 🟢 Advanced Pro Chart Generator (Dynamic Dark Theme VIP Edition)
def generate_candlestick_image_bytes(df, coin_name, direction, entry, tp1, tp2, tp3, sl, timeframe, detected_pattern):
    df_plot = df.tail(120).copy()
    
    # 1. Moving Averages & VWAP
    df_plot['MA_7'] = df_plot['Close'].rolling(window=7).mean()
    df_plot['MA_25'] = df_plot['Close'].rolling(window=25).mean()
    df_plot['MA_100'] = df_plot['Close'].rolling(window=100).mean()
    
    # 2. අනාගත කෑන්ඩල් සඳහා ඉඩ හැදීම
    freq = df_plot.index.to_series().diff().median()
    last_date = df_plot.index[-1]
    
    future_dates = [last_date + (freq * i) for i in range(1, 30)] 
    future_index = pd.DatetimeIndex(future_dates)
    future_df = pd.DataFrame(index=future_index, columns=df_plot.columns)
    df_padded = pd.concat([df_plot, future_df])
    
    total_len = len(df_padded)
    
    # 3. Fibonacci Retracement Levels
    low_val = df_plot['Low'].min()
    high_val = df_plot['High'].max()
    low_idx = df_plot['Low'].values.argmin()
    high_idx = df_plot['High'].values.argmax()
    
    diff = high_val - low_val
    fib_382 = high_val - (diff * 0.382) if low_idx < high_idx else low_val + (diff * 0.382)
    fib_618 = high_val - (diff * 0.618) if low_idx < high_idx else low_val + (diff * 0.618)
    
    start_fib_idx = min(low_idx, high_idx)
    end_fib_idx = max(low_idx, high_idx)
    
    where_mask = np.zeros(total_len, dtype=bool)
    where_mask[-(len(future_dates) + 5):] = True 
    
    where_fib = np.zeros(total_len, dtype=bool)
    where_fib[start_fib_idx:end_fib_idx+1] = True
    
    y_entry = np.full(total_len, entry)
    y_tp = np.full(total_len, tp3)
    y_sl = np.full(total_len, sl)
    y_fib_top = np.full(total_len, high_val)
    y_fib_bot = np.full(total_len, low_val)
    
    fills = [
        dict(y1=y_entry, y2=y_tp, where=where_mask, color='#089981', alpha=0.15), 
        dict(y1=y_entry, y2=y_sl, where=where_mask, color='#f23645', alpha=0.15), 
        dict(y1=y_fib_top, y2=y_fib_bot, where=where_fib, color='#787b86', alpha=0.08) 
    ]
    
    # Dark Mode Theme Configuration
    mc = mpf.make_marketcolors(up='#089981', down='#f23645', edge='inherit', wick='inherit', volume='in', ohlc='i')
    s = mpf.make_mpf_style(
        marketcolors=mc, 
        gridcolor='#2b2b43', 
        gridstyle='--', 
        facecolor='#131722', 
        edgecolor='#2b2b43',
        figcolor='#131722',
        rc={
            'font.size': 9, 
            'axes.grid': True,
            'text.color': '#d1d4dc',
            'axes.labelcolor': '#d1d4dc',
            'xtick.color': '#d1d4dc',
            'ytick.color': '#d1d4dc'
        }
    )
    
    ap = []
    if not df_padded['MA_7'].isna().all():
        ap.append(mpf.make_addplot(df_padded['MA_7'], color='#2962ff', width=1.5)) 
    if not df_padded['MA_25'].isna().all():
        ap.append(mpf.make_addplot(df_padded['MA_25'], color='#9c27b0', width=1.5)) 
    if not df_padded['MA_100'].isna().all():
        ap.append(mpf.make_addplot(df_padded['MA_100'], color='#66bb6a', width=1.5)) 
    if 'VWAP' in df_padded.columns and not df_padded['VWAP'].isna().all():
        ap.append(mpf.make_addplot(df_padded['VWAP'], color='#ff9800', width=1.8, linestyle='-.')) 
        
    # 🟢 Pattern Marker (Chart එකේ Arrow එකක් ඇඳීම)
    pattern_marker = [np.nan] * total_len
    last_candle_idx = len(df_plot) - 1
    
    if detected_pattern != "Standard Price Action":
        if "Bullish" in detected_pattern or "Buy" in direction or "Hammer" in detected_pattern:
            pattern_marker[last_candle_idx] = df_plot['Low'].iloc[-1] - (df_plot['ATR'].iloc[-1] * 0.8)
            ap.append(mpf.make_addplot(pattern_marker, type='scatter', markersize=200, marker='^', color='#089981'))
        else:
            pattern_marker[last_candle_idx] = df_plot['High'].iloc[-1] + (df_plot['ATR'].iloc[-1] * 0.8)
            ap.append(mpf.make_addplot(pattern_marker, type='scatter', markersize=200, marker='v', color='#f23645'))

    fig, axlist = mpf.plot(
        df_padded, 
        type='candle', 
        style=s, 
        volume=True,      
        addplot=ap,       
        fill_between=fills,
        returnfig=True, 
        figsize=(12, 6.5), 
        panel_ratios=(5,1), 
        tight_layout=True
    )
    
    ax_main = axlist[0] 
    
    # Volume Profile (VPVR)
    vp_bins = 50
    price_min, price_max = df_plot['Low'].min(), df_plot['High'].max()
    bin_size = (price_max - price_min) / vp_bins
    bins = np.linspace(price_min, price_max, vp_bins + 1)
    
    df_plot['Typical_Price'] = (df_plot['High'] + df_plot['Low'] + df_plot['Close']) / 3
    df_plot['Bin'] = pd.cut(df_plot['Typical_Price'], bins=bins, labels=False, include_lowest=True)
    
    df_up = df_plot[df_plot['Close'] >= df_plot['Open']]
    df_down = df_plot[df_plot['Close'] < df_plot['Open']]
    
    vp_up = df_up.groupby('Bin')['Volume'].sum()
    vp_down = df_down.groupby('Bin')['Volume'].sum()
    
    vp_up_arr = np.zeros(vp_bins)
    vp_down_arr = np.zeros(vp_bins)
    
    for b, vol in vp_up.items():
        if not np.isnan(b): vp_up_arr[int(b)] = vol
    for b, vol in vp_down.items():
        if not np.isnan(b): vp_down_arr[int(b)] = vol
        
    vp_y = bins[:-1] + (bin_size / 2)
    max_vol = np.max(vp_up_arr + vp_down_arr)
    
    if max_vol > 0:
        vp_widths_up = (vp_up_arr / max_vol) * 22  
        vp_widths_down = (vp_down_arr / max_vol) * 22
        ax_main.barh(vp_y, vp_widths_up, left=0, height=bin_size*0.9, color='#2962ff', alpha=0.2, zorder=1)
        ax_main.barh(vp_y, vp_widths_down, left=vp_widths_up, height=bin_size*0.9, color='#ff9800', alpha=0.2, zorder=1)

    # Fibonacci & Lines
    ax_main.plot([low_idx, high_idx], [low_val, high_val], color='#787b86', linestyle='--', linewidth=1.5, alpha=0.5)
    
    fib_levels_to_draw = [(high_val, '1 (100%)'), (fib_618, '0.618'), (fib_382, '0.382'), (low_val, '0 (0%)')]
    for val, label in fib_levels_to_draw:
        ax_main.plot([start_fib_idx, end_fib_idx], [val, val], color='#787b86', linestyle=':', linewidth=1.2, alpha=0.5)
        ax_main.text(start_fib_idx, val, f" {label}", color='#787b86', fontsize=8, va='bottom', ha='left')

    # Price Tags (Custom Labels generating dynamically for each coin)
    x_max = total_len - 1 
    target_levels = [
        (tp3, '#089981', 'Take Profit 3 (TP 3)'), 
        (tp2, '#089981', 'Take Profit 2 (TP 2)'), 
        (tp1, '#089981', 'Take Profit 1 (TP 1)'), 
        (entry, '#b2b5be', 'Entry Price'), 
        (sl, '#f23645', 'Stop Loss (SL)')
    ]
    
    atr_val = df_plot['ATR'].iloc[-1]
    
    for price, color, label in target_levels:
        ax_main.axhline(y=price, color=color, linestyle='-', linewidth=1.2, alpha=0.9)
        bbox_props = dict(boxstyle="square,pad=0.3", fc=color, ec=color, lw=0)
        dp = 6 if price < 0.01 else 2
        # Price label box on the right
        ax_main.text(x_max, price, f" {price:.{dp}f} ", ha="right", va="center", color="white" if color != '#b2b5be' else "#131722", fontsize=10, fontweight='bold', bbox=bbox_props)
        # Dynamic Text label positioning
        text_y_offset = atr_val * 0.15 if direction == "BUY" else -(atr_val * 0.15)
        va_align = "bottom" if direction == "BUY" else "top"
        if label == 'Entry Price':
            text_y_offset = atr_val * 0.15
            va_align = "bottom"
        ax_main.text(x_max - 5, price + text_y_offset, label, ha="right", va=va_align, color=color, fontsize=10, fontweight='bold')

    # Dynamic Support & Resistance Zones with Order Block (OB) Labels dynamically adjusting per signal
    if direction == "BUY":
        res_y = tp3 + (atr_val * 0.3)
        sup_y = sl - (atr_val * 0.3)
        ax_main.axhline(y=res_y, color='#f23645', linestyle='-', linewidth=1.5, alpha=0.4)
        ax_main.text(x_max - 15, res_y, "Red Resistance OB", ha="right", va="bottom", color="#f23645", fontsize=9, fontweight='bold')
        ax_main.axhline(y=sup_y, color='#089981', linestyle='-', linewidth=1.5, alpha=0.4)
        ax_main.text(x_max - 15, sup_y, "Support Zone / Bullish OB", ha="right", va="top", color="#089981", fontsize=9, fontweight='bold')
    else:
        res_y = sl + (atr_val * 0.3)
        sup_y = tp3 - (atr_val * 0.3)
        ax_main.axhline(y=res_y, color='#f23645', linestyle='-', linewidth=1.5, alpha=0.4)
        ax_main.text(x_max - 15, res_y, "Red Resistance / Bearish OB", ha="right", va="bottom", color="#f23645", fontsize=9, fontweight='bold')
        ax_main.axhline(y=sup_y, color='#089981', linestyle='-', linewidth=1.5, alpha=0.4)
        ax_main.text(x_max - 15, sup_y, "Support Zone", ha="right", va="top", color="#089981", fontsize=9, fontweight='bold')

    # Watermarks
    coin_clean = coin_name.replace('USDT', ' / TetherUS')
    ax_main.text(0.01, 0.96, f"💎 {coin_clean} • {timeframe} • BINANCE", transform=ax_main.transAxes, fontsize=12, fontweight='bold', color='#d1d4dc')
    ax_main.text(0.01, 0.91, "Multi MA + VPVR + Institutional VWAP", transform=ax_main.transAxes, fontsize=9, color='#787b86')
    ax_main.text(0.01, 0.86, f"AI Confidence: {direction} SETUP 🔥", transform=ax_main.transAxes, fontsize=10, fontweight='bold', color='#089981' if direction=="BUY" else '#f23645')
    ax_main.text(0.01, 0.81, f"🧩 Detected Pattern: {detected_pattern}", transform=ax_main.transAxes, fontsize=10, fontweight='bold', color='#ff9800')

    buf = io.BytesIO()
    fig.savefig(buf, dpi=120, bbox_inches='tight', facecolor='#131722')
    buf.seek(0)
    return buf.read()


HISTORY_FILE = "signal_history.csv"

# Global options for mapping
market_options = {
    "Bitcoin (BTC/USD)": "BTC-USD", "Ethereum (ETH/USD)": "ETH-USD", "Solana (SOL/USD)": "SOL-USD", "Binance Coin (BNB/USD)": "BNB-USD",
    "Ripple (XRP/USD)": "XRP-USD", "Cardano (ADA/USD)": "ADA-USD", "Dogwifhat (WIF/USD)": "WIF-USD", "Shiba Inu (SHIB/USD)": "SHIB-USD",
    "Pepe (PEPE/USD)": "PEPE-USD", "Avalanche (AVAX/USD)": "AVAX-USD", "Chainlink (LINK/USD)": "LINK-USD", "Polkadot (DOT/USD)": "DOT-USD",
    "Fantom (FTM/USD)": "FTM-USD", "Polygon (MATIC/USD)": "MATIC-USD", "Injective (INJ/USD)": "INJ-USD", "Dogecoin (DOGE/USD)": "DOGE-USD",
    "Litecoin (LTC/USD)": "LTC-USD", "Bitcoin Cash (BCH/USD)": "BCH-USD", "Stellar (XLM/USD)": "XLM-USD", "Uniswap (UNI/USD)": "UNI-USD",
    "Cosmos (ATOM/USD)": "ATOM-USD", "Monero (XMR/USD)": "XMR-USD", "Ethereum Classic (ETC/USD)": "ETC-USD", "Filecoin (FIL/USD)": "FIL-USD",
    "Internet Computer (ICP/USD)": "ICP-USD", "VeChain (VET/USD)": "VET-USD", "Hedera (HBAR/USD)": "HBAR-USD", "Aptos (APT/USD)": "APT-USD",
    "Arbitrum (ARB/USD)": "ARB-USD", "Near Protocol (NEAR/USD)": "NEAR-USD", "Optimism (OP/USD)": "OP-USD", "Stacks (STX/USD)": "STX-USD",
    "Render (RNDR/USD)": "RNDR-USD", "Immutable (IMX/USD)": "IMX-USD", "The Graph (GRT/USD)": "GRT-USD", "Theta Network (THETA/USD)": "THETA-USD",
    "Aave (AAVE/USD)": "AAVE-USD", "Synthetix (SNX/USD)": "SNX-USD", "Maker (MKR/USD)": "MKR-USD", "Algorand (ALGO/USD)": "ALGO-USD",
    "Flow (FLOW/USD)": "FLOW-USD", "MultiversX (EGLD/USD)": "EGLD-USD", "Mina (MINA/USD)": "MINA-USD", "THORChain (RUNE/USD)": "RUNE-USD",
    "Lido DAO (LDO/USD)": "LDO-USD", "Quant (QNT/USD)": "QNT-USD", "Gala (GALA/USD)": "GALA-USD", "The Sandbox (SAND/USD)": "SAND-USD",
    "Decentraland (MANA/USD)": "MANA-USD", "Axie Infinity (AXS/USD)": "AXS-USD", "Chiliz (CHZ/USD)": "CHZ-USD", "Enjin Coin (ENJ/USD)": "ENJ-USD",
    "Curve DAO (CRV/USD)": "CRV-USD", "Zilliqa (ZIL/USD)": "ZIL-USD", "NEO (NEO/USD)": "NEO-USD", "Dash (DASH/USD)": "DASH-USD",
    "Kava (KAVA/USD)": "KAVA-USD", "Compound (COMP/USD)": "COMP-USD", "IOTA (MIOTA/USD)": "MIOTA-USD", "Tezos (XTZ/USD)": "XTZ-USD",
    "Zcash (ZEC/USD)": "ZEC-USD", "Kusama (KSM/USD)": "KSM-USD", "Basic Attention Token (BAT/USD)": "BAT-USD", "Harmony (ONE/USD)": "ONE-USD",
    "Celo (CELO/USD)": "CELO-USD", "Qtum (QTUM/USD)": "QTUM-USD", "Ravencoin (RVN/USD)": "RVN-USD", "Ontology (ONT/USD)": "ONT-USD",
    "ICON (ICX/USD)": "ICX-USD", "DigiByte (DGB/USD)": "DGB-USD", "Horizen (ZEN/USD)": "ZEN-USD", "Nano (XNO/USD)": "XNO-USD",
    "Syscoin (SYS/USD)": "SYS-USD", "Sui (SUI/USD)": "SUI-USD", "Sei (SEI/USD)": "SEI-USD", "Worldcoin (WLD/USD)": "WLD-USD",
    "CyberConnect (CYBER/USD)": "CYBER-USD", "Pendle (PENDLE/USD)": "PENDLE-USD", "Radix (XRD/USD)": "XRD-USD", "Kaspa (KAS/USD)": "KAS-USD",
    "GMX (GMX/USD)": "GMX-USD", "Magic (MAGIC/USD)": "MAGIC-USD", "Illuvium (ILV/USD)": "ILV-USD", "Biconomy (BICO/USD)": "BICO-USD",
    "Gnosis (GNO/USD)": "GNO-USD", "Status (SNT/USD)": "SNT-USD", "Aragon (ANT/USD)": "ANT-USD", "Kyber Network (KNC/USD)": "KNC-USD",
    "Bancor (BNT/USD)": "BNT-USD", "Loopring (LRC/USD)": "LRC-USD", "Storj (STORJ/USD)": "STORJ-USD", "Civic (CVC/USD)": "CVC-USD",
    "Fetch.ai (FET/USD)": "FET-USD", "Band Protocol (BAND/USD)": "BAND-USD", "Numeraire (NMR/USD)": "NMR-USD", "iExec RLC (RLC/USD)": "RLC-USD",
    "Theta Fuel (TFUEL/USD)": "TFUEL-USD", "WazirX (WRX/USD)": "WRX-USD", "Swipe (SXP/USD)": "SXP-USD", "Klever (KLV/USD)": "KLV-USD",
    "Utrust (UTK/USD)": "UTK-USD", "Firo (FIRO/USD)": "FIRO-USD", "Dusk Network (DUSK/USD)": "DUSK-USD", "DIA (DIA/USD)": "DIA-USD",
    "Litentry (LIT/USD)": "LIT-USD", "Phala Network (PHA/USD)": "PHA-USD", "Marlin (POND/USD)": "POND-USD", "Radiant Capital (RDNT/USD)": "RDNT-USD",
    "Gains Network (GNS/USD)": "GNS-USD", "PancakeSwap (CAKE/USD)": "CAKE-USD", "Trust Wallet (TWT/USD)": "TWT-USD", "1inch (1INCH/USD)": "1INCH-USD", 
    "Ocean Protocol (OCEAN/USD)": "OCEAN-USD", "SKALE (SKL/USD)": "SKL-USD", "Cartesi (CTSI/USD)": "CTSI-USD", 
    "Coti (COTI/USD)": "COTI-USD", "NKN (NKN/USD)": "NKN-USD"
}

tf_mapping = {
    "5 min": {"yf": "5m", "tv": "5", "period": "60d"}, 
    "15 min": {"yf": "15m", "tv": "15", "period": "60d"},
    "30 min": {"yf": "30m", "tv": "30", "period": "60d"}, 
    "1 hour": {"yf": "1h", "tv": "60", "period": "730d"},
    "4 hour": {"yf": "4h", "tv": "240", "period": "730d"}, 
    "1 day": {"yf": "1d", "tv": "D", "period": "max"}
}

@st.cache_data
def get_market_data(symbol, tf, prd):
    df = yf.download(symbol, period=prd, interval=tf, auto_adjust=True)
    return df

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Live AI Signals", "📂 Auto Signal History", "💼 VIP Demo Trading", "🔍 Market Scanner"])

with tab1:
    st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න:")
    category = st.radio("ප්‍රවර්ගය තෝරන්න:", ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ", "💱 ෆොරෙක්ස්", "✨ ලෝහ සහ තෙල්", "✏️ වෙනත් (Custom)"], horizontal=True)

    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ":
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('-USD', 'USDT')
        full_tv_ticker = f"BINANCE:{clean_symbol}"

    elif category == "💱 ෆොරෙක්ස්":
        fx_options = {"Euro / US Dollar (EUR/USD)": "EURUSD=X", "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X", "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X", "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X"}
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(fx_options.keys()))
        ticker = fx_options[selected_display_name]
        clean_symbol = ticker.replace('=X', '')
        full_tv_ticker = f"FX_IDC:{clean_symbol}"

    elif category == "✨ ලෝහ සහ තෙල්":
        com_options = {"රන් / Gold (XAU/USD)": "GC=F", "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"}
        selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(com_options.keys()))
        ticker = com_options[selected_display_name]
        clean_symbol = ticker.replace('=F', '')
        full_tv_ticker = f"COMEX:{clean_symbol}" if "GC" in ticker else f"NYMEX:{clean_symbol}"

    else:
        st.info("💡 **ඔබට අවශ්‍ය ඕනෑම කාසියක් මෙහි ඇතුළත් කළ හැක.**")
        col_c1, col_c2 = st.columns(2)
        with col_c1: ticker = st.text_input("Yahoo Finance Ticker:", "DOGE-USD")
        with col_c2: full_tv_ticker = st.text_input("TradingView Symbol:", "BINANCE:DOGEUSDT")
        selected_display_name = f"Custom Symbol ({ticker})"

    tf_display = st.selectbox("Timeframe එක තෝරන්න:", list(tf_mapping.keys()))
    selected_tf = tf_mapping[tf_display]

    df = get_market_data(ticker, selected_tf["yf"], selected_tf["period"])

    if not df.empty and len(df) > 125: 
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
        df['Returns'] = df['Close'].pct_change()
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
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
        
        df['FVG_Bull'] = np.where(df['Low'] > df['High'].shift(2), 1, 0)
        df['FVG_Bear'] = np.where(df['High'] < df['Low'].shift(2), 1, 0)
        
        df['Target'] = np.where(df['Close'].shift(-2) > df['Close'], 1, 0)
        
        # --- VIP Additions (VWAP, OBV, Supertrend) ---
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (df['Typical_Price'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        df['VWAP_Dist'] = df['Close'] / df['VWAP']
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_ROC'] = df['OBV'].pct_change()
        df = add_supertrend(df)
        
        detected_pattern = detect_candlestick_pattern(df)
        
        # Updated Features including Pro Institutional Indicators
        features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns', 'ATR', 'FVG_Bull', 'FVG_Bear', 'MACD', 'Signal_Line', 'VWAP_Dist', 'ST_DIR']
        last_market_state = df[features].iloc[[-1]].copy()
        
        df_train = df.dropna() 
        
        if len(df_train) < 20:
            st.warning("⚠️ AI Model එකට ඉගෙනගැනීමට තරම් ප්‍රමාණවත් දත්ත (Data) Yahoo Finance හරහා ලැබී නොමැත. කරුණාකර වෙනත් Timeframe එකක් හෝ Coin එකක් තෝරන්න.")
        else:
            try:
                X = df_train[features]
                y = df_train['Target']
                
                split = int(0.85 * len(df_train))
                X_train, y_train = X[:split], y[:split]
                
                model = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=3, random_state=42)
                model.fit(X_train, y_train)
                
                prediction = model.predict(last_market_state)[0]
                probability = model.predict_proba(last_market_state)[0]
                
                try:
                    tkr_live = yf.Ticker(ticker)
                    current_price = float(tkr_live.fast_info['lastPrice'])
                except Exception:
                    current_price = float(df['Close'].iloc[-1])
                    
                atr_val = float(df['ATR'].iloc[-1])
                ai_confidence = max(probability) * 100
                dp = 8 if current_price < 0.01 else 4
                
                pullback_amount = atr_val * 0.3  
                sl_multiplier = 2.0  
                tp1_multiplier = 1.5
                tp2_multiplier = 3.0
                tp3_multiplier = 5.0
                
                if prediction == 1: 
                    entry_price = current_price - pullback_amount 
                    tp1_price = entry_price + (atr_val * tp1_multiplier)
                    tp2_price = entry_price + (atr_val * tp2_multiplier)
                    tp3_price = entry_price + (atr_val * tp3_multiplier)
                    sl_price = entry_price - (atr_val * sl_multiplier) 
                else: 
                    entry_price = current_price + pullback_amount 
                    tp1_price = entry_price - (atr_val * tp1_multiplier)
                    tp2_price = entry_price - (atr_val * tp2_multiplier)
                    tp3_price = entry_price - (atr_val * tp3_multiplier)
                    sl_price = entry_price + (atr_val * sl_multiplier) 
        
                st.write("---")
                st.subheader(f"📊 {selected_display_name} ({tf_display}) PRO AI විශ්ලේෂණය:")
                
                # --- Fear & Greed Index Fetching ---
                fng_value, fng_class = get_fear_and_greed()
                if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ":
                    st.info(f"🧭 **Crypto Market Sentiment (Fear & Greed):** {fng_class} ({fng_value}/100)")
                
                has_valid_signal = False
                
                # 🟢 Smarter Trend & Confluence Filter (WITH REVERSAL LOGIC & F&G Protection) 🟢
                last_ema9 = float(last_market_state['EMA_9'].iloc[0])
                last_ema21 = float(last_market_state['EMA_21'].iloc[0])
                last_macd = float(last_market_state['MACD'].iloc[0])
                last_rsi = float(last_market_state['RSI'].iloc[0])
                
                confluence_pass = True
                confluence_msg = ""
                is_reversal = False
                
                if prediction == 1: # AI කියන්නේ BUY කියලා
                    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ" and fng_value >= 75:
                        confluence_pass = False
                        confluence_msg = f"🚨 **Fear & Greed Warning:** මාකට් එක දැනට තියෙන්නේ '{fng_class}' (Overbought) මට්ටමේ. මෙවැනි අවස්ථාවක Market එක කඩා වැටෙන්නට (Crash) ඉඩ ඇති බැවින් AI මෙම BUY සිග්නලය ප්‍රතික්ෂේප කරයි."
                    elif (last_ema9 < last_ema21) and (last_macd < 0):
                        if last_rsi < 40 and ("Hammer" in detected_pattern or "Bullish" in detected_pattern):
                            is_reversal = True
                        else:
                            confluence_pass = False
                            confluence_msg = "🚨 **Trend Filter Warning:** මාකට් එකේ දැනට තියෙන්නේ ප්‍රබල Downtrend එකක්. පැහැදිලි Reversal Pattern එකක් නොමැතිව 'Falling Knife' එකක් ඇල්ලීම ඉතා අවදානම් වැඩක් බැවින් AI මෙම සිග්නලය ප්‍රතික්ෂේප කරයි."
                else: # AI කියන්නේ SELL කියලා
                    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ" and fng_value <= 25:
                        confluence_pass = False
                        confluence_msg = f"🚨 **Fear & Greed Warning:** මාකට් එක දැනට තියෙන්නේ '{fng_class}' (Oversold) මට්ටමේ. මෙතැනින් Reversal එකක් වීමට ඉඩ ඇති බැවින් AI මෙම SELL සිග්නලය ප්‍රතික්ෂේප කරයි."
                    elif (last_ema9 > last_ema21) and (last_macd > 0):
                        if last_rsi > 60 and ("Shooting Star" in detected_pattern or "Bearish" in detected_pattern):
                            is_reversal = True
                        else:
                            confluence_pass = False
                            confluence_msg = "🚨 **Trend Filter Warning:** මාකට් එකේ දැනට තියෙන්නේ ප්‍රබල Uptrend එකක්. පැහැදිලි Reversal Pattern එකක් නොමැතිව SELL සිග්නල් එකක් ගැනීම ඉතා අවදානම් බැවින් AI මෙම සිග්නලය ප්‍රතික්ෂේප කරයි."

                if ai_confidence < 65.0:
                    st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI විශ්වාසය මදියි ({ai_confidence:.1f}%). අවම වශයෙන් 65% ක විශ්වාසයක් (Confidence) අවශ්‍යයි.")
                elif not confluence_pass:
                    st.error(confluence_msg)
                else:
                    has_valid_signal = True
                    if is_reversal:
                        st.info("🔥 **SMART REVERSAL DETECTED!** AI එක Trend Reversal එකක් (හැරවුම් ලක්ෂ්‍යයක්) හඳුනාගත්තා!")
                        
                    if prediction == 1:
                        st.success(f"🟢 **DIRECTION: BUY / LONG** 📈 ⬆️ (Confidence: {ai_confidence:.1f}%)")
                    else:
                        st.error(f"🔴 **DIRECTION: SELL / SHORT** 📉 ⬇️ (Confidence: {ai_confidence:.1f}%)")
        
                chart_studies = '["MASimple@tv-basicstudies", "BBands@tv-basicstudies", "MACD@tv-basicstudies"]'
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
                    "toolbar_bg": "#131722",
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
                    if prediction == 1:
                        dir_text = "🟢 BUY / LONG 📈 ⬆️" 
                        if is_reversal: dir_text += " (🔥 Reversal Setup)"
                        direction_text = "BUY"
                    else:
                        dir_text = "🔴 SELL / SHORT 📉 ⬇️"
                        if is_reversal: dir_text += " (🔥 Reversal Setup)"
                        direction_text = "SELL"
                    
                    target_msg = (
                        f"📊 **ඇඳිය යුතු නිවැරදි මිල මට්ටම් (ATR & SMC Visual Targets):**\n\n"
                        f"🪙 **Coin:** {selected_display_name}\n\n"
                        f"🔥 **Signal Direction:** {dir_text}\n\n"
                        f"🧩 **Detected Pattern:** {detected_pattern}\n\n"
                        f"🔵 **Entry Limit Price:** ${entry_price:.{dp}f}\n\n"
                        f"🎯 **TP 1:** ${tp1_price:.{dp}f}\n\n"
                        f"🎯 **TP 2:** ${tp2_price:.{dp}f}\n\n"
                        f"🎯 **TP 3:** ${tp3_price:.{dp}f}\n\n"
                        f"🛑 **Stop Loss (SL):** ${sl_price:.{dp}f}"
                    )
                    st.info(target_msg)
                    
                    st.write("### 📸 Signal Visualizer Preview (Telegram වෙත යැවෙන ප්‍රස්ථාරය)")
                    
                    try:
                        chart_image_bytes = generate_candlestick_image_bytes(df, clean_symbol, direction_text, entry_price, tp1_price, tp2_price, tp3_price, sl_price, tf_display, detected_pattern)
                        st.image(chart_image_bytes, caption=f"Dynamically Generated Setup for {selected_display_name} (VPVR + VWAP + OB + {detected_pattern})")
                        image_generated_successfully = True
                    except Exception as img_err:
                        st.error(f"⚠️ ප්‍රස්ථාරය සැකසීමේදී දෝෂයක්. ({img_err})")
                        image_generated_successfully = False

                    st.write("### 📲 Telegram Group සහ Channel එකට Signal එක යවන්න")
                    if st.button("Send Signal & Auto Trade on Demo 🚀"):
                        
                        try:
                            check_live = float(yf.Ticker(ticker).fast_info['lastPrice'])
                        except:
                            check_live = current_price
                            
                        is_safe_to_send = True
                        if prediction == 1: 
                            if check_live >= tp1_price or check_live <= sl_price: is_safe_to_send = False
                        else:
                            if check_live <= tp1_price or check_live >= sl_price: is_safe_to_send = False
                                
                        if not is_safe_to_send:
                            st.error("⚠️ **මෙම Signal එක දැන් පරණ වැඩියි! (Expired)** ⚠️\n\nඔබ මෙය යැවීමට ප්‍රමාද වූ බැවින් මාකට් එක දැනටමත් වෙනස් වී ඇත. කරුණාකර අලුත් Signal එකක් ලබාගන්න.")
                        else:
                            telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n🪙 *Coin/Pair:* {selected_display_name}\n⏱ *Timeframe:* {tf_display}\n🔥 *Direction:* {dir_text}\n🧩 *Detected Pattern:* {detected_pattern}\n\n🔵 *Entry Price:* `${entry_price:.{dp}f}`\n🎯 *TP 1:* `${tp1_price:.{dp}f}`\n🎯 *TP 2:* `${tp2_price:.{dp}f}`\n🎯 *TP 3:* `${tp3_price:.{dp}f}`\n🛑 *Stop Loss (SL):* `${sl_price:.{dp}f}`\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            
                            with st.spinner("Chart එක සකසමින් සහ Telegram වෙත යවමින් පවතී... ⏳"):
                                success = False
                                if image_generated_successfully:
                                    success = send_telegram_photo_bytes(telegram_text, chart_image_bytes)
                                
                                if not success:
                                    success = send_telegram_message(telegram_text)
                                    st.warning("⚠️ Chart Photo එක යැවීමේදී දෝෂයක්. (Text Signal එක පමණක් යැවිණි).")
                                
                            if success:
                                st.success("✅ Signal එක සහ Chart එක සාර්ථකව Group සහ Channel දෙකටම යැව්වා! (History එකටත් Save වුණා)")
                                date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                                data = {"Date": [date_str], "Ticker": [ticker], "Coin": [selected_display_name.split()[0]], "Direction": ["BUY" if prediction == 1 else "SELL"], "Entry": [entry_price], "TP1": [tp1_price], "TP2": [tp2_price], "TP3": [tp3_price], "SL": [sl_price], "Status": ["⏳ Pending Entry"]}
                                df_new = pd.DataFrame(data)
                                if os.path.exists(HISTORY_FILE): df_new.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
                                else: df_new.to_csv(HISTORY_FILE, index=False)
                            else:
                                st.error("❌ Signal එක යැවීම අසාර්ථකයි. Settings > Secrets නිවැරදිදැයි බලන්න.")
            except Exception as e:
                st.error(f"⚠️ දත්ත විශ්ලේෂණයේදී ගැටලුවක් මතු විය. වෙනත් Timeframe එකක් තෝරන්න. Error: {e}")
    else:
        st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් දත්ත නොමැත. කරුණාකර වෙනත් Timeframe එකක් තෝරන්න.")

# --- Processing Display Data outside tabs so both Tab2 and Tab3 can use it ---
display_df = pd.DataFrame()
if os.path.exists(HISTORY_FILE):
    try:
        history_df = pd.read_csv(HISTORY_FILE)
        if "TP1" not in history_df.columns:
            os.remove(HISTORY_FILE)
            st.warning("🔄 පද්ධතිය යාවත්කාලීන විය. කරුණාකර අලුතින් Signal එකක් ලබා දෙන්න.")
            st.stop()
        
        updated = False
        live_prices_dict = {}
        
        with st.spinner('සජීවීව මාකට් එක පරීක්ෂා කරමින් පවතී... 🔍'):
            for index, row in history_df.iterrows():
                if "Cancelled" in str(row['Status']):
                    live_prices_dict[index] = np.nan
                    continue
                try:
                    current_live_price, current_low, current_high = None, None, None
                    df_hist = yf.download(row['Ticker'], period="5d", interval="5m", progress=False)
                    if not df_hist.empty:
                        if isinstance(df_hist.columns, pd.MultiIndex): df_hist.columns = df_hist.columns.get_level_values(0)
                        current_live_price = float(df_hist['Close'].dropna().iloc[-1])
                        current_low = float(df_hist['Low'].dropna().iloc[-1])
                        current_high = float(df_hist['High'].dropna().iloc[-1])
                    else:
                        tkr = yf.Ticker(row['Ticker'])
                        current_live_price = float(tkr.fast_info['lastPrice'])
                        current_low = current_high = current_live_price
                        
                    if current_live_price is not None:
                        live_prices_dict[index] = current_live_price
                        entry_val, tp1_val, tp2_val, tp3_val, sl_val = float(row['Entry']), float(row['TP1']), float(row['TP2']), float(row['TP3']), float(row['SL'])
                        new_status = str(row['Status'])
                        
                        if "Pending" in new_status:
                            if row['Direction'] == 'BUY':
                                if current_high >= tp1_val: new_status = "⚠️ Missed (Hit TP)"
                                elif current_low <= sl_val: new_status = "🚫 Invalid (Hit SL)"
                                elif current_low <= entry_val: new_status = "🟢 Active"
                            else: 
                                if current_low <= tp1_val: new_status = "⚠️ Missed (Hit TP)"
                                elif current_high >= sl_val: new_status = "🚫 Invalid (Hit SL)"
                                elif current_high >= entry_val: new_status = "🟢 Active"
                                    
                        if new_status in ["🟢 Active", "✅ TP1 HIT", "✅ TP2 HIT"]:
                            if row['Direction'] == 'BUY':
                                if current_high >= tp3_val: new_status = "✅ TP3 HIT"
                                elif current_high >= tp2_val and new_status not in ["✅ TP3 HIT"]: new_status = "✅ TP2 HIT"
                                elif current_high >= tp1_val and new_status not in ["✅ TP2 HIT", "✅ TP3 HIT"]: new_status = "✅ TP1 HIT"
                                elif new_status == "🟢 Active" and current_low <= sl_val: new_status = "🛑 SL HIT"
                            else: 
                                if current_low <= tp3_val: new_status = "✅ TP3 HIT"
                                elif current_low <= tp2_val and new_status not in ["✅ TP3 HIT"]: new_status = "✅ TP2 HIT"
                                elif current_low <= tp1_val and new_status not in ["✅ TP2 HIT", "✅ TP3 HIT"]: new_status = "✅ TP1 HIT"
                                elif new_status == "🟢 Active" and current_high >= sl_val: new_status = "🛑 SL HIT"
                                    
                        if new_status != str(row['Status']):
                            history_df.at[index, 'Status'] = new_status
                            updated = True
                    else: live_prices_dict[index] = np.nan
                except Exception: live_prices_dict[index] = np.nan
        
        if updated: history_df.to_csv(HISTORY_FILE, index=False)
            
        display_df = history_df.copy()
        display_df['Live Price'] = display_df.index.map(live_prices_dict)
        def format_price(x):
            if pd.isnull(x): return "N/A"
            val = float(x)
            return f"${val:.8f}" if val < 0.01 else f"${val:.4f}"

        for col in ['Entry', 'TP1', 'TP2', 'TP3', 'SL', 'Live Price']: 
            display_df[col] = display_df[col].apply(format_price)
        display_df.drop(columns=['Ticker'], inplace=True)
        display_df = display_df.iloc[::-1]

    except Exception:
        pass


with tab2:
    st.subheader("📂 ගත්තු Signals වල History එක සහ Live Price")
    st.write("මාකට් එකේ සජීවී මිල මෙහි යාවත්කාලීන වේ. TP 1, 2, හෝ 3 Hit වූ විට Status එක Auto වෙනස් වෙනවා!")
    auto_refresh = st.checkbox("🔄 Auto Refresh (සෑම තත්පර 15කට වරක් සජීවී මිල සහ Status පමණක් යාවත්කාලීන වීමට මෙහි ටික් එකක් දාන්න)")

    if not display_df.empty:
        html_style = "<style>.trading-history-container{overflow-x:auto;margin:10px 0;border-radius:8px;border:1px solid #31333f;}.trading-table{width:100%;border-collapse:collapse;background-color:#0e1117;color:#ffffff;font-size:13px;text-align:center;}.trading-table th{background-color:#1f2937;color:#ff4b4b;padding:12px 8px;border:1px solid #31333f;font-weight:bold;}.trading-table td{padding:10px 6px;border:1px solid #31333f;white-space:nowrap;}.marquee-container{width:95px;overflow:hidden;margin:0 auto;white-space:nowrap;}.marquee-scroll{display:inline-block;animation:marqueeEffect 6s linear infinite;}@keyframes marqueeEffect{0%{transform:translate(10%, 0);}50%{transform:translate(-100%, 0);}100%{transform:translate(10%, 0);}}</style>"
        html_table = html_style + "<div class='trading-history-container'><table class='trading-table'><tr><th>#</th><th>Date</th><th>Coin</th><th>Direction</th><th>Entry</th><th>TP1</th><th>TP2</th><th>TP3</th><th>SL</th><th>Status</th><th>Live Price</th></tr>"
        for idx, row in display_df.iterrows():
            status_text = str(row['Status'])
            status_td = f"<td><div class='marquee-container'><div class='marquee-scroll'>{status_text}</div></div></td>" if "Pending Entry" in status_text else f"<td>{status_text}</td>"
            html_table += f"<tr><td style='font-weight:bold; color:#888;'>{idx}</td><td>{row['Date']}</td><td>{row['Coin']}</td><td>{row['Direction']}</td><td>{row['Entry']}</td><td>{row['TP1']}</td><td>{row['TP2']}</td><td>{row['TP3']}</td><td>{row['SL']}</td>{status_td}<td style='color:#00ffcc; font-weight:bold;'>{row['Live Price']}</td></tr>"
        html_table += "</table></div>"
        st.markdown(html_table, unsafe_allow_html=True)

        st.write("---")
        st.subheader("📢 Result එක Telegram යවන්න")
        completed_signals = history_df[history_df['Status'].str.contains("Pending|HIT|Active|Missed|Invalid", na=False, case=False)].iloc[::-1]
        
        if not completed_signals.empty:
            options = [f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})" for index, row in completed_signals.iterrows()]
            selected_sig = st.selectbox("Update කරන්න අවශ්‍ය Signal එක තෝරන්න:", options)
            if selected_sig:
                selected_idx = options.index(selected_sig)
                sel_row = completed_signals.iloc[selected_idx]
                actual_index = sel_row.name 
                dir_text_with_icons = "🟢 BUY / LONG 📈 ⬆️" if sel_row['Direction'] == 'BUY' else "🔴 SELL / SHORT 📉 ⬇️"
                
                if "Pending" in sel_row['Status']:
                    entry_val = float(sel_row['Entry'])
                    dp_val = 8 if entry_val < 0.01 else 4
                    col_pend1, col_pend2 = st.columns(2)
                    with col_pend1:
                        if st.button("⏳ Pending Alert මැසේජ් එක යවන්න 🚀"):
                            msg = f"⏳ *TRADE SETUP READY (PENDING)* ⏳\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n🔵 *Entry Point:* `${entry_val:.{dp_val}f}`\n\nමාකට් එක අපේ Entry Point එකට එනකන් අපි බලාගෙන ඉන්නවා. Limit Order එක දාලා තියාගන්න! 🚀\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg): st.success("⏳ Pending Alert මැසේජ් එක සාර්ථකව යැව්වා!")
                    with col_pend2:
                        if st.button("🚫 Signal එක Cancel කරන්න"):
                            msg = f"🚫 *SIGNAL CANCELLED* 🚫\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමේ Setup එක දැන් අවලංගු (Invalid) නිසා අපි මේ සිග්නල් එක Cancel කරනවා. කරුණාකර ඔයාගේ Limit Orders අයින් කරගන්න! ❌\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg):
                                st.success("🚫 Cancel මැසේජ් එක යැව්වා! මේ Signal එක දැන් History එකේ Cancelled කියලා වැටෙයි.")
                                history_df.at[actual_index, 'Status'] = "🚫 Cancelled"
                                history_df.to_csv(HISTORY_FILE, index=False)
                                time.sleep(1)
                                try: st.rerun()
                                except AttributeError: st.experimental_rerun()

                elif "Missed (Hit TP)" in sel_row['Status']:
                    if st.button("⚠️ Missed Setup මැසේජ් එක යවන්න 🚀"):
                        msg = f"⚠️ *MISSED TRADE (HIT TP)* ⚠️\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nඅපේ Analysis එක 100% ක් නිවැරදියි! නමුත් මාකට් එක අපේ Entry එකට එන්නේ නැතුව කෙලින්ම Target (TP) එකට ගියා. Setup එක සම්පූර්ණයි, ඒ නිසා Limit Order එක අයින් කරගන්න. ඊළඟ Trade එකෙන් අල්ලමු! 🔥\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                        if send_telegram_message(msg):
                            st.success("⚠️ Missed Setup මැසේජ් එක සාර්ථකව යැව්වා!")
                            history_df.at[actual_index, 'Status'] = "🚫 Cancelled"
                            history_df.to_csv(HISTORY_FILE, index=False)
                            time.sleep(1)
                            try: st.rerun()
                            except AttributeError: st.experimental_rerun()

                elif "Invalid (Hit SL)" in sel_row['Status']:
                    if st.button("🚫 Invalid Setup මැසේජ් එක යවන්න 🚀"):
                        msg = f"🚫 *SETUP INVALID (HIT SL)* 🚫\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමාකට් එක අපේ Entry Point එකට කලින්ම Stop Loss (SL) මට්ටම කඩාගෙන ගියා. Market Structure එක වෙනස් වුණු නිසා මේ Setup එක දැන් අවලංගුයි. කරුණාකර ඔයාගේ Limit Orders අයින් කරගන්න! ❌\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                        if send_telegram_message(msg):
                            st.success("🚫 Setup Invalid මැසේජ් එක සාර්ථකව යැව්වා!")
                            history_df.at[actual_index, 'Status'] = "🚫 Cancelled"
                            history_df.to_csv(HISTORY_FILE, index=False)
                            time.sleep(1)
                            try: st.rerun()
                            except AttributeError: st.experimental_rerun()
                            
                elif "Active" in sel_row['Status']:
                    entry_val = float(sel_row['Entry'])
                    dp_val = 8 if entry_val < 0.01 else 4
                    if st.button("🟢 Active Alert මැසේජ් එක යවන්න 🚀"):
                        msg = f"🟢 *TRADE IS NOW ACTIVE!* 🚀\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n🔵 *Entry Triggered:* `${entry_val:.{dp_val}f}`\n\nමාකට් එක අපේ Entry ලෙවල් එකට ආවා! අපේ ට්‍රේඩ් එක දැන් පටන් ගත්තා (Running). Let's go! 🔥\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                        if send_telegram_message(msg): st.success("🟢 Active Alert මැසේජ් එක සාර්ථකව යැව්වා!")
                
                elif "TP" in sel_row['Status']:
                    hit_level = sel_row['Status'].split()[1]
                    tp_val, tp_dp = float(sel_row[hit_level]), 8 if float(sel_row[hit_level]) < 0.01 else 4
                    if st.button(f"✅ {hit_level} Profit මැසේජ් එක යවන්න 🚀"):
                        msg = f"✅ *PROFIT TARGET HIT!* 🎉\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n🎯 *{hit_level} Reached:* `${tp_val:.{tp_dp}f}`\n\n🤑 _💯PRO💥VIP⚡SIGNALS🛜 100% සාර්ථකයි!_"
                        if send_telegram_message(msg): st.success(f"✅ {hit_level} Profit මැසේජ් එක සාර්ථකව යැව්වා!")
                
                elif "SL" in sel_row['Status']:
                    if st.button("🛑 Loss මැසේජ් එක යවන්න"):
                        msg = f"🛑 *STOP LOSS HIT* 📉\n\n🪙 *Coin:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමාකට් එක වෙනස් වුණා. Risk Management අනුගමනය জ্ঞකරන්න. ඊළඟ Trade එකෙන් අපි අල්ලමු! 💪\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                        if send_telegram_message(msg): st.success("🛑 Stop Loss මැසේජ් එක සාර්ථකව යැව්වා!")
        else: st.info("තවම Active, Pending, TP, SL හෝ Invalid වුණු සිග්නල් කිසිවක් නැත.")

        st.write("---")
        st.subheader("🗑️ History කළමනාකරණය (Delete Signals)")
        all_delete_options = [f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})" for index, row in history_df.iterrows()][::-1]
        selected_to_delete = st.multiselect("මකා දැමීමට අවශ්‍ය සිග්නල් තෝරන්න:", all_delete_options)
        
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            if st.button("🗑️ තෝරාගත් ඒවා පමණක් මකන්න"):
                if selected_to_delete:
                    indices_to_drop = [index for index, row in history_df.iterrows() if f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})" in selected_to_delete]
                    history_df.drop(indices_to_drop, inplace=True)
                    history_df.to_csv(HISTORY_FILE, index=False)
                    st.success("✅ තෝරාගත් සිග්නල් සාර්ථකව මකා දැමුවා!")
                    time.sleep(1)
                    try: st.rerun()
                    except AttributeError: st.experimental_rerun()
                else: st.warning("⚠️ මකා දැමීමට කිසිවක් තෝරා නැත.")
                    
        with col_del2:
            if st.button("🚨 ඔක්කොම මකන්න (Clear All)"):
                os.remove(HISTORY_FILE)
                st.success("✅ History එක සම්පූර්ණයෙන්ම මකා දැමුවා!")
                time.sleep(1)
                try: st.rerun()
                except AttributeError: st.experimental_rerun()
            
        if auto_refresh:
            time.sleep(15)
            try: st.rerun()
            except AttributeError: st.experimental_rerun()
    else: st.info("දැනට කිසිම Signal එකක් Save වෙලා නෑ. අලුත් Signal එකක් Telegram එකට යැව්වම මෙතනට වැටෙයි.")

# --- Tab 3: Auto Demo Trading Account ---
with tab3:
    st.subheader("💼 VIP Auto Demo Trading Account (Simulated)")
    st.write("ඔබ ලබාගන්නා සියලුම AI Signals ස්වයංක්‍රීයව මෙම $10,000 ක අතත්‍ය (Demo) ගිණුමේ Trade වේ. සැබෑ Market Data අනුව මෙහි ලාභ/අලාභ (P&L) ගණනය වේ.")

    if not display_df.empty:
        INITIAL_BALANCE = 10000.0
        RISK_AMOUNT = 100.0 # $100 risk per trade (1% of 10k)
        
        realized_pnl = 0.0
        floating_pnl = 0.0
        active_trades_list = []
        closed_trades_list = []
        
        for idx, row in display_df.iterrows():
            status = str(row['Status'])
            
            # Skip trades that haven't triggered or were cancelled
            if "Pending" in status or "Cancelled" in status or "Invalid" in status or "Missed" in status:
                continue
                
            try:
                entry = float(row['Entry'].replace('$', '').replace(',', ''))
                sl = float(row['SL'].replace('$', '').replace(',', ''))
                tp3 = float(row['TP3'].replace('$', '').replace(',', ''))
                
                live_price_str = str(row['Live Price']).replace('$', '').replace(',', '').replace('N/A', '0')
                live_price = float(live_price_str) if live_price_str != '0' else entry
                
                direction = row['Direction']
                sl_dist = abs(entry - sl)
                units = RISK_AMOUNT / sl_dist if sl_dist > 0 else 0
                
                # --- PNL Calculations ---
                if "SL HIT" in status:
                    pnl = -RISK_AMOUNT
                    realized_pnl += pnl
                    trade_info = {"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Status": "🛑 SL Hit", "P&L": f"-${abs(pnl):.2f}"}
                    closed_trades_list.append(trade_info)
                    
                elif "TP3 HIT" in status:
                    pnl = units * abs(tp3 - entry)
                    realized_pnl += pnl
                    trade_info = {"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Status": "✅ TP3 Hit (Closed)", "P&L": f"+${pnl:.2f}"}
                    closed_trades_list.append(trade_info)
                    
                else:
                    # Active or partially hit TP1/TP2 -> Floating
                    if direction == 'BUY':
                        cur_pnl = units * (live_price - entry)
                    else:
                        cur_pnl = units * (entry - live_price)
                        
                    floating_pnl += cur_pnl
                    pnl_str = f"+${cur_pnl:.2f}" if cur_pnl >= 0 else f"-${abs(cur_pnl):.2f}"
                    trade_info = {"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Entry": f"${entry:.4f}", "Live Price": f"${live_price:.4f}", "Status": status, "Floating P&L": pnl_str}
                    active_trades_list.append(trade_info)
                    
            except Exception as e:
                continue

        current_balance = INITIAL_BALANCE + realized_pnl
        equity = current_balance + floating_pnl
        
        st.write("### 🏦 ගිණුමේ සාරාංශය (Account Summary)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("💰 Balance", f"${current_balance:,.2f}")
        col_m2.metric("📊 Equity", f"${equity:,.2f}", f"{floating_pnl:,.2f} Floating")
        col_m3.metric("🟢 Active Trades", len(active_trades_list))
        col_m4.metric("📁 Closed Trades", len(closed_trades_list))
        
        st.write("---")
        st.write("### 🟢 Active Positions (ක්‍රියාත්මක වන Trades)")
        if active_trades_list:
            st.dataframe(pd.DataFrame(active_trades_list), use_container_width=True)
        else:
            st.info("දැනට Active Trades කිසිවක් නොමැත.")
            
        st.write("---")
        st.write("### 📁 Trade History (අවසන් කළ Trades)")
        if closed_trades_list:
            st.dataframe(pd.DataFrame(closed_trades_list), use_container_width=True)
        else:
            st.info("තවම Trade කිසිවක් Close වී නොමැත.")
    else:
        st.info("ඔබ තවමත් Signals කිසිවක් ලබාගෙන නැත. පළමු ටැබ් එකෙන් Signals ලබාගත් පසු ඒවා ස්වයංක්‍රීයව මෙහි Trade වේ.")

# --- Tab 4: Auto Market Scanner ---
with tab4:
    st.subheader("🔍 VIP Market Scanner (Auto Signal Finder)")
    st.write("එකින් එක කාසි පරීක්ෂා කිරීම වෙනුවට, එකවර කාසි රාශියක් ස්කෑන් කර මේ මොහොතේ Valid Signals ඇති කාසි පමණක් පහසුවෙන් සොයාගන්න.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        scan_tf_display = st.selectbox("ස්කෑන් කළ යුතු Timeframe එක තෝරන්න:", ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"])
        scan_tf = tf_mapping[scan_tf_display]
        
    with col_s2:
        st.write("")
        st.write("")
        start_scan = st.button("🚀 Market එක ස්කෑන් කිරීම ආරම්භ කරන්න", use_container_width=True)
        
    if start_scan:
        valid_signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        fng_value, fng_class = get_fear_and_greed()
        
        coins_to_scan = list(market_options.keys())
        total_coins = len(coins_to_scan)
        
        for i, coin_name in enumerate(coins_to_scan):
            ticker_to_scan = market_options[coin_name]
            status_text.text(f"🔍 ස්කෑන් කරමින් පවතී: {coin_name}... ({i+1}/{total_coins})")
            
            try:
                df_scan = yf.download(ticker_to_scan, period=scan_tf["period"], interval=scan_tf["yf"], auto_adjust=True, progress=False)
                
                if not df_scan.empty and len(df_scan) > 125:
                    if isinstance(df_scan.columns, pd.MultiIndex): df_scan.columns = df_scan.columns.get_level_values(0)
                    
                    df_scan['Returns'] = df_scan['Close'].pct_change()
                    df_scan['EMA_9'] = df_scan['Close'].ewm(span=9, adjust=False).mean()
                    df_scan['EMA_21'] = df_scan['Close'].ewm(span=21, adjust=False).mean()
                    df_scan['MACD'] = df_scan['Close'].ewm(span=12, adjust=False).mean() - df_scan['Close'].ewm(span=26, adjust=False).mean()
                    df_scan['Signal_Line'] = df_scan['MACD'].ewm(span=9, adjust=False).mean()
                    
                    delta = df_scan['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    df_scan['RSI'] = 100 - (100 / (1 + rs))
                    
                    df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                    df_scan['StdDev'] = df_scan['Close'].rolling(window=20).std()
                    df_scan['BB_Upper'] = df_scan['MA20'] + (df_scan['StdDev'] * 2)
                    df_scan['BB_Lower'] = df_scan['MA20'] - (df_scan['StdDev'] * 2)
                    
                    df_scan['High-Low'] = df_scan['High'] - df_scan['Low']
                    df_scan['High-PrevClose'] = np.abs(df_scan['High'] - df_scan['Close'].shift(1))
                    df_scan['Low-PrevClose'] = np.abs(df_scan['Low'] - df_scan['Close'].shift(1))
                    df_scan['TR'] = df_scan[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
                    df_scan['ATR'] = df_scan['TR'].rolling(window=14).mean()
                    
                    df_scan['FVG_Bull'] = np.where(df_scan['Low'] > df_scan['High'].shift(2), 1, 0)
                    df_scan['FVG_Bear'] = np.where(df_scan['High'] < df_scan['Low'].shift(2), 1, 0)
                    df_scan['Target'] = np.where(df_scan['Close'].shift(-2) > df_scan['Close'], 1, 0)
                    
                    df_scan['Typical_Price'] = (df_scan['High'] + df_scan['Low'] + df_scan['Close']) / 3
                    df_scan['VWAP'] = (df_scan['Typical_Price'] * df_scan['Volume']).cumsum() / df_scan['Volume'].cumsum()
                    df_scan['VWAP_Dist'] = df_scan['Close'] / df_scan['VWAP']
                    df_scan['OBV'] = (np.sign(df_scan['Close'].diff()) * df_scan['Volume']).fillna(0).cumsum()
                    df_scan['OBV_ROC'] = df_scan['OBV'].pct_change()
                    df_scan = add_supertrend(df_scan)
                    
                    scan_pattern = detect_candlestick_pattern(df_scan)
                    features_scan = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'Returns', 'ATR', 'FVG_Bull', 'FVG_Bear', 'MACD', 'Signal_Line', 'VWAP_Dist', 'ST_DIR']
                    
                    df_train_scan = df_scan.dropna()
                    
                    if len(df_train_scan) >= 20:
                        last_market_state_scan = df_scan[features_scan].iloc[[-1]].copy()
                        X_s = df_train_scan[features_scan]
                        y_s = df_train_scan['Target']
                        
                        split_s = int(0.85 * len(df_train_scan))
                        X_train_s, y_train_s = X_s[:split_s], y_s[:split_s]
                        
                        # Use a slightly lighter model for fast scanning
                        model_s = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=3, random_state=42)
                        model_s.fit(X_train_s, y_train_s)
                        
                        prediction_s = model_s.predict(last_market_state_scan)[0]
                        probability_s = model_s.predict_proba(last_market_state_scan)[0]
                        ai_confidence_s = max(probability_s) * 100
                        
                        # Confluence Logic
                        last_ema9_s = float(last_market_state_scan['EMA_9'].iloc[0])
                        last_ema21_s = float(last_market_state_scan['EMA_21'].iloc[0])
                        last_macd_s = float(last_market_state_scan['MACD'].iloc[0])
                        last_rsi_s = float(last_market_state_scan['RSI'].iloc[0])
                        
                        confluence_pass_s = True
                        if prediction_s == 1:
                            if fng_value >= 75: 
                                confluence_pass_s = False
                            elif (last_ema9_s < last_ema21_s) and (last_macd_s < 0):
                                if not (last_rsi_s < 40 and ("Hammer" in scan_pattern or "Bullish" in scan_pattern)):
                                    confluence_pass_s = False
                        else:
                            if fng_value <= 25: 
                                confluence_pass_s = False
                            elif (last_ema9_s > last_ema21_s) and (last_macd_s > 0):
                                if not (last_rsi_s > 60 and ("Shooting Star" in scan_pattern or "Bearish" in scan_pattern)):
                                    confluence_pass_s = False
                                    
                        if ai_confidence_s >= 65.0 and confluence_pass_s:
                            dir_str = "🟢 BUY" if prediction_s == 1 else "🔴 SELL"
                            valid_signals.append({
                                "Coin / Pair": coin_name, 
                                "Direction": dir_str, 
                                "AI Confidence": f"{ai_confidence_s:.1f}%", 
                                "Detected Pattern": scan_pattern
                            })
            except Exception:
                pass
                
            progress_bar.progress((i + 1) / total_coins)
            
        status_text.text("✅ ස්කෑන් කිරීම අවසන්!")
        
        if valid_signals:
            st.success(f"🎉 Valid Signals {len(valid_signals)} ක් සොයාගන්නා ලදී!")
            st.dataframe(pd.DataFrame(valid_signals), use_container_width=True)
            st.info("💡 දැන් පළමු ටැබ් එකට (Live AI Signals) ගොස් ඉහත වගුවේ ඇති කාසි සහ Timeframe එක තෝරා Signal එක Telegram යවන්න.")
        else:
            st.warning(f"⚠️ මේ මොහොතේ {scan_tf_display} Timeframe එක සඳහා කිසිදු කාසියක පැහැදිලි (Valid) Signal එකක් නොමැත. ටික වෙලාවකින් නැවත උත්සාහ කරන්න.")
