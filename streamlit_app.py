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
    # הסתרת "Press Enter to apply" מכל השדות
st.markdown("""
<style>
@font-face {
  font-family:'David';
  src:url('https://example.com/David.ttf') format('truetype');
}
html, body, [class*="css"] {
  font-family:'David',sans-serif!important;
}

/* ====== עיצוב מודרני + RTL ====== */
:root{
  --bg-1:#e0f7fa;
  --bg-2:#ede7f6;
  --bg-3:#fff3e0;
  --bg-4:#fce4ec;
  --bg-5:#e8f5e9;
  --ink:#0f172a;
  --primary:#9b5de5;
  --primary-700:#f15bb5;
  --ring:rgba(155,93,229,.35);
}

[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, var(--bg-2) 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, var(--bg-3) 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, var(--bg-4) 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, var(--bg-5) 0%, transparent 70%),
    linear-gradient(135deg, var(--bg-1) 0%, #ffffff 100%) !important;
  color: var(--ink);
}

.main .block-container{
  background: rgba(255,255,255,.78);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px;
  padding:2rem 2rem 2.5rem;
}

h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  letter-spacing:.5px;
  text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700;
}

/* כפתור בהיר יותר */
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:16px!important;
  padding:.75rem 1.3rem!important;
  font-size:1rem!important;
  font-weight:600!important;
  box-shadow:0 6px 16px var(--ring)!important;
  transition:all .15s ease!important;
}
.stButton > button:hover{
  transform:translateY(-2px) scale(1.01);
  filter:brightness(1.08);
}
.stButton > button:focus{
  outline:none!important;
  box-shadow:0 0 0 4px var(--ring)!important;
}

/* קלטים ו-selectים ברורים */
div.stSelectbox > div,
div.stMultiSelect > div,
.stTextInput > div > div > input{
  border-radius:14px!important;
  border:1px solid rgba(15,23,42,.12)!important;
  box-shadow:0 3px 10px rgba(15,23,42,.04)!important;
  padding:.4rem .6rem!important;
  color:var(--ink)!important;
  font-size:1rem!important;
}

/* תיקון select/multiselect ב-RTL */
div[data-baseweb="select"] > div{
  height:48px!important;
  background:#fff!important;
  border:1px solid rgba(15,23,42,.14)!important;
  border-radius:14px!important;
  padding-inline-start:.8rem!important;
  padding-inline-end:2.2rem!important;
  box-shadow:0 3px 10px rgba(15,23,42,.04)!important;
  display:flex; align-items:center;
}
div[data-baseweb="select"] [class*="SingleValue"],
div[data-baseweb="select"] [class*="ValueContainer"]{
  color:#0f172a!important;
  font-size:1rem!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}
div[data-baseweb="select"] [class*="placeholder"],
.stTextInput > div > div > input::placeholder{
  color:#555!important;
  opacity:1!important;
  font-size:.95rem;
}
div[data-baseweb="select"] input{
  color:#0f172a!important;
  text-align:right!important;
}
div[data-baseweb="select"] svg{
  color:#333!important;
  inset-inline-end:.65rem!important;
  inset-inline-start:auto!important;
}
ul[role="listbox"]{
  direction:rtl!important;
  text-align:right!important;
}
ul[role="listbox"] [role="option"] > div{
  text-align:right!important;
}

/* RTL כללי */
.stApp,.main,[data-testid="stSidebar"]{
  direction:rtl;
  text-align:right;
}
label,.stMarkdown,.stText,.stCaption{
  text-align:right!important;
}

/* טאבים */
.stTabs [data-baseweb="tab"]{
  border-radius:14px!important;
  background:rgba(255,255,255,.65);
  margin-inline-start:.5rem;
  padding:.5rem 1rem;
  font-weight:600;
  transition:background .2s;
}
.stTabs [data-baseweb="tab"]:hover{
  background:rgba(255,255,255,.9);
}

/* הסתרת הודעת "Press Enter to apply" */
[data-testid="stInputInstructions"],
[data-testid="stTextInputInstructions"],
small.enter-to-apply {
  display: none !important;
}
</style>

<script>
(function(){
  function hideEnterHints(){
    const needles = ['press enter to apply','press enter to apply.'];
    document.querySelectorAll('div,span,p,small').forEach(el=>{
      const t = (el.textContent||'').trim().toLowerCase();
      if (needles.includes(t)) el.style.display='none';
    });
  }
  const obs = new MutationObserver(hideEnterHints);
  obs.observe(document.body, { childList:true, subtree:true });
  hideEnterHints();
})();
</script>
""", unsafe_allow_html=True)



