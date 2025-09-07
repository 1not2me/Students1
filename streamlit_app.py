# app.py
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

# --- פונקציית הצגת שגיאות (טקסט בלבד) ---
def show_errors(errors: list[str]):
    if not errors:
        return
    st.markdown("""
<style>
/* ===== תבנית בסיס זהה לזו של הרשימה הנפתחת ===== */
.field-like{
  background:#fff !important;
  border:1px solid rgba(15,23,42,.14) !important;
  border-radius:14px !important;
  box-shadow:0 3px 10px rgba(15,23,42,.04) !important;
  transition:background .2s ease, border-color .2s ease, box-shadow .2s ease !important;
}
.field-like:hover{
  border-color:rgba(15,23,42,.22) !important;
  box-shadow:0 4px 14px rgba(15,23,42,.08) !important;
}
.field-like:focus-within{
  border-color:#b892ff !important;              /* כמו ה-select */
  box-shadow:0 0 0 3px rgba(155,93,229,.25),    /* טבעת עדינה */
             0 4px 14px rgba(15,23,42,.1) !important;
}

/* ===== טקסט/מספר/תאריך – תיבת עוטפת ===== */
.stTextInput > div > div,
.stNumberInput > div > div,
.stDateInput > div > div{
  composes: field-like;
  height:48px !important;
  display:flex; align-items:center;
  padding-inline-start:.8rem !important;   /* ימין */
  padding-inline-end:.8rem !important;     /* שמאל */
}

/* שדות הקלט עצמם */
.stTextInput input,
.stNumberInput input,
.stDateInput input{
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  height:46px !important;
  width:100% !important;
  color:#0f172a !important;
  font-size:1rem !important;
  padding:0 !important;                     /* הריווח מגיע מהעוטף */
  text-align:right !important;              /* RTL */
}
.stTextInput input::placeholder,
.stNumberInput input::placeholder,
.stDateInput input::placeholder{
  color:#555 !important; opacity:1 !important; font-size:.95rem !important;
}

/* ===== TextArea – טקסט ארוך באותו סגנון ===== */
.stTextArea > div > div{
  composes: field-like;
  min-height:110px !important;
  padding:.6rem .8rem !important;
}
.stTextArea textarea{
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  color:#0f172a !important;
  font-size:1rem !important;
  width:100% !important;
  resize: vertical;
}

/* ריווח אנכי אחיד בין שדות (אופציונלי) */
.stTextInput, .stNumberInput, .stDateInput, .stTextArea{ margin-bottom:.9rem; }
</style>
""", unsafe_allow_html=True)

CSV_FILE = Path("שאלון_שיבוץ.csv")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# =========================
# פונקציות עזר
# =========================
def load_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()

def append_row(row: dict, path: Path):
    df_new = pd.DataFrame([row])
    df_new.to_csv(path, mode="a", index=False, encoding="utf-8-sig", header=not path.exists())

def _pick_excel_engine() -> str | None:
    try:
        import xlsxwriter  # noqa
        return "xlsxwriter"
    except Exception:
        try:
            import openpyxl  # noqa
            return "openpyxl"
        except Exception:
            return None

def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "תשובות") -> bytes:
    engine = _pick_excel_engine()
    if engine is None:
        st.markdown("<div style='color:#b91c1c'>לא נמצא מנוע לייצוא Excel. הוסיפו ל־requirements.txt: <b>xlsxwriter</b> או <b>openpyxl</b>.</div>", unsafe_allow_html=True)
        return b""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine=engine) as w:
        df.to_excel(w, sheet_name=sheet, index=False)
        if engine == "xlsxwriter":
            ws = w.sheets[sheet]
            for i, c in enumerate(df.columns):
                width = min(60, max(12, int(df[c].astype(str).map(len).max() if not df.empty else 12) + 4))
                ws.set_column(i, i, width)
    buf.seek(0)
    return buf.read()

