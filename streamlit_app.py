import csv
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo  # חדש: בשביל שעון ישראל

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
SHEET_ID = st.secrets.get("SHEET_ID", "1HBi9K4Sh06Xqw1TmHQSL0w2MQVbgfRbTyvMSspYTYf4")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds_dict = st.secrets["google_service_account"]
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

def save_master_dataframe(new_row: dict) -> None:
    df_master = load_csv_safely(CSV_FILE)
    df_master = pd.concat([df_master, pd.DataFrame([new_row])], ignore_index=True)

    tmp = CSV_FILE.with_suffix(".tmp.csv")
    df_master.to_csv(
        tmp, index=False, encoding="utf-8-sig",
        quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n"
    )
    tmp.replace(CSV_FILE)

    # ✅ שמות גיבוי לפי שעון ישראל
    ts = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"שאלון_שיבוץ_{ts}.csv"
    df_master.to_csv(
        backup_path, index=False, encoding="utf-8-sig",
        quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n"
    )

    # שמירה גם ל־Google Sheets
    if sheet:
        try:
            if len(sheet.get_all_values()) == 0:
                sheet.append_row(list(new_row.keys()))
            sheet.append_row(list(new_row.values()))
        except Exception as e:
            st.error(f"❌ לא ניתן לשמור ב־Google Sheets: {e}")

def append_to_log(row_df: pd.DataFrame) -> None:
    file_exists = CSV_LOG_FILE.exists()
    row_df.to_csv(CSV_LOG_FILE, mode="a", header=not file_exists,
                  index=False, encoding="utf-8-sig",
                  quoting=csv.QUOTE_MINIMAL, escapechar="\\", lineterminator="\n")

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
          if errors:
        show_errors(errors)
    else:
        # מפות דירוג לשמירה
        site_to_rank = {s: None for s in SITES}
        for i in range(1, RANK_COUNT + 1):
            site = st.session_state.get(f"rank_{i}")
            site_to_rank[site] = i

        # ✅ בניית שורה לשמירה עם זמן ישראל
        row = {
            "תאריך_שליחה": datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S"),
            "שם_פרטי": first_name.strip(),
            "שם_משפחה": last_name.strip(),
            "תעודת_זהות": nat_id.strip(),
            "מין": gender,
            "שיוך_חברתי": social_affil,
            "שפת_אם": (other_mt.strip() if mother_tongue == "אחר..." else mother_tongue),
            "שפות_נוספות": "; ".join([x for x in extra_langs if x != "אחר..."] +
                                     ([extra_langs_other.strip()] if "אחר..." in extra_langs else [])),
            "טלפון": phone.strip(),
            "כתובת": address.strip(),
            "אימייל": email.strip(),
            "שנת_לימודים": (study_year_other.strip() if study_year == "אחר..." else study_year),
            "מסלול_לימודים": track.strip(),
            "ניידות": (mobility_other.strip() if mobility == "אחר..." else mobility),
            "הכשרה_קודמת": prev_training,
            "הכשרה_קודמת_מקום_ותחום": prev_place.strip(),
            "הכשרה_קודמת_מדריך_ומיקום": prev_mentor.strip(),
            "הכשרה_קודמת_בן_זוג": prev_partner.strip(),
            "תחומים_מועדפים": "; ".join([d for d in chosen_domains if d != "אחר..."] +
                                       ([domains_other.strip()] if "אחר..." in chosen_domains else [])),
            "תחום_מוביל": (top_domain if top_domain and top_domain != "— בחר/י —" else ""),
            "בקשה_מיוחדת": special_request.strip(),
            "ממוצע": avg_grade,
            "התאמות": "; ".join([a for a in adjustments if a != "אחר..."] +
                                ([adjustments_other.strip()] if "אחר..." in adjustments else [])),
            "התאמות_פרטים": adjustments_details.strip(),
            "מוטיבציה_1": m1,
            "מוטיבציה_2": m2,
            "מוטיבציה_3": m3,
        }

        # הוספת שדות דירוג
        for i in range(1, RANK_COUNT + 1):
            row[f"דירוג_מדרגה_{i}_מוסד"] = st.session_state.get(f"rank_{i}")
        for s in SITES:
            row[f"דירוג_{s}"] = site_to_rank[s]

        # ✅ שמירה
        try:
            save_master_dataframe(row)
            append_to_log(pd.DataFrame([row]))
            st.success("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
        except Exception as e:
            st.error(f"❌ שמירה נכשלה: {e}")


