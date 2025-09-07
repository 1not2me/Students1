import streamlit as st
import pandas as pd
from datetime import datetime
import re
from pathlib import Path
from io import BytesIO

# ===== הגדרות כלליות =====
st.set_page_config(page_title='מיפוי מדריכים לשיבוץ סטודנטים - תשפ"ו', layout='centered')

# RTL + יישור לימין לכל הרכיבים
st.markdown("""
<style>
  .stApp, .main, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
  .row-widget.stRadio > div, div[role="radiogroup"], div[data-baseweb="select"] { direction: rtl; text-align: right; }
  label, .stMarkdown, .stText, .stCaption { text-align: right !important; }
</style>
""", unsafe_allow_html=True)

# קובץ הנתונים
CSV_FILE = Path("mapping_data.csv")

# סיסמת מנהל: מומלץ לשים ב-st.secrets["ADMIN_PASSWORD"]
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "rawan_0304")

# בדיקה אם במצב מנהל (לפי פרמטר ב-URL: ?admin=1)
# streamlit>=1.32 תומך st.query_params
is_admin_mode = st.query_params.get("admin", ["0"])[0] == "1"

# ------ פונקציות עזר ------
def load_df(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path, encoding="utf-8-sig")

def save_df_append(row: dict, csv_path: Path):
    df = pd.DataFrame([row])
    header = not csv_path.exists()
    df.to_csv(csv_path, mode="a", index=False, encoding="utf-8-sig", header=header)

def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Responses") -> bytes:
    """ייצוא DataFrame לקובץ Excel בזיכרון"""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        wb  = writer.book
        ws  = writer.sheets[sheet_name]
        # התאמת רוחב עמודות בסיסית
        for i, col in enumerate(df.columns):
            width = min(60, max(12, int(df[col].astype(str).map(len).max()) + 4 if not df.empty else 12))
            ws.set_column(i, i, width)
    buf.seek(0)
    return buf.read()

def validate_phone(v: str) -> bool:
    v = v.strip()
    # תומך "050-1234567" או "0501234567" (כולל 02/03/04/08 וכו')
    return bool(re.match(r"^0\d{1,2}-?\d{6,7}$", v))

def validate_email(v: str) -> bool:
    v = v.strip()
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", v))

