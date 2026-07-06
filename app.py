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
import base64
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. App පෙනුම සහ Title සැකසීම ---
st.set_page_config(page_title="PRO AI Trading Signal App", page_icon="⚡", layout="wide")

# ==========================================
# 🚀 DYNAMIC APP SETTINGS & SUPABASE INIT
# ==========================================

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_data' not in st.session_state: st.session_state.user_data = None

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("⚠️ Supabase Secrets සකසා නැත!")
    st.stop()

# 🟢 FEATURE: Default Settings (Database එකේ නැත්නම් මේවා පාවිච්චි වේ)
DEFAULT_SETTINGS = {
    "whatsapp": "94757970703",
    "price_7d": "1000",
    "price_1m": "2500",
    "price_2m": "5000",
    "price_3m": "6500",
    "free_trial": "true",
    "trial_days": "3",
    "details_ipay": "<div style='background-color:#1e293b; padding:15px; border-radius:8px; border-left:5px solid #2962ff; margin-bottom:10px;'><b style='color:#00ffcc; font-size:16px;'>📲 iPay Payment Details</b><br><br>• <b>App Name:</b> iPay<br>• <b>Mobile Number:</b> 0757970703<br>• <b>Account Name:</b> Pradeep prasanna</div>",
    "details_flex": "<div style='background-color:#1e293b; padding:15px; border-radius:8px; border-left:5px solid #ff9800; margin-bottom:10px;'><b style='color:#ffeb3b; font-size:16px;'>📲 Flex Payment Details</b><br><br>• <b>Method:</b> Flex BOC<br>• <b>Account Number:</b> 88314511<br>• <b>Account Name:</b> W.K.P.P.SENAVIRATHNA</div>",
    "details_bank": "<div style='background-color:#1e293b; padding:15px; border-radius:8px; border-left:5px solid #089981; margin-bottom:10px;'><b style='color:#0bfd9e; font-size:16px;'>🏦 CDM / Bank Transfer Details</b><br><br>• <b>Bank Name:</b> BOC (ලංකා බැංකුව)<br>• <b>Account Number:</b> 88314511<br>• <b>Account Name:</b> W.K.P.P.SENAVIRATHNA</div>"
}

# 🟢 Database එකෙන් Settings ලබා ගැනීම සහ Default ඒවා සමඟ ගැලපීම
try:
    db_settings_data = supabase.table("app_settings").select("*").execute().data
    db_settings = {s['setting_name']: s['setting_value'] for s in db_settings_data}
except: db_settings = {}

settings = {k: db_settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}

# --- Functions ---
def admin_panel():
    st.title("⚙️ Admin / Moderator Dashboard")
    tab_users, tab_payments, tab_settings = st.tabs(["👥 User Management", "💳 Payment Approvals", "🛠️ Dynamic Settings"])
    current_user_role = st.session_state.user_data['role']
    
    with tab_users:
        st.subheader("Users ලව පාලනය කරන්න (Roles, Passwords & Delete)")
        users = supabase.table("custom_users").select("*").execute().data
        user_emails = [u['email'] for u in users]
        user_roles, user_passwords = {u['email']: u['role'] for u in users}, {u['email']: u['password'] for u in users}
        
        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1: selected_user = st.selectbox("User කෙනෙක් තෝරන්න:", user_emails)
        with col_u2:
            available_roles = ["User", "Moderator", "Admin"] + (["Owner"] if current_user_role == "Owner" else [])
            current_role = user_roles.get(selected_user, "User")
            new_role = st.selectbox("අලුත් Role එක:", available_roles, index=available_roles.index(current_role) if current_role in available_roles else 0)
        with col_u3: new_password = st.text_input("Password වෙනස් කරන්න:", value=user_passwords.get(selected_user, ""))
            
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("🔄 Role එක වෙනස් කරන්න"):
                if user_roles.get(selected_user) == "Owner" and current_user_role != "Owner": st.error("⚠️ Owner ගේ ගිණුම වෙනස් කිරීමට බලයක් නැත!")
                else: supabase.table("custom_users").update({"role": new_role}).eq("email", selected_user).execute(); st.success(f"✅ {selected_user} ගේ Role එක '{new_role}' ලෙස වෙනස් විය!")
        with col_b2:
            if st.button("🔑 Password එක වෙනස් කරන්න"):
                if user_roles.get(selected_user) == "Owner" and current_user_role != "Owner": st.error("⚠️ Owner ගේ ගිණුම වෙනස් කිරීමට බලයක් නැත!")
                else: supabase.table("custom_users").update({"password": new_password}).eq("email", selected_user).execute(); st.success(f"✅ {selected_user} ගේ Password වෙනස් විය!")
        with col_b3:
            if st.button("🗑️ User ව මකා දමන්න (Block)"):
                if user_roles.get(selected_user) == "Owner": st.error("⚠️ Owner ව මකා දැමිය නොහැක!")
                else: supabase.table("custom_users").delete().eq("email", selected_user).execute(); st.warning(f"🚫 {selected_user} ව ඉවත් කළා!")

        st.write("---"); st.write("දැනට ඉන්න Users ලගේ සම්පූර්ණ ලැයිස්තුව:")
        st.dataframe(pd.DataFrame(users)[['email', 'password', 'role', 'phone', 'sub_end']], use_container_width=True)

    with tab_payments:
        st.subheader("Pending Payments (ගෙවීම් අනුමත කිරීම)")
        payments = supabase.table("manual_payments").select("*").eq("status", "Pending").execute().data
        if payments:
            for p in payments:
                with st.expander(f"{p['email']} | {p['method']}"):
                    st.write(f"Ref/Note: {p['reference']}")
                    if p.get('receipt_base64'):
                        try: st.image(base64.b64decode(p['receipt_base64']), caption="Payment Receipt", use_container_width=True)
                        except: st.write("⚠️ රිසිට් පින්තූරය පෙන්වීමේ දෝෂයක්.")
                    
                    # 🟢 FEATURE: Auto calculate days based on pkg
                    days_to_add = 30
                    if "7 Days" in p['method']: days_to_add = 7
                    elif "2 Months" in p['method']: days_to_add = 60
                    elif "3 Months" in p['method']: days_to_add = 90
                        
                    if st.button(f"✅ Approve & Add {days_to_add} Days", key=f"app_{p['id']}"):
                        user = supabase.table("custom_users").select("sub_end").eq("email", p['email']).execute().data[0]
                        current_end = datetime.fromisoformat(user['sub_end']) if user['sub_end'] else datetime.now()
                        new_end = (max(current_end, datetime.now()) + timedelta(days=days_to_add)).isoformat()
                        supabase.table("custom_users").update({"sub_end": new_end}).eq("email", p['email']).execute()
                        supabase.table("manual_payments").update({"status": "Approved"}).eq("id", p['id']).execute()
                        st.success(f"✅ දවස් {days_to_add}ක් එකතු කළා."); st.rerun()
        else: st.info("අලුත් Payments කිසිවක් නැත.")
        
    with tab_settings:
        st.write("### ⚙️ System Configurations (ඇප් එකේ සැකසුම්)")
        st.info("කෝඩ් එක වෙනස් නොකර, මෙතැනින් ඇප් එකේ Packages, Prices සහ Payment විස්තර වෙනස් කරන්න.")
        
        st.write("#### 📞 WhatsApp Number")
        new_wa = st.text_input("WhatsApp අංකය (උදා: 94757970703)", value=settings['whatsapp'])
        
        st.write("---")
        st.write("#### 🎁 Free Trial Settings (නොමිලේ දෙන දින ගණන)")
        col_t1, col_t2 = st.columns(2)
        with col_t1: is_trial_on = st.toggle("Enable Free Trial", value=(settings['free_trial'] == 'true'))
        with col_t2: trial_d_input = st.number_input("දෙන්න ඕනේ දවස් ගාණ:", min_value=1, value=int(settings['trial_days']))
            
        st.write("---")
        st.write("#### 💰 Package Prices (මිල ගණන්)")
        col_p0, col_p1, col_p2, col_p3 = st.columns(4)
        with col_p0: p_7d = st.number_input("7 Days Price", value=int(settings['price_7d']))
        with col_p1: p_1m = st.number_input("1 Month Price", value=int(settings['price_1m']))
        with col_p2: p_2m = st.number_input("2 Months Price", value=int(settings['price_2m']))
        with col_p3: p_3m = st.number_input("3 Months Price", value=int(settings['price_3m']))
            
        st.write("---")
        st.write("#### 💳 Payment Text/Details (බැංකු විස්තර)")
        det_ipay = st.text_area("iPay Details (HTML අනුමතයි):", value=settings['details_ipay'], height=100)
        det_flex = st.text_area("Flex Details (HTML අනුමතයි):", value=settings['details_flex'], height=100)
        det_bank = st.text_area("Bank Details (HTML අනුමතයි):", value=settings['details_bank'], height=100)

        if st.button("💾 Save All Settings", type="primary"):
            updates = {
                "whatsapp": new_wa, "free_trial": 'true' if is_trial_on else 'false', "trial_days": str(trial_d_input),
                "price_7d": str(p_7d), "price_1m": str(p_1m), "price_2m": str(p_2m), "price_3m": str(p_3m),
                "details_ipay": det_ipay, "details_flex": det_flex, "details_bank": det_bank
            }
            with st.spinner("සැකසුම් Save වෙමින් පවතී..."):
                for k, v in updates.items():
                    supabase.table("app_settings").delete().eq("setting_name", k).execute()
                    supabase.table("app_settings").insert({"setting_name": k, "setting_value": v}).execute()
            st.success("✅ සියලුම සැකසුම් සාර්ථකව යාවත්කාලීන විය!"); time.sleep(1); st.rerun()

def messaging_system():
    st.title("💬 Messages & Support")
    user_email, role = st.session_state.user_data['email'], st.session_state.user_data['role']
    if role in ["Admin", "Moderator", "Owner"]:
        send_to = st.selectbox("කාටද යවන්නේ?", ["ALL (හැමෝටම)"] + [u['email'] for u in supabase.table("custom_users").select("email").execute().data])
        msg_text = st.text_area("Message එක Type කරන්න:")
        if st.button("Send Message"):
            supabase.table("in_app_messages").insert({"sender": role, "receiver": send_to if send_to != "ALL (හැමෝටම)" else "ALL", "message": msg_text}).execute()
            st.success("✅ Message එක යැව්වා!")
    st.subheader("Inbox")
    msgs = supabase.table("in_app_messages").select("*").in_("receiver", ["ALL", "Admin", "Moderator", "Owner", user_email] if role in ["Admin", "Moderator", "Owner"] else ["ALL", user_email]).order("timestamp", desc=True).execute().data
    for m in msgs:
        with st.container():
            st.markdown(f"<div style='background-color:{'#1e293b' if m['receiver'] == 'ALL' else '#0f172a'}; padding:10px; border-radius:5px; margin-bottom:5px;'><b>From: {m['sender']}</b><br>{m['message']}</div>", unsafe_allow_html=True)
            if role in ["Admin", "Moderator", "Owner"] and st.button("🗑️ Delete", key=f"del_msg_{m['id']}"): supabase.table("in_app_messages").delete().eq("id", m['id']).execute(); st.rerun()
            st.write("")
    if role == "User":
        support_msg = st.text_area("Admin ට Message එකක් දාන්න:")
        if st.button("Send to Admin"): supabase.table("in_app_messages").insert({"sender": user_email, "receiver": "Admin", "message": support_msg}).execute(); st.success("✅ Admin වෙත යවන ලදී!")

