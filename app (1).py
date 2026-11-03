import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import calendar
import urllib.parse

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="Pocket & Khata Tracker",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM DARK THEME (YELLOW & DARK ORANGE ACCENTS) ----------------
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }
    .metric-card {
        background: linear-gradient(145deg, #181c24, #12151c);
        border: 1px solid #2d3340;
        border-left: 5px solid #ff6b00;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        margin-bottom: 12px;
    }
    .metric-title {
        color: #9ba3b0;
        font-size: 0.88rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-value {
        color: #ffb703;
        font-size: 1.75rem;
        font-weight: 800;
        margin-top: 6px;
    }
    .metric-sub {
        color: #ff6b00;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .khata-card {
        background-color: #161922;
        border: 1px solid #ff6b00;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(255, 107, 0, 0.12);
        margin-bottom: 15px;
    }
    .wa-btn {
        display: inline-block;
        background: linear-gradient(90deg, #25D366, #128C7E);
        color: white !important;
        padding: 10px 18px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 700;
        font-size: 0.9rem;
        margin-top: 12px;
        width: 100%;
        text-align: center;
        box-shadow: 0 3px 8px rgba(37, 211, 102, 0.3);
    }
    .wa-btn:hover {
        opacity: 0.92;
    }
    .badge-owe {
        background-color: rgba(255, 75, 75, 0.15);
        color: #ff4b4b;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
    }
    .badge-get {
        background-color: rgba(0, 230, 118, 0.15);
        color: #00e676;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE SETUP (SQLite) ----------------
conn = sqlite3.connect("budget_khata.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS personal_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_date TEXT,
    title TEXT,
    category TEXT,
    amount REAL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS shared_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_date TEXT,
    description TEXT,
    paid_by TEXT,
    total_amount REAL,
    share_p1 REAL,
    share_p2 REAL,
    share_p3 REAL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    settle_date TEXT,
    from_person TEXT,
    to_person TEXT,
    amount REAL
)""")
conn.commit()

# ---------------- HELPER FUNCTIONS ----------------
def get_setting(key, default):
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    return row[0] if row else default

def set_setting(key, value):
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

def calculate_net_balances(friends):
    """Calculates exactly who owes whom after all bills and settlements."""
    p1, p2, p3 = friends
    raw_debt = {p: {q: 0.0 for q in friends if q != p} for p in friends}

    c.execute("SELECT paid_by, share_p1, share_p2, share_p3 FROM shared_bills")
    for paid_by, s1, s2, s3 in c.fetchall():
        shares = {p1: s1, p2: s2, p3: s3}
        if paid_by in friends:
            for person, share_amt in shares.items():
                if person != paid_by:
                    raw_debt[person][paid_by] += share_amt

    c.execute("SELECT from_person, to_person, amount FROM settlements")
    for frm, to, amt in c.fetchall():
        if frm in raw_debt and to in raw_debt[frm]:
            raw_debt[frm][to] -= amt

    net_pairs = []
    for i in range(3):
        for j in range(i + 1, 3):
            u, v = friends[i], friends[j]
            diff = raw_debt[u][v] - raw_debt[v][u]
            if diff > 0.5:
                net_pairs.append({"from": u, "to": v, "amount": round(diff)})
            elif diff < -0.5:
                net_pairs.append({"from": v, "to": u, "amount": round(-diff)})
    return net_pairs

def make_whatsapp_link(phone, message):
    clean_phone = ''.join(filter(str.isdigit, phone))
    if clean_phone.startswith("03") and len(clean_phone) == 11:
        clean_phone = "92" + clean_phone[1:]
    encoded_msg = urllib.parse.quote(message)
    if clean_phone:
        return f"https://wa.me/{clean_phone}?text={encoded_msg}"
    return f"https://wa.me/?text={encoded_msg}"

# ---------------- LOAD SETTINGS ----------------
p1_name = get_setting("p1_name", "Ukasha")
p2_name = get_setting("p2_name", "Dost 1")
p3_name = get_setting("p3_name", "Dost 2")

p1_phone = get_setting("p1_phone", "923000000000")
p2_phone = get_setting("p2_phone", "923000000000")
p3_phone = get_setting("p3_phone", "923000000000")

monthly_budget = float(get_setting("monthly_budget", "25000"))
secret_pin = get_setting("secret_pin", "1234")

friends_list = [p1_name, p2_name, p3_name]
phones_dict = {p1_name: p1_phone, p2_name: p2_phone, p3_name: p3_phone}

# ---------------- SIDEBAR NAVIGATION & SETTINGS ----------------
with st.sidebar:
    st.markdown("## 🔥 **Khata & Budget Hub**")
    viewer = st.selectbox("👤 Kon Website Dekh Raha Hai?", friends_list)
    st.caption("Apna naam select karein taake apko apka exact hisab nazar aye.")
    st.divider()

    with st.expander("⚙️ Friends & Budget Settings"):
        new_budget = st.number_input("Monthly Budget (Rs.)", value=monthly_budget, step=500.0)
        st.markdown("**Doston Ke Naam & WhatsApp Numbers**")
        n1 = st.text_input("Person 1 (Owner)", value=p1_name)
        ph1 = st.text_input("Person 1 Phone (03xx...)", value=p1_phone)
        n2 = st.text_input("Person 2 Name", value=p2_name)
        ph2 = st.text_input("Person 2 Phone (03xx...)", value=p2_phone)
        n3 = st.text_input("Person 3 Name", value=p3_name)
        ph3 = st.text_input("Person 3 Phone (03xx...)", value=p3_phone)
        new_pin = st.text_input("Personal Tab PIN", value=secret_pin, type="password")

        if st.button("💾 Save Settings", use_container_width=True):
            set_setting("monthly_budget", new_budget)
            set_setting("p1_name", n1.strip() or "Ukasha")
            set_setting("p1_phone", ph1.strip())
            set_setting("p2_name", n2.strip() or "Dost 1")
            set_setting("p2_phone", ph2.strip())
            set_setting("p3_name", n3.strip() or "Dost 2")
            set_setting("p3_phone", ph3.strip())
            set_setting("secret_pin", new_pin)
            st.success("Settings Saved! Reloading...")
            st.rerun()

# ---------------- MAIN TABS ----------------
tab_khata, tab_personal = st.tabs([
    "🤝 3-Friends Live Khata Board (Public)",
    f"🔒 {p1_name}'s Personal Budget"
])

# ==============================================================================
# TAB 1: 3-FRIENDS SHARED KHATA BOARD (LIVE VIEW + WHATSAPP ALERTS)
# ==============================================================================
with tab_khata:
    st.markdown(f"### 🤝 Teen Doston Ka Live Khata ({p1_name}, {p2_name}, {p3_name})")
    st.caption("Yahan har dost kisi bhi waqt website khol kar dekh sakta hai ke kis ne kis din kitne paise dene hain.")

    net_settlements = calculate_net_balances(friends_list)

    # ---- Personalized Status Banner for Active Viewer ----
    my_dues = [x for x in net_settlements if x["from"] == viewer]
    my_receivables = [x for x in net_settlements if x["to"] == viewer]

    if not my_dues and not my_receivables:
        st.success(f"🎉 **{viewer}**, apka hisab bilkul clear (Rs. 0) hai! Kisi ko kuch nahi dena.")
    else:
        for d in my_dues:
            st.error(f"📢 **{viewer}**, apne **{d['to']}** ko net **Rs. {d['amount']:,}** dene hain.")
        for r in my_receivables:
            st.info(f"💰 **{viewer}**, apne **{r['from']}** se net **Rs. {r['amount']:,}** lene hain.")

    # ---- 3 Cards Showing Net Settlements & WhatsApp Reminder Button ----
    st.markdown("#### 📊 Live Net Hisab (Who Owes Whom)")
    if not net_settlements:
        st.markdown("<div class='khata-card'><h4>✨ Sab Doston Ka Khata Clear Hai!</h4></div>", unsafe_allow_html=True)
    else:
        cols = st.columns(len(net_settlements))
        for idx, item in enumerate(net_settlements):
            debtor = item["from"]
            creditor = item["to"]
            amt = item["amount"]
            wa_msg = (
                f"Salam {debtor}! 🍽️ Humare Shared Khata ke mutabiq aj tak tumhare "
                f"*Rs. {amt:,}* ({creditor} ko dene wale) ban rahe hain. "
                f"Jab easy ho settle kar dena ya website par live hisab dekh lo!"
            )
            wa_url = make_whatsapp_link(phones_dict.get(debtor, ""), wa_msg)

            with cols[idx]:
                st.markdown(f"""
                <div class="khata-card">
                    <div style="font-size:1.05rem; color:#d0d7de;">
                        <b style="color:#ff4b4b;">{debtor}</b> ne dene hain <b style="color:#00e676;">{creditor}</b> ko
                    </div>
                    <div class="metric-value">Rs. {amt:,}</div>
                    <a href="{wa_url}" target="_blank" class="wa-btn">📲 Send WhatsApp Reminder to {debtor}</a>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ---- Add Shared Meal / Bill & Settle Up Forms ----
    col_add_bill, col_settle = st.columns([3, 2])

    with col_add_bill:
        st.markdown("#### 🍔 Add New Shared Khana / Bill")
        with st.form("shared_bill_form", clear_on_submit=True):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                bill_desc = st.text_input("Kya Khaya / Kis Cheez Ka Bill?", placeholder="e.g., Butt Karahi, Shawarma, Chai")
                paid_by = st.selectbox("💳 Bill Kis Ne Pay Kiya?", friends_list)
                bill_date = st.date_input("Date", value=date.today())
            with b_col2:
                total_bill = st.number_input("Total Bill Amount (Rs.)", min_value=0.0, step=50.0)
                split_type = st.radio("Hisab Kaise Divide Karna Hai?", ["Barabar (Equal 3-Way)", "Custom (Alag Alag Amount)"])

            st.caption("Agar Custom select kiya hai toh neeche teeno ka hissa likhein (warna Equal khud calculate ho jayega):")
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                custom_s1 = st.number_input(f"{p1_name}'s Share", min_value=0.0, step=10.0)
            with c_s2:
                custom_s2 = st.number_input(f"{p2_name}'s Share", min_value=0.0, step=10.0)
            with c_s3:
                custom_s3 = st.number_input(f"{p3_name}'s Share", min_value=0.0, step=10.0)

            auto_personal = st.checkbox(f"{p1_name} ka hissa uske Personal Daily Budget mein bhi auto-add karein", value=True)
            sub_bill = st.form_submit_button("➕ Add Shared Bill & Generate WhatsApp Links", use_container_width=True)

            if sub_bill:
                if not bill_desc or total_bill <= 0:
                    st.warning("Bill ka naam aur total amount sahi likhein!")
                else:
                    if split_type == "Barabar (Equal 3-Way)":
                        s1 = s2 = s3 = round(total_bill / 3.0, 2)
                    else:
                        s1, s2, s3 = custom_s1, custom_s2, custom_s3

                    if abs((s1 + s2 + s3) - total_bill) > 2.0:
                        st.error(f"Teeno ke hisson ka total ({s1+s2+s3}) Total Bill ({total_bill}) ke barabar nahi hai!")
                    else:
                        c.execute("""INSERT INTO shared_bills 
                                     (bill_date, description, paid_by, total_amount, share_p1, share_p2, share_p3)
                                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                  (str(bill_date), bill_desc, paid_by, total_bill, s1, s2, s3))

                        if auto_personal and s1 > 0:
                            c.execute("""INSERT INTO personal_expenses (exp_date, title, category, amount)
                                         VALUES (?, ?, ?, ?)""",
                                      (str(bill_date), f"[Shared] {bill_desc}", "Food & Friends", s1))
                        conn.commit()
                        st.session_state["last_bill_msg"] = {
                            "desc": bill_desc,
                            "paid_by": paid_by,
                            "total": total_bill,
                            "date": str(bill_date),
                            "shares": {p1_name: s1, p2_name: s2, p3_name: s3}
                        }
                        st.rerun()

        # Instant WhatsApp Trigger for Newly Added Bill
        if "last_bill_msg" in st.session_state:
            lb = st.session_state["last_bill_msg"]
            st.success(f"✅ **{lb['desc']}** (Rs. {lb['total']:,.0f}) add ho gaya! Ab 1-Click se doston ko WhatsApp bhejein:")
            w_cols = st.columns(2)
            other_friends = [f for f in friends_list if f != lb["paid_by"]]
            for i, friend in enumerate(other_friends):
                f_share = lb["shares"][friend]
                msg_text = (
                    f"🍔 *New Shared Bill Added!*\n"
                    f"📅 Date: {lb['date']}\n"
                    f"📝 Item: *{lb['desc']}*\n"
                    f"💳 Paid By: *{lb['paid_by']}*\n"
                    f"💰 Total Bill: Rs. {lb['total']:,.0f}\n"
                    f"👉 *Tumhara Aaj Ka Hissa: Rs. {f_share:,.0f}*\n\n"
                    f"Website khol kar apna mukammal live khata dekh lo!"
                )
                link = make_whatsapp_link(phones_dict.get(friend, ""), msg_text)
                with w_cols[i]:
                    st.markdown(f'<a href="{link}" target="_blank" class="wa-btn">📲 Send Bill Alert to {friend}</a>', unsafe_allow_html=True)

    with col_settle:
        st.markdown("#### 🤝 Paisay Wapis Mil Gaye? (Settle Up)")
        with st.form("settle_form", clear_on_submit=True):
            frm_p = st.selectbox("Kis Ne Paisay Diye? (Sender)", friends_list, index=1)
            to_p = st.selectbox("Kis Ko Paisay Mile? (Receiver)", friends_list, index=0)
            s_amt = st.number_input("Kitne Paisay Diye? (Rs.)", min_value=0.0, step=50.0)
            s_date = st.date_input("Date", value=date.today(), key="settle_dt")
            sub_settle = st.form_submit_button("✅ Record Payment (Khata Minus Karein)", use_container_width=True)

            if sub_settle:
                if frm_p == to_p:
                    st.warning("Dene wala aur lene wala aik hi banda nahi ho sakta!")
                elif s_amt <= 0:
                    st.warning("Amount 0 se zyada likhein!")
                else:
                    c.execute("INSERT INTO settlements (settle_date, from_person, to_person, amount) VALUES (?, ?, ?, ?)",
                              (str(s_date), frm_p, to_p, s_amt))
                    conn.commit()
                    st.success(f"Rs. {s_amt:,.0f} from {frm_p} to {to_p} record ho gaye!")
                    st.rerun()

    st.divider()

    # ---- Date-Wise Shared Khata History Table (Visible to All 3 Friends) ----
    st.markdown("#### 📜 Date-Wise Shared Khana & Bills History (Sab Dekh Sakte Hain)")
    df_bills = pd.read_sql_query("SELECT id, bill_date, description, paid_by, total_amount, share_p1, share_p2, share_p3 FROM shared_bills ORDER BY bill_date DESC, id DESC", conn)

    if not df_bills.empty:
        df_bills.columns = ["ID", "Date", "Item / Khana", "Paid By", "Total Bill (Rs.)", f"{p1_name}'s Share", f"{p2_name}'s Share", f"{p3_name}'s Share"]
        st.dataframe(df_bills, use_container_width=True, hide_index=True)

        with st.expander("🗑️ Galat Entry Delete Karein"):
            del_id = st.number_input("Bill ID likhein jo delete karni hai", min_value=1, step=1)
            if st.button("Delete Shared Bill"):
                c.execute("DELETE FROM shared_bills WHERE id=?", (del_id,))
                conn.commit()
                st.rerun()
    else:
        st.info("Abhi tak koi shared khana add nahi hua.")

# ==============================================================================
# TAB 2: UKASHA'S PERSONAL DAILY & MONTHLY BUDGET TRACKER
# ==============================================================================
with tab_personal:
    st.markdown(f"### 🔒 {p1_name}'s Personal Daily & Monthly Budget")
    pin_input = st.text_input("Apna Personal Budget dekhne ke liye PIN likhein (Default: 1234):", type="password")

    if pin_input != secret_pin:
        st.warning("🔐 Yeh section private hai. Upar sahi PIN lagayein taake apka personal kharcha khul sake.")
    else:
        today_str = str(date.today())
        curr_month_prefix = date.today().strftime("%Y-%m")

        # Calculate Monthly & Today's Spend
        c.execute("SELECT SUM(amount) FROM personal_expenses WHERE exp_date LIKE ?", (f"{curr_month_prefix}%",))
        month_spent = c.fetchone()[0] or 0.0

        c.execute("SELECT SUM(amount) FROM personal_expenses WHERE exp_date = ?", (today_str,))
        today_spent = c.fetchone()[0] or 0.0

        remaining_budget = monthly_budget - month_spent

        # Calculate remaining days in current month for Safe Daily Limit
        today_obj = date.today()
        total_days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
        remaining_days = max(1, (total_days_in_month - today_obj.day) + 1)
        safe_daily_limit = max(0.0, remaining_budget / remaining_days)

        # ---- 4 Top Summary Cards ----
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">📅 Monthly Total Budget</div>
                <div class="metric-value">Rs. {monthly_budget:,.0f}</div>
                <div class="metric-sub">Month: {today_obj.strftime('%B %Y')}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🔥 Aaj Ka Kharcha (Today)</div>
                <div class="metric-value">Rs. {today_spent:,.0f}</div>
                <div class="metric-sub">Date: {today_str}</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            rem_color = "#00e676" if remaining_budget >= 0 else "#ff4b4b"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">💰 Baqi Monthly Balance</div>
                <div class="metric-value" style="color:{rem_color};">Rs. {remaining_budget:,.0f}</div>
                <div class="metric-sub">Total Spent: Rs. {month_spent:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🛡️ Daily Safe Limit</div>
                <div class="metric-value">Rs. {safe_daily_limit:,.0f} / day</div>
                <div class="metric-sub">Baqi {remaining_days} dinon ke hisab se</div>
            </div>
            """, unsafe_allow_html=True)

        # Budget Progress Bar
        spend_ratio = min(1.0, max(0.0, month_spent / monthly_budget)) if monthly_budget > 0 else 0.0
        st.progress(spend_ratio, text=f"Monthly Budget Used: {spend_ratio*100:.1f}% (Rs. {month_spent:,.0f} of Rs. {monthly_budget:,.0f})")

        st.divider()

        p_col1, p_col2 = st.columns([2, 3])

        with p_col1:
            st.markdown("#### ➕ Aaj Ka Personal Kharcha Likhein")
            with st.form("personal_exp_form", clear_on_submit=True):
                p_title = st.text_input("Kis cheez par kharch hua?", placeholder="e.g., University Bus, Chai, Printouts")
                p_cat = st.selectbox("Category", ["Food & Friends", "Transport / Fuel", "Study / Stationary", "Mobile / Internet", "Other"])
                p_amt = st.number_input("Amount (Rs.)", min_value=0.0, step=20.0)
                p_date = st.date_input("Date", value=date.today(), key="p_dt")
                p_sub = st.form_submit_button("💾 Save Personal Expense", use_container_width=True)

                if p_sub:
                    if not p_title or p_amt <= 0:
                        st.warning("Item ka naam aur amount sahi likhein!")
                    else:
                        c.execute("INSERT INTO personal_expenses (exp_date, title, category, amount) VALUES (?, ?, ?, ?)",
                                  (str(p_date), p_title, p_cat, p_amt))
                        conn.commit()
                        st.success("Personal kharcha add ho gaya!")
                        st.rerun()

        with p_col2:
            st.markdown("#### 📋 Personal Expenses History")
            df_pers = pd.read_sql_query("SELECT id, exp_date, title, category, amount FROM personal_expenses ORDER BY exp_date DESC, id DESC", conn)
            if not df_pers.empty:
                df_pers.columns = ["ID", "Date", "Description", "Category", "Amount (Rs.)"]
                st.dataframe(df_pers, use_container_width=True, hide_index=True)

                st.markdown("##### 📊 Category-Wise Spending")
                cat_summary = df_pers.groupby("Category")["Amount (Rs.)"].sum()
                st.bar_chart(cat_summary, color="#ff6b00")
            else:
                st.info("Abhi tak koi personal kharcha record nahi hua.")
