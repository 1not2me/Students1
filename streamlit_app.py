def style_google_sheet(ws):
    """Apply styling to the Google Sheet similar to the screenshot."""
    # צבע כותרת: רקע כחול, טקסט לבן מודגש
    header_fmt = CellFormat(
        backgroundColor=Color(0.2, 0.4, 0.8),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment='CENTER'
    )
    format_cell_range(ws, "1:1", header_fmt)  # כל שורת הכותרת

    # צבעים מתחלפים לשורות
    rule = ConditionalFormatRule(
        ranges=[GridRange.from_a1_range('A2:Z1000', ws)],
        booleanRule=BooleanRule(
            condition={'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': '=ISEVEN(ROW())'}]},
            format=CellFormat(backgroundColor=Color(0.95, 0.95, 0.95))
        )
    )
    rules = get_conditional_format_rules(ws)
    rules.append(rule)
    rules.save()

    # עמודה ראשונה (ID / ת"ז) בצבעים שונים
    id_fmt = CellFormat(
        horizontalAlignment='CENTER',
        backgroundColor=Color(0.9, 0.9, 0.9)
    )
    format_cell_range(ws, "A2:A1000", id_fmt)

# בתוך save_master_dataframe, אחרי שמכניסים כותרות:
if not headers or headers != COLUMNS_ORDER:
    sheet.clear()
    sheet.append_row(COLUMNS_ORDER, value_input_option="USER_ENTERED")
    style_google_sheet(sheet)   # <<<< כאן מוסיפים


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
# טופס — טאבים
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
    st.subheader("פרטים אישיים של הסטודנט/ית")
    first_name = st.text_input("שם פרטי *")
    last_name  = st.text_input("שם משפחה *")
    nat_id     = st.text_input("מספר תעודת זהות *")
    gender = st.radio("מין *", ["זכר","נקבה"], horizontal=True)
    social_affil = st.selectbox("שיוך חברתי *", ["יהודי/ה","מוסלמי/ת","נוצרי/ה","דרוזי/ת"])
    mother_tongue = st.selectbox("שפת אם *", ["עברית","ערבית","רוסית","אחר..."])
    other_mt = st.text_input("ציין/ני שפת אם אחרת *") if mother_tongue == "אחר..." else ""
    extra_langs = st.multiselect(
        "ציין/י שפות נוספות (ברמת שיחה) *",
        ["עברית","ערבית","רוסית","אמהרית","אנגלית","ספרדית","אחר..."],
        placeholder="בחר/י שפות נוספות"
    )
    extra_langs_other = st.text_input("ציין/י שפה נוספת (אחר) *") if "אחר..." in extra_langs else ""
    phone   = st.text_input("מספר טלפון נייד * (למשל 050-1234567)")
    address = st.text_input("כתובת מלאה (כולל יישוב) *")
    email   = st.text_input("כתובת דוא״ל *")
    study_year = st.selectbox("שנת הלימודים *", [
        "תואר ראשון - שנה א'", "תואר ראשון - שנה ב'", "תואר ראשון - שנה ג'",
        "הסבה א'", "הסבה ב'", "אחר..."
    ])
    study_year_other = st.text_input("ציין/י שנה/מסלול אחר *") if study_year == "אחר..." else ""
    track = st.text_input("מסלול לימודים / תואר *")
    mobility = st.selectbox("אופן ההגעה להתמחות (ניידות) *", [
        "אוכל להיעזר ברכב / ברשותי רכב",
        "אוכל להגיע בתחבורה ציבורית",
        "אחר..."
    ])
    mobility_other = st.text_input("פרט/י אחר לגבי ניידות *") if mobility == "אחר..." else ""