if not st.session_state.logged_in:
    st.title("🔐 VIP Signal App - Login")
    tab_login, tab_reg = st.tabs(["Login", "Register"])
    with tab_login:
        email, password = st.text_input("Email:"), st.text_input("Password:", type="password")
        if st.button("Login"):
            res = supabase.table("custom_users").select("*").eq("email", email).eq("password", password).execute()
            if res.data: st.session_state.logged_in, st.session_state.user_data = True, res.data[0]; st.rerun()
            else: st.error("❌ Email හෝ Password වැරදියි!")
    with tab_reg:
        new_email, new_phone, new_play_id, new_password = st.text_input("New Email:"), st.text_input("Phone Number:"), st.text_input("Play ID / Other ID:"), st.text_input("New Password:", type="password")
        if st.button("Register & Get Access"):
            if not all([new_email, new_phone, new_play_id, new_password]): st.error("⚠️ කරුණාකර සියලුම තොරතුරු සම්පූර්ණ කරන්න!")
            elif "@" not in new_email or "." not in new_email: st.error("⚠️ නිවැරදි Email එකක් දෙන්න.")
            elif supabase.table("custom_users").select("*").eq("email", new_email).execute().data: st.error("⚠️ මේ Email එක දැනටමත් ලියාපදිංචි කර ඇත!")
            else:
                has_trial = settings['free_trial'] == 'true'
                sub_end = (datetime.now() + timedelta(days=int(settings['trial_days']))).isoformat() if has_trial else datetime.now().isoformat()
                supabase.table("custom_users").insert({"email": new_email, "password": new_password, "phone": new_phone, "play_id": new_play_id, "role": "User", "sub_end": sub_end, "trial_used": has_trial}).execute()
                st.success("✅ සාර්ථකව Register විය! කරුණාකර Login වෙන්න.")
    st.stop() 

user_info = st.session_state.user_data
latest_user = supabase.table("custom_users").select("*").eq("email", user_info['email']).execute().data
if latest_user: st.session_state.user_data = latest_user[0]
user_info = st.session_state.user_data
sub_end_date = datetime.fromisoformat(user_info['sub_end']) if user_info['sub_end'] else datetime.min
is_active = sub_end_date > datetime.now() or user_info['role'] == "Owner"

st.sidebar.markdown(f"### 👋 Welcome,\n**{user_info['email'].split('@')[0]}**")
st.sidebar.info(f"🎭 **Role:** {user_info['role']}")
if is_active: st.sidebar.success("👑 VIP Access: Lifetime" if user_info['role'] == "Owner" else f"✅ Active until:\n{sub_end_date.strftime('%Y-%m-%d')}")
else: st.sidebar.error("❌ Subscription Expired!")

menu_options = ["📈 Trading Signals", "💬 Messages"] + (["⚙️ Admin Dashboard"] if user_info['role'] in ["Admin", "Moderator", "Owner"] else [])
selection = st.sidebar.radio("Navigation", menu_options)
st.sidebar.markdown("---"); st.sidebar.markdown("💬 **Help & Support**")
st.sidebar.markdown(f'<a href="https://wa.me/{settings["whatsapp"]}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; width:100%; font-weight:bold; cursor:pointer;">📞 WhatsApp Admin</button></a>', unsafe_allow_html=True)
st.sidebar.markdown("---")
if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

try:
    if supabase:
        all_signals = supabase.table("signal_history").select("*").execute().data
        hit_signals = [s for s in all_signals if "HIT" in str(s.get("Status", "")) and "SL" not in str(s.get("Status", ""))]
        if hit_signals:
            latest_hit = sorted(hit_signals, key=lambda x: x['Date'], reverse=True)[0]
            st.markdown(f"""<div style="background-color:#089981; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px; animation: blinker 1.5s linear infinite; border: 2px solid #0bfd9e;"><b style="color:white; font-size:16px;">🏆 PRO TRADER: {latest_hit.get('created_by', 'Admin').split('@')[0]} | {latest_hit['Coin']} Signal Successfully Achieved {latest_hit['Status'].replace('✅', '')}! 🔥 🎉</b></div><style>@keyframes blinker {{ 50% {{ opacity: 0.6; }} }}</style>""", unsafe_allow_html=True)
except: pass

if selection == "⚙️ Admin Dashboard": admin_panel(); st.stop() 
elif selection == "💬 Messages": messaging_system(); st.stop() 
elif selection == "📈 Trading Signals" and not is_active and user_info['role'] not in ["Admin", "Owner"]:
    st.warning("⚠️ ඔබගේ Subscription කාලය හෝ Free Trial එක අවසන් වී ඇත.")
    st.subheader("💳 App එක Activate කරගන්න")
    
    # 🟢 FEATURE: Dynamic Pricing Array
    pkg_options = [
        f"7 Days (1 Week) - Rs. {settings['price_7d']}",
        f"1 Month (30 Days) - Rs. {settings['price_1m']}", 
        f"2 Months (60 Days) - Rs. {settings['price_2m']}", 
        f"3 Months (90 Days) - Rs. {settings['price_3m']}"
    ]
    selected_pkg = st.radio("ඔබට අවශ්‍ය පැකේජය තෝරන්න:", pkg_options)
    
    st.write("---")
    pay_method = st.selectbox("මුදල් ගෙවන ක්‍රමය තෝරන්න:", ["iPay", "Flex", "Bank Transfer", "CDM", "Other"])
    st.markdown(settings['details_ipay'] if pay_method == "iPay" else settings['details_flex'] if pay_method == "Flex" else settings['details_bank'] if pay_method in ["Bank Transfer", "CDM"] else "වෙනත් ක්‍රමයක් නම් WhatsApp හරහා කතා කරන්න.", unsafe_allow_html=True)
    st.write("---")
    pay_ref, receipt_file = st.text_input("Reference Number / Receipt ID / Notes:"), st.file_uploader("රිසිට් එකේ ෆොටෝ එකක් දාන්න (අනිවාර්යයි)", type=["png", "jpg", "jpeg"])
    
    if st.button("Submit Payment for Approval"):
        if not pay_ref and receipt_file is None: st.error("⚠️ කරුණාකර Reference Number එක හෝ රිසිට් එකේ ෆොටෝ එකක් අනිවාර්යයෙන් ඇතුළත් කරන්න.")
        else:
            receipt_b64 = base64.b64encode(receipt_file.read()).decode("utf-8") if receipt_file else ""
            supabase.table("manual_payments").insert({"email": user_info['email'], "method": f"{pay_method} [{selected_pkg.split(' -')[0]}]", "reference": pay_ref, "receipt_base64": receipt_b64}).execute()
            st.success("✅ ඔබගේ Payment විස්තර Admin වෙත යවන ලදී! පැය කිහිපයක් ඇතුළත ගිණුම සක්‍රීය වනු ඇත.")
    st.stop() 

# ==========================================
# 📈 TRADING APP MAIN LOGIC
# ==========================================

st.title("⚡ PRO AI Trading Signal App (Institutional VIP Edition)")
st.write("SMC (FVG & Order Blocks), ATR, VWAP, Supertrend, 200 EMA, StochRSI, BB Squeeze සහ Market Sentiment (Fear & Greed) එකතු කර සකස් කළ ස්මාර්ට් ඇනලයිසර් එක.")

if 'scan_results' not in st.session_state: st.session_state.scan_results = []
if 'scan_tf' not in st.session_state: st.session_state.scan_tf = "15 min"
if 'scanning' not in st.session_state: st.session_state.scanning = False

try: TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID, TELEGRAM_CHANNEL_ID = st.secrets["TELEGRAM_BOT_TOKEN"], st.secrets["TELEGRAM_GROUP_ID"], st.secrets["TELEGRAM_CHANNEL_ID"]
except KeyError: st.error("⚠️ රහස්‍ය දත්ත (Secrets) සොයාගත නොහැක."); TELEGRAM_BOT_TOKEN = TELEGRAM_GROUP_ID = TELEGRAM_CHANNEL_ID = ""

def save_to_supabase(data):
    if not supabase: return False
    try: supabase.table("signal_history").insert(data).execute(); return True
    except Exception as e: st.error(f"⚠️ Database Error: {e}"); return False

def get_from_supabase():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("signal_history").select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty: df = df.sort_values(by='Date', ascending=False).reset_index(drop=True)
        return df
    except: return pd.DataFrame()

def update_supabase_status(date_val, coin_val, new_status):
    if not supabase: return
    try: supabase.table("signal_history").update({"Status": new_status}).eq("Date", date_val).eq("Coin", coin_val).execute()
    except: pass

def delete_from_supabase(date_val, coin_val, email, role):
    if not supabase: return
    try: 
        if role in ["Admin", "Owner"]: supabase.table("signal_history").delete().eq("Date", date_val).eq("Coin", coin_val).execute()
        else: supabase.table("signal_history").delete().eq("Date", date_val).eq("Coin", coin_val).eq("created_by", email).execute()
    except: pass

def clear_all_supabase(email, role):
    if not supabase: return
    try: 
        if role in ["Admin", "Owner"]: supabase.table("signal_history").delete().neq("Status", "ClearAllTrigger").execute()
        else: supabase.table("signal_history").delete().eq("created_by", email).execute()
    except: pass

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: return requests.post(url, json={"chat_id": TELEGRAM_GROUP_ID, "text": message, "parse_mode": "Markdown"}).status_code == 200 and requests.post(url, json={"chat_id": TELEGRAM_CHANNEL_ID, "text": message, "parse_mode": "Markdown"}).status_code == 200
    except: return False

def send_telegram_photo_bytes(caption, photo_bytes):
    if not TELEGRAM_BOT_TOKEN: return False
    url, success = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", True
    for chat_id in [TELEGRAM_GROUP_ID, TELEGRAM_CHANNEL_ID]:
        try:
            if requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}, files={"photo": ("chart.png", photo_bytes, "image/png")}).status_code != 200: success = False
        except: success = False
    return success

@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try: data = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json(); return int(data['data'][0]['value']), data['data'][0]['value_classification']
    except: return 50, "Neutral"

def detect_candlestick_pattern(df):
    try:
        if len(df) < 3: return "Not Enough Data"
        last, prev = df.iloc[-1], df.iloc[-2]
        last_body, last_is_green, prev_is_green = abs(last['Close'] - last['Open']), last['Close'] > last['Open'], prev['Close'] > prev['Open']
        last_upper_wick, last_lower_wick = last['High'] - max(last['Open'], last['Close']), min(last['Open'], last['Close']) - last['Low']
        if not prev_is_green and last_is_green and (last['Close'] > prev['Open']) and (last['Open'] < prev['Close']): return "Bullish Engulfing 📈"
        if prev_is_green and not last_is_green and (last['Close'] < prev['Open']) and (last['Open'] > prev['Close']): return "Bearish Engulfing 📉"
        if last_lower_wick > (2 * last_body) and last_upper_wick < (0.2 * last_body): return "Hammer (Bullish) 🔨"
        if last_upper_wick > (2 * last_body) and last_lower_wick < (0.2 * last_body): return "Shooting Star (Bearish) 🌠"
        if last_body < (0.01 * (last['Open'] if last['Open'] > 0 else 0.0001)): return "Doji (Indecision) ⚖️"
        if last['Low'] > df.iloc[-3]['High']: return "Bullish FVG 🟢"
        if last['High'] < df.iloc[-3]['Low']: return "Bearish FVG 🔴"
        return "Standard Price Action"
    except: return "Standard Price Action"

def add_supertrend(df, period=10, multiplier=3):
    atr = df['TR'].rolling(window=period).mean()
    upper_band, lower_band = ((df['High'] + df['Low']) / 2) + (multiplier * atr), ((df['High'] + df['Low']) / 2) - (multiplier * atr)
    upper_band, lower_band = upper_band.bfill().ffill(), lower_band.bfill().ffill()
    in_uptrend, supertrend, st_dir = True, np.zeros(len(df)), np.ones(len(df))
    close_vals, ub_vals, lb_vals = df['Close'].values, upper_band.values, lower_band.values
    for i in range(1, len(df)):
        if close_vals[i] > ub_vals[i-1]: in_uptrend = True
        elif close_vals[i] < lb_vals[i-1]: in_uptrend = False
        else:
            if in_uptrend and lb_vals[i] < lb_vals[i-1]: lb_vals[i] = lb_vals[i-1]
            if not in_uptrend and ub_vals[i] > ub_vals[i-1]: ub_vals[i] = ub_vals[i-1]
        st_dir[i], supertrend[i] = 1 if in_uptrend else -1, lb_vals[i] if in_uptrend else ub_vals[i]
    df['Supertrend'], df['ST_DIR'] = supertrend, st_dir
    return df

