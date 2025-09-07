import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from io import BytesIO
import re

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="שאלון שיבוץ סטודנטים – תשפ״ו", layout="centered")

# --- גופן David (כפי שביקשת) ---
st.markdown("""
<style>
/* ===== תיקון תיבות select/multiselect ב-RTL ===== */

/* הקונטיינר הפנימי של התיבה */
div[data-baseweb="select"] > div{
  height: 48px !important;
  background:#fff !important;
  border:1px solid rgba(15,23,42,.14) !important;
  border-radius: 14px !important;

  /* מרווחים לוגיים: ב-RTL ה-start = ימין, end = שמאל */
  padding-inline-start: .80rem !important;  /* ימין – טקסט לא נדבק לשוליים */
  padding-inline-end: 2.2rem !important;    /* שמאל – מקום לאיקון החץ */

  box-shadow: 0 3px 10px rgba(15,23,42,.04) !important;
  display:flex; align-items:center;
  overflow: visible !important;  /* שלא יחתוך תוכן פנימי */
}

/* טקסט/placeholder בתיבה – חד וברור */
div[data-baseweb="select"] [class*="SingleValue"],
div[data-baseweb="select"] [class*="ValueContainer"]{
  color:#0f172a !important;
  font-size:1rem !important;
  line-height:1.2 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
div[data-baseweb="select"] [class*="placeholder"]{
  color:#515151 !important;
  opacity:1 !important;
  font-size:.95rem !important;
}

/* שדה ה-input הפנימי (למצב חיפוש) */
div[data-baseweb="select"] input{
  color:#0f172a !important;
  text-align:right !important;
}

/* איקון החץ – שיהיה בצד שמאל + ניגודיות טובה */
div[data-baseweb="select"] svg{
  color:#333 !important;
  inset-inline-end: .65rem !important;  /* ב-RTL זה שמאל */
  inset-inline-start: auto !important;
}

/* רשימת האפשרויות – יישור לימין */
ul[role="listbox"]{
  direction: rtl !important;
  text-align: right !important;
}
ul[role="listbox"] [role="option"] > div{
  text-align:right !important;
}
</style>
""", unsafe_allow_html=True)

CSV_FILE = Path("שאלון_שיבוץ.csv")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")  # מומלץ לשמור בענן

# מצב מנהל ע"פ פרמטר ב־URL: ?admin=1 (streamlit>=1.32)
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# =========================
# פונקציות עזר
# =========================
def load_df(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path, encoding="utf-8-sig")

def append_row(row: dict, csv_path: Path):
    df_new = pd.DataFrame([row])
    header = not csv_path.exists()
    df_new.to_csv(csv_path, mode="a", index=False, encoding="utf-8-sig", header=header)

def _pick_excel_engine() -> str | None:
    """
    בוחרת מנוע לכתיבת Excel:
    - קודם כל מנסה xlsxwriter
    - אם לא קיים, מנסה openpyxl
    - אם אף אחד לא קיים, מחזירה None
    """
    try:
        import xlsxwriter  # noqa: F401
        return "xlsxwriter"
    except Exception:
        try:
            import openpyxl  # noqa: F401
            return "openpyxl"
        except Exception:
            return None

def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "תשובות") -> bytes:
    engine = _pick_excel_engine()
    if engine is None:
        # הודעת שגיאה ידידותית + הנחיות להתקנה
        st.error("לא נמצא מנוע לייצוא Excel. יש להוסיף לקובץ requirements.txt אחד מאלה: `xlsxwriter` או `openpyxl`.")
        return b""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine=engine) as w:
        df.to_excel(w, sheet_name=sheet, index=False)
        # התאמות רוחב עמודות (רק אם זה xlsxwriter – openpyxl לא תומך set_column)
        if engine == "xlsxwriter":
            ws = w.sheets[sheet]
            for i, col in enumerate(df.columns):
                width = min(60, max(12, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
                ws.set_column(i, i, width)
    buf.seek(0)
    return buf.read()

def valid_email(v: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))

def valid_phone(v: str) -> bool:
    return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))

