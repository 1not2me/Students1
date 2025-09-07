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

# ====== עיצוב מודרני + RTL + הסתרת "Press Enter to apply" ======
st.markdown("""
<style>
@font-face { font-family:'David'; src:url('https://example.com/David.ttf') format('truetype'); }
html, body, [class*="css"] { font-family:'David',sans-serif!important; }
/* ====== עיצוב ====== */
:root{ --bg-1:#e0f7fa; --bg-2:#ede7f6; --bg-3:#fff3e0; --bg-4:#fce4ec; --bg-5:#e8f5e9; --ink:#0f172a; --primary:#9b5de5; --primary-700:#f15bb5; --ring:rgba(155,93,229,.35); }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, var(--bg-2) 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, var(--bg-3) 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, var(--bg-4) 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, var(--bg-5) 0%, transparent 70%),
    linear-gradient(135deg, var(--bg-1) 0%, #ffffff 100%) !important;
  color: var(--ink);
}
.main .block-container{ background: rgba(255,255,255,.78); backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08); box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px; padding:2rem 2rem 2.5rem; }
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{ letter-spacing:.5px; text-shadow:0 1px 2px rgba(255,255,255,.7); font-weight:700; }
/* כפתור */
.stButton > button{ background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important; border:none!important; border-radius:16px!important; padding:.75rem 1.3rem!important;
  font-size:1rem!important; font-weight:600!important; box-shadow:0 6px 16px var(--ring)!important; transition:all .15s ease!important; }
.stButton > button:hover{ transform:translateY(-2px) scale(1.01); filter:brightness(1.08); }
.stButton > button:focus{ outline:none!important; box-shadow:0 0 0 4px var(--ring)!important; }
/* קלטים/בחירות */
div.stSelectbox > div, div.stMultiSelect > div, .stTextInput > div > div > input{
  border-radius:14px!important; border:1px solid rgba(15,23,42,.12)!important; box-shadow:0 3px 10px rgba(15,23,42,.04)!important;
  padding:.4rem .6rem!important; color:var(--ink)!important; font-size:1rem!important;
}
div[data-baseweb="select"] > div{ height:48px!important; background:#fff!important; border:1px solid rgba(15,23,42,.14)!important; border-radius:14px!important;
  padding-inline-start:.8rem!important; padding-inline-end:2.2rem!important; box-shadow:0 3px 10px rgba(15,23,42,.04)!important; display:flex; align-items:center; }
div[data-baseweb="select"] [class*="SingleValue"], div[data-baseweb="select"] [class*="ValueContainer"]{ color:#0f172a!important; font-size:1rem!important;
  white-space:nowrap!important; overflow:hidden!important; text-overflow:ellipsis!important; }
div[data-baseweb="select"] [class*="placeholder"], .stTextInput > div > div > input::placeholder{ color:#555!important; opacity:1!important; font-size:.95rem; }
div[data-baseweb="select"] input{ color:#0f172a!important; text-align:right!important; }
div[data-baseweb="select"] svg{ color:#333!important; inset-inline-end:.65rem!important; inset-inline-start:auto!important; }
ul[role="listbox"]{ direction:rtl!important; text-align:right!important; }
ul[role="listbox"] [role="option"] > div{ text-align:right!important; }
/* RTL כללי */
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }
/* טאבים */
.stTabs [data-baseweb="tab"]{ border-radius:14px!important; background:rgba(255,255,255,.65); margin-inline-start:.5rem; padding:.5rem 1rem; font-weight:600; transition:background .2s; }
.stTabs [data-baseweb="tab"]:hover{ background:rgba(255,255,255,.9); }
/* הסתרת הנחיית "Press Enter to apply" אם קיימת */
[data-testid="stInputInstructions"], [data-testid="stTextInputInstructions"], small.enter-to-apply { display:none!important; }
</style>
<script>
(function(){
  function hideEnterHints(){
    const needles = ['press enter to apply','press enter to apply.'];
    document.querySelectorAll('div,span,p,small').forEach(el=>{
      const t=(el.textContent||'').trim().toLowerCase(); if(needles.includes(t)) el.style.display='none';
    });
  }
  const obs=new MutationObserver(hideEnterHints); obs.observe(document.body,{childList:true,subtree:true}); hideEnterHints();
})();
</script>
""", unsafe_allow_html=True)