def generate_candlestick_image_bytes(df, coin_name, direction, entry, tp1, tp2, tp3, sl, timeframe, detected_pattern):
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df_plot = df.tail(120).copy()
    df_plot['MA_7'], df_plot['MA_25'], df_plot['MA_100'] = df_plot['Close'].rolling(window=7).mean(), df_plot['Close'].rolling(window=25).mean(), df_plot['Close'].rolling(window=100).mean()
    freq, last_date = df_plot.index.to_series().diff().median(), df_plot.index[-1]
    df_padded = pd.concat([df_plot, pd.DataFrame(index=pd.DatetimeIndex([last_date + (freq * i) for i in range(1, 30)]), columns=df_plot.columns)])
    total_len = len(df_padded)
    
    low_val, high_val = df_plot['Low'].min(), df_plot['High'].max()
    low_idx, high_idx = df_plot['Low'].values.argmin(), df_plot['High'].values.argmax()
    diff = high_val - low_val
    fib_382, fib_618 = high_val - (diff * 0.382) if low_idx < high_idx else low_val + (diff * 0.382), high_val - (diff * 0.618) if low_idx < high_idx else low_val + (diff * 0.618)
    start_fib_idx, end_fib_idx = min(low_idx, high_idx), max(low_idx, high_idx)
    
    where_mask, where_fib = np.zeros(total_len, dtype=bool), np.zeros(total_len, dtype=bool)
    where_mask[-34:], where_fib[start_fib_idx:end_fib_idx+1] = True, True
    
    y_entry, y_tp, y_sl, y_fib_top, y_fib_bot = np.full(total_len, entry), np.full(total_len, tp3), np.full(total_len, sl), np.full(total_len, high_val), np.full(total_len, low_val)
    fills = [dict(y1=y_entry, y2=y_tp, where=where_mask, color='#089981', alpha=0.15), dict(y1=y_entry, y2=y_sl, where=where_mask, color='#f23645', alpha=0.15), dict(y1=y_fib_top, y2=y_fib_bot, where=where_fib, color='#787b86', alpha=0.08)]
    s = mpf.make_mpf_style(marketcolors=mpf.make_marketcolors(up='#089981', down='#f23645', edge='inherit', wick='inherit', volume='in', ohlc='i'), gridcolor='#2b2b43', gridstyle='--', facecolor='#131722', edgecolor='#2b2b43', figcolor='#131722', rc={'font.size': 9, 'axes.grid': True, 'text.color': '#d1d4dc', 'axes.labelcolor': '#d1d4dc', 'xtick.color': '#d1d4dc', 'ytick.color': '#d1d4dc'})
    
    ap = []
    if not df_padded['MA_7'].isna().all(): ap.append(mpf.make_addplot(df_padded['MA_7'], color='#2962ff', width=1.5)) 
    if not df_padded['MA_25'].isna().all(): ap.append(mpf.make_addplot(df_padded['MA_25'], color='#9c27b0', width=1.5)) 
    if not df_padded['MA_100'].isna().all(): ap.append(mpf.make_addplot(df_padded['MA_100'], color='#66bb6a', width=1.5)) 
    if 'EMA_200' in df_padded.columns and not df_padded['EMA_200'].isna().all(): ap.append(mpf.make_addplot(df_padded['EMA_200'], color='#ffeb3b', width=2.0)) 
    if 'VWAP' in df_padded.columns and not df_padded['VWAP'].isna().all(): ap.append(mpf.make_addplot(df_padded['VWAP'], color='#ff9800', width=1.8, linestyle='-.')) 
        
    pattern_marker = [np.nan] * total_len
    if detected_pattern != "Standard Price Action":
        is_bullish = "Bullish" in detected_pattern or "Buy" in direction or "Hammer" in detected_pattern
        pattern_marker[len(df_plot) - 1] = df_plot['Low'].iloc[-1] - (df_plot['ATR'].iloc[-1] * 0.8) if is_bullish else df_plot['High'].iloc[-1] + (df_plot['ATR'].iloc[-1] * 0.8)
        ap.append(mpf.make_addplot(pattern_marker, type='scatter', markersize=200, marker='^' if is_bullish else 'v', color='#089981' if is_bullish else '#f23645'))

    fig, axlist = mpf.plot(df_padded, type='candle', style=s, volume=True, addplot=ap, fill_between=fills, returnfig=True, figsize=(12, 6.5), panel_ratios=(5,1), tight_layout=True)
    ax_main = axlist[0] 
    
    vp_bins, price_min, price_max = 50, df_plot['Low'].min(), df_plot['High'].max()
    bin_size, bins = (price_max - price_min) / vp_bins, np.linspace(price_min, price_max, vp_bins + 1)
    df_plot['Bin'] = pd.cut((df_plot['High'] + df_plot['Low'] + df_plot['Close']) / 3, bins=bins, labels=False, include_lowest=True)
    vp_up_arr, vp_down_arr = np.zeros(vp_bins), np.zeros(vp_bins)
    for b, vol in df_plot[df_plot['Close'] >= df_plot['Open']].groupby('Bin')['Volume'].sum().items(): 
        if not np.isnan(b): vp_up_arr[int(b)] = vol
    for b, vol in df_plot[df_plot['Close'] < df_plot['Open']].groupby('Bin')['Volume'].sum().items(): 
        if not np.isnan(b): vp_down_arr[int(b)] = vol
        
    max_vol = np.max(vp_up_arr + vp_down_arr)
    if max_vol > 0:
        vp_widths_up, vp_widths_down, vp_y = (vp_up_arr / max_vol) * 22, (vp_down_arr / max_vol) * 22, bins[:-1] + (bin_size / 2)
        ax_main.barh(vp_y, vp_widths_up, left=0, height=bin_size*0.9, color='#2962ff', alpha=0.2, zorder=1)
        ax_main.barh(vp_y, vp_widths_down, left=vp_widths_up, height=bin_size*0.9, color='#ff9800', alpha=0.2, zorder=1)

    ax_main.plot([low_idx, high_idx], [low_val, high_val], color='#787b86', linestyle='--', linewidth=1.5, alpha=0.5)
    for val, label in [(high_val, '1 (100%)'), (fib_618, '0.618'), (fib_382, '0.382'), (low_val, '0 (0%)')]:
        ax_main.plot([start_fib_idx, end_fib_idx], [val, val], color='#787b86', linestyle=':', linewidth=1.2, alpha=0.5)
        ax_main.text(start_fib_idx, val, f" {label}", color='#787b86', fontsize=8, va='bottom', ha='left')

    x_max, atr_val = total_len - 1, df_plot['ATR'].iloc[-1]
    for price, color, label in [(tp3, '#089981', 'Take Profit 3 (TP 3)'), (tp2, '#089981', 'Take Profit 2 (TP 2)'), (tp1, '#089981', 'Take Profit 1 (TP 1)'), (entry, '#b2b5be', 'Entry Price'), (sl, '#f23645', 'Stop Loss (SL)')]:
        ax_main.axhline(y=price, color=color, linestyle='-', linewidth=1.2, alpha=0.9)
        ax_main.text(x_max, price, f" {price:.{6 if price < 0.01 else 2}f} ", ha="right", va="center", color="white" if color != '#b2b5be' else "#131722", fontsize=10, fontweight='bold', bbox=dict(boxstyle="square,pad=0.3", fc=color, ec=color, lw=0))
        ax_main.text(x_max - 5, price + (atr_val * 0.15 if direction == "BUY" or label == 'Entry Price' else -(atr_val * 0.15)), label, ha="right", va="bottom" if direction == "BUY" or label == 'Entry Price' else "top", color=color, fontsize=10, fontweight='bold')

    res_y, sup_y = (tp3 + (atr_val * 0.3), sl - (atr_val * 0.3)) if direction == "BUY" else (sl + (atr_val * 0.3), tp3 - (atr_val * 0.3))
    ax_main.axhline(y=res_y, color='#f23645', linestyle='-', linewidth=1.5, alpha=0.4)
    ax_main.text(x_max - 15, res_y, "Red Resistance OB" if direction == "BUY" else "Red Resistance / Bearish OB", ha="right", va="bottom", color="#f23645", fontsize=9, fontweight='bold')
    ax_main.axhline(y=sup_y, color='#089981', linestyle='-', linewidth=1.5, alpha=0.4)
    ax_main.text(x_max - 15, sup_y, "Support Zone / Bullish OB" if direction == "BUY" else "Support Zone", ha="right", va="top", color="#089981", fontsize=9, fontweight='bold')

    ax_main.text(0.01, 0.96, f"💎 {coin_name.replace('USDT', ' / TetherUS')} • {timeframe} • BINANCE", transform=ax_main.transAxes, fontsize=12, fontweight='bold', color='#d1d4dc')
    ax_main.text(0.01, 0.91, "Multi MA + VPVR + Institutional VWAP", transform=ax_main.transAxes, fontsize=9, color='#787b86')
    ax_main.text(0.01, 0.86, f"AI Confidence: {direction} SETUP 🔥", transform=ax_main.transAxes, fontsize=10, fontweight='bold', color='#089981' if direction=="BUY" else '#f23645')
    ax_main.text(0.01, 0.81, f"🧩 Detected Pattern: {detected_pattern}", transform=ax_main.transAxes, fontsize=10, fontweight='bold', color='#ff9800')

    buf = io.BytesIO()
    fig.savefig(buf, dpi=120, bbox_inches='tight', facecolor='#131722')
    buf.seek(0)
    return buf.read()

