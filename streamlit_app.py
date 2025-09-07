import streamlit as st
import pandas as pd
from datetime import datetime

# --- כותרת כללית ---
st.title("📋 שאלון שיבוץ סטודנטים – שנת הכשרה תשפ״ו")
st.caption("התמיכה בקוראי מסך הופעלה.")

# --- יצירת שישה טאבים ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "סעיף 1: פרטים אישיים",
    "סעיף 2: העדפת שיבוץ",
    "סעיף 3: נתונים אקדמיים",
    "סעיף 4: התאמות",
    "סעיף 5: מוטיבציה",
    "סעיף 6: סיכום ושליחה"
])

# --- סעיף 1 ---
with tab1:
    st.subheader("פרטים אישיים")
    first_name = st.text_input("שם פרטי *")
    last_name = st.text_input("שם משפחה *")
    nat_id = st.text_input("תעודת זהות *")

# --- סעיף 2 ---
with tab2:
    st.subheader("העדפת שיבוץ")
    chosen_domains = st.multiselect("תחומים מועדפים *", ["קהילה", "ילדים ונוער", "זקנה"])

# --- סעיף 3 ---
with tab3:
    st.subheader("נתונים אקדמיים")
    avg_grade = st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0)

# --- סעיף 4 ---
with tab4:
    st.subheader("התאמות")
    adjustments = st.text_area("פרט/י התאמות (אם יש)")

# --- סעיף 5 ---
with tab5:
    st.subheader("מוטיבציה")
    m1 = st.radio("אני מוכן/ה להשקיע מאמץ נוסף", ["בכלל לא", "קצת", "מאוד"], horizontal=True)

# --- סעיף 6 ---
with tab6:
    st.subheader("סיכום ושליחה")
    st.markdown("בדקו את הנתונים שמילאתם לפני השליחה.")
    confirm = st.checkbox("אני מאשר/ת כי כל הפרטים נכונים *")
    submitted = st.button("שליחה ✉️")
    if submitted and confirm:
        st.success("✅ הטופס נשלח בהצלחה")
