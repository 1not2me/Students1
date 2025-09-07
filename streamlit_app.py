import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from pathlib import Path
from io import BytesIO

# =========================
# הגדרות
# =========================
st.set_page_config(page_title="שאלון", page_icon="📝", layout="centered")

# כיוון מימין לשמאל + יישור לימין (כולל קבוצות רדיו/צ'קבוקסים)
st.markdown("""
<style>
  .stApp, .main, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
  label, .stMarkdown, .stText, .stCaption, .st-emotion-cache-1y4p8pa { text-align: right; }
  div[role="radiogroup"], div[data-baseweb="select"] { direction: rtl; text-align: right; }
  .row-widget.stRadio > div { direction: rtl; }
  .st-emotion-cache-1dp5vir { text-align: right; } /* טקסט עזרה */
</style>
""", unsafe_allow_html=True)

# מיקום קובץ התשובות
RESPONSES_CSV = Path("responses.csv")

# סיסמת מנהל (לבדיקות מקומי). לפרודקשן – ממליץ לשים ב-st.secrets["ADMIN_PASSWORD"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "1234")

# =========================
# סכימת שאלות (החליפי לשאלון שלך)
# type נתמכים: text, textarea, number, radio, checkbox, multiselect, select, slider, date, time, file
# =========================
FORM_SCHEMA = [
    {"id": "full_name", "label": "שם מלא", "type": "text", "required": True, "placeholder": "רואן סעב"},
    {"id": "email", "label": "אימייל", "type": "text", "required": True,
     "validators": {"regex": r"^[^\s@]+@[^\s@]+\.[^\s@]+$", "message": "כתובת אימייל לא תקינה."}},
    {"id": "track", "label": "מסלול מועדף", "type": "radio", "required": True,
     "options": ["תוכנה", "מידע רפואי", "לא החלטתי עדיין"]},
    {"id": "skills", "label": "מיומנויות (אפשר לבחור כמה)", "type": "multiselect", "options": ["Python","Java","Excel","SQL","מנהיגות","הנחיית קבוצות"]},
    {"id": "motivation", "label": "מה המוטיבציה שלך להצטרף? (עד 600 תווים)", "type": "textarea", "required": True, "max_chars": 600},
    {"id": "availability", "label": "זמינות יומית משוערת (שעות)", "type": "slider", "required": True, "min_value": 0, "max_value": 10, "value": 2},
    {"id": "agree", "label": "אני מאשר/ת שימוש במידע לצורכי שיבוץ", "type": "checkbox", "required": True},
]

# =========================
# פונקציות עזר
# =========================
def render_field(q):
    t = q["type"]
    label = q["label"]
    key = q["id"]
    help_txt = q.get("help")

    if t == "text":
        return st.text_input(label, key=key, placeholder=q.get("placeholder",""), help=help_txt)
    if t == "textarea":
        return st.text_area(label, key=key, max_chars=q.get("max_chars"), height=q.get("height",140), help=help_txt)
    if t == "number":
        return st.number_input(label, key=key, min_value=q.get("min_value"), max_value=q.get("max_value"),
                               step=q.get("step",1), help=help_txt)
    if t == "radio":
        return st.radio(label, options=q.get("options",[]), key=key, help=help_txt)
    if t == "select":
        return st.selectbox(label, options=q.get("options",[]), key=key, help=help_txt)
    if t == "multiselect":
        return st.multiselect(label, options=q.get("options",[]), key=key, help=help_txt)
    if t == "checkbox":
        return st.checkbox(label, key=key, help=help_txt)
    if t == "slider":
        return st.slider(label, min_value=q.get("min_value",0), max_value=q.get("max_value",10),
                         value=q.get("value",0), step=q.get("step",1), key=key, help=help_txt)
    if t == "date":
        return st.date_input(label, key=key, help=help_txt)
    if t == "time":
        return st.time_input(label, key=key, help=help_txt)
    if t == "file":
        return st.file_uploader(label, type=q.get("type_filter"), accept_multiple_files=q.get("accept_multiple_files", False),
                                key=key, help=help_txt)

    st.warning(f"סוג שדה לא נתמך: {t}")
    return None

def validate_required(q, value):
    if q.get("required", False):
        if q["type"] == "checkbox" and value is not True:
            return False, "יש לסמן את התיבה."
        if q["type"] == "multiselect" and (not value):
            return False, "יש לבחור לפחות אפשרות אחת."
        if q["type"] == "file" and (value is None or (isinstance(value, list) and len(value)==0)):
            return False, "יש להעלות קובץ."
        if q["type"] not in ("checkbox","multiselect","file"):
            if value is None or (isinstance(value,str) and value.strip()==""):
                return False, "שדה זה הוא חובה."
    # בדיקות Regex
    validators = q.get("validators")
    if validators and validators.get("regex") and isinstance(value, str):
        import re
        if not re.match(validators["regex"], value.strip()):
            return False, validators.get("message","הערך אינו תקין.")
    return True, None