market_options = {"Bitcoin (BTC/USD)": "BTC-USD", "Ethereum (ETH/USD)": "ETH-USD", "Solana (SOL/USD)": "SOL-USD", "Binance Coin (BNB/USD)": "BNB-USD", "Ripple (XRP/USD)": "XRP-USD", "Cardano (ADA/USD)": "ADA-USD", "Dogwifhat (WIF/USD)": "WIF-USD", "Shiba Inu (SHIB/USD)": "SHIB-USD", "Pepe (PEPE/USD)": "PEPE-USD", "Avalanche (AVAX/USD)": "AVAX-USD", "Chainlink (LINK/USD)": "LINK-USD", "Polkadot (DOT/USD)": "DOT-USD", "Fantom (FTM/USD)": "FTM-USD", "Polygon (MATIC/USD)": "MATIC-USD", "Injective (INJ/USD)": "INJ-USD", "Dogecoin (DOGE/USD)": "DOGE-USD", "Litecoin (LTC/USD)": "LTC-USD", "Bitcoin Cash (BCH/USD)": "BCH-USD", "Stellar (XLM/USD)": "XLM-USD", "Uniswap (UNI/USD)": "UNI-USD", "Cosmos (ATOM/USD)": "ATOM-USD", "Monero (XMR/USD)": "XMR-USD", "Ethereum Classic (ETC/USD)": "ETC-USD", "Filecoin (FIL/USD)": "FIL-USD", "Internet Computer (ICP/USD)": "ICP-USD", "VeChain (VET/USD)": "VET-USD", "Hedera (HBAR/USD)": "HBAR-USD", "Aptos (APT/USD)": "APT-USD", "Arbitrum (ARB/USD)": "ARB-USD", "Near Protocol (NEAR/USD)": "NEAR-USD", "Optimism (OP/USD)": "OP-USD", "Stacks (STX/USD)": "STX-USD", "Render (RNDR/USD)": "RNDR-USD", "Immutable (IMX/USD)": "IMX-USD", "The Graph (GRT/USD)": "GRT-USD", "Theta Network (THETA/USD)": "THETA-USD", "Aave (AAVE/USD)": "AAVE-USD", "Synthetix (SNX/USD)": "SNX-USD", "Maker (MKR/USD)": "MKR-USD", "Algorand (ALGO/USD)": "ALGO-USD", "Flow (FLOW/USD)": "FLOW-USD", "MultiversX (EGLD/USD)": "EGLD-USD", "Mina (MINA/USD)": "MINA-USD", "THORChain (RUNE/USD)": "RUNE-USD", "Lido DAO (LDO/USD)": "LDO-USD", "Quant (QNT/USD)": "QNT-USD", "Gala (GALA/USD)": "GALA-USD", "The Sandbox (SAND/USD)": "SAND-USD", "Decentraland (MANA/USD)": "MANA-USD", "Axie Infinity (AXS/USD)": "AXS-USD", "Chiliz (CHZ/USD)": "CHZ-USD", "Enjin Coin (ENJ/USD)": "ENJ-USD", "Curve DAO (CRV/USD)": "CRV-USD", "Zilliqa (ZIL/USD)": "ZIL-USD", "NEO (NEO/USD)": "NEO-USD", "Dash (DASH/USD)": "DASH-USD", "Kava (KAVA/USD)": "KAVA-USD", "Compound (COMP/USD)": "COMP-USD", "IOTA (MIOTA/USD)": "MIOTA-USD", "Tezos (XTZ/USD)": "XTZ-USD", "Zcash (ZEC/USD)": "ZEC-USD", "Kusama (KSM/USD)": "KSM-USD", "Basic Attention Token (BAT/USD)": "BAT-USD", "Harmony (ONE/USD)": "ONE-USD", "Celo (CELO/USD)": "CELO-USD", "Qtum (QTUM/USD)": "QTUM-USD", "Ravencoin (RVN/USD)": "RVN-USD", "Ontology (ONT/USD)": "ONT-USD", "ICON (ICX/USD)": "ICX-USD", "DigiByte (DGB/USD)": "DGB-USD", "Horizen (ZEN/USD)": "ZEN-USD", "Nano (XNO/USD)": "XNO-USD", "Syscoin (SYS/USD)": "SYS-USD", "Sui (SUI/USD)": "SUI-USD", "Sei (SEI/USD)": "SEI-USD", "Worldcoin (WLD/USD)": "WLD-USD", "CyberConnect (CYBER/USD)": "CYBER-USD", "Pendle (PENDLE/USD)": "PENDLE-USD", "Radix (XRD/USD)": "XRD-USD", "Kaspa (KAS/USD)": "KAS-USD", "GMX (GMX/USD)": "GMX-USD", "Magic (MAGIC/USD)": "MAGIC-USD", "Illuvium (ILV/USD)": "ILV-USD", "Biconomy (BICO/USD)": "BICO-USD", "Gnosis (GNO/USD)": "GNO-USD", "Status (SNT/USD)": "SNT-USD", "Aragon (ANT/USD)": "ANT-USD", "Kyber Network (KNC/USD)": "KNC-USD", "Bancor (BNT/USD)": "BNT-USD", "Loopring (LRC/USD)": "LRC-USD", "Storj (STORJ/USD)": "STORJ-USD", "Civic (CVC/USD)": "CVC-USD", "Fetch.ai (FET/USD)": "FET-USD", "Band Protocol (BAND/USD)": "BAND-USD", "Numeraire (NMR/USD)": "NMR-USD", "iExec RLC (RLC/USD)": "RLC-USD", "Theta Fuel (TFUEL/USD)": "TFUEL-USD", "WazirX (WRX/USD)": "WRX-USD", "Swipe (SXP/USD)": "SXP-USD", "Klever (KLV/USD)": "KLV-USD", "Utrust (UTK/USD)": "UTK-USD", "Firo (FIRO/USD)": "FIRO-USD", "Dusk Network (DUSK/USD)": "DUSK-USD", "DIA (DIA/USD)": "DIA-USD", "Litentry (LIT/USD)": "LIT-USD", "Phala Network (PHA/USD)": "PHA-USD", "Marlin (POND/USD)": "POND-USD", "Radiant Capital (RDNT/USD)": "RDNT-USD", "Gains Network (GNS/USD)": "GNS-USD", "PancakeSwap (CAKE/USD)": "CAKE-USD", "Trust Wallet (TWT/USD)": "TWT-USD", "1inch (1INCH/USD)": "1INCH-USD", "Ocean Protocol (OCEAN/USD)": "OCEAN-USD", "SKALE (SKL/USD)": "SKL-USD", "Cartesi (CTSI/USD)": "CTSI-USD", "Coti (COTI/USD)": "COTI-USD", "NKN (NKN/USD)": "NKN-USD"}
fx_options_dict = {"Euro / US Dollar (EUR/USD)": "EURUSD=X", "Great Britain Pound / US Dollar (GBP/USD)": "GBPUSD=X", "US Dollar / Japanese Yen (USD/JPY)": "USDJPY=X", "Australian Dollar / US Dollar (AUD/USD)": "AUDUSD=X"}
com_options_dict = {"රන් / Gold (XAU/USD)": "GC=F", "කෲඩ් ඔයිල් / Crude Oil (WTI)": "CL=F"}
tf_mapping = {"5 min": {"yf": "5m", "tv": "5", "period": "60d"}, "15 min": {"yf": "15m", "tv": "15", "period": "60d"}, "30 min": {"yf": "30m", "tv": "30", "period": "60d"}, "1 hour": {"yf": "1h", "tv": "60", "period": "730d"}, "4 hour": {"yf": "4h", "tv": "240", "period": "730d"}, "1 day": {"yf": "1d", "tv": "D", "period": "max"}}