def valid_email(v: str) -> bool: return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))
def valid_phone(v: str) -> bool: return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))
def valid_id(v: str) -> bool:    return bool(re.match(r"^\d{8,9}$", v.strip()))

def unique_ranks(r: dict) -> bool:
    seen=set()
    for v in r.values():
        if v in (None, "דלג"): continue
        if v in seen: return False
        seen.add(v)
    return True

# =========================
# עמוד מנהל
# =========================
if is_admin_mode:
    st.title("🔑 גישת מנהל – צפייה והורדת Excel")
    pwd = st.text_input("סיסמת מנהל:", type="password", key="admin_pwd")
    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("התחברת בהצלחה ✅")
            df = load_df(CSV_FILE)
            if df.empty:
                st.info("אין עדיין נתונים.")
            else:
                st.dataframe(df, use_container_width=True)
                xls = df_to_excel_bytes(df)
                if xls:
                    st.download_button("📥 הורדת אקסל (כל הנתונים)",
                                       data=xls,
                                       file_name="שאלון_שיבוץ_כל_הנתונים.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.markdown("<div style='color:#b91c1c'>סיסמה שגויה</div>", unsafe_allow_html=True)
    st.stop()

# =========================
# אשף 6 סעיפים (מצב נשמר אוטומטית ב-session_state)
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("התמיכה בקוראי מסך הופעלה.")

# שמירת צעד נוכחי (Persist בין רינדורים). רענון דפדפן מוחק session_state — זה טבעי ב-Streamlit
if "step" not in st.session_state:
    st.session_state.step = 1

def nav_buttons(show_back=True, proceed_label="המשך לסעיף הבא"):
    c1, c2 = st.columns([1,1])
    back = c1.button("חזרה", use_container_width=True) if show_back else False  # בלי החץ
    nxt  = c2.button(proceed_label, use_container_width=True)
    return back, nxt

# --- סעיף 1 ---
if st.session_state.step == 1:
    st.subheader("סעיף 1 מתוך 6 – פרטים אישיים של הסטודנט/ית")

    first_name = st.text_input("שם פרטי *", key="first_name")
    last_name  = st.text_input("שם משפחה *", key="last_name")
    nat_id     = st.text_input("מספר תעודת זהות *", key="nat_id")

    gender = st.radio("מין *", ["זכר","נקבה"], horizontal=True, key="gender")
    social_affil = st.selectbox("שיוך חברתי *", ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"], key="social_affil")

    mother_tongue = st.selectbox("שפת אם *", ["עברית","ערבית","רוסית","אחר..."], key="mother_tongue")
    if mother_tongue == "אחר...":
        st.text_input("ציין/י שפת אם אחרת *", key="other_mt")
    else:
        st.session_state.pop("other_mt", None)

    st.multiselect("ציין/י שפות נוספות (ברמת שיחה) *",
                   ["עברית","ערבית","רוסית","אמהרית","אנגלית","ספרדית","אחר..."],
                   placeholder="בחרי שפות נוספות", key="extra_langs")
    if "אחר..." in st.session_state.get("extra_langs", []):
        st.text_input("ציין/י שפה נוספת (אחר) *", key="extra_langs_other")
    else:
        st.session_state.pop("extra_langs_other", None)

    st.text_input("מספר טלפון נייד * (לדוגמה 050-1234567)", key="phone")
    st.text_input("כתובת מלאה (כולל יישוב) *", key="address")
    st.text_input("כתובת דוא״ל *", key="email")

    st.selectbox("שנת הלימודים *",
                 ["תואר ראשון - שנה א'","תואר ראשון - שנה ב'","תואר ראשון - שנה ג'","הסבה א'","הסבה ב'","אחר..."],
                 key="study_year")
    if st.session_state.study_year == "אחר...":
        st.text_input("ציין/י שנה/מסלול אחר *", key="study_year_other")
    else:
        st.session_state.pop("study_year_other", None)

    st.text_input("מסלול לימודים / תואר *", key="track")

    st.selectbox("אופן ההגעה להתמחות (ניידות) *",
                 ["אוכל להיעזר ברכב / ברשותי רכב","אוכל להגיע בתחבורה ציבורית","אחר..."],
                 key="mobility")
    if st.session_state.mobility == "אחר...":
        st.text_input("פרט/י אחר לגבי ניידות *", key="mobility_other")
    else:
        st.session_state.pop("mobility_other", None)

    st.checkbox("אני מאשר/ת את המידע בסעיף 1 ומעונ/ה להמשיך", key="confirm1")
    _, nxt = nav_buttons(False)

    if nxt:
        errors=[]
        if not st.session_state.first_name.strip(): errors.append("יש למלא שם פרטי.")
        if not st.session_state.last_name.strip():  errors.append("יש למלא שם משפחה.")
        if not valid_id(st.session_state.nat_id):   errors.append("ת״ז חייבת להיות 8–9 ספרות.")
        if st.session_state.mother_tongue=="אחר..." and not st.session_state.get("other_mt","").strip(): errors.append("יש לציין שפת אם (אחר).")
        if (not st.session_state.get("extra_langs") or
            ("אחר..." in st.session_state.extra_langs and not st.session_state.get("extra_langs_other","").strip())):
            errors.append("יש לבחור שפות נוספות (ואם נבחר 'אחר', לפרט).")
        if not valid_phone(st.session_state.phone): errors.append("מספר טלפון אינו תקין.")
        if not st.session_state.address.strip():    errors.append("יש למלא כתובת מלאה.")
        if not valid_email(st.session_state.email): errors.append("כתובת דוא״ל אינה תקינה.")
        if st.session_state.study_year=="אחר..." and not st.session_state.get("study_year_other","").strip():
            errors.append("יש לפרט שנת לימודים (אחר).")
        if not st.session_state.track.strip(): errors.append("יש למלא מסלול לימודים/תואר.")
        if st.session_state.mobility=="אחר..." and not st.session_state.get("mobility_other","").strip():
            errors.append("יש לפרט ניידות (אחר).")
        if not st.session_state.confirm1: errors.append("יש לאשר את סעיף 1 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step=2
            st.rerun()

# --- סעיף 2 ---
if st.session_state.step == 2:
    st.subheader("סעיף 2 מתוך 6 – העדפת שיבוץ")

    st.selectbox("האם עברת הכשרה מעשית בשנה קודמת? *", ["כן","לא","אחר..."], key="prev_training")
    if st.session_state.prev_training in ["כן","אחר..."]:
        st.text_input("אם כן, נא ציין שם מקום ותחום ההתמחות *", key="prev_place")
        st.text_input("שם המדריך והמיקום הגיאוגרפי של ההכשרה *", key="prev_mentor")
        st.text_input("בן/בת הזוג להתמחות בשנה הקודמת *", key="prev_partner")
    else:
        st.session_state.pop("prev_place", None)
        st.session_state.pop("prev_mentor", None)
        st.session_state.pop("prev_partner", None)

    all_domains=["קהילה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש","שיקום","משפחה","נשים","בריאות","תָקוֹן","אחר..."]
    st.multiselect("בחרו עד 3 תחומים *", all_domains, max_selections=3,
                   placeholder="בחרי עד שלושה תחומים", key="chosen_domains")
    if "אחר..." in st.session_state.get("chosen_domains", []):
        st.text_input("פרט/י תחום אחר *", key="domains_other")
    else:
        st.session_state.pop("domains_other", None)

    st.selectbox("מה התחום הכי מועדף עליך, מבין שלושתם? *",
                 ["— בחר/י —"]+st.session_state.get("chosen_domains", []) if st.session_state.get("chosen_domains") else ["— בחר/י —"],
                 key="top_domain_select")

    st.markdown("**דרגו את העדפותיכם (1=מועדף ביותר, 10=פחות מועדף). אפשר לדלג.**")
    sites=["בית חולים זיו","שירותי רווחה קריית שמונה","מרכז יום לגיל השלישי","מועדונית נוער בצפת","...","6","7","8","9","10"]
    rank_options=["דלג"]+[str(i) for i in range(1,11)]
    ranks={}
    cols = st.columns(2)
    for i, s in enumerate(sites):
        with cols[i%2]:
            ranks[s]=st.selectbox(f"דירוג – {s}", rank_options, index=0, key=f"rank_{i}")

    st.text_area("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות? *", height=100, key="special_request")
    st.checkbox("אני מאשר/ת את המידע בסעיף 2 ומעונ/ה להמשיך", key="confirm2")

    back, nxt = nav_buttons(True)
    if back: st.session_state.step=1; st.rerun()
    if nxt:
        errors=[]
        if st.session_state.prev_training in ["כן","אחר..."]:
            if not st.session_state.get("prev_place","").strip():  errors.append("יש למלא מקום/תחום אם הייתה הכשרה קודמת.")
            if not st.session_state.get("prev_mentor","").strip(): errors.append("יש למלא שם מדריך ומיקום.")
            if not st.session_state.get("prev_partner","").strip():errors.append("יש למלא בן/בת זוג.")
        if not st.session_state.get("chosen_domains"): errors.append("יש לבחור לפחות תחום אחד (עד 3).")
        if "אחר..." in st.session_state.get("chosen_domains", []) and not st.session_state.get("domains_other","").strip():
            errors.append("נבחר 'אחר' – יש לפרט תחום.")
        if st.session_state.get("chosen_domains") and (st.session_state.top_domain_select not in st.session_state.chosen_domains):
            errors.append("בחר/י תחום מוביל מתוך השלושה.")
        if not unique_ranks(ranks): errors.append("לא ניתן להשתמש באותו דירוג ליותר ממוסד אחד.")
        if not st.session_state.get("special_request","").strip(): errors.append("יש לציין אם יש בקשה מיוחדת (אפשר לכתוב 'אין').")
        if not st.session_state.confirm2: errors.append("יש לאשר את סעיף 2 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.ranks=ranks
            st.session_state.step=3
            st.rerun()

# --- סעיף 3 ---
if st.session_state.step == 3:
    st.subheader("סעיף 3 מתוך 6 – נתונים אקדמיים")
    st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0, step=0.1, key="avg_grade")
    st.checkbox("אני מאשר/ת את המידע בסעיף 3 ומעונ/ה להמשיך", key="confirm3")
    back, nxt = nav_buttons(True)
    if back: st.session_state.step=2; st.rerun()
    if nxt:
        errors=[]
        if st.session_state.avg_grade is None or st.session_state.avg_grade<=0: errors.append("יש להזין ממוצע ציונים גדול מ-0.")
        if not st.session_state.confirm3: errors.append("יש לאשר את סעיף 3 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step=4
            st.rerun()

# --- סעיף 4 ---
if st.session_state.step == 4:
    st.subheader("סעיף 4 מתוך 6 – התאמות רפואיות, אישיות וחברתיות")
    st.multiselect("סוגי התאמות (ניתן לבחור כמה) *",
                   ["הריון","מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)",
                    "רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)","אלרגיה חמורה",
                    "נכות","רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)","אחר..."],
                   placeholder="בחרי אפשרויות התאמה", key="adjustments")
    if "אחר..." in st.session_state.get("adjustments", []):
        st.text_input("פרט/י התאמה אחרת *", key="adjustments_other")
    else:
        st.session_state.pop("adjustments_other", None)
    st.text_area("פרט: *", height=100, key="adjustments_details")

    st.checkbox("אני מאשר/ת את המידע בסעיף 4 ומעונ/ה להמשיך", key="confirm4")
    back, nxt = nav_buttons(True)
    if back: st.session_state.step=3; st.rerun()
    if nxt:
        errors=[]
        if not st.session_state.get("adjustments"): errors.append("יש לבחור לפחות סוג התאמה אחד (או לציין 'אין').")
        if "אחר..." in st.session_state.get("adjustments", []) and not st.session_state.get("adjustments_other","").strip():
            errors.append("נבחר 'אחר' – יש לפרט התאמה.")
        if not st.session_state.get("adjustments_details","").strip(): errors.append("יש לפרט התייחסות להתאמות (אפשר לכתוב 'אין').")
        if not st.session_state.confirm4: errors.append("יש לאשר את סעיף 4 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step=5
            st.rerun()

# --- סעיף 5 ---
if st.session_state.step == 5:
    st.subheader("סעיף 5 מתוך 6 – מוטיבציה")
    likert=["בכלל לא מסכים/ה","1","2","3","4","מסכים/ה מאוד"]
    st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert, horizontal=True, key="m1")
    st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert, horizontal=True, key="m2")
    st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert, horizontal=True, key="m3")
    st.checkbox("אני מאשר/ת את המידע בסעיף 5 ומעונ/ה להמשיך", key="confirm5")
    back, nxt = nav_buttons(True)
    if back: st.session_state.step=4; st.rerun()
    if nxt:
        errors=[]
        if not (st.session_state.m1 and st.session_state.m2 and st.session_state.m3):
            errors.append("יש לענות על שלוש שאלות המוטיבציה.")
        if not st.session_state.confirm5: errors.append("יש לאשר את סעיף 5 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step=6
            st.rerun()

# --- סעיף 6 ---
if st.session_state.step == 6:
    st.subheader("סעיף 6 מתוך 6 – סיכום ושליחה")
    st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *", key="confirm_final")
    back, send = nav_buttons(True, "שליחה ✉️")
    if back: st.session_state.step=5; st.rerun()
    if send:
        errors=[]
        if not st.session_state.confirm_final: errors.append("יש לאשר את ההצהרה.")
        if not st.session_state.get("first_name","").strip(): errors.append("סעיף 1: חסר שם פרטי.")
        if not st.session_state.get("last_name","").strip():  errors.append("סעיף 1: חסר שם משפחה.")
        if not valid_id(st.session_state.get("nat_id","")):  errors.append("סעיף 1: ת״ז חייבת להיות 8–9 ספרות.")
        show_errors(errors)
        if not errors:
            ranks = st.session_state.get("ranks", {})
            rank_clean = {f"דירוג_{k}": v for k,v in ranks.items()}
            extra_langs = st.session_state.get("extra_langs", [])
            row = {
                "תאריך_שליחה": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "שם_פרטי": st.session_state.first_name.strip(),
                "שם_משפחה": st.session_state.last_name.strip(),
                "תעודת_זהות": st.session_state.nat_id.strip(),
                "מין": st.session_state.gender,
                "שיוך_חברתי": st.session_state.social_affil,
                "שפת_אם": (st.session_state.get("other_mt","").strip()
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
                "ממוצע": st.session_state.avg_grade,
                "התאמות": "; ".join(
                    [a for a in st.session_state.get("adjustments", []) if a != "אחר..."] +
                    ([st.session_state.get("adjustments_other","").strip()]
                     if "אחר..." in st.session_state.get("adjustments", []) else [])
                ),
                "התאמות_פרטים": st.session_state.get("adjustments_details","").strip(),
                "מוטיבציה_1": st.session_state.m1, "מוטיבציה_2": st.session_state.m2, "מוטיבציה_3": st.session_state.m3,
            }
            row.update(rank_clean)
            try:
                append_row(row, CSV_FILE)
                st.success("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
                st.session_state.step=1
            except Exception as e:
                st.markdown(f"<div style='color:#b91c1c'>❌ שמירה נכשלה: {e}</div>", unsafe_allow_html=True)