# =========================
# קבצים/סודות
# =========================
CSV_FILE = Path("שאלון_שיבוץ.csv")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")  # מומלץ לשים בענן

# מצב מנהל: ?admin=1
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# =========================
# פונקציות עזר
# =========================
def load_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig") if path.exists() else pd.DataFrame()

def append_row(row: dict, path: Path):
    df_new = pd.DataFrame([row])
    df_new.to_csv(path, mode="a", index=False, encoding="utf-8-sig", header=not path.exists())

def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "תשובות") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name=sheet, index=False)
        ws = w.sheets[sheet]
        for i, col in enumerate(df.columns):
            width = min(60, max(12, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
            ws.set_column(i, i, width)
    buf.seek(0)
    return buf.read()

def valid_email(v: str) -> bool:  return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v.strip()))
def valid_phone(v: str) -> bool:  return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v.strip()))   # 050-1234567 / 04-8123456
def valid_id(v: str) -> bool:     return bool(re.match(r"^\d{8,9}$", v.strip()))

def unique_ranks(ranks: dict) -> bool:
    seen=set()
    for v in ranks.values():
        if v in (None, "דלג"): continue
        if v in seen: return False
        seen.add(v)
    return True

def show_errors(errors: list[str]):
    if not errors: return
    st.markdown("### :red[נמצאו שגיאות:]")
    for e in errors:
        st.markdown(f"- :red[{e}]")

# =========================
# עמוד מנהל
# =========================
if is_admin_mode:
    st.title("🔑 גישת מנהל – צפייה והורדות")
    pwd = st.text_input("סיסמת מנהל:", type="password")
    if pwd:
        if pwd == ADMIN_PASSWORD:
            st.success("התחברת בהצלחה ✅")
            df = load_df(CSV_FILE)
            if df.empty:
                st.info("אין עדיין נתונים בקובץ.")
            else:
                st.dataframe(df, use_container_width=True)
                with st.expander("📥 הורדות", expanded=True):
                    st.download_button("Excel – כל הנתונים", data=df_to_excel_bytes(df),
                        file_name="שאלון_שיבוץ_כללי.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.download_button("CSV – כל הנתונים",
                        data=df.to_csv(index=False, encoding="utf-8-sig"),
                        file_name="שאלון_שיבוץ_כללי.csv", mime="text/csv")
        else:
            st.error("סיסמה שגויה")
    st.stop()

# =========================
# שאלון – טאבים (שמירה אוטו’ של הערכים)
# =========================
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("התמיכה בקוראי מסך הופעלה.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "סעיף 1: פרטים אישיים", "סעיף 2: העדפת שיבוץ",
    "סעיף 3: נתונים אקדמיים", "סעיף 4: התאמות",
    "סעיף 5: מוטיבציה", "סעיף 6: סיכום ושליחה"
])