@st.cache_data
def get_market_data(symbol, tf, prd): return yf.download(symbol, period=prd, interval=tf, auto_adjust=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Live AI Signals", "🔍 VIP Market Scanner", "📂 Auto Signal History", "💼 VIP Demo Trading"])

with tab1:
    st.subheader("🌐 Market සහ Coins තෝරන්න:")
    category = st.radio("ප්‍රවර්ගය තෝරන්න (Select Category):", ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)", "💱 ෆොරෙක්ස් (Forex)", "✨ ලෝහ සහ තෙල් (Metals & Oil)", "✏️ වෙනත් (Custom)"], horizontal=True)
    strategy_mode = st.radio("Trading Strategy Mode:", ["🔥 Aggressive Mode (More Signals)", "🛡️ Safe Mode (Strict)"], horizontal=True)

    if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)":
        selected_display_name = st.selectbox("Coins තෝරන්න:", list(market_options.keys()))
        ticker = market_options[selected_display_name]
        clean_symbol = ticker.replace('-USD', 'USDT')
        full_tv_ticker = f"BINANCE:{clean_symbol}"
    elif category == "💱 ෆොරෙක්ස් (Forex)":
        selected_display_name = st.selectbox("Coins තෝරන්න:", list(fx_options_dict.keys()))
        ticker = fx_options_dict[selected_display_name]
        clean_symbol = ticker.replace('=X', '')
        full_tv_ticker = f"FX_IDC:{clean_symbol}"
    elif category == "✨ ලෝහ සහ තෙල් (Metals & Oil)":
        selected_display_name = st.selectbox("Coins තෝරන්න:", list(com_options_dict.keys()))
        ticker = com_options_dict[selected_display_name]
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
        df['EMA_9'], df['EMA_21'] = df['Close'].ewm(span=9, adjust=False).mean(), df['Close'].ewm(span=21, adjust=False).mean()
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain, loss = (delta.where(delta > 0, 0)).rolling(window=14).mean(), (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        min_val, max_val = df['RSI'].rolling(window=14).min(), df['RSI'].rolling(window=14).max()
        df['StochRSI'] = (df['RSI'] - min_val) / (max_val - min_val)
        df['StochRSI_K'] = df['StochRSI'].rolling(window=3).mean().fillna(0)
        df['StochRSI_D'] = df['StochRSI_K'].rolling(window=3).mean().fillna(0)
        
        df['MA20'], df['StdDev'] = df['Close'].rolling(window=20).mean(), df['Close'].rolling(window=20).std()
        df['BB_Upper'], df['BB_Lower'] = df['MA20'] + (df['StdDev'] * 2), df['MA20'] - (df['StdDev'] * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20']
        
        df['High-Low'], df['High-PrevClose'], df['Low-PrevClose'] = df['High'] - df['Low'], np.abs(df['High'] - df['Close'].shift(1)), np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        df['FVG_Bull'], df['FVG_Bear'] = np.where(df['Low'] > df['High'].shift(2), 1, 0), np.where(df['High'] < df['Low'].shift(2), 1, 0)
        df['Target'] = np.where(df['Close'].shift(-2) > df['Close'], 1, 0)
        
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        vol_cumsum = df['Volume'].cumsum()
        df['VWAP'] = np.where(vol_cumsum > 0, (df['Typical_Price'] * df['Volume']).cumsum() / vol_cumsum, df['Close'])
        df['VWAP_Dist'] = np.where(df['VWAP'] > 0, df['Close'] / df['VWAP'], 1.0)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_ROC'] = df['OBV'].pct_change().fillna(0)
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean().fillna(0)
        df = add_supertrend(df)
        
        detected_pattern = detect_candlestick_pattern(df)
        features = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'BB_Width', 'Returns', 'ATR', 'FVG_Bull', 'FVG_Bear', 'MACD', 'Signal_Line', 'VWAP_Dist', 'ST_DIR', 'EMA_200', 'StochRSI_K', 'StochRSI_D']
        last_market_state = df[features].iloc[[-1]].copy()
        df_train = df.dropna() 
        
        if len(df_train) < 20: st.warning("⚠️ AI Model එකට ඉගෙනගැනීමට තරම් ප්‍රමාණවත් දත්ත (Data) Yahoo Finance හරහා ලැබී නොමැත. කරුණාකර වෙනත් Timeframe එකක් හෝ Coin එකක් තෝරන්න.")
        else:
            try:
                X, y = df_train[features], df_train['Target']
                split = int(0.85 * len(df_train))
                X_train, y_train = X[:split], y[:split]
                model = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=3, random_state=42)
                model.fit(X_train, y_train)
                prediction, probability = model.predict(last_market_state)[0], model.predict_proba(last_market_state)[0]
                
                try: current_price = float(yf.Ticker(ticker).fast_info['lastPrice'])
                except Exception: current_price = float(df['Close'].iloc[-1])
                    
                atr_val = float(df['ATR'].iloc[-1])
                ai_confidence = max(probability) * 100
                dp = 8 if current_price < 0.01 else 4
                pullback_amount = atr_val * 0.3  
                
                if prediction == 1: 
                    entry_price = current_price - pullback_amount 
                    tp1_price, tp2_price, tp3_price = entry_price + (atr_val * 1.5), entry_price + (atr_val * 3.0), entry_price + (atr_val * 5.0)
                    sl_price = entry_price - (atr_val * 2.0) 
                else: 
                    entry_price = current_price + pullback_amount 
                    tp1_price, tp2_price, tp3_price = entry_price - (atr_val * 1.5), entry_price - (atr_val * 3.0), entry_price - (atr_val * 5.0)
                    sl_price = entry_price + (atr_val * 2.0) 
        
                st.write("---")
                st.subheader(f"📊 {selected_display_name} ({tf_display}) PRO AI විශ්ලේෂණය:")
                fng_value, fng_class = get_fear_and_greed()
                if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)": st.info(f"🧭 **Crypto Market Sentiment (Fear & Greed):** {fng_class} ({fng_value}/100)")
                
                has_valid_signal, is_reversal, confluence_pass, confluence_msg = False, False, True, ""
                last_ema9, last_ema21, last_macd, last_rsi = float(last_market_state['EMA_9'].iloc[0]), float(last_market_state['EMA_21'].iloc[0]), float(last_market_state['MACD'].iloc[0]), float(last_market_state['RSI'].iloc[0])
                
                if "Aggressive" in strategy_mode:
                    min_conf = 50.1
                    if prediction == 1 and last_rsi > 75: confluence_pass, confluence_msg = False, "🚨 Aggressive Mode වුවත් RSI > 75 (Overbought) බැවින් BUY කිරීම අවදානම්ය."
                    elif prediction == 0 and last_rsi < 25: confluence_pass, confluence_msg = False, "🚨 Aggressive Mode වුවත් RSI < 25 (Oversold) බැවින් SELL කිරීම අවදානම්ය."
                else:
                    min_conf = 60.0
                    if prediction == 1: 
                        if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)" and fng_value >= 80: confluence_pass, confluence_msg = False, f"🚨 **Fear & Greed Warning:** මාකට් එක දැනට තියෙන්නේ '{fng_class}' (Overbought) මට්ටමේ. මෙවැනි අවස්ථාවක Market එක කඩා වැටෙන්නට (Crash) ඉඩ ඇති බැවින් AI මෙම BUY සිග්නලය ප්‍රතික්ෂේප කරයි."
                        elif (last_ema9 < last_ema21) and (last_macd < 0):
                            if last_rsi < 45 and ("Hammer" in detected_pattern or "Bullish" in detected_pattern): is_reversal = True
                            else: confluence_pass, confluence_msg = False, "🚨 **Trend Filter Warning:** මාකට් එකේ දැනට තියෙන්නේ ප්‍රබල Downtrend එකක්. පැහැදිලි Reversal Pattern එකක් නොමැතිව 'Falling Knife' එකක් ඇල්ලීම ඉතා අවදානම් වැඩක් බැවින් AI මෙම සිග්නලය ප්‍රතික්ෂේප කරයි."
                    else: 
                        if category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)" and fng_value <= 20: confluence_pass, confluence_msg = False, f"🚨 **Fear & Greed Warning:** මාකට් එක දැනට තියෙන්නේ '{fng_class}' (Oversold) මට්ටමේ. මෙතැනින් Reversal එකක් වීමට ඉඩ ඇති බැවින් AI මෙම SELL සිග්නලය ප්‍රතික්ෂේප කරයි."
                        elif (last_ema9 > last_ema21) and (last_macd > 0):
                            if last_rsi > 55 and ("Shooting Star" in detected_pattern or "Bearish" in detected_pattern): is_reversal = True
                            else: confluence_pass, confluence_msg = False, "🚨 **Trend Filter Warning:** මාකට් එකේ දැනට තියෙන්නේ ප්‍රබල Uptrend එකක්. පැහැදිලි Reversal Pattern එකක් නොමැතිව SELL සිග්නල් එකක් ගැනීම ඉතා අවදානම් බැවින් AI මෙම සිග්නලය ප්‍රතික්ෂේප කරයි."

                if ai_confidence < min_conf: st.warning(f"⚠️ **NO SIGNAL (මාකට් එක පැහැදිලි නැත)** \n\nAI විශ්වාසය මදියි ({ai_confidence:.1f}%). අවම වශයෙන් {min_conf}% ක විශ්වාසයක් අවශ්‍යයි.")
                elif not confluence_pass: st.error(confluence_msg)
                else:
                    has_valid_signal = True
                    if is_reversal: st.info("🔥 **SMART REVERSAL DETECTED!** AI එක Trend Reversal එකක් (හැරවුම් ලක්ෂ්‍යයක්) හඳුනාගත්තා!")
                    if prediction == 1: st.success(f"🟢 **DIRECTION: BUY / LONG** 📈 ⬆️ (Confidence: {ai_confidence:.1f}%)")
                    else: st.error(f"🔴 **DIRECTION: SELL / SHORT** 📉 ⬇️ (Confidence: {ai_confidence:.1f}%)")
        
                chart_studies = '["MASimple@tv-basicstudies", "BBands@tv-basicstudies", "MACD@tv-basicstudies"]'
                tradingview_html = f"""<div class="tradingview-widget-container" style="height:500px; width:100%;"><div id="tradingview_chart" style="height:500px;"></div><script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script><script type="text/javascript">new TradingView.widget({{"autosize": true, "height": 500, "symbol": "{full_tv_ticker}", "interval": "{selected_tf['tv']}", "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "withdateranges": true, "hide_side_toolbar": false, "allow_symbol_change": true, "studies": {chart_studies}, "container_id": "tradingview_chart"}});</script></div>"""
                components.html(tradingview_html, height=510)
        
                st.write("---")
                if has_valid_signal:
                    dir_text = "🟢 BUY / LONG 📈 ⬆️" + (" (🔥 Reversal Setup)" if is_reversal else "") if prediction == 1 else "🔴 SELL / SHORT 📉 ⬇️" + (" (🔥 Reversal Setup)" if is_reversal else "")
                    direction_text = "BUY" if prediction == 1 else "SELL"
                    
                    target_msg = f"📊 **ඇඳිය යුතු නිවැරදි මිල මට්ටම් (ATR & SMC Visual Targets):**\n\n🪙 **Coin:** {selected_display_name}\n\n🔥 **Signal Direction:** {dir_text}\n\n🧩 **Detected Pattern:** {detected_pattern}\n\n🔵 **Entry Limit Price:** ${entry_price:.{dp}f}\n\n🎯 **TP 1:** ${tp1_price:.{dp}f}\n\n🎯 **TP 2:** ${tp2_price:.{dp}f}\n\n🎯 **TP 3:** ${tp3_price:.{dp}f}\n\n🛑 **Stop Loss (SL):** ${sl_price:.{dp}f}"
                    st.info(target_msg)
                    
                    st.write("### 📸 AI Signal Visualizer Preview (Trading Setup එක)")
                    try:
                        chart_image_bytes = generate_candlestick_image_bytes(df, clean_symbol, direction_text, entry_price, tp1_price, tp2_price, tp3_price, sl_price, tf_display, detected_pattern)
                        st.image(chart_image_bytes, caption=f"Dynamically Generated Setup for {selected_display_name} (VPVR + VWAP + 200 EMA + OB + {detected_pattern})")
                        image_generated_successfully = True
                    except Exception as img_err: st.error(f"⚠️ ප්‍රස්ථාරය සැකසීමේදී දෝෂයක්. ({img_err})"); image_generated_successfully = False

                    st.write("---")
                    st.write("### ⚙️ Signal Actions")
                    
                    if st.button("💾 Save Signal to My History", use_container_width=True):
                        chart_b64 = base64.b64encode(chart_image_bytes).decode("utf-8") if image_generated_successfully else ""
                        date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                        data_to_save = {"Date": date_str, "Ticker": ticker, "Coin": selected_display_name.split()[0], "Category": category, "Strategy": strategy_mode, "Direction": direction_text, "Entry": entry_price, "TP1": tp1_price, "TP2": tp2_price, "TP3": tp3_price, "SL": sl_price, "Status": "⏳ Pending Entry", "created_by": user_info['email'], "TF": tf_display, "Pattern": detected_pattern, "chart_base64": chart_b64}
                        if save_to_supabase(data_to_save): st.success("✅ සිග්නල් එක සහ ප්‍රස්ථාරය සාර්ථකව ඔබගේ History එකට සේව් වුණා!")
                        else: st.error("❌ සේව් කිරීම අසාර්ථකයි.")
                            
                    if user_info['role'] in ["Owner", "Admin"]:
                        if st.button("🚀 Send Signal to Telegram & Save", type="primary", use_container_width=True):
                            try: check_live = float(yf.Ticker(ticker).fast_info['lastPrice'])
                            except: check_live = current_price
                            is_safe_to_send = True
                            if prediction == 1 and (check_live >= tp1_price or check_live <= sl_price): is_safe_to_send = False
                            elif prediction == 0 and (check_live <= tp1_price or check_live >= sl_price): is_safe_to_send = False
                                    
                            if not is_safe_to_send: st.error("⚠️ **මෙම Signal එක දැන් පරණ වැඩියි! (Expired)** ⚠️\n\nඔබ මෙය යැවීමට ප්‍රමාද වූ බැවින් මාකට් එක දැනටමත් වෙනස් වී ඇත. කරුණාකර අලුත් Signal එකක් ලබාගන්න.")
                            else:
                                cat_name = "Crypto 🪙" if "Crypto" in category else "Forex 💱" if "Forex" in category else "Commodities ✨" if "Metals" in category else "Custom ✏️"
                                telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n🏦 *Market:* {cat_name}\n⚙️ *Strategy Mode:* {strategy_mode}\n🪙 *Coin/Pair:* {selected_display_name}\n⏱ *Timeframe:* {tf_display}\n🔥 *Direction:* {dir_text}\n🧩 *Detected Pattern:* {detected_pattern}\n\n🔵 *Entry Price:* `${entry_price:.{dp}f}`\n🎯 *TP 1:* `${tp1_price:.{dp}f}`\n🎯 *TP 2:* `${tp2_price:.{dp}f}`\n🎯 *TP 3:* `${tp3_price:.{dp}f}`\n🛑 *Stop Loss (SL):* `${sl_price:.{dp}f}`\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                                with st.spinner("Chart එක සකසමින් සහ Telegram වෙත යවමින් පවතී... ⏳"):
                                    success = False
                                    if image_generated_successfully: success = send_telegram_photo_bytes(telegram_text, chart_image_bytes)
                                    if not success: success = send_telegram_message(telegram_text); st.warning("⚠️ Chart Photo එක යැවීමේදී දෝෂයක්. (Text Signal පමණි).")
                                if success:
                                    chart_b64 = base64.b64encode(chart_image_bytes).decode("utf-8") if image_generated_successfully else ""
                                    date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                                    data_to_save = {"Date": date_str, "Ticker": ticker, "Coin": selected_display_name.split()[0], "Category": cat_name, "Strategy": strategy_mode, "Direction": direction_text, "Entry": entry_price, "TP1": tp1_price, "TP2": tp2_price, "TP3": tp3_price, "SL": sl_price, "Status": "⏳ Pending Entry", "created_by": user_info['email'], "TF": tf_display, "Pattern": detected_pattern, "chart_base64": chart_b64}
                                    if save_to_supabase(data_to_save): st.success("✅ Telegram එකට යැව්වා සහ History එකටත් සේව් වුණා!")
                                else: st.error("❌ Telegram යැවීම අසාර්ථකයි.")
            except Exception as e: st.error(f"⚠️ දත්ත විශ්ලේෂණයේදී ගැටලුවක් මතු විය. වෙනත් Timeframe එකක් තෝරන්න. Error: {e}")
    else: st.error("තෝරාගත් කාල රාමුව සඳහා ප්‍රමාණවත් දත්ත නොමැත. කරුණාකර වෙනත් Timeframe එකක් තෝරන්න.")