CSV_FILE = Path("שאלון_שיבוץ.csv")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# =========================
# פונקציות עזר קבצים
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

# =========================
# ולידציות
# =========================
def valid_email(v: str) -> bool: return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))
def valid_phone(v: str) -> bool: return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))
def valid_id(v: str) -> bool:    return bool(re.match(r"^\d{8,9}$", v.strip()))

def unique_ranks(r: dict) -> bool:
    seen = set()
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
# אשף 6 סעיפים
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("התמיכה בקוראי מסך הופעלה.")

# ברירת מחדל לצעד
st.session_state.setdefault("step", 1)

def nav_buttons(show_back=True, proceed_label="המשך לסעיף הבא"):
    c1, c2 = st.columns([1,1])
    back = c1.button("חזרה", use_container_width=True) if show_back else False  # ללא חץ
    nxt  = c2.button(proceed_label, use_container_width=True)
    return back, nxt

# --- סעיף 1 ---
if st.session_state.step == 1:
    st.subheader("סעיף 1 מתוך 6 – פרטים אישיים של הסטודנט/ית")

    ti("שם פרטי *", "first_name")
    ti("שם משפחה *", "last_name")
    ti("מספר תעודת זהות *", "nat_id")

    # radio/checkbox אוספים את הערך ישירות לפי key, אבל כדי שה־UI תמיד יציג את השמורים – נחשב index
    gender_opts = ["זכר","נקבה"]
    st.radio("מין *", gender_opts, index=_idx(gender_opts, st.session_state.get("gender", gender_opts[0])), key="gender", horizontal=True)

    social_opts = ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"]
    sb("שיוך חברתי *", social_opts, "social_affil")

    mt_opts = ["עברית","ערבית","רוסית","אחר..."]
    sb("שפת אם *", mt_opts, "mother_tongue")
    if st.session_state.mother_tongue == "אחר...":
        ti("ציין/י שפת אם אחרת *", "other_mt")
    else:
        st.session_state.pop("other_mt", None)

    langs_opts = ["עברית","ערבית","רוסית","אמהרית","אנגלית","ספרדית","אחר..."]
    ms("ציין/י שפות נוספות (ברמת שיחה)", langs_opts, "extra_langs", placeholder="בחרי שפות נוספות")
    if "אחר..." in st.session_state.get("extra_langs", []):
        ti("ציין/י שפה נוספת (אחר) *", "extra_langs_other")
    else:
        st.session_state.pop("extra_langs_other", None)

    ti("מספר טלפון נייד * (לדוגמה 050-1234567)", "phone")
    ti("כתובת מלאה (כולל יישוב) *", "address")
    ti("כתובת דוא״ל *", "email")

    year_opts = ["תואר ראשון - שנה א'","תואר ראשון - שנה ב'","תואר ראשון - שנה ג'","הסבה א'","הסבה ב'","אחר..."]
    sb("שנת הלימודים *", year_opts, "study_year")
    if st.session_state.study_year == "אחר...":
        ti("ציין/י שנה/מסלול אחר *", "study_year_other")
    else:
        st.session_state.pop("study_year_other", None)

    ti("מסלול לימודים / תואר *", "track")

    mobility_opts = ["אוכל להיעזר ברכב / ברשותי רכב", "אוכל להגיע בתחבורה ציבורית", "אחר..."]
    sb("אופן ההגעה להתמחות (ניידות) *", mobility_opts, "mobility")
    if st.session_state.mobility == "אחר...":
        ti("פרט/י אחר לגבי ניידות *", "mobility_other")
    else:
        st.session_state.pop("mobility_other", None)

    st.checkbox("אני מאשר/ת את המידע בסעיף 1 ומעונ/ה להמשיך", key="confirm1",
                value=st.session_state.get("confirm1", False))

    _, nxt = nav_buttons(False)
    if nxt:
        errors=[]
        if not st.session_state.first_name.strip(): errors.append("יש למלא שם פרטי.")
        if not st.session_state.last_name.strip():  errors.append("יש למלא שם משפחה.")
        if not valid_id(st.session_state.nat_id):   errors.append("ת״ז חייבת להיות 8–9 ספרות.")
        if st.session_state.mother_tongue=="אחר..." and not st.session_state.get("other_mt","").strip():
            errors.append("יש לציין שפת אם (אחר).")
        if "אחר..." in st.session_state.get("extra_langs", []) and not st.session_state.get("extra_langs_other","").strip():
            errors.append("נבחר 'אחר' בשפות נוספות – יש לפרט.")
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
            st.session_state.step = 2
            st.rerun()