def normalize_value_for_csv(v):
    if isinstance(v, list):
        return "; ".join(map(str, v))
    if hasattr(v, "name"):  # קבצים – נשמור רק את שם הקובץ
        return v.name
    return v

def append_row_to_csv(row: dict, csv_path: Path):
    df_new = pd.DataFrame([row])
    header = not csv_path.exists()
    df_new.to_csv(csv_path, mode="a", index=False, encoding="utf-8-sig", header=header)

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Responses", index=False)
        # עיצוב בסיסי
        workbook  = writer.book
        worksheet = writer.sheets["Responses"]
        for i, col in enumerate(df.columns):
            col_width = max(12, min(60, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
            worksheet.set_column(i, i, col_width)
    buf.seek(0)
    return buf.read()

# =========================
# ניווט
# =========================
page = st.sidebar.radio("ניווט", ["מילוי טופס", "מנהל 🔐"], index=0)

# =========================
# עמוד מילוי טופס
# =========================
if page == "מילוי טופס":
    st.title("📝 שאלון")
    st.caption("מוכן ל-RTL, שמירת תשובות ל-CSV והפקת Excel בעמוד המנהל.")

    with st.form("survey_form", clear_on_submit=False):
        values = {}
        for q in FORM_SCHEMA:
            values[q["id"]] = render_field(q)
        submitted = st.form_submit_button("שליחה")

    if submitted:
        # בדיקות חובה
        errors = {}
        for q in FORM_SCHEMA:
            ok, msg = validate_required(q, values[q["id"]])
            if not ok:
                errors[q["id"]] = msg

        if errors:
            st.error("יש שגיאות בטופס. נא לתקן ולנסות שוב.")
            for q in FORM_SCHEMA:
                if q["id"] in errors:
                    st.markdown(f"**{q['label']}**: :red[{errors[q['id']]}]")
        else:
            row = {"_response_id": str(uuid.uuid4()), "_submitted_at": datetime.now().isoformat(timespec="seconds")}
            for q in FORM_SCHEMA:
                row[q["id"]] = normalize_value_for_csv(values[q["id"]])

            try:
                append_row_to_csv(row, RESPONSES_CSV)
                st.success("התשובה נשמרה בהצלחה! 🎉")
                # הורדה של שורת התשובה (CSV)
                st.download_button(
                    "הורדת שורת התשובה (CSV)",
                    data=pd.DataFrame([row]).to_csv(index=False, encoding="utf-8-sig"),
                    file_name=f"response_{row['_response_id']}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"נכשלה שמירת התשובה: {e}")

# =========================
# עמוד מנהל
# =========================
if page == "מנהל 🔐":
    st.title("ממשק מנהל")
    st.caption("צפייה בנתוני המועמדים והורדה ל-Excel. (שימי לב: זו אינה אבטחה חזקה—לפרודקשן השתמשי ב-st.secrets או ב-Auth מאובטח)")

    # אימות בסיסי
    pwd = st.text_input("סיסמה", type="password", help="ברירת מחדל לדוגמה בקוד: 1234 (מומלץ להגדיר ב-st.secrets).")
    if st.button("כניסה"):
        st.session_state["_is_admin"] = (pwd == ADMIN_PASSWORD)

    if st.session_state.get("_is_admin", False):
        if RESPONSES_CSV.exists():
            df = pd.read_csv(RESPONSES_CSV)
            st.subheader("טבלת נתונים")
            st.dataframe(df, use_container_width=True)

            # סינון מהיר
            with st.expander("סינון חכם"):
                cols = st.multiselect("בחרי עמודות להצגה", df.columns.tolist(), default=df.columns.tolist())
                df_view = df[cols] if cols else df
                query = st.text_input("סינון טקסטואלי (שאילתת pandas.query, אופציונלי). דוגמה: track == 'תוכנה'")
                if st.button("החילי סינון"):
                    try:
                        df_view = df_view.query(query) if query.strip() else df_view
                        st.success("סינון הוחל.")
                    except Exception as e:
                        st.error(f"שגיאה בביטוי הסינון: {e}")
                st.dataframe(df_view, use_container_width=True)

                # הורדת Excel לפי התצוגה המסוננת
                excel_bytes = dataframe_to_excel_bytes(df_view)
                st.download_button(
                    "הורדת Excel (התצוגה הנוכחית)",
                    data=excel_bytes,
                    file_name="responses.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # הורדת כל הנתונים כפי שהם
            excel_all = dataframe_to_excel_bytes(df)
            st.download_button(
                "הורדת Excel (כל הנתונים)",
                data=excel_all,
                file_name="responses_all.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("עדיין אין נתונים. קובץ responses.csv לא נמצא.")
    else:
        st.warning("יש להזין סיסמה נכונה כדי להיכנס לממשק המנהל.")