# --- סעיף 2 ---
with tab2:
    st.subheader("העדפת שיבוץ")

    prev_training = st.selectbox("האם עברת הכשרה מעשית בשנה קודמת? *", ["כן","לא","אחר..."])
    prev_place = prev_mentor = prev_partner = ""
    if prev_training in ["כן","אחר..."]:
        prev_place  = st.text_input("אם כן, נא ציין שם מקום ותחום ההתמחות *")
        prev_mentor = st.text_input("שם המדריך והמיקום הגיאוגרפי של ההכשרה *")
        prev_partner= st.text_input("מי היה/תה בן/בת הזוג להתמחות בשנה הקודמת? *")

    all_domains = ["קהילה","מוגבלות","זקנה","ילדים ונוער","בריאות הנפש","שיקום","משפחה","נשים","בריאות","תָקוֹן","אחר..."]
    chosen_domains = st.multiselect("בחרו עד 3 תחומים *", all_domains, max_selections=3, placeholder="בחר/י עד שלושה תחומים")
    domains_other = st.text_input("פרט/י תחום אחר *") if "אחר..." in chosen_domains else ""
    top_domain = st.selectbox(
        "מה התחום הכי מועדף עליך, מבין שלושתם? *",
        ["— בחר/י —"] + chosen_domains if chosen_domains else ["— בחר/י —"]
    )

    st.markdown("**בחר/י מוסד לכל מדרגה דירוג (1 = הכי רוצים, 3 = הכי פחות). הבחירה כובלת קדימה — מוסדות שנבחרו ייעלמו מהמדרגות הבאות.**")

    # אתחול מצב הבחירות
    for i in range(1, RANK_COUNT + 1):
        st.session_state.setdefault(f"rank_{i}", "— בחר/י —")

    def options_for_rank(rank_i: int) -> list:
        current = st.session_state.get(f"rank_{rank_i}", "— בחר/י —")
        chosen_before = {
            st.session_state.get(f"rank_{j}")
            for j in range(1, rank_i)
        }
        base = ["— בחר/י —"] + [s for s in SITES if (s not in chosen_before or s == current)]
        ordered = ["— בחר/י —"] + [s for s in SITES if s in base]
        return ordered

    cols = st.columns(2)
    for i in range(1, RANK_COUNT + 1):
        with cols[(i - 1) % 2]:
            opts = options_for_rank(i)
            current = st.session_state.get(f"rank_{i}", "— בחר/י —")
            st.session_state[f"rank_{i}"] = st.selectbox(
                f"מדרגה {i} (בחר/י מוסד)*",
                options=opts,
                index=opts.index(current) if current in opts else 0,
                key=f"rank_{i}_select"
            )
            st.session_state[f"rank_{i}"] = st.session_state[f"rank_{i}_select"]

    used = set()
    for i in range(1, RANK_COUNT + 1):
        sel = st.session_state.get(f"rank_{i}", "— בחר/י —")
        if sel != "— בחר/י —":
            if sel in used:
                st.session_state[f"rank_{i}"] = "— בחר/י —"
                st.session_state[f"rank_{i}_select"] = "— בחר/י —"
            else:
                used.add(sel)

    special_request = st.text_area("האם קיימת בקשה מיוחדת הקשורה למיקום או תחום ההתמחות? *", height=100)


# --- סעיף 3 ---
with tab3:
    st.subheader("נתונים אקדמיים")
    avg_grade = st.number_input("ממוצע ציונים *", min_value=0.0, max_value=100.0, step=0.1)

# --- סעיף 4 ---
with tab4:
    st.subheader("התאמות רפואיות, אישיות וחברתיות")
    adjustments = st.multiselect(
        "סוגי התאמות (ניתן לבחור כמה) *",
        ["הריון","מגבלה רפואית (למשל: מחלה כרונית, אוטואימונית)","רגישות למרחב רפואי (למשל: לא לשיבוץ בבית חולים)",
         "אלרגיה חמורה","נכות","רקע משפחתי רגיש (למשל: בן משפחה עם פגיעה נפשית)","אחר..."],
        placeholder="בחר/י אפשרויות התאמה"
    )
    adjustments_other = st.text_input("פרט/י התאמה אחרת *") if "אחר..." in adjustments else ""
    adjustments_details = st.text_area("פרט: *", height=100)

# --- סעיף 5 ---
with tab5:
    st.subheader("מוטיבציה")
    likert = ["בכלל לא מסכים/ה","1","2","3","4","מסכים/ה מאוד"]
    m1 = st.radio("1) מוכן/ה להשקיע מאמץ נוסף להגיע למקום המועדף *", likert, horizontal=True)
    m2 = st.radio("2) ההכשרה המעשית חשובה לי כהזדמנות משמעותית להתפתחות *", likert, horizontal=True)
    m3 = st.radio("3) אהיה מחויב/ת להגיע בזמן ולהתמיד גם בתנאים מאתגרים *", likert, horizontal=True)