# ===== מצב מנהל =====
if is_admin_mode:
    st.title("🔑 גישת מנהל - צפייה וייצוא נתונים")
    password = st.text_input("הכנסי סיסמת מנהל:", type="password",
                              help="מומלץ להגדיר ADMIN_PASSWORD ב-st.secrets לצורך אבטחה טובה יותר.")
    if password:
        if password == ADMIN_PASSWORD:
            st.success("התחברת בהצלחה ✅")
            df = load_df(CSV_FILE)
            if df.empty:
                st.info("אין עדיין נתונים בקובץ.")
            else:
                st.subheader("טבלת נתונים")
                st.dataframe(df, use_container_width=True)

                with st.expander("סינון והורדות", expanded=True):
                    cols_sel = st.multiselect("בחרי עמודות להצגה", df.columns.tolist(), default=df.columns.tolist())
                    view_df = df[cols_sel] if cols_sel else df

                    # אופציונלי: שאילתת pandas.query למשתמשת מתקדמת
                    query = st.text_input("סינון (pandas.query), לדוגמה: `עיר == \"נהריה\" and מספר_סטודנטים > 1`")
                    if st.button("החילי סינון"):
                        try:
                            view_df = view_df.query(query) if query.strip() else view_df
                            st.success("הסינון הוחל.")
                        except Exception as e:
                            st.error(f"שגיאה בביטוי הסינון: {e}")

                    st.dataframe(view_df, use_container_width=True)

                    # הורדת Excel (תצוגה מסוננת)
                    xlsx_filtered = dataframe_to_excel_bytes(view_df)
                    st.download_button(
                        "📥 הורדת Excel (התצוגה הנוכחית)",
                        data=xlsx_filtered,
                        file_name="mapping_data_filtered.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # הורדת Excel (כל הנתונים)
                    xlsx_all = dataframe_to_excel_bytes(df)
                    st.download_button(
                        "📥 הורדת Excel (כל הנתונים)",
                        data=xlsx_all,
                        file_name="mapping_data_all.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                # הורדת CSV (מי שרוצה)
                st.download_button(
                    "📥 הורדת CSV (כל הנתונים)",
                    data=df.to_csv(index=False, encoding='utf-8-sig'),
                    file_name="mapping_data.csv",
                    mime="text/csv"
                )
        else:
            st.error("סיסמה שגויה")
    st.stop()

# ===== טופס למילוי =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו")
st.write("""
שלום רב, מטרת טופס זה היא לאסוף מידע עדכני על מדריכים ומוסדות הכשרה לקראת שיבוץ הסטודנטים לשנת ההכשרה הקרובה.  
אנא מלא/י את כל השדות בצורה מדויקת. המידע ישמש לצורך תכנון השיבוץ בלבד.
""")

with st.form("mapping_form"):
    st.subheader("פרטים אישיים")
    last_name = st.text_input("שם משפחה *")
    first_name = st.text_input("שם פרטי *")

    st.subheader("מוסד והכשרה")
    institution = st.text_input("מוסד / שירות ההכשרה *")
    specialization = st.selectbox("תחום ההתמחות *", ["Please Select", "חינוך", "בריאות", "רווחה", "אחר"])
    specialization_other = ""
    if specialization == "אחר":
        specialization_other = st.text_input("אם ציינת 'אחר' – כתבי את תחום ההתמחות *")

    st.subheader("כתובת מקום ההכשרה")
    street = st.text_input("רחוב *")
    city = st.text_input("עיר *")
    postal_code = st.text_input("מיקוד *")

    st.subheader("קליטת סטודנטים")
    num_students = st.number_input("מספר סטודנטים שניתן לקלוט השנה *", min_value=0, step=1)
    continue_mentoring = st.radio("האם מעוניין/ת להמשיך להדריך השנה? *", ["כן", "לא"], horizontal=True)

    st.subheader("פרטי התקשרות")
    phone = st.text_input("טלפון * (לדוגמה: 050-1234567 או 0501234567)")
    email = st.text_input("כתובת אימייל *")

    submit_btn = st.form_submit_button("שלח/י")

# ===== טיפול בטופס =====
if submit_btn:
    errors = []

    if not last_name.strip():
        errors.append("יש למלא שם משפחה")
    if not first_name.strip():
        errors.append("יש למלא שם פרטי")
    if not institution.strip():
        errors.append("יש למלא מוסד/שירות ההכשרה")
    if specialization == "Please Select":
        errors.append("יש לבחור תחום התמחות")
    if specialization == "אחר" and not specialization_other.strip():
        errors.append("יש למלא את תחום ההתמחות")
    if not street.strip():
        errors.append("יש למלא רחוב")
    if not city.strip():
        errors.append("יש למלא עיר")
    if not postal_code.strip():
        errors.append("יש למלא מיקוד")
    if num_students <= 0:
        errors.append("יש להזין מספר סטודנטים גדול מ-0")
    if not validate_phone(phone):
        errors.append("מספר הטלפון אינו תקין")
    if not validate_email(email):
        errors.append("כתובת האימייל אינה תקינה")

    if errors:
        for e in errors:
            st.error(e)
    else:
        row = {
            "תאריך": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "שם משפחה": last_name.strip(),
            "שם פרטי": first_name.strip(),
            "מוסד/שירות ההכשרה": institution.strip(),
            "תחום התמחות": (specialization_other.strip() if specialization == "אחר" else specialization),
            "רחוב": street.strip(),
            "עיר": city.strip(),
            "מיקוד": postal_code.strip(),
            "מספר סטודנטים": int(num_students),
            "המשך הדרכה": continue_mentoring,
            "טלפון": phone.strip(),
            "אימייל": email.strip()
        }

        try:
            save_df_append(row, CSV_FILE)
            st.success("✅ הנתונים נשמרו בהצלחה!")
        except Exception as ex:
            st.error(f"❌ שמירה נכשלה: {ex}")
