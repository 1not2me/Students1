import csv
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime
import pytz
import streamlit as st
import pandas as pd

# --- Google Sheets
import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    ConditionalFormatRule, BooleanRule, BooleanCondition,
    GridRange, format_cell_range, get_conditional_format_rules
)

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="שאלון לסטודנטים – תשפ״ו", layout="centered")
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
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&family=Noto+Sans+Hebrew:wght@400;600&display=swap" rel="stylesheet">

<style>
:root { --app-font: 'Assistant', 'Noto Sans Hebrew', 'Segoe UI', -apple-system, sans-serif; }
.stApp * { font-family: var(--app-font) !important; }
div[data-baseweb], .stTextInput input, .stTextArea textarea, .stSelectbox div, .stMultiSelect div, .stRadio, .stCheckbox, .stButton > button { font-family: var(--app-font) !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# נתיבים/סודות
# =========================
DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE = DATA_DIR / "שאלון_שיבוץ.csv"
CSV_LOG_FILE = DATA_DIR / "שאלון_שיבוץ_log.csv"
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")

query_params = st.query_params
is_admin_mode = query_params.get("admin", ["0"])[0] == "1"

# =========================
# Google Sheets הגדרות
# =========================
SHEET_ID = st.secrets.get("sheets", {}).get("spreadsheet_id")

sheet = None
if SHEET_ID and "gcp_service_account" in st.secrets:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gclient = gspread.authorize(creds)
        sheet = gclient.open_by_key(SHEET_ID).sheet1
    except Exception:
        pass 

# =========================
# קבועים לשימוש כללי
# =========================
SITES = [
    "כפר הילדים חורפיש", "אנוש כרמיאל", "הפוך על הפוך צפת", "שירות מבחן לנוער עכו", 
    "כלא חרמון", "בית חולים זיו", "שירותי רווחה קריית שמונה", "מרכז יום לגיל השלישי", 
    "מועדונית נוער בצפת", "מרפאת בריאות הנפש צפת",
]
RANK_COUNT = 3

COLUMNS_ORDER = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "תעודת זהות", "מין", "שיוך חברתי",
    "שפת אם", "שפות נוספות", "טלפון", "כתובת", "אימייל",
    "שנת לימודים", "מסלול לימודים",
    "הכשרה קודמת", "הכשרה קודמת מקום ותחום",
    "הכשרה קודמת מדריך ומיקום", "הכשרה קודמת בן זוג",
    "תחומים מועדפים", "תחום מוביל", "בקשה מיוחדת",
    "ממוצע", "התאמות", "התאמות פרטים",
    "מוטיבציה 1", "מוטיבציה 2", "מוטיבציה 3",
] + [f"מקום הכשרה {i}" for i in range(1, RANK_COUNT+1)] + [f"דירוג_{s}" for s in SITES] + [
    "אישור הגעה להכשרה"
]
likert = ["בכלל לא מסכים/ה","1","2","3","4","מסכים/ה מאוד"]

# =========================
# פונקציות עזר
# =========================
def style_google_sheet(ws):
    header_fmt = CellFormat(
        backgroundColor=Color(0.6, 0.4, 0.8), textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment='CENTER'
    )
    format_cell_range(ws, "1:1", header_fmt)
    rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range('A2:Z1000', ws)],
        booleanRule=BooleanRule(
            condition=BooleanCondition('CUSTOM_FORMULA', ['=ISEVEN(ROW())']),
            format=CellFormat(backgroundColor=Color(0.95, 0.95, 0.95))
        )
    )
    rules = get_conditional_format_rules(ws)
    rules.clear()
    rules.append(rule)
    rules.save()
    id_fmt = CellFormat(horizontalAlignment='CENTER', backgroundColor=Color(0.9, 0.9, 0.9))
    format_cell_range(ws, "C2:C1000", id_fmt)

def load_csv_safely(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    attempts = [dict(encoding="utf-8-sig"), dict(encoding="utf-8")]
    for kw in attempts:
        try:
            df = pd.read_csv(path, **kw)
            df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]
            return df
        except Exception: continue
    return pd.DataFrame()