# --- סעיף 6 (סיכום ושליחה) ---
with tab6:
    st.subheader("סיכום ושליחה")
    st.markdown("בדקו את התקציר. אם יש טעות – חזרו לטאב המתאים, תקנו וחזרו לכאן. לאחר אישור ולחיצה על **שליחה** המידע יישמר.")

    # מיפוי מדרגה->מוסד + מוסד->מדרגה
    rank_to_site = {i: st.session_state.get(f"rank_{i}", "— בחר/י —") for i in range(1, RANK_COUNT + 1)}
    site_to_rank = {s: None for s in SITES}
    for i, s in rank_to_site.items():
        if s and s != "— בחר/י —":
            site_to_rank[s] = i

    st.markdown("### 📍 העדפות שיבוץ (1=הכי רוצים)")
    summary_pairs = [f"{rank_to_site[i]} – {i}" if rank_to_site[i] != "— בחר/י —" else f"(לא נבחר) – {i}"
                     for i in range(1, RANK_COUNT + 1)]
    st.table(pd.DataFrame({"דירוג": summary_pairs}))

    st.markdown("### 🧑‍💻 פרטים אישיים")
    st.table(pd.DataFrame([{
        "שם פרטי": first_name, "שם משפחה": last_name, "ת״ז": nat_id, "מין": gender,
        "שיוך חברתי": social_affil,
        "שפת אם": (other_mt if mother_tongue == "אחר..." else mother_tongue),
        "שפות נוספות": "; ".join([x for x in extra_langs if x != "אחר..."] + ([extra_langs_other] if "אחר..." in extra_langs else [])),
        "טלפון": phone, "כתובת": address, "אימייל": email,
        "שנת לימודים": (study_year_other if study_year == "אחר..." else study_year),
        "מסלול לימודים": track,
        "ניידות": (mobility_other if mobility == "אחר..." else mobility),
    }]).T.rename(columns={0: "ערך"}))

    st.markdown("### 🎓 נתונים אקדמיים")
    st.table(pd.DataFrame([{"ממוצע ציונים": avg_grade}]).T.rename(columns={0: "ערך"}))

    st.markdown("### 🧪 התאמות")
    st.table(pd.DataFrame([{
        "התאמות": "; ".join([a for a in adjustments if a != "אחר..."] + ([adjustments_other] if "אחר..." in adjustments else [])),
        "פירוט התאמות": adjustments_details,
    }]).T.rename(columns={0: "ערך"}))

    st.markdown("### 🔥 מוטיבציה")
    st.table(pd.DataFrame([{"מוכנות להשקיע מאמץ": m1, "חשיבות ההכשרה": m2, "מחויבות והתמדה": m3}]).T.rename(columns={0: "ערך"}))

    st.markdown("---")
    confirm = st.checkbox("אני מאשר/ת כי המידע שמסרתי נכון ומדויק, וידוע לי שאין התחייבות להתאמה מלאה לבחירותיי. *")
    submitted = st.button("שליחה ✉️")