with tab2:
    st.subheader("🔍 VIP Market Scanner (Auto Signal Finder)")
    st.write("එකින් එක Coins පරීක්ෂා කිරීම වෙනුවට, එකවර මුළු Category එකක්ම ස්කෑන් කර මේ මොහොතේ Valid Signals ඇති Coins පමණක් පහසුවෙන් සොයාගන්න.")
    scan_category = st.radio("ප්‍රවර්ගය තෝරන්න (Select Category):", ["🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)", "💱 ෆොරෙක්ස් (Forex)", "✨ ලෝහ සහ තෙල් (Metals & Oil)"], horizontal=True, key="scanner_category_radio")
    strategy_mode_scan = st.radio("Trading Strategy Mode (Scanner):", ["🔥 Aggressive Mode (More Signals)", "🛡️ Safe Mode (Strict)"], horizontal=True, key="scan_strat")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1: scan_tf_display = st.selectbox("ස්කෑන් කළ යුතු Timeframe එක තෝරන්න:", ["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"], index=["5 min", "15 min", "30 min", "1 hour", "4 hour", "1 day"].index(st.session_state.scan_tf))
        
    if scan_category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)": current_scan_options, max_limit_val = market_options, len(market_options)
    elif scan_category == "💱 ෆොරෙක්ස් (Forex)": current_scan_options, max_limit_val = fx_options_dict, len(fx_options_dict)
    else: current_scan_options, max_limit_val = com_options_dict, len(com_options_dict)
        
    with col_s2: scan_limit = st.slider("ස්කෑන් කරන Coins ගණන (වේගවත් කිරීම සඳහා):", min_value=1, max_value=max_limit_val, value=min(30, max_limit_val), step=1)
    with col_s3:
        st.write(""); st.write("")
        start_scan = st.button("🚀 Start Scan", use_container_width=True)

    if start_scan:
        st.session_state.scanning = True
        st.session_state.scan_results = []
        st.session_state.scan_tf = scan_tf_display
        st.session_state.last_scan_empty = False

    if st.session_state.get('scanning', False):
        st.warning("⚠️ ස්කෑන් වෙමින් පවතී... හොඳ සිග්නල් එකක් දැක්කොත් පහළින් ඇති 'Stop Scan' බොත්තම ඔබන්න.")
        if st.button("🛑 Stop Scan (නවත්වන්න)", type="primary"):
            st.session_state.scanning = False
            if len(st.session_state.scan_results) == 0: st.session_state.last_scan_empty = True
            st.rerun()

        progress_bar, status_text, results_placeholder = st.progress(0), st.empty(), st.empty()
        if not st.session_state.scan_results: results_placeholder.table(pd.DataFrame(columns=['Coin / Pair', 'Direction', 'Confidence', 'Pattern']))
        fng_value, fng_class = get_fear_and_greed()
        coins_to_scan = list(current_scan_options.keys())[:scan_limit]
        total_coins, scan_tf = len(coins_to_scan), tf_mapping[st.session_state.scan_tf]
        
        for i, coin_name in enumerate(coins_to_scan):
            if not st.session_state.scanning: break
            ticker_to_scan = current_scan_options[coin_name]
            status_text.info(f"🔍 ස්කෑන් කරමින් පවතී: {coin_name}... ({i+1}/{total_coins})")
            try:
                time.sleep(0.05)
                df_scan = yf.download(ticker_to_scan, period=scan_tf["period"], interval=scan_tf["yf"], auto_adjust=True, progress=False)
                if not df_scan.empty and len(df_scan) > 125:
                    if isinstance(df_scan.columns, pd.MultiIndex): df_scan.columns = df_scan.columns.get_level_values(0)
                    if 'Volume' not in df_scan.columns or df_scan['Volume'].isna().all() or (df_scan['Volume'] == 0).all(): df_scan['Volume'] = 1.0  
                    else: df_scan['Volume'] = df_scan['Volume'].fillna(1.0)
                    df_scan = df_scan.tail(600).copy() 
                    df_scan['Returns'] = df_scan['Close'].pct_change()
                    df_scan['EMA_9'], df_scan['EMA_21'] = df_scan['Close'].ewm(span=9, adjust=False).mean(), df_scan['Close'].ewm(span=21, adjust=False).mean()
                    df_scan['MACD'] = df_scan['Close'].ewm(span=12, adjust=False).mean() - df_scan['Close'].ewm(span=26, adjust=False).mean()
                    df_scan['Signal_Line'] = df_scan['MACD'].ewm(span=9, adjust=False).mean()
                    delta = df_scan['Close'].diff()
                    rs = (delta.where(delta > 0, 0)).rolling(window=14).mean() / (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    df_scan['RSI'] = 100 - (100 / (1 + rs))
                    min_val_s, max_val_s = df_scan['RSI'].rolling(window=14).min(), df_scan['RSI'].rolling(window=14).max()
                    df_scan['StochRSI'] = (df_scan['RSI'] - min_val_s) / (max_val_s - min_val_s)
                    df_scan['StochRSI_K'] = df_scan['StochRSI'].rolling(window=3).mean().fillna(0)
                    df_scan['StochRSI_D'] = df_scan['StochRSI_K'].rolling(window=3).mean().fillna(0)
                    df_scan['MA20'] = df_scan['Close'].rolling(window=20).mean()
                    df_scan['StdDev'] = df_scan['Close'].rolling(window=20).std()
                    df_scan['BB_Upper'], df_scan['BB_Lower'] = df_scan['MA20'] + (df_scan['StdDev'] * 2), df_scan['MA20'] - (df_scan['StdDev'] * 2)
                    df_scan['BB_Width'] = (df_scan['BB_Upper'] - df_scan['BB_Lower']) / df_scan['MA20']
                    df_scan['TR'] = df_scan[['High', 'Low']].max(axis=1) - df_scan[['High', 'Low']].min(axis=1)
                    df_scan['ATR'] = df_scan['TR'].rolling(window=14).mean()
                    df_scan['FVG_Bull'], df_scan['FVG_Bear'] = np.where(df_scan['Low'] > df_scan['High'].shift(2), 1, 0), np.where(df_scan['High'] < df_scan['Low'].shift(2), 1, 0)
                    df_scan['Target'] = np.where(df_scan['Close'].shift(-2) > df_scan['Close'], 1, 0)
                    df_scan['Typical_Price'] = (df_scan['High'] + df_scan['Low'] + df_scan['Close']) / 3
                    vol_cumsum = df_scan['Volume'].cumsum()
                    df_scan['VWAP'] = np.where(vol_cumsum > 0, (df_scan['Typical_Price'] * df_scan['Volume']).cumsum() / vol_cumsum, df_scan['Close'])
                    df_scan['VWAP_Dist'] = np.where(df_scan['VWAP'] > 0, df_scan['Close'] / df_scan['VWAP'], 1.0)
                    df_scan['OBV'] = (np.sign(df_scan['Close'].diff()) * df_scan['Volume']).fillna(0).cumsum()
                    df_scan['OBV_ROC'] = df_scan['OBV'].pct_change().fillna(0)
                    df_scan['EMA_200'] = df_scan['Close'].ewm(span=200, adjust=False).mean().fillna(0)
                    df_scan = add_supertrend(df_scan)
                    scan_pattern = detect_candlestick_pattern(df_scan)
                    features_scan = ['EMA_9', 'EMA_21', 'RSI', 'BB_Upper', 'BB_Lower', 'BB_Width', 'Returns', 'ATR', 'FVG_Bull', 'FVG_Bear', 'MACD', 'Signal_Line', 'VWAP_Dist', 'ST_DIR', 'EMA_200', 'StochRSI_K', 'StochRSI_D']
                    df_train_scan = df_scan.dropna()
                    
                    if len(df_train_scan) >= 20:
                        last_market_state_scan = df_scan[features_scan].iloc[[-1]].copy()
                        X_s, y_s = df_train_scan[features_scan], df_train_scan['Target']
                        split_s = int(0.85 * len(df_train_scan))
                        model_s = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=3, random_state=42)
                        model_s.fit(X_s[:split_s], y_s[:split_s])
                        prediction_s, probability_s = model_s.predict(last_market_state_scan)[0], model_s.predict_proba(last_market_state_scan)[0]
                        ai_confidence_s = max(probability_s) * 100
                        last_ema9_s, last_ema21_s, last_macd_s, last_rsi_s = float(last_market_state_scan['EMA_9'].iloc[0]), float(last_market_state_scan['EMA_21'].iloc[0]), float(last_market_state_scan['MACD'].iloc[0]), float(last_market_state_scan['RSI'].iloc[0])
                        
                        confluence_pass_s = True
                        if "Aggressive" in strategy_mode_scan:
                            min_conf_s = 50.1 
                            if prediction_s == 1 and last_rsi_s > 80: confluence_pass_s = False
                            elif prediction_s == 0 and last_rsi_s < 20: confluence_pass_s = False
                        else:
                            min_conf_s = 60.0
                            if prediction_s == 1:
                                if scan_category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)" and fng_value >= 80: confluence_pass_s = False
                                elif (last_ema9_s < last_ema21_s) and (last_macd_s < 0) and not (last_rsi_s < 45 and ("Hammer" in scan_pattern or "Bullish" in scan_pattern)): confluence_pass_s = False
                            else:
                                if scan_category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)" and fng_value <= 20: confluence_pass_s = False
                                elif (last_ema9_s > last_ema21_s) and (last_macd_s > 0) and not (last_rsi_s > 55 and ("Shooting Star" in scan_pattern or "Bearish" in scan_pattern)): confluence_pass_s = False
                                    
                        if ai_confidence_s >= min_conf_s and confluence_pass_s:
                            dir_str, dir_text = ("🟢 BUY", "BUY") if prediction_s == 1 else ("🔴 SELL", "SELL")
                            try: current_price_s = float(yf.Ticker(ticker_to_scan).fast_info['lastPrice'])
                            except Exception: current_price_s = float(df_scan['Close'].iloc[-1])
                                
                            atr_val_s = float(df_scan['ATR'].iloc[-1])
                            pullback_amount_s = atr_val_s * 0.3  
                            if prediction_s == 1: 
                                entry_price_s = current_price_s - pullback_amount_s 
                                tp1_price_s, tp2_price_s, tp3_price_s = entry_price_s + (atr_val_s * 1.5), entry_price_s + (atr_val_s * 3.0), entry_price_s + (atr_val_s * 5.0)
                                sl_price_s = entry_price_s - (atr_val_s * 2.0) 
                            else: 
                                entry_price_s = current_price_s + pullback_amount_s 
                                tp1_price_s, tp2_price_s, tp3_price_s = entry_price_s - (atr_val_s * 1.5), entry_price_s - (atr_val_s * 3.0), entry_price_s - (atr_val_s * 5.0)
                                sl_price_s = entry_price_s + (atr_val_s * 2.0)
                                
                            clean_symbol = ticker_to_scan.replace('-USD', 'USDT') if scan_category == "🔥 ජනප්‍රිය ක්‍රිප්ටෝ (Crypto)" else ticker_to_scan.replace('=X', '') if scan_category == "💱 ෆොරෙක්ස් (Forex)" else ticker_to_scan.replace('=F', '')
                            st.session_state.scan_results.append({"Coin": coin_name, "Ticker": ticker_to_scan, "Clean_Symbol": clean_symbol, "Direction_Label": dir_str, "Direction": dir_text, "Confidence": ai_confidence_s, "Pattern": scan_pattern, "Entry": entry_price_s, "TP1": tp1_price_s, "TP2": tp2_price_s, "TP3": tp3_price_s, "SL": sl_price_s, "TF": st.session_state.scan_tf, "Category": scan_category, "Strategy_Mode": strategy_mode_scan, "Chart_DF": df_scan.tail(120).copy()})
                            
                            if st.session_state.scan_results:
                                df_show = pd.DataFrame(st.session_state.scan_results)[['Coin', 'Direction_Label', 'Confidence', 'Pattern']]
                                df_show.columns, df_show['Confidence'] = ['Coin / Pair', 'Direction', 'Confidence', 'Pattern'], df_show['Confidence'].apply(lambda x: f"{x:.1f}%")
                                results_placeholder.table(df_show) 
            except Exception: pass
            progress_bar.progress((i + 1) / total_coins)
            
        st.session_state.scanning = False
        st.session_state.last_scan_empty = len(st.session_state.scan_results) == 0
        st.rerun()

    if not st.session_state.get('scanning', False):
        if st.session_state.get('scan_results'):
            st.success(f"🎉 Valid Signals {len(st.session_state.scan_results)} ක් සොයාගන්නා ලදී!")
            df_show = pd.DataFrame(st.session_state.scan_results)[['Coin', 'Direction_Label', 'Confidence', 'Pattern']]
            df_show.columns, df_show['Confidence'] = ['Coin / Pair', 'Direction', 'Confidence', 'Pattern'], df_show['Confidence'].apply(lambda x: f"{x:.1f}%" if isinstance(x, float) else x)
            st.table(df_show)
            
            st.write("---")
            st.write("### ⚙️ Scanner Actions")
            options = [f"{s['Coin']} - {s['Direction_Label']} ({s['Confidence']:.1f}%)" for s in st.session_state.scan_results]
            select_all = st.checkbox("සියල්ල තෝරන්න (Select All)")
            selected_opts = st.multiselect("Signals තෝරන්න:", options, default=options if select_all else None)
            
            if st.button("💾 Save Selected to My History", use_container_width=True):
                if not selected_opts: st.warning("⚠️ කරුණාකර Save කිරීමට සිග්නල් තෝරන්න.")
                else:
                    for opt in selected_opts:
                        idx = options.index(opt)
                        sel_s = st.session_state.scan_results[idx]
                        date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                        try:
                            chart_image_bytes = generate_candlestick_image_bytes(sel_s['Chart_DF'], sel_s['Clean_Symbol'], sel_s['Direction'], sel_s['Entry'], sel_s['TP1'], sel_s['TP2'], sel_s['TP3'], sel_s['SL'], sel_s['TF'], sel_s['Pattern'])
                            chart_b64 = base64.b64encode(chart_image_bytes).decode('utf-8')
                        except: chart_b64 = ""
                        data_to_save = {"Date": date_str, "Ticker": sel_s['Ticker'], "Coin": sel_s['Coin'].split()[0], "Category": sel_s['Category'], "Strategy": sel_s['Strategy_Mode'], "Direction": sel_s['Direction'], "Entry": sel_s['Entry'], "TP1": sel_s['TP1'], "TP2": sel_s['TP2'], "TP3": sel_s['TP3'], "SL": sel_s['SL'], "Status": "⏳ Pending Entry", "created_by": user_info['email'], "TF": sel_s['TF'], "Pattern": sel_s['Pattern'], "chart_base64": chart_b64}
                        save_to_supabase(data_to_save)
                    st.success("✅ තෝරාගත් Signals සාර්ථකව ප්‍රස්ථාර සමග ඔබගේ History එකට සේව් වුණා!")

            if user_info['role'] in ["Owner", "Admin"]:
                if st.button("🚀 Broadcast Selected to Telegram", type="primary", use_container_width=True):
                    if not selected_opts: st.warning("⚠️ කරුණාකර යැවීමට සිග්නල් තෝරන්න.")
                    else:
                        for opt in selected_opts:
                            idx = options.index(opt)
                            sel_s = st.session_state.scan_results[idx]
                            dp = 8 if sel_s['Entry'] < 0.01 else 4
                            dir_text_full = "🟢 BUY / LONG 📈 ⬆️" if sel_s['Direction'] == 'BUY' else "🔴 SELL / SHORT 📉 ⬇️"
                            cat_tag = "Crypto 🪙" if "Crypto" in sel_s['Category'] else "Forex 💱" if "Forex" in sel_s['Category'] else "Commodities ✨"
                            telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n🏦 *Market:* {cat_tag}\n⚙️ *Strategy Mode:* {sel_s['Strategy_Mode']}\n🪙 *Coin/Pair:* {sel_s['Coin']}\n⏱ *Timeframe:* {sel_s['TF']}\n🔥 *Direction:* {dir_text_full}\n🧩 *Detected Pattern:* {sel_s['Pattern']}\n\n🔵 *Entry Price:* `${sel_s['Entry']:.{dp}f}`\n🎯 *TP 1:* `${sel_s['TP1']:.{dp}f}`\n🎯 *TP 2:* `${sel_s['TP2']:.{dp}f}`\n🎯 *TP 3:* `${sel_s['TP3']:.{dp}f}`\n🛑 *Stop Loss (SL):* `${sel_s['SL']:.{dp}f}`\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            with st.spinner(f"⏳ {sel_s['Coin']} යවමින් පවතී..."):
                                try:
                                    chart_image_bytes = generate_candlestick_image_bytes(sel_s['Chart_DF'], sel_s['Clean_Symbol'], sel_s['Direction'], sel_s['Entry'], sel_s['TP1'], sel_s['TP2'], sel_s['TP3'], sel_s['SL'], sel_s['TF'], sel_s['Pattern'])
                                    success = send_telegram_photo_bytes(telegram_text, chart_image_bytes)
                                    if not success: success = send_telegram_message(telegram_text)
                                except: success = send_telegram_message(telegram_text)
                            if success:
                                chart_b64 = base64.b64encode(chart_image_bytes).decode('utf-8') if 'chart_image_bytes' in locals() else ""
                                date_str = pd.Timestamp.utcnow().tz_convert('Asia/Colombo').strftime('%Y-%m-%d %H:%M')
                                data_to_save = {"Date": date_str, "Ticker": sel_s['Ticker'], "Coin": sel_s['Coin'].split()[0], "Category": cat_tag, "Strategy": sel_s['Strategy_Mode'], "Direction": sel_s['Direction'], "Entry": sel_s['Entry'], "TP1": sel_s['TP1'], "TP2": sel_s['TP2'], "TP3": sel_s['TP3'], "SL": sel_s['SL'], "Status": "⏳ Pending Entry", "created_by": user_info['email'], "TF": sel_s['TF'], "Pattern": sel_s['Pattern'], "chart_base64": chart_b64}
                                save_to_supabase(data_to_save)
                                st.success(f"✅ {sel_s['Coin']} සාර්ථකව Telegram යැව්වා!")
                            else: st.error(f"❌ {sel_s['Coin']} යැවීම අසාර්ථකයි.")
        elif st.session_state.get('last_scan_empty', False): st.warning(f"⚠️ ස්කෑන් කිරීම අවසන්! නමුත් මේ මොහොතේ {st.session_state.scan_tf} Timeframe එක සඳහා තෝරාගත් ප්‍රවර්ගයේ කිසිදු Coin එකක පැහැදිලි (Valid) Signal එකක් නොමැත. කරුණාකර වෙනත් Timeframe එකක් තෝරා නැවත උත්සාහ කරන්න.")
        else: st.info("අලුත් Signals සෙවීමට 'Start Scan' බොත්තම ඔබන්න.")