def save_master_dataframe(new_row: dict) -> None:
    df_master = pd.DataFrame([new_row])
    if CSV_FILE.exists():
        df_master = pd.concat([load_csv_safely(CSV_FILE), df_master], ignore_index=True)
    df_master.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"שאלון_שיבוץ_{ts}.csv"
    df_master.to_csv(backup_path, index=False, encoding="utf-8-sig")

    if sheet:
        try:
            headers = sheet.row_values(1)
            if not headers or headers != COLUMNS_ORDER:
                sheet.clear()
                sheet.append_row(COLUMNS_ORDER, value_input_option="USER_ENTERED")
                style_google_sheet(sheet)
            row_values = [new_row.get(col, "") for col in COLUMNS_ORDER]
            sheet.append_row(row_values, value_input_option="USER_ENTERED")
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
def valid_id(v: str) -> bool:      return bool(re.match(r"^\d{8,9}$", v.strip()))

def show_errors(errors: list[str]):
    if not errors: return
    st.markdown("### :red[נמצאו שגיאות:]")
    for e in errors:
        st.markdown(f"- :red[{e}]")

# =========================
# מצב מנהל
# =========================
if is_admin_mode:
    # ... (קוד מצב מנהל - נשאר ללא שינוי מהותי) ...
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


# =======================================================
# *** תיקון קריטי: אתחול מאובטח של st.session_state ***
# =======================================================

STEPS = [
    "סעיף 1: פרטים אישיים", "סעיף 2: העדפת שיבוץ", "סעיף 3: נתונים אקדמיים", 
    "סעיף 4: התאמות", "סעיף 5: מוטיבציה", "סעיף 6: סיכום ושליחה"
]

def initialize_session_state():
    # 1. ניהול שלבים ואישורים
    if "step" not in st.session_state: st.session_state.step = 0
    if "acks" not in st.session_state: 
        st.session_state.acks = {i: False for i in range(len(STEPS)-1)}
        
    # 2. ערכי ברירת מחדל לכל השדות (כדי למנוע איפוס ל-None)
    default_values = {
        "first_name": "", "last_name": "", "nat_id": "", "phone": "", 
        "address": "", "email": "", "other_mt": "", "extra_langs_other": "",
        "study_year_other": "", "prev_place": "", "prev_mentor": "", 
        "prev_partner": "", "domains_other": "", "special_request": "",
        "avg_grade": 0.0, "adjustments_other": "", "adjustments_details": "",
        # ברירות מחדל לרכיבי בחירה
        "gender": "זכר", "social_affil": "יהודי/ה", "mother_tongue": "עברית",
        "study_year": "תואר ראשון - שנה א", "track": "תואר ראשון – תוכנית רגילה",
        "prev_training": "לא", "chosen_domains": [], "top_domain": "— בחר/י —",
        "adjustments": ["אין"],
        "m1": likert[5], "m2": likert[5], "m3": likert[5],
        "arrival_confirm": False, "confirm": False,
    }
    
    for key, default_val in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default_val

    # 3. אתחול שדות דירוג
    for i in range(1, RANK_COUNT + 1):
        if f"rank_{i}" not in st.session_state:
            st.session_state[f"rank_{i}"] = "— בחר/י —"

initialize_session_state()

# =========================
# טופס — מנוע שלבים
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("מלאו/מלאי את כל הסעיפים. השדות המסומנים ב-* הינם חובה.")

def goto(i: int):
    st.session_state.step = int(i)

def prev_next():
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.session_state.step > 0:
            st.button("➡ חזרה", on_click=goto, args=(st.session_state.step - 1,), use_container_width=True)
    with c2:
        st.markdown(f"<div style='text-align:center;color:#64748b'>שלב {st.session_state.step+1} מתוך {len(STEPS)}</div>", unsafe_allow_html=True)
    with c3:
        if st.session_state.step < len(STEPS) - 1:
            disabled = not st.session_state.acks.get(st.session_state.step, True) if st.session_state.step <= 4 else False
            st.button("הבא ⬅", on_click=goto, args=(st.session_state.step + 1,), disabled=disabled, use_container_width=True)

step = st.session_state.step
st.subheader(STEPS[step])


