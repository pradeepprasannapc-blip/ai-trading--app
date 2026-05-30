import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import streamlit.components.v1 as components
import requests

# 1. App පෙනුම සහ Title සැකසීම
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="centered")

st.title("⚡ PRO AI Trading Signal App")
st.write("SMC තාක්ෂණය, ලෝකයේ හොඳම Technical Indicators සහ 100% Live TradingView Chart එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

# Secrets හරහා Token ලබා ගැනීම (ආරක්ෂිත ක්‍රමය)
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

# 💡 ජනප්‍රිය වෙළඳපොලවල් සහිත සජීවී ලැයිස්තුව
st.subheader("🌐 වෙළඳපොල සහ කාසිය තෝරන්න (Select Market):")

category = st.radio(
    "ප්‍රවර්ගය තෝරන්න (Select Category):",
    ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ", "💱 ෆොරෙක්ස්", "✨ ලෝහ සහ තෙල්", "✏️ වෙනත් (Custom)"],
    horizontal=True
)

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
    selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
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
    selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
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
    selected_display_name = st.selectbox("කාසිය තෝරන්න:", list(market_options.keys()))
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
        ticker = st.text_input("Yahoo Finance Ticker (උදා: DOGE-USD):", "DOGE-USD")
    with col_c2:
        full_tv_ticker = st.text_input("TradingView Symbol (උදා: BINANCE:DOGEUSDT):", "BINANCE:DOGEUSDT")
    selected