# --- Tab 3 & 4: Data Processing ---
display_df = pd.DataFrame()
history_df = get_from_supabase()

if not history_df.empty:
    if user_info['role'] not in ["Admin", "Owner", "Moderator"]:
        if 'created_by' in history_df.columns:
            history_df = history_df[history_df['created_by'] == user_info['email']]

if not history_df.empty:
    updated, live_prices_dict = False, {}
    with st.spinner('සජීවීව මාකට් එක පරීක්ෂා කරමින් පවතී... 🔍'):
        for index, row in history_df.iterrows():
            status_val = str(row['Status'])
            if "Cancelled" in status_val: live_prices_dict[index] = np.nan; continue
            try:
                entry_str = str(row['Entry']).replace('$', '').replace(',', '')
                if entry_str.isalpha() or entry_str == 'nan' or entry_str.strip() == '': live_prices_dict[index] = np.nan; continue
                current_live_price, current_low, current_high = None, None, None
                df_hist = yf.download(row['Ticker'], period="5d", interval="5m", progress=False)
                if not df_hist.empty:
                    if isinstance(df_hist.columns, pd.MultiIndex): df_hist.columns = df_hist.columns.get_level_values(0)
                    current_live_price, current_low, current_high = float(df_hist['Close'].dropna().iloc[-1]), float(df_hist['Low'].dropna().iloc[-1]), float(df_hist['High'].dropna().iloc[-1])
                else: current_live_price = current_low = current_high = float(yf.Ticker(row['Ticker']).fast_info['lastPrice'])
                    
                if current_live_price is not None:
                    live_prices_dict[index] = current_live_price
                    entry_val, tp1_val, tp2_val, tp3_val, sl_val = float(entry_str), float(str(row['TP1']).replace('$', '').replace(',', '')), float(str(row['TP2']).replace('$', '').replace(',', '')), float(str(row['TP3']).replace('$', '').replace(',', '')), float(str(row['SL']).replace('$', '').replace(',', ''))
                    new_status = status_val
                    
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
                                
                    if new_status != status_val: history_df.at[index, 'Status'] = new_status; update_supabase_status(row['Date'], row['Coin'], new_status); updated = True
                else: live_prices_dict[index] = np.nan
            except Exception: live_prices_dict[index] = np.nan
            
    display_df = history_df.copy()
    display_df['Live Price'] = display_df.index.map(live_prices_dict)
    
    def format_price(x):
        if pd.isnull(x): return "N/A"
        try: val = float(str(x).replace('$', '').replace(',', '')); return f"${val:.8f}" if val < 0.01 else f"${val:.4f}"
        except: return str(x)

    for col in ['Entry', 'TP1', 'TP2', 'TP3', 'SL', 'Live Price']: display_df[col] = display_df[col].apply(format_price)
    if 'Ticker' in display_df.columns: display_df.drop(columns=['Ticker'], inplace=True)
    if 'id' in display_df.columns: display_df.drop(columns=['id'], inplace=True)