# ===== שלב 1: פרטים אישיים =====
if step == 0:
    st.text_input("שם פרטי *", key="first_name", value=st.session_state.first_name)
    st.text_input("שם משפחה *", key="last_name", value=st.session_state.last_name)
    st.text_input("מספר תעודת זהות *", key="nat_id", value=st.session_state.nat_id)

    gender_options = ["זכר","נקבה"]
    st.radio("מין *", gender_options, horizontal=True, key="gender", index=gender_options.index(st.session_state.gender))
    
    social_options = ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"]
    st.selectbox("שיוך חברתי *", social_options, key="social_affil", index=social_options.index(st.session_state.social_affil))

    mt_options = ["עברית","ערבית","רוסית","אחר..."]
    st.selectbox("שפת אם *", mt_options, key="mother_tongue", index=mt_options.index(st.session_state.mother_tongue))

    if st.session_state.mother_tongue == "אחר...":
        st.text_input("ציין/ני שפת אם אחרת *", key="other_mt", value=st.session_state.other_mt)

    extra_langs_options = ["עברית","ערבית","רוסית","אמהרית","אנגלית","ספרדית","אחר..."]
    st.multiselect(
        "ציין/י שפות נוספות (ברמת שיחה) *",
        extra_langs_options,
        default=st.session_state.extra_langs,
        placeholder="בחר/י שפות נוספות", key="extra_langs"
    )
    if "אחר..." in st.session_state.extra_langs:
        st.text_input("ציין/י שפה נוספת (אחר) *", key="extra_langs_other", value=st.session_state.extra_langs_other)

    st.text_input("מספר טלפון נייד * (למשל 050-1234567)", key="phone", value=st.session_state.phone)
    st.text_input("כתובת מלאה (כולל יישוב) *", key="address", value=st.session_state.address)
    st.text_input("כתובת דוא״ל *", key="email", value=st.session_state.email)

    study_year_options = [
        "תואר ראשון - שנה א", "תואר ראשון - שנה ב", "תואר ראשון - שנה ג'",
        "תואר שני - שנה א'", "תואר שני - שנה ב", "אחר"
    ]
    st.selectbox("שנת הלימודים *", study_year_options, key="study_year", index=study_year_options.index(st.session_state.study_year))
    if st.session_state.study_year == "אחר":
        st.text_input("פרט/י שנת לימודים *", key="study_year_other", value=st.session_state.study_year_other)

    track_options = [
        "תואר ראשון – תוכנית רגילה", "תואר ראשון – הסבה", "תואר שני"
    ]
    st.selectbox("מסלול הלימודים / תואר *", track_options, key="track", index=track_options.index(st.session_state.track))

    st.markdown("---")
    st.session_state.acks[0] = st.checkbox("אני מצהיר/ה כי מילאתי פרטים אישיים באופן מדויק. *", 
                                          key="ack_0", 
                                          value=st.session_state.acks.get(0, False))
    prev_next()

# ===== שלב 2: העדפת שיבוץ =====
if step == 1:
    prev_training_options = ["כן","לא","אחר..."]
    st.selectbox("האם עברת הכשרה מעשית בשנה קודמת? *", prev_training_options, 
                 key="prev_training", index=prev_training_options.index(st.session_state.prev_training))
    
    if st.session_state.prev_training in ["כן","אחר..."]:
        st.text_input("אם כן, נא ציין שם מקום ותחום ההתמחות *", key="prev_place", value=st.session_state.prev_place)
        st.text_input("שם המדריך והמיקום הגיאוגרפי של ההכשרה *", key="prev_mentor", value=st.session_state.prev_mentor)
        st.text_input("מי היה/תה בן/בת הזוג להתמחות בשנה הקודמת? *", key="prev_partner", value=st.session_state.prev_partner)

    all_domains = ["רווחה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש",
                   "שיקום","משפחה","נשים","בריאות","קהילה","אחר..."]
    st.multiselect("בחרו עד 3 תחומים *", all_domains, max_selections=3,
                   default=st.session_state.chosen_domains,
                   placeholder="בחר/י עד שלושה תחומים", key="chosen_domains")

    if "אחר..." in st.session_state.chosen_domains:
        st.text_input("פרט/י תחום אחר *", key="domains_other", value=st.session_state.domains_other)

    # יצירת רשימת אפשרויות ל-top_domain בהתבסס על הבחירה הנוכחית
    top_domain_options = ["— בחר/י —"]
    for d in st.session_state.chosen_domains:
        if d != "אחר...":
            top_domain_options.append(d)
    if "אחר..." in st.session_state.chosen_domains and st.session_state.domains_other.strip():
        top_domain_options.append(st.session_state.domains_other.strip())
        
    top_domain_index = top_domain_options.index(st.session_state.top_domain) if st.session_state.top_domain in top_domain_options else 0
        
    st.selectbox(
        "מה התחום הכי מועדף עליך, מבין שלושתם? *",
        options=top_domain_options,
        index=top_domain_index,
        key="top_domain"
    )

    st.markdown("<div style='font-weight:700; font-size:1rem; color:#0f172a;'>הדירוג אינו מחייב את מורי השיטות.</div>", unsafe_allow_html=True)
    st.markdown("**בחר/י מוסד לכל מקום הכשרה (1 = הכי רוצים, 3 = הכי פחות). הבחירה כובלת קדימה — מוסדות שנבחרו ייעלמו מהבחירות הבאות.**")

    # פונקציה לבחירת אתרים פנויים
    def options_for_rank(rank_i: int) -> list:
        current = st.session_state[f"rank_{rank_i}"]
        chosen_before = {st.session_state[f"rank_{j}"] for j in range(1, rank_i) if st.session_state[f"rank_{j}"] != "— בחר/י —"}
        base = ["— בחר/י —"] + [s for s in SITES if (s not in chosen_before or s == current)]
        return base

    cols = st.columns(2)
    for i in range(1, RANK_COUNT + 1):
        with cols[(i - 1) % 2]:
            opts = options_for_rank(i)
            current = st.session_state[f"rank_{i}"]
            
            index = opts.index(current) if current in opts else 0
            
            st.selectbox(
                f"מקום הכשרה {i} (בחר/י מוסד) *",
                options=opts,
                index=index,
                key=f"rank_{i}"
            )
            
    st.text_area("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות? *", 
                 height=100, 
                 key="special_request", 
                 value=st.session_state.special_request)

    st.markdown("---")
    st.session_state.acks[1] = st.checkbox("אני מצהיר/ה כי העדפתי הוזנו במלואן. *", 
                                          key="ack_1", 
                                          value=st.session_state.acks.get(1, False))
    prev_next()