# --- סעיף 1 ---
with tab1:
    st.subheader("פרטים אישיים של הסטודנט/ית")
    first_name = st.text_input("שם פרטי *")
    last_name  = st.text_input("שם משפחה *")
    nat_id     = st.text_input("מספר תעודת זהות *")
    gender = st.radio("מין *", ["זכר","נקבה"], horizontal=True)
    social_affil = st.selectbox("שיוך חברתי *", ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"])
    mother_tongue = st.selectbox("שפת אם *", ["עברית","ערבית","רוסית","אחר..."])
    other_mt = st.text_input("ציין/ני שפת אם אחרת *") if mother_tongue=="אחר..." else ""
    extra_langs = st.multiselect("ציין/י שפות נוספות (ברמת שיחה) *",
                    ["עברית","ערבית","רוסית","אמהרית","אנגלית","ספרדית","אחר..."],
                    placeholder="בחרי שפות נוספות")
    extra_langs_other = st.text_input("ציין/י שפה נוספת (אחר) *") if "אחר..." in extra_langs else ""
    phone   = st.text_input("מספר טלפון נייד * (למשל 050-1234567)")
    address = st.text_input("כתובת מלאה (כולל יישוב) *")
    email   = st.text_input("כתובת דוא״ל *")
    study_year = st.selectbox("שנת הלימודים *", ["תואר ראשון - שנה א'","תואר ראשון - שנה ב'","תואר ראשון - שנה ג'","הסבה א'","הסבה ב'","אחר..."])
    study_year_other = st.text_input("ציין/י שנה/מסלול אחר *") if study_year=="אחר..." else ""
    track = st.text_input("מסלול לימודים / תואר *")
    mobility = st.selectbox("אופן ההגעה להתמחות (ניידות) *", ["אוכל להיעזר ברכב / ברשותי רכב","אוכל להגיע בתחבורה ציבורית","אחר..."])
    mobility_other = st.text_input("פרט/י אחר לגבי ניידות *") if mobility=="אחר..." else ""

# --- סעיף 2 ---
with tab2:
    st.subheader("העדפת שיבוץ")
    prev_training = st.selectbox("האם עברת הכשרה מעשית בשנה קודמת? *", ["כן","לא","אחר..."])
    prev_place=prev_mentor=prev_partner=""
    if prev_training in ["כן","אחר..."]:
        prev_place  = st.text_input("אם כן, נא ציין שם מקום ותחום ההתמחות *")
        prev_mentor = st.text_input("שם המדריך והמיקום הגיאוגרפי של ההכשרה *")
        prev_partner= st.text_input("מי היה/תה בן/בת הזוג להתמחות בשנה הקודמת? *")
    all_domains = ["קהילה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש","שיקום","משפחה","נשים","בריאות","תָקוֹן","אחר..."]
    chosen_domains = st.multiselect("בחרו עד 3 תחומים *", all_domains, max_selections=3, placeholder="בחרי עד שלושה תחומים")
    domains_other = st.text_input("פרט/י תחום אחר *") if "אחר..." in chosen_domains else ""
    top_domain = st.selectbox("מה התחום הכי מועדף עליך, מבין שלושתם? *", ["— בחר/י —"]+chosen_domains if chosen_domains else ["— בחר/י —"])
    st.markdown("**דרגו העדפות (1=מועדף, 10=פחות מועדף). אפשר לדלג.**")
    sites=["בית חולים זיו","שירותי רווחה קריית שמונה","מרכז יום לגיל השלישי","מועדונית נוער בצפת","...","6","7","8","9","10"]
    rank_options=["דלג"]+[str(i) for i in range(1,11)]
    ranks={}; cols=st.columns(2)
    for i,s in enumerate(sites):
        with cols[i%2]:
            ranks[s]=st.selectbox(f"דירוג – {s}", rank_options, index=0, key=f"rank_{i}")
    special_request = st.text_area("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות? *", height=100)

# --- סעיף 3 ---
with tab3:
    st.subheader("נתונים אקדמיים")
    avg_grade = st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0, step=0.1)

# --- סעיף 4 ---
with tab4:
    st.subheader("התאמות רפואיות, אישיות וחברתיות")
    adjustments = st.multiselect("סוגי התאמות (ניתן לבחור כמה) *",
                    ["הריון","מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)","רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)",
                     "אלרגיה חמורה","נכות","רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)","אחר..."],
                    placeholder="בחרי אפשרויות התאמה")
    adjustments_other = st.text_input("פרט/י התאמה אחרת *") if "אחר..." in adjustments else ""
    adjustments_details = st.text_area("פרט: *", height=100)

# --- סעיף 5 ---
with tab5:
    st.subheader("מוטיבציה")
    likert=["בכלל לא מסכים/ה","1","2","3","4","מסכים/ה מאוד"]
    m1 = st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert, horizontal=True)
    m2 = st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert, horizontal=True)
    m3 = st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert, horizontal=True)

