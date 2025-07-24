# personal_accounts_app.py
import streamlit as st
import pandas as pd
import os
import datetime
import altair as alt
import io
import streamlit_authenticator as stauth

# ----- Page Config -----
st.set_page_config(page_title="Personal Accounts", layout="centered")

# ----- Authentication -----
credentials = {
    "usernames": {
        "user1": {
            "name": "User",
            "password": "$2b$12$Rjf3RrX6Rmj1HZigpRbWy.A1I1uhzKoD2W6MfExY.KWD2zOxycZhi"  # bcrypt hash
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "auth_cookie",
    "auth_signature",
    cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login('Login', location='sidebar')

if authentication_status:
    authenticator.logout('Logout', 'sidebar')

    # ----- Initialize File -----
    DATA_FILE = "transactions.csv"
    if not os.path.exists(DATA_FILE):
        df_init = pd.DataFrame(columns=["Date", "Category", "Type", "Amount", "Notes"])
        df_init.to_csv(DATA_FILE, index=False)

    # ----- Load Data -----
    df = pd.read_csv(DATA_FILE, parse_dates=["Date"])

    # ----- Sidebar: Add Entry -----
    st.sidebar.header("Add New Transaction")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        date = st.date_input("Date", value=datetime.date.today())
        category = st.text_input("Category (e.g. Groceries, Salary)")
        t_type = st.selectbox("Type", ["Income", "Expense"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        notes = st.text_area("Notes", height=50)
        submitted = st.form_submit_button("Add Transaction")

    if submitted:
        new_entry = pd.DataFrame({
            "Date": [date],
            "Category": [category],
            "Type": [t_type],
            "Amount": [amount],
            "Notes": [notes]
        })
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("Transaction added successfully!")

    # ----- Main Interface -----
    st.title("💰 Personal Accounts Dashboard")

    # Filter section
    with st.expander("🔍 Filter by Date"):
        start_date = st.date_input("Start Date", value=df["Date"].min() if not df.empty else datetime.date.today())
        end_date = st.date_input("End Date", value=df["Date"].max() if not df.empty else datetime.date.today())
        filtered_df = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]

    # ----- Summary -----
    income = filtered_df[filtered_df["Type"] == "Income"]["Amount"].sum()
    expense = filtered_df[filtered_df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expense

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹ {income:,.2f}")
    col2.metric("Total Expense", f"₹ {expense:,.2f}")
    col3.metric("Net Balance", f"₹ {balance:,.2f}", delta=f"{income - expense:,.2f}")

    # ----- Chart -----
    if not filtered_df.empty:
        st.subheader("📊 Income vs Expense Over Time")
        chart_data = filtered_df.copy()
        chart_data["Month"] = chart_data["Date"].dt.to_period("M").astype(str)
        chart_summary = chart_data.groupby(["Month", "Type"])["Amount"].sum().reset_index()

        chart = alt.Chart(chart_summary).mark_bar().encode(
            x="Month:N",
            y="Amount:Q",
            color="Type:N",
            tooltip=["Month", "Type", "Amount"]
        ).properties(width=700)

        st.altair_chart(chart)

        # ----- Budget Tracking -----
        st.subheader("📅 Monthly Budget Tracker (₹50,000)")
        monthly_expense = chart_data[chart_data["Type"] == "Expense"].groupby("Month")["Amount"].sum()
        for month, spent in monthly_expense.items():
            remaining = 50000 - spent
            st.write(f"**{month}** - Spent: ₹{spent:,.0f} / Budget: ₹50,000 → Remaining: ₹{remaining:,.0f}")

    # ----- View Table -----
    st.subheader("📄 All Transactions")
    st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True)

    # ----- Export CSV -----
    st.download_button(
        label="📅 Export Filtered Data to CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_transactions.csv",
        mime="text/csv"
    )

elif authentication_status is False:
    st.error("Username/password is incorrect")
elif authentication_status is None:
    st.warning("Please enter your username and password")