def valid_id(v: str) -> bool:
    return bool(re.match(r"^\d{8,9}$", v.strip()))

def unique_ranks(ranks: dict) -> bool:
    seen = set()
    for _, v in ranks.items():
        if v is None or v == "דלג":
            continue
        if v in seen:
            return False
        seen.add(v)
    return True

# =========================
# עמוד מנהל – צפייה + הורדת Excel של כל הנתונים (ללא סינון)
# =========================
if is_admin_mode:
    st.title("🔑 גישת מנהל – צפייה והורדת Excel")
    pwd = st.text_input("סיסמת מנהל:", type="password",
                        help="מומלץ לשמור ADMIN_PASSWORD ב־st.secrets בענן.")
    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("התחברת בהצלחה ✅")
            df = load_df(CSV_FILE)
            if df.empty:
                st.info("אין עדיין נתונים בקובץ.")
            else:
                st.subheader("כל הנתונים")
                st.dataframe(df, use_container_width=True)
                excel_bytes = df_to_excel_bytes(df)
                if excel_bytes:
                    st.download_button(
                        "📥 הורדת אקסל (כל הנתונים)",
                        data=excel_bytes,
                        file_name="שאלון_שיבוץ_כל_הנתונים.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.error("סיסמה שגויה")
    st.stop()

# =========================
# אשף 6 סעיפים (עם אישור בין סעיפים)
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("התמיכה בקוראי מסך הופעלה.")

if "step" not in st.session_state:
    st.session_state.step = 1

def nav_buttons(show_back=True, proceed_label="המשך לסעיף הבא"):
    cols = st.columns([1,1])
    back_clicked, next_clicked = False, False
    with cols[0]:
        if show_back:
            back_clicked = st.button("⬅ חזרה", use_container_width=True)
    with cols[1]:
        next_clicked = st.button(proceed_label, use_container_width=True)
    return back_clicked, next_clicked

# --- סעיף 1: פרטים אישיים ---
if st.session_state.step == 1:
    st.subheader("סעיף 1 מתוך 6 – פרטים אישיים של הסטודנט/ית")
    st.write("""סטודנטים יקרים,
בשאלון להלן, אתם מתבקשים למלא את פרטיכם האישיים לצורך זיהוי, תקשורת והתאמה ראשונית לשיבוץ.
אנא מלאו את הפרטים בצורה מדויקת ועדכנית, שכן הם מהווים בסיס לכל שאר תהליך ההתאמה.
השאלון פונה בלשון זכר, אך מיועד לכל המגדרים. תודה על שיתוף הפעולה.""")

    first_name = st.text_input("שם פרטי *", key="first_name")
    last_name  = st.text_input("שם משפחה *", key="last_name")
    nat_id     = st.text_input("מספר תעודת זהות *", key="nat_id")

    gender = st.radio("מין *", ["זכר", "נקבה"], horizontal=True, key="gender")
    social_affil = st.selectbox("שיוך חברתי *", ["יהודי/ה", "מוסלמי/ת", "נוצרי/ה", "דרוזי/ת"], key="social_affil")

    mother_tongue = st.selectbox("שפת אם *", ["עברית", "ערבית", "רוסית", "אחר..."], key="mother_tongue")
    if mother_tongue == "אחר...":
        st.session_state.other_mt = st.text_input("ציין/י שפת אם אחרת *", key="other_mt")
    else:
        st.session_state.other_mt = ""

    extra_langs = st.multiselect(
        "ציין/י שפות נוספות (ברמת שיחה) *",
        ["עברית", "ערבית", "רוסית", "אמהרית", "אנגלית", "ספרדית", "אחר..."],
        placeholder="בחרי שפות נוספות", key="extra_langs"
    )
    if "אחר..." in extra_langs:
        st.session_state.extra_langs_other = st.text_input("ציין/י שפה נוספת (אחר) *", key="extra_langs_other")
    else:
        st.session_state.extra_langs_other = ""

    phone = st.text_input("מספר טלפון נייד * (למשל 050-1234567)", key="phone")
    address = st.text_input("כתובת מלאה (כולל יישוב) *", key="address")
    email   = st.text_input("כתובת דוא״ל *", key="email")

    study_year = st.selectbox("שנת הלימודים *", [
        "תואר ראשון - שנה א'", "תואר ראשון - שנה ב'", "תואר ראשון - שנה ג'",
        "הסבה א'", "הסבה ב'", "אחר..."
    ], key="study_year")
    if study_year == "אחר...":
        st.session_state.study_year_other = st.text_input("ציין/י שנה/מסלול אחר *", key="study_year_other")
    else:
        st.session_state.study_year_other = ""

    track = st.text_input("מסלול לימודים / תואר *", key="track")

    mobility = st.selectbox("אופן ההגעה להתמחות (ניידות) *", [
        "אוכל להיעזר ברכב / ברשותי רכב",
        "אוכל להגיע בתחבורה ציבורית",
        "אחר..."
    ], key="mobility")
    if mobility == "אחר...":
        st.session_state.mobility_other = st.text_input("פרט/י אחר לגבי ניידות *", key="mobility_other")
    else:
        st.session_state.mobility_other = ""

    confirm1 = st.checkbox("אני מאשר/ת את המידע בסעיף 1 ומעונ/ה להמשיך", key="confirm1")
    _, nxt = nav_buttons(show_back=False)

    if nxt:
        errors = []
        if not st.session_state.first_name.strip(): errors.append("יש למלא שם פרטי.")
        if not st.session_state.last_name.strip():  errors.append("יש למלא שם משפחה.")
        if not valid_id(st.session_state.nat_id):  errors.append("ת״ז חייבת להיות 8–9 ספרות.")
        if st.session_state.mother_tongue == "אחר..." and not st.session_state.other_mt.strip():
            errors.append("יש לציין שפת אם (אחר).")
        if (not st.session_state.extra_langs) or ("אחר..." in st.session_state.extra_langs and not st.session_state.extra_langs_other.strip()):
            errors.append("יש לבחור שפות נוספות (ואם נבחר 'אחר', לפרט).")
        if not valid_phone(st.session_state.phone): errors.append("מספר טלפון אינו תקין.")
        if not st.session_state.address.strip():    errors.append("יש למלא כתובת מלאה.")
        if not valid_email(st.session_state.email): errors.append("כתובת דוא״ל אינה תקינה.")
        if st.session_state.study_year == "אחר..." and not st.session_state.study_year_other.strip():
            errors.append("יש לפרט שנת לימודים (אחר).")
        if not st.session_state.track.strip(): errors.append("יש למלא מסלול לימודים/תואר.")
        if st.session_state.mobility == "אחר..." and not st.session_state.mobility_other.strip():
            errors.append("יש לפרט ניידות (אחר).")
        if not confirm1:
            errors.append("יש לאשר את סעיף 1 כדי להמשיך.")

        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            st.session_state.step = 2
            st.rerun()

# --- סעיף 2: העדפת שיבוץ ---
if st.session_state.step == 2:
    st.subheader("סעיף 2 מתוך 6 – העדפת שיבוץ")
    st.write("פרטים על שיבוץ קודם (אם היה) + בחירת עד 3 תחומים להעדפה השנה.")

    prev_training = st.selectbox("האם עברת הכשרה מעשית בשנה קודמת? *", ["כן", "לא", "אחר..."], key="prev_training")
    if prev_training in ["כן", "אחר..."]:
        st.session_state.prev_place  = st.text_input("אם כן, נא ציין שם מקום ותחום ההתמחות *", key="prev_place")
        st.session_state.prev_mentor = st.text_input("שם המדריך והמיקום הגיאוגרפי של ההכשרה *", key="prev_mentor")
        st.session_state.prev_partner = st.text_input("מי היה/תה בן/בת הזוג להתמחות בשנה הקודמת? *", key="prev_partner")
    else:
        st.session_state.prev_place = st.session_state.prev_mentor = st.session_state.prev_partner = ""

    all_domains = ["קהילה", "מוגבלות", "זקנה", "ילדים ונוער", "בריאות הנפש",
                   "שיקום", "משפחה", "נשים", "בריאות", "תָקוֹן", "אחר..."]
    chosen_domains = st.multiselect("בחרו עד 3 תחומים *", all_domains, max_selections=3,
                                    placeholder="בחרי עד שלושה תחומים", key="chosen_domains")
    if "אחר..." in chosen_domains:
        st.session_state.domains_other = st.text_input("פרט/י תחום אחר *", key="domains_other")
    else:
        st.session_state.domains_other = ""

    st.session_state.top_domain_select = st.selectbox(
        "מה התחום הכי מועדף עליך, מבין שלושתם? *",
        ["— בחר/י —"] + chosen_domains if chosen_domains else ["— בחר/י —"],
        key="top_domain_select"
    )

    st.markdown("**דרגו את העדפותיכם בין מקומות ההתמחות (1=מועדף ביותר, 10=פחות מועדף). אפשר לדלג.**")
    sites = ["בית חולים זיו", "שירותי רווחה קריית שמונה", "מרכז יום לגיל השלישי",
             "מועדונית נוער בצפת", "...", "6", "7", "8", "9", "10"]
    rank_options = ["דלג"] + [str(i) for i in range(1, 11)]
    ranks = {}
    cols = st.columns(2)
    for i, site in enumerate(sites):
        with cols[i % 2]:
            ranks[site] = st.selectbox(f"דירוג – {site}", rank_options, index=0, key=f"rank_{i}")

    st.session_state.special_request = st.text_area("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות? *", height=100, key="special_request")

    confirm2 = st.checkbox("אני מאשר/ת את המידע בסעיף 2 ומעונ/ה להמשיך", key="confirm2")
    back, nxt = nav_buttons(show_back=True)

    if back:
        st.session_state.step = 1
        st.rerun()
    if nxt:
        errors = []
        if st.session_state.prev_training in ["כן", "אחר..."]:
            if not st.session_state.prev_place.strip():   errors.append("יש למלא מקום/תחום אם הייתה הכשרה קודמת.")
            if not st.session_state.prev_mentor.strip():  errors.append("יש למלא שם מדריך ומיקום.")
            if not st.session_state.prev_partner.strip(): errors.append("יש למלא בן/בת זוג להתמחות.")
        if not st.session_state.chosen_domains:
            errors.append("יש לבחור עד 3 תחומים (לפחות אחד).")
        if "אחר..." in st.session_state.chosen_domains and not st.session_state.domains_other.strip():
            errors.append("נבחר 'אחר' – יש לפרט תחום.")
        if st.session_state.chosen_domains and (st.session_state.top_domain_select not in st.session_state.chosen_domains):
            errors.append("יש לבחור תחום מוביל מתוך השלושה.")
        if not unique_ranks(ranks):
            errors.append("לא ניתן להשתמש באותו דירוג ליותר ממוסד אחד.")
        if not st.session_state.special_request.strip():
            errors.append("יש לציין אם יש בקשה מיוחדת (אפשר לכתוב 'אין').")
        if not confirm2:
            errors.append("יש לאשר את סעיף 2 כדי להמשיך.")

        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            st.session_state.ranks = ranks
            st.session_state.step = 3
            st.rerun()

# --- סעיף 3: נתונים אקדמיים ---
if st.session_state.step == 3:
    st.subheader("סעיף 3 מתוך 6 – נתונים אקדמיים")
    st.write("יש להזין את ממוצע הציונים העדכני ביותר (נכון לסיום הסמסטר האחרון).")
    avg_grade = st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0, step=0.1, key="avg_grade")

    confirm3 = st.checkbox("אני מאשר/ת את המידע בסעיף 3 ומעונ/ה להמשיך", key="confirm3")
    back, nxt = nav_buttons(show_back=True)

    if back:
        st.session_state.step = 2
        st.rerun()
    if nxt:
        errors = []
        if st.session_state.avg_grade is None or st.session_state.avg_grade <= 0:
            errors.append("יש להזין ממוצע ציונים גדול מ-0.")
        if not confirm3:
            errors.append("יש לאשר את סעיף 3 כדי להמשיך.")
        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            st.session_state.step = 4
            st.rerun()