# --- סעיף 6 (יחיד!) ---
with tab6:
    st.subheader("סיכום ושליחה")
    st.markdown("בדקו את התקציר. אם יש טעות – חזרו לטאב המתאים, תקנו וחזרו לכאן. לאחר אישור ולחיצה על **שליחה** המידע יישמר.")
    # תקציר נעים לקריאה
    st.markdown("### 🧑‍💻 פרטים אישיים")
    st.table(pd.DataFrame([{
        "שם פרטי": first_name, "שם משפחה": last_name, "ת״ז": nat_id, "מין": gender,
        "שיוך חברתי": social_affil,
        "שפת אם": (other_mt if mother_tongue=="אחר..." else mother_tongue),
        "שפות נוספות": "; ".join([x for x in extra_langs if x!="אחר..."] + ([extra_langs_other] if "אחר..." in extra_langs else [])),
        "טלפון": phone, "כתובת": address, "אימייל": email,
        "שנת לימודים": (study_year_other if study_year=="אחר..." else study_year),
        "מסלול לימודים": track,
        "ניידות": (mobility_other if mobility=="אחר..." else mobility),
    }]).T.rename(columns={0:"ערך"}))

    st.markdown("### 📍 העדפות שיבוץ")
    ranks_clean = {f"דירוג {k}": v for k,v in ranks.items()}
    st.table(pd.DataFrame([{
        "הכשרה קודמת": prev_training,
        "מקום/תחום (אם היה)": prev_place,
        "מדריך/מיקום": prev_mentor,
        "בן/בת זוג להתמחות": prev_partner,
        "תחומים מועדפים": "; ".join([d for d in chosen_domains if d!="אחר..."] + ([domains_other] if "אחר..." in chosen_domains else [])),
        "תחום מוביל": (top_domain if top_domain and top_domain!="— בחר/י —" else ""),
        "בקשה מיוחדת": special_request,
        **ranks_clean
    }]).T.rename(columns={0:"ערך"}))

    st.markdown("### 🎓 נתונים אקדמיים")
    st.table(pd.DataFrame([{"ממוצע ציונים": avg_grade}]).T.rename(columns={0:"ערך"}))

    st.markdown("### 🧪 התאמות")
    st.table(pd.DataFrame([{
        "התאמות": "; ".join([a for a in adjustments if a!="אחר..."] + ([adjustments_other] if "אחר..." in adjustments else [])),
        "פירוט התאמות": adjustments_details,
    }]).T.rename(columns={0:"ערך"}))

    st.markdown("### 🔥 מוטיבציה")
    st.table(pd.DataFrame([{"מוכנות להשקיע מאמץ": m1, "חשיבות ההכשרה": m2, "מחויבות והתמדה": m3}]).T.rename(columns={0:"ערך"}))

    st.markdown("---")
    confirm = st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *")
    submitted = st.button("שליחה ✉️")