with tab3:
    st.subheader("📂 ගත්තු Signals වල History එක සහ Live Price")
    st.write("මාකට් එකේ සජීවී මිල මෙහි යාවත්කාලීන වේ. TP 1, 2, හෝ 3 Hit වූ විට Status එක Auto වෙනස් වෙනවා!")
    auto_refresh = st.checkbox("🔄 Auto Refresh (සෑම තත්පර 15කට වරක් යාවත්කාලීන වීමට මෙහි ටික් එකක් දාන්න)")

    if not display_df.empty:
        html_style = "<style>.trading-history-container{overflow-x:auto;margin:10px 0;border-radius:8px;border:1px solid #31333f;}.trading-table{width:100%;border-collapse:collapse;background-color:#0e1117;color:#ffffff;font-size:13px;text-align:center;}.trading-table th{background-color:#1f2937;color:#ff4b4b;padding:12px 8px;border:1px solid #31333f;font-weight:bold;}.trading-table td{padding:10px 6px;border:1px solid #31333f;white-space:nowrap;}.marquee-container{width:95px;overflow:hidden;margin:0 auto;white-space:nowrap;}.marquee-scroll{display:inline-block;animation:marqueeEffect 6s linear infinite;}@keyframes marqueeEffect{0%{transform:translate(10%, 0);}50%{transform:translate(-100%, 0);}100%{transform:translate(10%, 0);}} .corrupt-row td {color: #ff4b4b;}</style>"
        html_table = html_style + "<div class='trading-history-container'><table class='trading-table'><tr><th>#</th><th>Date</th><th>Trader</th><th>Coin</th><th>Direction</th><th>Entry</th><th>TP1</th><th>TP2</th><th>TP3</th><th>SL</th><th>Status</th><th>Live Price</th></tr>"
        for idx, row in display_df.iterrows():
            trader = str(row.get('created_by', 'Admin')).split('@')[0]
            status_text = str(row['Status'])
            status_td = f"<td><div class='marquee-container'><div class='marquee-scroll'>{status_text}</div></div></td>" if "Pending Entry" in status_text else f"<td>{status_text}</td>"
            html_table += f"<tr><td>{idx}</td><td>{row['Date']}</td><td style='color:#ffeb3b;'><b>{trader}</b></td><td>{row['Coin']}</td><td>{row['Direction']}</td><td>{row['Entry']}</td><td>{row['TP1']}</td><td>{row['TP2']}</td><td>{row['TP3']}</td><td>{row['SL']}</td>{status_td}<td style='color:#00ffcc; font-weight:bold;'>{row['Live Price']}</td></tr>"
        html_table += "</table></div>"
        st.markdown(html_table, unsafe_allow_html=True)
        
        chart_df = history_df[history_df.get('chart_base64', pd.Series(dtype=object)).notna() & (history_df.get('chart_base64', '') != "")]
        if not chart_df.empty:
            st.write("---")
            st.subheader("🖼️ Saved Charts (ප්‍රස්ථාර බලන්න)")
            c_options = [f"{row['Date']} | {row['Coin']} | {row['Direction']}" for _, row in chart_df.iterrows()]
            selected_c = st.selectbox("ප්‍රස්ථාරය බැලීමට Signal එක තෝරන්න:", c_options)
            if selected_c:
                sel_row_c = chart_df.iloc[c_options.index(selected_c)]
                try:
                    img_bytes = base64.b64decode(sel_row_c['chart_base64'])
                    st.image(img_bytes, caption=f"Saved Setup for {sel_row_c['Coin']} - {sel_row_c['Direction']} ({sel_row_c['Date']})", use_container_width=True)
                except: st.error("ප්‍රස්ථාරය පෙන්වීමේ දෝෂයක්.")

        if user_info['role'] in ["Admin", "Owner", "Moderator"]:
            st.write("---")
            st.subheader("📢 Result එක Telegram යවන්න")
            completed_signals = history_df[history_df['Status'].str.contains("Pending|HIT|Active|Missed|Invalid", na=False, case=False)]
            
            if not completed_signals.empty:
                options = [f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})" for index, row in completed_signals.iterrows()]
                selected_sig = st.selectbox("Update කරන්න අවශ්‍ය Signal එක තෝරන්න:", options)
                if selected_sig:
                    selected_idx = options.index(selected_sig)
                    sel_row = completed_signals.iloc[selected_idx]
                    dir_text_with_icons = "🟢 BUY / LONG 📈 ⬆️" if sel_row['Direction'] == 'BUY' else "🔴 SELL / SHORT 📉 ⬇️"
                    cat_val, strat_val = sel_row.get('Category', 'Crypto 🪙'), sel_row.get('Strategy', 'N/A')
                    
                    st.markdown(f"**Selected:** {sel_row['Coin']} ({sel_row['Direction']})")
                    if st.button("🚀 Initial Signal එක Telegram යවන්න (ප්‍රස්ථාරය සමග)", type="primary"):
                        tf_val, pattern_val = sel_row.get('TF', 'N/A'), sel_row.get('Pattern', 'N/A')
                        dp_val = 8 if float(str(sel_row['Entry']).replace('$', '').replace(',', '')) < 0.01 else 4
                        entry_v, tp1_v, tp2_v, tp3_v, sl_v = [float(str(sel_row[k]).replace('$', '').replace(',', '')) for k in ['Entry', 'TP1', 'TP2', 'TP3', 'SL']]
                        telegram_text = f"🚨 *PRO AI TRADING SIGNAL* 🚨\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Asset:* {sel_row['Coin']}\n⏱ *Timeframe:* {tf_val}\n🔥 *Direction:* {dir_text_with_icons}\n🧩 *Detected Pattern:* {pattern_val}\n\n🔵 *Entry Price:* `${entry_v:.{dp_val}f}`\n🎯 *TP 1:* `${tp1_v:.{dp_val}f}`\n🎯 *TP 2:* `${tp2_v:.{dp_val}f}`\n🎯 *TP 3:* `${tp3_v:.{dp_val}f}`\n🛑 *Stop Loss (SL):* `${sl_v:.{dp_val}f}`\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                        
                        success = False
                        if pd.notna(sel_row.get('chart_base64')) and sel_row['chart_base64'] != "":
                            try: success = send_telegram_photo_bytes(telegram_text, base64.b64decode(sel_row['chart_base64']))
                            except: pass
                        if not success: success = send_telegram_message(telegram_text)
                        if success: st.success("✅ Initial Signal එක සාර්ථකව Telegram යැව්වා!")
                        else: st.error("❌ යැවීම අසාර්ථකයි.")
                    
                    st.write("---")
                    
                    if "Pending" in sel_row['Status']:
                        entry_val = float(str(sel_row['Entry']).replace('$', '').replace(',', ''))
                        dp_val = 8 if entry_val < 0.01 else 4
                        col_pend1, col_pend2 = st.columns(2)
                        with col_pend1:
                            if st.button("⏳ Pending Alert මැසේජ් එක යවන්න"):
                                msg = f"⏳ *TRADE SETUP READY (PENDING)* ⏳\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n🔵 *Entry Point:* `${entry_val:.{dp_val}f}`\n\nමාකට් එක අපේ Entry Point එකට එනකන් අපි බලාගෙන ඉන්නවා. Limit Order එක දාලා තියාගන්න! 🚀\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                                if send_telegram_message(msg): st.success("⏳ Pending Alert මැසේජ් එක සාර්ථකව යැව්වා!")
                        with col_pend2:
                            if st.button("🚫 Signal එක Cancel කරන්න"):
                                msg = f"🚫 *SIGNAL CANCELLED* 🚫\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමේ Setup එක දැන් අවලංගු (Invalid) නිසා අපි මේ සිග්නල් එක Cancel කරනවා. ❌\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                                if send_telegram_message(msg): update_supabase_status(sel_row['Date'], sel_row['Coin'], "🚫 Cancelled"); st.success("🚫 Cancel මැසේජ් එක යැව්වා! Database අප්ඩේට් විය."); time.sleep(1); st.rerun()

                    elif "Missed (Hit TP)" in sel_row['Status']:
                        if st.button("⚠️ Missed Setup මැසේජ් එක යවන්න"):
                            msg = f"⚠️ *MISSED TRADE (HIT TP)* ⚠️\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nඅපේ Analysis එක 100% ක් නිවැරදියි! නමුත් මාකට් එක අපේ Entry එකට එන්නේ නැතුව කෙලින්ම Target (TP) එකට ගියා. Setup එක සම්පූර්ණයි, ඒ නිසා Limit Order එක අයින් කරගන්න. 🔥\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg): update_supabase_status(sel_row['Date'], sel_row['Coin'], "🚫 Cancelled"); st.success("⚠️ Missed Setup මැසේජ් එක සාර්ථකව යැව්වා!"); time.sleep(1); st.rerun()

                    elif "Invalid (Hit SL)" in sel_row['Status']:
                        if st.button("🚫 Invalid Setup මැසේජ් එක යවන්න"):
                            msg = f"🚫 *SETUP INVALID (HIT SL)* 🚫\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමාකට් එක අපේ Entry Point එකට කලින්ම Stop Loss (SL) මට්ටම කඩාගෙන ගියා. Market Structure එක වෙනස් වුණු නිසා මේ Setup එක දැන් අවලංගුයි. ❌\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg): update_supabase_status(sel_row['Date'], sel_row['Coin'], "🚫 Cancelled"); st.success("🚫 Setup Invalid මැසේජ් එක සාර්ථකව යැව්වා!"); time.sleep(1); st.rerun()
                                
                    elif "Active" in sel_row['Status']:
                        entry_val = float(str(sel_row['Entry']).replace('$', '').replace(',', ''))
                        dp_val = 8 if entry_val < 0.01 else 4
                        if st.button("🟢 Active Alert මැසේජ් එක යවන්න"):
                            msg = f"🟢 *TRADE IS NOW ACTIVE!* 🚀\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n🔵 *Entry Triggered:* `${entry_val:.{dp_val}f}`\n\nමාකට් එක අපේ Entry ලෙවල් එකට ආවා! අපේ ට්‍රේඩ් එක දැන් පටන් ගත්තා (Running). Let's go! 🔥\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg): st.success("🟢 Active Alert මැසේජ් එක සාර්ථකව යැව්වා!")
                    
                    elif "TP" in sel_row['Status']:
                        hit_level = sel_row['Status'].split()[1]
                        tp1_v, tp2_v, tp3_v = float(str(sel_row['TP1']).replace('$', '').replace(',', '')), float(str(sel_row['TP2']).replace('$', '').replace(',', '')), float(str(sel_row['TP3']).replace('$', '').replace(',', ''))
                        dp_1, dp_2, dp_3 = 8 if tp1_v < 0.01 else 4, 8 if tp2_v < 0.01 else 4, 8 if tp3_v < 0.01 else 4
                        if hit_level == "TP1": tp_msg_part = f"🥇 🎯 *TP1 Reached:* `${tp1_v:.{dp_1}f}` ✅"
                        elif hit_level == "TP2": tp_msg_part = f"🥇 🎯 *TP1 Reached:* `${tp1_v:.{dp_1}f}` ✅\n🥈 🎯 *TP2 Reached:* `${tp2_v:.{dp_2}f}` ✅"
                        elif hit_level == "TP3": tp_msg_part = f"🥇 🎯 *TP1 Reached:* `${tp1_v:.{dp_1}f}` ✅\n🥈 🎯 *TP2 Reached:* `${tp2_v:.{dp_2}f}` ✅\n🥉 🎯 *TP3 Reached:* `${tp3_v:.{dp_3}f}` ✅\n\nALL 🎯TARGET 💯% COMPLETE 🏆️🎖️🎉️"
                        else: tp_msg_part = f"🎯 *Target Reached*"

                        if st.button(f"✅ {hit_level} Profit මැසේජ් එක යවන්න"):
                            msg = f"✅ *PROFIT TARGET HIT!* 🎉\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\n{tp_msg_part}\n\n🤑 _💯PRO💥VIP⚡SIGNALS🛜 100% සාර්ථකයි!_"
                            if send_telegram_message(msg): st.success(f"✅ {hit_level} Profit මැසේජ් එක යැව්වා!")
                    
                    elif "SL" in sel_row['Status']:
                        if st.button("🛑 Loss මැසේජ් එක යවන්න"):
                            msg = f"🛑 *STOP LOSS HIT* 📉\n\n🏦 *Market:* {cat_val}\n⚙️ *Strategy Mode:* {strat_val}\n🪙 *Coin/Pair:* {sel_row['Coin']}\n🔥 *Direction:* {dir_text_with_icons}\n\nමාකට් එක වෙනස් වුණා. Risk Management අනුගමනය කරන්න. ඊළඟ Trade එකෙන් අපි අල්ලමු! 💪\n\n💎 _Exclusive Signal by_ 💯PRO💥VIP⚡SIGNALS🛜"
                            if send_telegram_message(msg): st.success("🛑 Stop Loss මැසේජ් එක යැව්වා!")
            else: st.info("තවම Active, Pending, TP, SL හෝ Invalid වුණු සිග්නල් නැත.")

        st.write("---")
        st.subheader("🗑️ History කළමනාකරණය (Database එකෙන් මැකීම)")
        all_delete_options = [f"{row['Date']} | {row['Coin']} | {row['Direction']} ({row['Status']})" for index, row in history_df.iterrows()]
        selected_to_delete = st.multiselect("මකා දැමීමට අවශ්‍ය සිග්නල් තෝරන්න:", all_delete_options)
        
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            if st.button("🗑️ තෝරාගත් ඒවා පමණක් මකන්න"):
                if selected_to_delete:
                    for item in selected_to_delete:
                        date_str_del, coin_str_del = item.split(" | ")[0], item.split(" | ")[1]
                        delete_from_supabase(date_str_del, coin_str_del, user_info['email'], user_info['role'])
                    st.success("✅ තෝරාගත් සිග්නල් Database එකෙන් මකා දැමුවා!"); time.sleep(1); st.rerun()
                else: st.warning("⚠️ මකා දැමීමට කිසිවක් තෝරා නැත.")
                    
        with col_del2:
            if st.button("🚨 මගේ History ඔක්කොම මකන්න (Clear All)"):
                clear_all_supabase(user_info['email'], user_info['role'])
                st.success("✅ Database History එක මකා දැමුවා!"); time.sleep(1); st.rerun()
            
        if auto_refresh: time.sleep(15); st.rerun()
    else: st.info("දැනට Database එකේ කිසිම Signal එකක් Save වෙලා නෑ.")

with tab4:
    st.subheader("💼 VIP Auto Demo Trading Account (Simulated)")
    st.write("ඔබ ලබාගන්නා සියලුම AI Signals ස්වයංක්‍රීයව මෙම $10,000 ක අතත්‍ය ගිණුමේ Trade වේ.")

    if not display_df.empty:
        INITIAL_BALANCE, RISK_AMOUNT = 10000.0, 100.0 
        realized_pnl, floating_pnl = 0.0, 0.0
        active_trades_list, closed_trades_list = [], []
        
        for idx, row in display_df.iterrows():
            status = str(row['Status'])
            if "Pending" in status or "Cancelled" in status or "Invalid" in status or "Missed" in status or "Corrupt" in status: continue
            try:
                entry, sl, tp3 = float(str(row['Entry']).replace('$', '').replace(',', '')), float(str(row['SL']).replace('$', '').replace(',', '')), float(str(row['TP3']).replace('$', '').replace(',', ''))
                live_price_str = str(row['Live Price']).replace('$', '').replace(',', '').replace('N/A', '0')
                live_price = float(live_price_str) if live_price_str != '0' else entry
                direction, sl_dist = row['Direction'], abs(entry - sl)
                units = RISK_AMOUNT / sl_dist if sl_dist > 0 else 0
                
                if "SL HIT" in status:
                    realized_pnl += -RISK_AMOUNT; closed_trades_list.append({"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Status": "🛑 SL Hit", "P&L": f"-${RISK_AMOUNT:.2f}"})
                elif "TP3 HIT" in status:
                    pnl = units * abs(tp3 - entry); realized_pnl += pnl; closed_trades_list.append({"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Status": "✅ TP3 Hit (Closed)", "P&L": f"+${pnl:.2f}"})
                else:
                    cur_pnl = units * (live_price - entry) if direction == 'BUY' else units * (entry - live_price)
                    floating_pnl += cur_pnl; pnl_str = f"+${cur_pnl:.2f}" if cur_pnl >= 0 else f"-${abs(cur_pnl):.2f}"
                    active_trades_list.append({"Date": row['Date'], "Coin": row['Coin'], "Type": direction, "Entry": f"${entry:.4f}", "Live Price": f"${live_price:.4f}", "Status": status, "Floating P&L": pnl_str})
            except Exception: continue

        current_balance, equity = INITIAL_BALANCE + realized_pnl, (INITIAL_BALANCE + realized_pnl) + floating_pnl
        st.write("### 🏦 ගිණුමේ සාරාංශය (Account Summary)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("💰 Balance", f"${current_balance:,.2f}"); col_m2.metric("📊 Equity", f"${equity:,.2f}", f"{floating_pnl:,.2f} Floating")
        col_m3.metric("🟢 Active Trades", len(active_trades_list)); col_m4.metric("📁 Closed Trades", len(closed_trades_list))
        
        st.write("---"); st.write("### 🟢 Active Positions (ක්‍රියාත්මක වන Trades)")
        if active_trades_list: st.dataframe(pd.DataFrame(active_trades_list), use_container_width=True)
        else: st.info("දැනට Active Trades කිසිවක් නොමැත.")
            
        st.write("---"); st.write("### 📁 Trade History (අවසන් කළ Trades)")
        if closed_trades_list: st.dataframe(pd.DataFrame(closed_trades_list), use_container_width=True)
        else: st.info("තවම Trade කිසිවක් Close වී නොමැත.")
    else: st.info("ඔබ තවමත් Signals කිසිවක් ලබාගෙන නැත.")