# ===== שלב 3: נתונים אקדמיים =====
if step == 2:
    st.number_input("ממוצע ציונים *", 
                    min_value=0.0, max_value=100.0, step=0.1, 
                    key="avg_grade", 
                    value=st.session_state.avg_grade)
    st.markdown("---")
    st.session_state.acks[2] = st.checkbox("אני מצהיר/ה כי הממוצע שהזנתי נכון. *", 
                                          key="ack_2", 
                                          value=st.session_state.acks.get(2, False))
    prev_next()

# ===== שלב 4: התאמות =====
if step == 3:
    adjustment_options = ["אין","הריון","מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)",
                         "רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)",
                         "אלרגיה חמורה","נכות",
                         "רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)","אחר..."]
    st.multiselect(
        "סוגי התאמות (ניתן לבחור כמה) *",
        adjustment_options,
        default=st.session_state.adjustments,
        placeholder="בחר/י אפשרויות התאמה", key="adjustments"
    )
    if "אחר..." in st.session_state.adjustments:
        st.text_input("פרט/י התאמה אחרת *", key="adjustments_other", value=st.session_state.adjustments_other)
    
    # הצגת פירוט התאמות רק אם נבחרה התאמה שאינה "אין" בלבד
    has_specific_adjustment = any(a not in ["אין"] for a in st.session_state.adjustments)
    if has_specific_adjustment:
        st.text_area("פרט: *", 
                     height=100, 
                     key="adjustments_details", 
                     value=st.session_state.adjustments_details)
    else:
        # אם אין התאמות ספציפיות, מאפסים את הפירוט (כדי שלא ישפיע על ולידציה)
        st.session_state["adjustments_details"] = ""


    st.markdown("---")
    st.session_state.acks[3] = st.checkbox("אני מצהיר/ה כי מסרתי מידע מדויק על התאמות. *", 
                                          key="ack_3", 
                                          value=st.session_state.acks.get(3, False))
    prev_next()


# ===== שלב 5: מוטיבציה =====
if step == 4:
    
    st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert, horizontal=True, 
             key="m1", index=likert.index(st.session_state.m1))
    st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert, horizontal=True, 
             key="m2", index=likert.index(st.session_state.m2))
    st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert, horizontal=True, 
             key="m3", index=likert.index(st.session_state.m3))

    st.markdown("---")
    st.session_state.acks[4] = st.checkbox("אני מצהיר/ה כי עניתי בכנות על שאלות המוטיבציה. *", 
                                          key="ack_4", 
                                          value=st.session_state.acks.get(4, False))
    prev_next()

