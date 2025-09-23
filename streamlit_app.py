# streamlit_app.py
# -*- coding: utf-8 -*-
import csv
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# --- Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="שאלון לסטודנטים – תשפ״ו", layout="centered")

# ====== עיצוב — לפי ה-CSS שביקשת ======
st.markdown("""
<style>
:root{
  --ink:#0f172a; 
  --muted:#475569; 
  --ring:rgba(99,102,241,.25); 
  --card:rgba(255,255,255,.85);
}
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top:1.1rem; }
[data-testid="stForm"]{
  background:var(--card);
  border:1px solid #e2e8f0;
  border-radius:16px;
  padding:18px 20px;
  box-shadow:0 8px 24px rgba(2,6,23,.06);
}
[data-testid="stWidgetLabel"] p{ text-align:right; margin-bottom:.25rem; color:var(--muted); }
[data-testid="stWidgetLabel"] p::after{ content: " :"; }
input, textarea, select{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

# =========================
# נתיבים/סודות + התמדה ארוכת טווח
# =========================
DATA_DIR   = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE      = DATA_DIR / "שאלון_שיבוץ.csv"
CSV_LOG_FILE  = DATA_DIR / "שאלון_שיבוץ_log.csv"
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")

query_params = st.query_params
is_admin_mode = query_params.get("admin", ["0"])[0] == "1"

# =========================
# Google Sheets הגדרות
# =========================
SHEET_ID = st.secrets["sheets"]["spreadsheet_id"]

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gclient = gspread.authorize(creds)
    sheet = gclient.open_by_key(SHEET_ID).sheet1
except Exception as e:
    sheet = None
    st.error(f"⚠ לא ניתן להתחבר ל־Google Sheets: {e}")

# =========================
# פונקציות עזר
# =========================
def load_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    attempts = [
        dict(encoding="utf-8-sig"),
        dict(encoding="utf-8"),
        dict(encoding="utf-8-sig", engine="python", on_bad_lines="skip"),
        dict(encoding="utf-8", engine="python", on_bad_lines="skip"),
        dict(encoding="latin-1", engine="python", on_bad_lines="skip"),
    ]
    for kw in attempts:
        try:
            df = pd.read_csv(path, **kw)
            df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
            return df
        except Exception:
            continue
    return pd.DataFrame()

def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "Sheet1") -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name=sheet, index=False)
        ws = w.sheets[sheet]
        for i, col in enumerate(df.columns):
            width = 12
            if not df.empty:
                width = min(60, max(12, int(df[col].astype(str).map(len).max()) + 4))
            ws.set_column(i, i, width)
    bio.seek(0)
    return bio.read()

def valid_email(v: str) -> bool:  return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))
def valid_phone(v: str) -> bool:  return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))
def valid_id(v: str) -> bool:     return bool(re.match(r"^\d{8,9}$", v.strip()))

def show_errors(errors: list[str]):
    if not errors: return
    st.markdown("### :red[נמצאו שגיאות:]")
    for e in errors:
        st.markdown(f"- :red[{e}]")

# =========================
# עמודות קבועות (כולל דירוגים)
# =========================
SITES = [
    "כפר הילדים חורפיש",
    "אנוש כרמיאל",
    "הפוך על הפוך צפת",
    "שירות מבחן לנוער עכו",
    "כלא חרמון",
    "בית חולים זיו",
    "שירותי רווחה קריית שמונה",
    "מרכז יום לגיל השלישי",
    "מועדונית נוער בצפת",
    "מרפאת בריאות הנפש צפת",
]
RANK_COUNT = 3

COLUMNS_ORDER = [
    "תאריך_שליחה", "שם_פרטי", "שם_משפחה", "תעודת_זהות", "מין", "שיוך_חברתי",
    "שפת_אם", "שפות_נוספות", "טלפון", "כתובת", "אימייל",
    "שנת_לימודים", "מסלול_לימודים", "ניידות",
    "הכשרה_קודמת", "הכשרה_קודמת_מקום_ותחום",
    "הכשרה_קודמת_מדריך_ומיקום", "הכשרה_קודמת_בן_זוג",
    "תחומים_מועדפים", "תחום_מוביל", "בקשה_מיוחדת",
    "ממוצע", "התאמות", "התאמות_פרטים",
    "מוטיבציה_1", "מוטיבציה_2", "מוטיבציה_3",
] + [f"דירוג_מדרגה_{i}_מוסד" for i in range(1, RANK_COUNT+1)] + [f"דירוג_{s}" for s in SITES]

# =========================
# פונקציה לשמירה (כולל כותרות קבועות)
# =========================
def save_master_dataframe(new_row: dict) -> None:
    # --- שמירה מקומית ---
    df_master = load_csv_safely(CSV_FILE)
    df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)

    df_master.to_csv(CSV_FILE, index=False, encoding="utf-8-sig",
                     quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"שאלון_שיבוץ_{ts}.csv"
    df_master.to_csv(backup_path, index=False, encoding="utf-8-sig",
                     quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n")

    # --- שמירה ל-Google Sheets ---
    if sheet:
        try:
            headers = sheet.row_values(1)
            if not headers or headers != COLUMNS_ORDER:
                sheet.clear()
                sheet.append_row(COLUMNS_ORDER, value_input_option="USER_ENTERED")

            row_values = [new_row.get(col, "") for col in COLUMNS_ORDER]
            sheet.append_row(row_values, value_input_option="USER_ENTERED")

        except Exception as e:
            st.error(f"❌ לא ניתן לשמור ב־Google Sheets: {e}")

def append_to_log(row_df: pd.DataFrame) -> None:
    file_exists = CSV_LOG_FILE.exists()
    row_df.to_csv(CSV_LOG_FILE, mode="a", header=not file_exists,
                  index=False, encoding="utf-8-sig",
                  quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n")
  # =========================
# מצב מנהל
# =========================
if is_admin_mode:
    st.title("🔑 גישת מנהל – צפייה והורדות (מאסטר + יומן)")
    pwd = st.text_input("סיסמת מנהל", type="password", key="admin_pwd_input")
    if pwd == ADMIN_PASSWORD:
        st.success("התחברת בהצלחה ✅")

        df_master = load_csv_safely(CSV_FILE)
        df_log    = load_csv_safely(CSV_LOG_FILE)

        st.subheader("📦 קובץ ראשי (מאסטר)")
        if not df_master.empty:
            st.dataframe(df_master, use_container_width=True)
            st.download_button(
                "⬇ הורד Excel – קובץ ראשי",
                data=df_to_excel_bytes(df_master, sheet="Master"),
                file_name="שאלון_שיבוץ_master.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("אין עדיין נתונים בקובץ הראשי.")

        st.subheader("🧾 קובץ יומן (Append-Only)")
        if not df_log.empty:
            st.dataframe(df_log, use_container_width=True)
            st.download_button(
                "⬇ הורד Excel – קובץ יומן",
                data=df_to_excel_bytes(df_log, sheet="Log"),
                file_name="שאלון_שיבוץ_log.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("אין עדיין נתונים ביומן.")

    else:
        if pwd:
            st.error("סיסמה שגויה")
    st.stop()

# =========================
# טופס לסטודנטים – טאבים
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("מלאו/מלאי את כל הסעיפים. השדות המסומנים ב-* הינם חובה.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "סעיף 1: פרטים אישיים", "סעיף 2: העדפת שיבוץ",
    "סעיף 3: נתונים אקדמיים", "סעיף 4: התאמות",
    "סעיף 5: מוטיבציה", "סעיף 6: סיכום ושליחה"
])

# --- סעיף 1 ---
with tab1:
    st.subheader("פרטים אישיים")
    first_name = st.text_input("שם פרטי *")
    last_name  = st.text_input("שם משפחה *")
    nat_id     = st.text_input("תעודת זהות *")
    gender     = st.radio("מין *", ["זכר","נקבה"], horizontal=True)
    social_affil = st.selectbox("שיוך חברתי *", ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"])
    mother_tongue = st.selectbox("שפת אם *", ["עברית","ערבית","רוסית","אחר..."])
    other_mt = st.text_input("פרט/י שפה אחרת") if mother_tongue == "אחר..." else ""
    extra_langs = st.multiselect("שפות נוספות *", ["עברית","ערבית","רוסית","אנגלית","אמהרית","ספרדית","אחר..."])
    extra_langs_other = st.text_input("פרט/י שפה נוספת") if "אחר..." in extra_langs else ""
    phone   = st.text_input("טלפון נייד * (למשל 050-1234567)")
    address = st.text_input("כתובת מלאה *")
    email   = st.text_input("אימייל *")
    study_year = st.selectbox("שנת לימודים *", ["שנה א'","שנה ב'","שנה ג'","הסבה","אחר..."])
    study_year_other = st.text_input("פרט שנה/מסלול") if study_year == "אחר..." else ""
    track = st.text_input("מסלול לימודים *")
    mobility = st.selectbox("ניידות *", ["רכב","תחבורה ציבורית","אחר..."])
    mobility_other = st.text_input("פרט ניידות") if mobility == "אחר..." else ""

# --- סעיף 2 ---
with tab2:
    st.subheader("העדפות שיבוץ")
    prev_training = st.selectbox("האם עברת הכשרה קודמת? *", ["כן","לא"])
    prev_place = prev_mentor = prev_partner = ""
    if prev_training == "כן":
        prev_place  = st.text_input("מקום ותחום")
        prev_mentor = st.text_input("שם מדריך ומיקום")
        prev_partner= st.text_input("בן/בת זוג להכשרה")

    chosen_domains = st.multiselect("תחומים מועדפים (עד 3)", ["קהילה","בריאות","משפחה","ילדים","זקנה","נפש","שיקום","נשים","אחר..."], max_selections=3)
    domains_other = st.text_input("פרט תחום אחר") if "אחר..." in chosen_domains else ""
    top_domain = st.selectbox("תחום מוביל", ["—"] + chosen_domains if chosen_domains else ["—"])

    st.markdown("#### דירוג מוסדות (1=הכי רוצים, 3=פחות)")
    for i in range(1, RANK_COUNT+1):
        st.session_state.setdefault(f"rank_{i}", "—")
        st.session_state[f"rank_{i}"] = st.selectbox(
            f"מדרגה {i}", ["—"] + SITES, key=f"rank_{i}_select"
        )

    special_request = st.text_area("בקשות מיוחדות")

# --- סעיף 3 ---
with tab3:
    avg_grade = st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0, step=0.1)

# --- סעיף 4 ---
with tab4:
    adjustments = st.multiselect("התאמות *", ["הריון","מגבלה רפואית","רגישות למרחב רפואי","אלרגיה","נכות","רקע משפחתי","אחר..."])
    adjustments_other = st.text_input("פרט התאמה אחרת") if "אחר..." in adjustments else ""
    adjustments_details = st.text_area("פרטי התאמות")

# --- סעיף 5 ---
with tab5:
    likert = ["בכלל לא","1","2","3","4","מאוד"]
    m1 = st.radio("השקעה בהגעה למקום *", likert, horizontal=True)
    m2 = st.radio("חשיבות ההכשרה *", likert, horizontal=True)
    m3 = st.radio("מחויבות והתמדה *", likert, horizontal=True)

# --- סעיף 6 ---
with tab6:
    st.subheader("סיכום ושליחה")
    confirm = st.checkbox("אני מאשר/ת שהמידע נכון *")
    submitted = st.button("שליחה ✉️")

# =========================
# ולידציה + שמירה
# =========================
if submitted:
    errors = []
    if not first_name.strip(): errors.append("חסר שם פרטי")
    if not last_name.strip():  errors.append("חסר שם משפחה")
    if not valid_id(nat_id):   errors.append("תעודת זהות לא תקינה")
    if not valid_phone(phone): errors.append("טלפון לא תקין")
    if not valid_email(email): errors.append("אימייל לא תקין")
    if not confirm: errors.append("יש לאשר את ההצהרה")

    if errors:
        show_errors(errors)
    else:
        site_to_rank = {s: None for s in SITES}
        for i in range(1, RANK_COUNT+1):
            site = st.session_state.get(f"rank_{i}", "—")
            if site and site != "—":
                site_to_rank[site] = i

        row = {
            "תאריך_שליחה": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "שם_פרטי": first_name.strip(),
            "שם_משפחה": last_name.strip(),
            "תעודת_זהות": nat_id.strip(),
            "מין": gender,
            "שיוך_חברתי": social_affil,
            "שפת_אם": other_mt.strip() if mother_tongue=="אחר..." else mother_tongue,
            "שפות_נוספות": "; ".join(extra_langs + ([extra_langs_other] if "אחר..." in extra_langs else [])),
            "טלפון": phone.strip(),
            "כתובת": address.strip(),
            "אימייל": email.strip(),
            "שנת_לימודים": study_year_other if study_year=="אחר..." else study_year,
            "מסלול_לימודים": track.strip(),
            "ניידות": mobility_other if mobility=="אחר..." else mobility,
            "הכשרה_קודמת": prev_training,
            "הכשרה_קודמת_מקום_ותחום": prev_place.strip(),
            "הכשרה_קודמת_מדריך_ומיקום": prev_mentor.strip(),
            "הכשרה_קודמת_בן_זוג": prev_partner.strip(),
            "תחומים_מועדפים": "; ".join(chosen_domains + ([domains_other] if "אחר..." in chosen_domains else [])),
            "תחום_מוביל": top_domain if top_domain!="—" else "",
            "בקשה_מיוחדת": special_request.strip(),
            "ממוצע": avg_grade,
            "התאמות": "; ".join(adjustments + ([adjustments_other] if "אחר..." in adjustments else [])),
            "התאמות_פרטים": adjustments_details.strip(),
            "מוטיבציה_1": m1,
            "מוטיבציה_2": m2,
            "מוטיבציה_3": m3,
        }

        for i in range(1, RANK_COUNT+1):
            row[f"דירוג_מדרגה_{i}_מוסד"] = st.session_state.get(f"rank_{i}", "—")
        for s in SITES:
            row[f"דירוג_{s}"] = site_to_rank[s]

        try:
            save_master_dataframe(row)
            append_to_log(pd.DataFrame([row]))
            st.success("✅ הטופס נשלח ונשמר בהצלחה!")
        except Exception as e:
            st.error(f"שגיאת שמירה: {e}")