# --- סעיף 4: התאמות ---
if st.session_state.step == 4:
    st.subheader("סעיף 4 מתוך 6 – התאמות רפואיות, אישיות וחברתיות")
    st.write("ציינו כל מגבלה/צורך שיש להתחשב בו בתהליך השיבוץ.")

    adjustments = st.multiselect(
        "סוגי התאמות (ניתן לבחור כמה) *",
        [
            "הריון",
            "מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)",
            "רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)",
            "אלרגיה חמורה",
            "נכות",
            "רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)",
            "אחר..."
        ],
        placeholder="בחרי אפשרויות התאמה",
        key="adjustments"
    )
    if "אחר..." in adjustments:
        st.session_state.adjustments_other = st.text_input("פרט/י התאמה אחרת *", key="adjustments_other")
    else:
        st.session_state.adjustments_other = ""
    st.session_state.adjustments_details = st.text_area("פרט: *", height=100, key="adjustments_details")

    confirm4 = st.checkbox("אני מאשר/ת את המידע בסעיף 4 ומעונ/ה להמשיך", key="confirm4")
    back, nxt = nav_buttons(show_back=True)

    if back:
        st.session_state.step = 3
        st.rerun()
    if nxt:
        errors = []
        if not st.session_state.adjustments:
            errors.append("יש לבחור לפחות סוג התאמה אחד (או לציין 'אין').")
        if "אחר..." in st.session_state.adjustments and not st.session_state.adjustments_other.strip():
            errors.append("נבחר 'אחר' – יש לפרט התאמה.")
        if not st.session_state.adjustments_details.strip():
            errors.append("יש לפרט התייחסות להתאמות (אפשר לכתוב 'אין').")
        if not confirm4:
            errors.append("יש לאשר את סעיף 4 כדי להמשיך.")
        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            st.session_state.step = 5
            st.rerun()