# =========================
# ולידציה + שמירה (פועלת פעם אחת כשנלחץ שליחה)
# =========================
if submitted:
    errors=[]
    # סעיף 1
    if not first_name.strip(): errors.append("סעיף 1: יש למלא שם פרטי.")
    if not last_name.strip():  errors.append("סעיף 1: יש למלא שם משפחה.")
    if not valid_id(nat_id):   errors.append("סעיף 1: ת״ז חייבת להיות 8–9 ספרות.")
    if mother_tongue=="אחר..." and not other_mt.strip(): errors.append("סעיף 1: יש לציין שפת אם (אחר).")
    if not extra_langs or ("אחר..." in extra_langs and not extra_langs_other.strip()):
        errors.append("סעיף 1: יש לבחור שפות נוספות (ואם 'אחר' – לפרט).")
    if not valid_phone(phone): errors.append("סעיף 1: מספר טלפון אינו תקין.")
    if not address.strip():    errors.append("סעיף 1: יש למלא כתובת מלאה.")
    if not valid_email(email): errors.append("סעיף 1: כתובת דוא״ל אינה תקינה.")
    if study_year=="אחר..." and not study_year_other.strip(): errors.append("סעיף 1: יש לפרט שנת לימודים (אחר).")
    if not track.strip(): errors.append("סעיף 1: יש למלא מסלול לימודים/תואר.")
    if mobility=="אחר..." and not mobility_other.strip(): errors.append("סעיף 1: יש לפרט ניידות (אחר).")

    # סעיף 2
    if prev_training in ["כן","אחר..."]:
        if not prev_place.strip():  errors.append("סעיף 2: יש למלא מקום/תחום אם הייתה הכשרה קודמת.")
        if not prev_mentor.strip(): errors.append("סעיף 2: יש למלא שם מדריך ומיקום.")
        if not prev_partner.strip():errors.append("סעיף 2: יש למלא בן/בת זוג להתמחות.")
    if not chosen_domains: errors.append("סעיף 2: יש לבחור עד 3 תחומים (לפחות אחד).")
    if "אחר..." in chosen_domains and not domains_other.strip(): errors.append("סעיף 2: נבחר 'אחר' – יש לפרט תחום.")
    if chosen_domains and (top_domain not in chosen_domains): errors.append("סעיף 2: יש לבחור תחום מוביל מתוך השלושה.")
    if not unique_ranks(ranks): errors.append("סעיף 2: לא ניתן להשתמש באותו דירוג ליותר ממוסד אחד.")
    if not special_request.strip(): errors.append("סעיף 2: יש לציין בקשה מיוחדת (אפשר 'אין').")

    # סעיף 3
    if avg_grade is None or avg_grade <= 0: errors.append("סעיף 3: יש להזין ממוצע ציונים גדול מ-0.")

    # סעיף 4
    if not adjustments: errors.append("סעיף 4: יש לבחור לפחות סוג התאמה אחד (או לציין 'אין').")
    if "אחר..." in adjustments and not adjustments_other.strip(): errors.append("סעיף 4: נבחר 'אחר' – יש לפרט התאמה.")
    if not adjustments_details.strip(): errors.append("סעיף 4: יש לפרט התייחסות להתאמות (אפשר 'אין').")

    # סעיף 5
    if not (m1 and m2 and m3): errors.append("סעיף 5: יש לענות על שלוש שאלות המוטיבציה.")

    # סעיף 6
    if not confirm: errors.append("סעיף 6: יש לאשר את ההצהרה.")

    if errors:
        show_errors(errors)
    else:
        # בניית שורה לשמירה
        row = {
            "תאריך_שליחה": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "שם_פרטי": first_name.strip(), "שם_משפחה": last_name.strip(), "תעודת_זהות": nat_id.strip(),
            "מין": gender, "שיוך_חברתי": social_affil,
            "שפת_אם": (other_mt.strip() if mother_tongue=="אחר..." else mother_tongue),
            "שפות_נוספות": "; ".join([x for x in extra_langs if x!="אחר..."] + ([extra_langs_other.strip()] if "אחר..." in extra_langs else [])),
            "טלפון": phone.strip(), "כתובת": address.strip(), "אימייל": email.strip(),
            "שנת_לימודים": (study_year_other.strip() if study_year=="אחר..." else study_year),
            "מסלול_לימודים": track.strip(),
            "ניידות": (mobility_other.strip() if mobility=="אחר..." else mobility),
            "הכשרה_קודמת": prev_training,
            "הכשרה_קודמת_מקום_ותחום": prev_place.strip(),
            "הכשרה_קודמת_מדריך_ומיקום": prev_mentor.strip(),
            "הכשרה_קודמת_בן_זוג": prev_partner.strip(),
            "תחומים_מועדפים": "; ".join([d for d in chosen_domains if d!="אחר..."] + ([domains_other.strip()] if "אחר..." in chosen_domains else [])),
            "תחום_מוביל": (top_domain if top_domain and top_domain!="— בחר/י —" else ""),
            "בקשה_מיוחדת": special_request.strip(),
            "ממוצע": avg_grade,
            "התאמות": "; ".join([a for a in adjustments if a!="אחר..."] + ([adjustments_other.strip()] if "אחר..." in adjustments else [])),
            "התאמות_פרטים": adjustments_details.strip(),
            "מוטיבציה_1": m1, "מוטיבציה_2": m2, "מוטיבציה_3": m3,
        }
        # דירוגים
        row.update({f"דירוג_{k}": v for k,v in ranks.items()})

        try:
            append_row(row, CSV_FILE)
            st.success("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
            st.download_button("📥 הורדת תשובה (CSV)",
                               data=pd.DataFrame([row]).to_csv(index=False, encoding="utf-8-sig"),
                               file_name="תשובה_בודדת.csv", mime="text/csv")
        except Exception as e:
            st.error(f"❌ שמירה נכשלה: {e}")