# ===== שלב 6: סיכום ושליחה =====
submitted = False
if step == 5:
    st.markdown("בדקו את התקציר. אם יש טעות – חזרו לשלבים המתאימים עם הכפתורים למעלה, תקנו וחזרו לכאן. לאחר אישור ולחיצה על **שליחה** המידע יישמר.")

    # מיפוי מקום הכשרה->מוסד + מוסד->דירוג
    rank_to_site = {i: st.session_state[f"rank_{i}"] for i in range(1, RANK_COUNT + 1)}

    st.markdown("### 📍 העדפות שיבוץ (1=הכי רוצים)")
    summary_pairs = [f"{rank_to_site[i]} – {i}" if rank_to_site[i] != "— בחר/י —" else f"(לא נבחר) – {i}"
                     for i in range(1, RANK_COUNT + 1)]
    st.table(pd.DataFrame({"דירוג": summary_pairs}))

    st.markdown("### 🧑‍💻 פרטים אישיים")
    # חישוב שדות מורכבים להצגה
    mt_display = st.session_state.other_mt if st.session_state.mother_tongue == "אחר..." else st.session_state.mother_tongue
    el_list = [x for x in st.session_state.extra_langs if x != "אחר..."]
    if "אחר..." in st.session_state.extra_langs and st.session_state.extra_langs_other: el_list.append(st.session_state.extra_langs_other)
    el_display = "; ".join(el_list)
    sy_display = st.session_state.study_year_other if st.session_state.study_year == "אחר" else st.session_state.study_year
    
    st.table(pd.DataFrame([{
        "שם פרטי": st.session_state.first_name, "שם משפחה": st.session_state.last_name, "ת״ז": st.session_state.nat_id, "מין": st.session_state.gender,
        "שפת אם": mt_display, "שפות נוספות": el_display, "טלפון": st.session_state.phone, 
        "שנת לימודים": sy_display, "מסלול לימודים": st.session_state.track,
    }]).T.rename(columns={0: "ערך"}))

    st.markdown("---")
    
    # חשוב: שומר את המצב הנוכחי של הצ'קבוקסים מיד ל-session_state
    arrival_confirm = st.checkbox("אני מצהיר/ה שאגיע בכל דרך להכשרה המעשית שתיקבע לי. *", 
                                  key="arrival_confirm", 
                                  value=st.session_state.arrival_confirm)
    
    confirm = st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *", 
                          key="confirm", 
                          value=st.session_state.confirm)
    
    submitted = st.button("שליחה ✉️")