# --- סעיף 2 ---
if st.session_state.step == 2:
    st.subheader("סעיף 2 מתוך 6 – העדפת שיבוץ")

    prev_opts = ["כן","לא","אחר..."]
    sb("האם עברת הכשרה מעשית בשנה קודמת? *", prev_opts, "prev_training")
    if st.session_state.prev_training in ["כן","אחר..."]:
        ti("אם כן, נא ציין שם מקום ותחום ההתמחות *", "prev_place")
        ti("שם המדריך והמיקום הגיאוגרפי של ההכשרה *", "prev_mentor")
        ti("בן/בת הזוג להתמחות בשנה הקודמת *", "prev_partner")
    else:
        st.session_state.pop("prev_place", None)
        st.session_state.pop("prev_mentor", None)
        st.session_state.pop("prev_partner", None)

    all_domains = ["קהילה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש","שיקום","משפחה","נשים","בריאות","תָקוֹן","אחר..."]
    ms("בחרו עד 3 תחומים *", all_domains, "chosen_domains", max_selections=3, placeholder="בחרי עד שלושה תחומים")
    if "אחר..." in st.session_state.get("chosen_domains", []):
        ti("פרט/י תחום אחר *", "domains_other")
    else:
        st.session_state.pop("domains_other", None)

    # תחום מוביל – בנוי דינמית מהבחירה (שומר את הבחירה הקודמת אם עדיין קיימת)
    leading_options = ["— בחר/י —"] + st.session_state.get("chosen_domains", [])
    sb("מה התחום הכי מועדף עליך, מבין שלושתם? *", leading_options, "top_domain_select")

    st.markdown("**דרגו את העדפותיכם (1=מועדף ביותר, 10=פחות מועדף). אפשר לדלג.**")
    sites = ["בית חולים זיו","שירותי רווחה קריית שמונה","מרכז יום לגיל השלישי","מועדונית נוער בצפת","...","6","7","8","9","10"]
    rank_options = ["דלג"] + [str(i) for i in range(1, 11)]
    ranks = {}
    cols = st.columns(2)
    for i, s in enumerate(sites):
        key = f"rank_{i}"
        # שמירה/שחזור דירוג לכל אתר בנפרד
        prev = st.session_state.get(key, "דלג")
        with cols[i % 2]:
            val = st.selectbox(f"דירוג – {s}", rank_options, index=_idx(rank_options, prev), key=key)
            ranks[s] = val

    ta("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות?", "special_request", height=100)
    st.checkbox("אני מאשר/ת את המידע בסעיף 2 ומעונ/ה להמשיך", key="confirm2",
                value=st.session_state.get("confirm2", False))

    back, nxt = nav_buttons(True)
    if back:
        st.session_state.step = 1
        st.rerun()
    if nxt:
        errors = []
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
        if not st.session_state.confirm2: errors.append("יש לאשר את סעיף 2 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.ranks = ranks
            st.session_state.step = 3
            st.rerun()

# --- סעיף 3 ---
if st.session_state.step == 3:
    st.subheader("סעיף 3 מתוך 6 – נתונים אקדמיים")
    st.number_input("ממוצע ציונים *",
                    min_value=0.0, max_value=100.0, step=0.1,
                    key="avg_grade",
                    value=float(st.session_state.get("avg_grade", 0.0)) if st.session_state.get("avg_grade") else 0.0)
    st.checkbox("אני מאשר/ת את המידע בסעיף 3 ומעונ/ה להמשיך", key="confirm3",
                value=st.session_state.get("confirm3", False))
    back, nxt = nav_buttons(True)
    if back:
        st.session_state.step = 2
        st.rerun()
    if nxt:
        errors=[]
        if st.session_state.avg_grade is None or st.session_state.avg_grade <= 0:
            errors.append("יש להזין ממוצע ציונים גדול מ-0.")
        if not st.session_state.confirm3:
            errors.append("יש לאשר את סעיף 3 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step = 4
            st.rerun()

# --- סעיף 4 ---
if st.session_state.step == 4:
    st.subheader("סעיף 4 מתוך 6 – התאמות רפואיות, אישיות וחברתיות")
    adj_opts = ["הריון","מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)",
                "רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)","אלרגיה חמורה",
                "נכות","רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)","אחר..."]
    ms("סוגי התאמות (ניתן לבחור כמה) *", adj_opts, "adjustments", placeholder="בחרי אפשרויות התאמה")
    if "אחר..." in st.session_state.get("adjustments", []):
        ti("פרט/י התאמה אחרת *", "adjustments_other")
    else:
        st.session_state.pop("adjustments_other", None)
    ta("פרט: *", "adjustments_details", height=100)

    st.checkbox("אני מאשר/ת את המידע בסעיף 4 ומעונ/ה להמשיך", key="confirm4",
                value=st.session_state.get("confirm4", False))
    back, nxt = nav_buttons(True)
    if back:
        st.session_state.step = 3
        st.rerun()
    if nxt:
        errors=[]
        if not st.session_state.get("adjustments"):
            errors.append("יש לבחור לפחות סוג התאמה אחד (או לציין 'אין').")
        if "אחר..." in st.session_state.get("adjustments", []) and not st.session_state.get("adjustments_other","").strip():
            errors.append("נבחר 'אחר' – יש לפרט התאמה.")
        if not st.session_state.get("adjustments_details","").strip():
            errors.append("יש לפרט התייחסות להתאמות (אפשר לכתוב 'אין').")
        if not st.session_state.confirm4:
            errors.append("יש לאשר את סעיף 4 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step = 5
            st.rerun()

# --- סעיף 5 ---
if st.session_state.step == 5:
    st.subheader("סעיף 5 מתוך 6 – מוטיבציה")
    likert = ["בכלל לא מסכים/ה","1","2","3","4","מסכים/ה מאוד"]
    st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert,
             index=_idx(likert, st.session_state.get("m1", likert[0])), key="m1", horizontal=True)
    st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert,
             index=_idx(likert, st.session_state.get("m2", likert[0])), key="m2", horizontal=True)
    st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert,
             index=_idx(likert, st.session_state.get("m3", likert[0])), key="m3", horizontal=True)
    st.checkbox("אני מאשר/ת את המידע בסעיף 5 ומעונ/ה להמשיך", key="confirm5",
                value=st.session_state.get("confirm5", False))
    back, nxt = nav_buttons(True)
    if back:
        st.session_state.step = 4
        st.rerun()
    if nxt:
        errors=[]
        if not (st.session_state.m1 and st.session_state.m2 and st.session_state.m3):
            errors.append("יש לענות על שלוש שאלות המוטיבציה.")
        if not st.session_state.confirm5:
            errors.append("יש לאשר את סעיף 5 כדי להמשיך.")
        show_errors(errors)
        if not errors:
            st.session_state.step = 6
            st.rerun()

# --- סעיף 6 ---
if st.session_state.step == 6:
    st.subheader("סעיף 6 מתוך 6 – סיכום ושליחה")
    st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *",
                key="confirm_final", value=st.session_state.get("confirm_final", False))
    back, send = nav_buttons(True, "שליחה ✉️")
    if back:
        st.session_state.step = 5
        st.rerun()
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
                st.session_state.step = 1
            except Exception as e:
                st.markdown(f"<div style='color:#b91c1c'>❌ שמירה נכשלה: {e}</div>", unsafe_allow_html=True)
