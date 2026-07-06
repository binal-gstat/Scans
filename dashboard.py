import streamlit as st
import pandas as pd
from datetime import date, timedelta
import json
import gspread
from google.oauth2.service_account import Credentials

# ====== חובה — פקודת Streamlit ראשונה ======
st.set_page_config(page_title="דשבורד סריקת מסמכים", layout="wide", page_icon="📄")

# ====== הגדרות ======
TARGET = 2_000_000
END_DATE = date(2026, 12, 31)

# ====== חיבור ל-Google Sheets ======
SHEET_ID = "1bXuXqZ4VLHR0bdBNveTENPK23a91LzzHlSKUqP1O0ZM"

# קורא credentials מ-secrets
if "gcp_service_account" in st.secrets:
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
else:
    st.error("❌ חסר מפתח Google — פנה למנהל המערכת")
    st.stop()

@st.cache_data(ttl=30, show_spinner=False)
def load_data():
    """טוען נתונים מ-Google Sheets"""
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    ws = sheet.sheet1
    rows = ws.get_all_records()

    if rows:
        df = pd.DataFrame(rows)
        df["תאריך"] = pd.to_datetime(df["תאריך"]).dt.date
    else:
        df = pd.DataFrame(columns=["תאריך", "נסרק היום", 'סה"כ נסרק'])

    return df


def save_new_row(scanned_today, last_total):
    """מוסיף שורה חדשה לגיליון"""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).sheet1
    today_str = date.today().isoformat()
    new_total = last_total + scanned_today
    ws.append_row([today_str, scanned_today, new_total])
    return True


def delete_last_row():
    """מוחק את השורה האחרונה"""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).sheet1
    all_rows = ws.get_all_values()
    if len(all_rows) > 1:  # יש יותר מכותרת
        ws.delete_rows(len(all_rows))
    return True


def reset_all():
    """מאפס את כל הנתונים חוץ מהכותרת"""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).sheet1
    all_rows = ws.get_all_values()
    if len(all_rows) > 1:
        ws.delete_rows(2, len(all_rows))
    return True


# ====== סיסמה ======
#APP_PASSWORD = st.secrets.get("APP_PASSWORD", "ganzach2424")

# ====== עמוד כניסה ======
#if "authenticated" not in st.session_state:
#    st.session_state.authenticated = False

#if not st.session_state.authenticated:
#    st.markdown("<h1 style='text-align: center;'>🔐 דשבורד סריקת מסמכים</h1>", unsafe_allow_html=True)
#    st.markdown("<br>", unsafe_allow_html=True)

#    col1, col2, col3 = st.columns([1, 1, 1])
#    with col2:
#        password_input = st.text_input("הכנס סיסמה", type="password", label_visibility="collapsed", placeholder="סיסמה")
#        if st.button("🔓 כניסה", use_container_width=True):
#            if password_input == APP_PASSWORD:
#                st.session_state.authenticated = True
#                st.rerun()
#            else:
#                st.error("❌ סיסמה שגויה")
#    st.stop()

# ====== תצוגה ראשית ======

st.title("📄 דשבורד סריקת מסמכים")
st.markdown("---")

# ====== טעינת נתונים ======
df = load_data()

# ====== סרגל צד ======
with st.sidebar:
    st.header("📥 הכנסת נתונים")
    scanned_today = st.number_input("מסמכים שנסרקו היום", min_value=0, step=1, value=0)

    if st.button("📤 עדכן נתונים", use_container_width=True):
        last_total = df['סה"כ נסרק'].iloc[-1] if len(df) > 0 else 0
        today = date.today()

        if len(df) > 0 and today in df["תאריך"].values:
            st.warning("⚠️ כבר הוכנסו נתונים להיום")
        elif scanned_today == 0:
            st.warning("⚠️ אנא הכנס מספר מסמכים")
        else:
            save_new_row(scanned_today, last_total)
            load_data.clear()  # מנקה cache
            st.success(f"✅ עודכנו {scanned_today:,} מסמכים")
            st.rerun()

    st.markdown("---")
    st.header("⚙️ ניהול נתונים")

    if len(df) > 0:
        last_date = df["תאריך"].iloc[-1]
        if st.button(f"🗑️ מחק יום אחרון ({last_date})", use_container_width=True):
            delete_last_row()
            load_data.clear()
            st.success(f"נמחק התאריך {last_date}")
            st.rerun()

    if st.button("🔄 אפס את כל הנתונים", use_container_width=True):
        reset_all()
        load_data.clear()
        st.success("כל הנתונים נמחקו")
        st.rerun()

    st.markdown("---")
    if st.button("🚪 יציאה", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ====== חישובי KPI ======
total_scanned = df['סה"כ נסרק'].iloc[-1] if len(df) > 0 else 0
percent_of_target = total_scanned / TARGET
target_85 = TARGET * 0.85
remaining_to_85 = max(target_85 - total_scanned, 0)
remaining_to_100 = max(TARGET - total_scanned, 0)
days_left = (END_DATE - date.today()).days
required_per_day = int(remaining_to_85 / days_left) if days_left > 0 else 0

# ====== KPI ======
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("📊 סה\"כ נסרק", f"{total_scanned:,}")

with col2:
    st.metric("🎯 אחוז מהיעד", f"{percent_of_target:.2%}")

with col3:
    st.metric("📋 נותר ל-85%", f"{int(remaining_to_85):,}")

with col4:
    st.metric("📋 נותר ל-100%", f"{int(remaining_to_100):,}")

with col5:
    st.metric("📅 ימים נותרו", days_left)

with col6:
    st.metric("⚡ דרישה יומית", f"{required_per_day:,}")

# ====== הודעת חגיגה ======
if total_scanned >= TARGET:
    st.balloons()
    st.success("🎉🎉🎉 **מזל טוב! הגעתם ל-100% מהיעד!** 🎉🎉🎉")
    st.markdown(
        "<h1 style='text-align: center; color: green; font-size: 48px;'>"
        "🎉 100% — היעד הושג במלואו! 🎉</h1>",
        unsafe_allow_html=True
    )
elif total_scanned >= target_85:
    st.balloons()
    st.success(f"🎉🎉 **מזל טוב! הגעתם ל-{percent_of_target:.1%} מהיעד!** 🎉🎉")
    st.markdown(
        f"<h1 style='text-align: center; color: green; font-size: 48px;'>"
        f"🎉 {percent_of_target:.1%} מהיעד הושג! 🎉</h1>",
        unsafe_allow_html=True
    )

st.markdown("---")

# ====== גרפים ======
if len(df) > 0:
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📈 התקדמות מצטברת")
        chart_df = df.set_index("תאריך")
        st.line_chart(
            chart_df['סה"כ נסרק'],
            use_container_width=True,
            height=400
        )
        st.caption(f"▬ 85% = {int(target_85):,} | ▬ 100% = {TARGET:,}")

    with col_chart2:
        st.subheader("📊 סריקות יומיות")
        st.bar_chart(
            chart_df["נסרק היום"],
            use_container_width=True,
            height=400
        )
        st.caption(f"דרישה יומית: {required_per_day:,}")

    with st.expander("📋 הצג נתונים מלאים"):
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("ℹ️ עדיין אין נתונים. הכניסו נתונים בסרגל הצד 👈")

st.markdown("---")
st.caption(f"יעד סופי: {TARGET:,} מסמכים | 85%: {int(target_85):,} | תאריך סיום: {END_DATE}")