# ===== ולידציה ושמירה =====
if submitted:
    errors = []
    
    # ... (הבדיקות האחרות שלך נשארות) ...
    # סעיף 1 — פרטים אישיים
    if not st.session_state.first_name.strip(): errors.append("סעיף 1: יש למלא שם פרטי.")
    if not st.session_state.last_name.strip(): errors.append("סעיף 1: יש למלא שם משפחה.")
    if not valid_id(st.session_state.nat_id): errors.append("סעיף 1: ת״ז חייבת להיות 8–9 ספרות.")
    if not valid_phone(st.session_state.phone): errors.append("סעיף 1: מספר טלפון אינו תקין.")
    if not valid_email(st.session_state.email): errors.append("סעיף 1: כתובת דוא״ל אינה תקינה.")
    if st.session_state.mother_tongue == "אחר..." and not st.session_state.other_mt.strip(): errors.append("סעיף 1: יש לציין שפת אם (אחר).")
    
    # סעיף 2 — העדפת שיבוץ
    rank_to_site_final = {i: st.session_state[f"rank_{i}"] for i in range(1, RANK_COUNT + 1)}
    missing = [i for i, s in rank_to_site_final.items() if s == "— בחר/י —"]
    if missing: errors.append(f"סעיף 2: יש לבחור מוסד לכל מקום הכשרה. חסר/ים: {', '.join(map(str, missing))}.")
    chosen_sites = [s for s in rank_to_site_final.values() if s != "— בחר/י —"]
    if len(set(chosen_sites)) != len(chosen_sites): errors.append("סעיף 2: קיימת כפילות בבחירת מוסדות.")
    if not st.session_state.special_request.strip(): errors.append("סעיף 2: יש לציין בקשה מיוחדת (אפשר 'אין').")

    # סעיף 3 — נתונים אקדמיים
    if st.session_state.avg_grade is None or st.session_state.avg_grade <= 0: errors.append("סעיף 3: יש להזין ממוצע ציונים גדול מ-0.")

    # סעיף 4 — התאמות
    has_specific_adjustment = any(a not in ["אין"] for a in st.session_state.adjustments)
    if has_specific_adjustment and not st.session_state.adjustments_details.strip(): errors.append("סעיף 4: יש לפרט התייחסות להתאמות שנבחרו.")
    if "אחר..." in st.session_state.adjustments and not st.session_state.adjustments_other.strip(): errors.append("סעיף 4: נבחר 'אחר' – יש לפרט התאמה.")

    # סעיף 6 — הצהרות
    if not st.session_state.arrival_confirm: errors.append("סעיף 6: יש לסמן את ההצהרה על הגעה להכשרה.")
    if not st.session_state.confirm: errors.append("סעיף 6: יש לאשר את הצהרת הדיוק וההתאמה.")

    if errors:
        show_errors(errors)
    else:
        # עיבוד סופי לשמירה (משתמש בנתונים שכבר נמצאים ב-session_state)
        site_to_rank_final = {s: None for s in SITES}
        for i, site in rank_to_site_final.items():
            if site and site != "— בחר/י —": site_to_rank_final[site] = i

        # עיבוד שדות מרובי בחירה לפני שמירה
        extra_langs_proc = [x for x in st.session_state.extra_langs if x != "אחר..."]
        if "אחר..." in st.session_state.extra_langs and st.session_state.extra_langs_other.strip():
            extra_langs_proc.append(st.session_state.extra_langs_other.strip())

        chosen_domains_proc = [d for d in st.session_state.chosen_domains if d != "אחר..."]
        if "אחר..." in st.session_state.chosen_domains and st.session_state.domains_other.strip():
            chosen_domains_proc.append(st.session_state.domains_other.strip())

        adjustments_proc = [a for a in st.session_state.adjustments if a != "אחר..."]
        if "אחר..." in st.session_state.adjustments and st.session_state.adjustments_other.strip():
            adjustments_proc.append(st.session_state.adjustments_other.strip())

        tz = pytz.timezone("Asia/Jerusalem")

        row = {
            "תאריך שליחה": datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S"),
            "שם פרטי": st.session_state.first_name.strip(),
            "שם משפחה": st.session_state.last_name.strip(),
            "תעודת זהות": st.session_state.nat_id.strip(),
            "מין": st.session_state.gender, "שיוך חברתי": st.session_state.social_affil,
            "שפת אם": (st.session_state.other_mt.strip() if st.session_state.mother_tongue == "אחר..." else st.session_state.mother_tongue),
            "שפות נוספות": "; ".join(extra_langs_proc),
            "טלפון": st.session_state.phone.strip(), "כתובת": st.session_state.address.strip(), "אימייל": st.session_state.email.strip(),
            "שנת לימודים": (st.session_state.study_year_other.strip() if st.session_state.study_year == "אחר" else st.session_state.study_year),
            "מסלול לימודים": st.session_state.track.strip(),
            "הכשרה קודמת": st.session_state.prev_training,
            "הכשרה קודמת מקום ותחום": st.session_state.prev_place.strip(),
            "הכשרה קודמת מדריך ומיקום": st.session_state.prev_mentor.strip(),
            "הכשרה קודמת בן זוג": st.session_state.prev_partner.strip(),
            "תחומים מועדפים": "; ".join(chosen_domains_proc),
            "תחום מוביל": (st.session_state.top_domain if st.session_state.top_domain and st.session_state.top_domain != "— בחר/י —" else ""),
            "בקשה מיוחדת": st.session_state.special_request.strip(),
            "ממוצע": st.session_state.avg_grade,
            "התאמות": "; ".join(adjustments_proc),
            "התאמות פרטים": st.session_state.adjustments_details.strip(),
            "מוטיבציה 1": st.session_state.m1, "מוטיבציה 2": st.session_state.m2, "מוטיבציה 3": st.session_state.m3,
            "אישור הגעה להכשרה": "כן" if st.session_state.arrival_confirm else "לא",
        }

        for i in range(1, RANK_COUNT + 1):
            row[f"מקום הכשרה {i}"] = st.session_state[f"rank_{i}"]
        for s in SITES:
            rank_value = site_to_rank_final.get(s)
            row[f"דירוג_{s}"] = rank_value if isinstance(rank_value, int) else ""

        try:
            save_master_dataframe(row)
            append_to_log(pd.DataFrame([row]))
            
            # מעבר למסך סיום
            st.session_state.clear()
            st.session_state.step = 6

            st.rerun() # הפעלה מחדש כדי לעבור למצב "נשלח"
        except Exception as e:
            st.error(f"❌ שמירה נכשלה: {e}")

# אם נשלח בהצלחה, מציג הודעת סיום (רק אם step=6)
if st.session_state.get("step") == 6:
    st.title("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
    st.balloons()
    st.markdown("---")
    st.info("כדי לשלוח טופס חדש, אנא רענן/י את הדף.")