# --- סעיף 5: מוטיבציה ---
if st.session_state.step == 5:
    st.subheader("סעיף 5 מתוך 6 – מוטיבציה להשתבץ בהכשרה המעשית")
    st.write("הערכה זו תסייע להבין מחויבות גם בתנאים מאתגרים.")
    likert = ["בכלל לא מסכים/ה", "1", "2", "3", "4", "מסכים/ה מאוד"]
    m1 = st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert, horizontal=True, key="m1")
    m2 = st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert, horizontal=True, key="m2")
    m3 = st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert, horizontal=True, key="m3")

    confirm5 = st.checkbox("אני מאשר/ת את המידע בסעיף 5 ומעונ/ה להמשיך", key="confirm5")
    back, nxt = nav_buttons(show_back=True)

    if back:
        st.session_state.step = 4
        st.rerun()
    if nxt:
        errors = []
        if not st.session_state.m1 or not st.session_state.m2 or not st.session_state.m3:
            errors.append("יש לענות על שלוש שאלות המוטיבציה.")
        if not confirm5:
            errors.append("יש לאשר את סעיף 5 כדי להמשיך.")
        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            st.session_state.step = 6
            st.rerun()

# --- סעיף 6: סיכום ושליחה ---
if st.session_state.step == 6:
    st.subheader("סעיף 6 מתוך 6 – סיכום ושליחה")
    st.write("עברו על הנתונים שמילאתם ואשרו את הצהרת הדיוק כדי להגיש.")
    confirm_final = st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *",
                                key="confirm_final")

    back, send = nav_buttons(show_back=True, proceed_label="שליחה ✉️")

    if back:
        st.session_state.step = 5
        st.rerun()

    if send:
        errors = []
        if not confirm_final:
            errors.append("יש לאשר את ההצהרה.")
        if not st.session_state.get("first_name","").strip(): errors.append("סעיף 1: חסר שם פרטי.")
        if not st.session_state.get("last_name","").strip():  errors.append("סעיף 1: חסר שם משפחה.")
        if not valid_id(st.session_state.get("nat_id","")):  errors.append("סעיף 1: ת״ז לא תקינה.")
        if errors:
            st.error("נמצאו שגיאות:")
            for e in errors: st.markdown(f"- :red[{e}]")
        else:
            ranks = st.session_state.get("ranks", {})
            rank_clean = {f"דירוג_{k}": v for k, v in ranks.items()}
            extra_langs = st.session_state.get("extra_langs", [])
            row = {
                "תאריך_שליחה": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # סעיף 1
                "שם_פרטי": st.session_state.first_name.strip(),
                "שם_משפחה": st.session_state.last_name.strip(),
                "תעודת_זהות": st.session_state.nat_id.strip(),
                "מין": st.session_state.gender,
                "שיוך_חברתי": st.session_state.social_affil,
                "שפת_אם": (st.session_state.other_mt.strip()
                           if st.session_state.mother_tongue == "אחר..." else st.session_state.mother_tongue),
                "שפות_נוספות": "; ".join([x for x in extra_langs if x != "אחר..."] +
                                          ([st.session_state.get("extra_langs_other","").strip()]
                                           if "אחר..." in extra_langs else [])),
                "טלפון": st.session_state.phone.strip(),
                "כתובת": st.session_state.address.strip(),
                "אימייל": st.session_state.email.strip(),
                "שנת_לימודים": (st.session_state.get("study_year_other","").strip()
                                if st.session_state.study_year == "אחר..." else st.session_state.study_year),
                "מסלול_לימודים": st.session_state.track.strip(),
                "ניידות": (st.session_state.get("mobility_other","").strip()
                          if st.session_state.mobility == "אחר..." else st.session_state.mobility),
                # סעיף 2
                "הכשרה_קודמת": st.session_state.prev_training,
                "הכשרה_קודמת_מקום_ותחום": st.session_state.get("prev_place","").strip(),
                "הכשרה_קודמת_מדריך_ומיקום": st.session_state.get("prev_mentor","").strip(),
                "הכשרה_קודמת_בן_זוג": st.session_state.get("prev_partner","").strip(),
                "תחומים_מועדפים": "; ".join(
                    [d for d in st.session_state.get("chosen_domains", []) if d != "אחר..."] +
                    ([st.session_state.get("domains_other","").strip()]
                     if "אחר..." in st.session_state.get("chosen_domains", []) else [])
                ),
                "תחום_מוביל": (st.session_state.top_domain_select
                              if st.session_state.get("top_domain_select","") and
                                 st.session_state.top_domain_select != "— בחר/י —" else ""),
                "בקשה_מיוחדת": st.session_state.get("special_request","").strip(),
                # סעיף 3
                "ממוצע": st.session_state.avg_grade,
                # סעיף 4
                "התאמות": "; ".join(
                    [a for a in st.session_state.get("adjustments", []) if a != "אחר..."] +
                    ([st.session_state.get("adjustments_other","").strip()]
                     if "אחר..." in st.session_state.get("adjustments", []) else [])
                ),
                "התאמות_פרטים": st.session_state.get("adjustments_details","").strip(),
                # סעיף 5
                "מוטיבציה_1": st.session_state.m1,
                "מוטיבציה_2": st.session_state.m2,
                "מוטיבציה_3": st.session_state.m3,
            }
            row.update(rank_clean)

            try:
                append_row(row, CSV_FILE)
                st.success("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
                st.session_state.step = 1
            except Exception as e:
                st.error(f"❌ שמירה נכשלה: {e}")