# =========================
# ולידציה + שמירה
# =========================
if submitted:
    errors = []

    # סעיף 1 — בסיסי
    if not first_name.strip(): errors.append("סעיף 1: יש למלא שם פרטי.")
    if not last_name.strip():  errors.append("סעיף 1: יש למלא שם משפחה.")
    if not valid_id(nat_id):   errors.append("סעיף 1: ת״ז חייבת להיות 8–9 ספרות.")
    if mother_tongue == "אחר..." and not other_mt.strip():
        errors.append("סעיף 1: יש לציין שפת אם (אחר).")
    if not extra_langs or ("אחר..." in extra_langs and not extra_langs_other.strip()):
        errors.append("סעיף 1: יש לבחור שפות נוספות (ואם 'אחר' – לפרט).")
    if not valid_phone(phone): errors.append("סעיף 1: מספר טלפון אינו תקין.")
    if not address.strip():    errors.append("סעיף 1: יש למלא כתובת מלאה.")
    if not valid_email(email): errors.append("סעיף 1: כתובת דוא״ל אינה תקינה.")
    if study_year == "אחר..." and not study_year_other.strip():
        errors.append("סעיף 1: יש לפרט שנת לימודים (אחר).")
    if not track.strip(): errors.append("סעיף 1: יש למלא מסלול לימודים/תואר.")
    if mobility == "אחר..." and not mobility_other.strip():
        errors.append("סעיף 1: יש לפרט ניידות (אחר).")

    # סעיף 2 — דירוג חובה 1..10 ללא כפילויות
    rank_to_site = {i: st.session_state.get(f"rank_{i}", "— בחר/י —") for i in range(1, RANK_COUNT + 1)}
    missing = [i for i, s in rank_to_site.items() if s == "— בחר/י —"]
    if missing:
        errors.append(f"סעיף 2: יש לבחור מוסד לכל מדרגה. חסר/ים: {', '.join(map(str, missing))}.")
    chosen_sites = [s for s in rank_to_site.values() if s != "— בחר/י —"]
    if len(set(chosen_sites)) != len(chosen_sites):
        errors.append("סעיף 2: קיימת כפילות בבחירת מוסדות. כל מוסד יכול להופיע פעם אחת בלבד.")

    if prev_training in ["כן","אחר..."]:
        if not prev_place.strip():  errors.append("סעיף 2: יש למלא מקום/תחום אם הייתה הכשרה קודמת.")
        if not prev_mentor.strip(): errors.append("סעיף 2: יש למלא שם מדריך ומיקום.")
        if not prev_partner.strip():errors.append("ಸעיף 2: יש למלא בן/בת זוג להתמחות.")

    if not chosen_domains:
        errors.append("סעיף 2: יש לבחור עד 3 תחומים (לפחות אחד).")
    if "אחר..." in chosen_domains and not domains_other.strip():
        errors.append("סעיף 2: נבחר 'אחר' – יש לפרט תחום.")
    if chosen_domains and (top_domain not in chosen_domains):
        errors.append("סעיף 2: יש לבחור תחום מוביל מתוך השלושה.")

    if not special_request.strip():
        errors.append("סעיף 2: יש לציין בקשה מיוחדת (אפשר 'אין').")

    # סעיף 3
    if avg_grade is None or avg_grade <= 0:
        errors.append("סעיף 3: יש להזין ממוצע ציונים גדול מ-0.")

    # סעיף 4
    if not adjustments:
        errors.append("סעיף 4: יש לבחור לפחות סוג התאמה אחד (או לציין 'אין').")
    if "אחר..." in adjustments and not adjustments_other.strip():
        errors.append("סעיף 4: נבחר 'אחר' – יש לפרט התאמה.")
    if not adjustments_details.strip():
        errors.append("סעיף 4: יש לפרט התייחסות להתאמות (אפשר 'אין').")

    # סעיף 5
    if not (m1 and m2 and m3):
        errors.append("סעיף 5: יש לענות על שלוש שאלות המוטיבציה.")

    # סעיף 6
    if not confirm:
        errors.append("סעיף 6: יש לאשר את ההצהרה.")

    if errors:
        show_errors(errors)
    else:
        # מפות דירוג לשמירה
        site_to_rank = {s: None for s in SITES}
        for i in range(1, RANK_COUNT + 1):
            site = st.session_state.get(f"rank_{i}")
            site_to_rank[site] = i

        # בניית שורה לשמירה (שימי לב: אין שבירת מחרוזות בעברית)
        tz = pytz.timezone("Asia/Jerusalem")
        row = {
            "תאריך שליחה": datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S"),
            "שם פרטי": first_name.strip(),
            "שם משפחה": last_name.strip(),
            "תעודת זהות": nat_id.strip(),
            "מין": gender,
            "שיוך חברתי": social_affil,
            "שפת אם": (other_mt.strip() if mother_tongue == "אחר..." else mother_tongue),
            "שפות_נוספות": "; ".join([x for x in extra_langs if x != "אחר..."] + ([extra_langs_other.strip()] if "אחר..." in extra_langs else [])),
            "טלפון": phone.strip(),
            "כתובת": address.strip(),
            "אימייל": email.strip(),
            "שנת לימודים": (study_year_other.strip() if study_year == "אחר..." else study_year),
            "מסלול לימודים": track.strip(),
            "ניידות": (mobility_other.strip() if mobility == "אחר..." else mobility),
            "הכשרה קודמת": prev_training,
            "הכשרה קודמת מקום ותחום": prev_place.strip(),
            "הכשרה קודמת מדריך ומיקום": prev_mentor.strip(),
            "הכשרה קודמת בן זוג": prev_partner.strip(),
            "תחומים מועדפים": "; ".join([d for d in chosen_domains if d != "אחר..."] + ([domains_other.strip()] if "אחר..." in chosen_domains else [])),
            "תחום מוביל": (top_domain if top_domain and top_domain != "— בחר/י —" else ""),
            "בקשה מיוחדת": special_request.strip(),
            "ממוצע": avg_grade,
            "התאמות": "; ".join([a for a in adjustments if a != "אחר..."] + ([adjustments_other.strip()] if "אחר..." in adjustments else [])),
            "התאמות פרטים": adjustments_details.strip(),
            "מוטיבציה 1": m1,
            "מוטיבציה 2": m2,
            "מוטיבציה 3": m3,
        }

        # הוספת שדות דירוג:
        # 1) Rank_i -> Site (מוסד שנבחר לכל מדרגה)
        for i in range(1, RANK_COUNT + 1):
            row[f"דירוג_מדרגה_{i}_מוסד"] = st.session_state.get(f"rank_{i}")
        # 2) Site -> Rank (לשימוש נוח ב-Excel)
        for s in SITES:
            row[f"דירוג_{s}"] = site_to_rank[s]

        try:
            # שמירה במאסטר + Google Sheets
            save_master_dataframe(row)

            # יומן Append-Only
            append_to_log(pd.DataFrame([row]))

            st.success("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.")
        except Exception as e:
            st.error(f"❌ שמירה נכשלה: {e}")
