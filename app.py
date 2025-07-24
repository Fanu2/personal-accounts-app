# personal_accounts_app.py
import streamlit as st
import pandas as pd
import os
import datetime
import altair as alt
import yaml
from streamlit_authenticator import Authenticate
from pathlib import Path

# ----- Constants -----
DATA_FILE = "transactions.csv"
DEFAULT_BUDGET = 50000
CATEGORIES = ["Groceries", "Salary", "Utilities", "Entertainment", "Travel", "Other"]

# ----- Page Config -----
st.set_page_config(page_title="Personal Accounts", layout="centered")

# ----- Load Configuration -----
def load_config():
    """Load configuration from YAML file."""
    try:
        with open("config.yaml", "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        st.error("Configuration file (config.yaml) not found!")
        return None

config = load_config()
if not config:
    st.stop()

# ----- Authentication -----
authenticator = Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

auth_status, username, name = authenticator.login("Login", "sidebar")

if auth_status:
    authenticator.logout("Logout", "sidebar")
    
    # ----- Initialize File -----
    @st.cache_data
    def initialize_data():
        """Initialize the transactions CSV if it doesn't exist."""
        if not os.path.exists(DATA_FILE):
            df_init = pd.DataFrame(columns=["Date", "Category", "Type", "Amount", "Notes"])
            df_init.to_csv(DATA_FILE, index=False)
        return pd.read_csv(DATA_FILE, parse_dates=["Date"])

    # ----- Load Data -----
    df = initialize_data()

    # ----- Helper Functions -----
    def validate_transaction(date, category, amount, t_type):
        """Validate transaction input fields."""
        if not category.strip():
            st.error("Category cannot be empty.")
            return False
        if amount <= 0:
            st.error("Amount must be greater than 0.")
            return False
        return True

    def save_transaction(df, date, category, t_type, amount, notes):
        """Save a new transaction to the CSV."""
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
        st.cache_data.clear()  # Clear cache after saving
        return df

    def delete_transaction(df, index):
        """Delete a transaction by index."""
        df = df.drop(index).reset_index(drop=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("Transaction deleted successfully!")
        st.cache_data.clear()  # Clear cache after deletion
        return df

    # ----- Sidebar: Add Transaction -----
    st.sidebar.header("Add New Transaction")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        date = st.date_input("Date", value=datetime.date.today())
        category = st.selectbox("Category", CATEGORIES, index=len(CATEGORIES)-1)
        t_type = st.selectbox("Type", ["Income", "Expense"])
        amount = st.number_input("Amount", min_value=0.01, format="%.2f")
        notes = st.text_area("Notes", height=50)
        submitted = st.form_submit_button("Add Transaction")

        if submitted and validate_transaction(date, category, amount, t_type):
            df = save_transaction(df, date, category, t_type, amount, notes)

    # ----- Main Interface -----
    st.title("💰 Personal Accounts Dashboard")

    # ----- Filter Section -----
    with st.expander("🔍 Filter by Date"):
        default_start = df["Date"].min() if not df.empty else datetime.date.today()
        default_end = df["Date"].max() if not df.empty else datetime.date.today()
        start_date = st.date_input("Start Date", value=default_start)
        end_date = st.date_input("End Date", value=default_end)
        if start_date > end_date:
            st.error("Start date cannot be after end date.")
            filtered_df = df
        else:
            filtered_df = df[(df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))]

    # ----- Summary -----
    income = filtered_df[filtered_df["Type"] == "Income"]["Amount"].sum()
    expense = filtered_df[filtered_df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expense

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹ {income:,.2f}")
    col2.metric("Total Expense", f"₹ {expense:,.2f}")
    col3.metric("Net Balance", f"₹ {balance:,.2f}", delta=f"{balance:,.2f}")

    # ----- Chart -----
    if not filtered_df.empty:
        st.subheader("📊 Income vs Expense Over Time")
        chart_data = filtered_df.copy()
        chart_data["Month"] = chart_data["Date"].dt.to_period("M").astype(str)
        chart_summary = chart_data.groupby(["Month", "Type"])["Amount"].sum().reset_index()

        chart = alt.Chart(chart_summary).mark_bar().encode(
            x=alt.X("Month:N", title="Month"),
            y=alt.Y("Amount:Q", title="Amount (₹)"),
            color=alt.Color("Type:N", legend=alt.Legend(title="Transaction Type")),
            tooltip=["Month", "Type", alt.Tooltip("Amount", format=",.2f")]
        ).properties(width=700)

        st.altair_chart(chart, use_container_width=True)

        # ----- Budget Tracking -----
        st.subheader(f"📅 Monthly Budget Tracker (₹{DEFAULT_BUDGET:,})")
        monthly_expense = chart_data[chart_data["Type"] == "Expense"].groupby("Month")["Amount"].sum()
        for month, spent in monthly_expense.items():
            remaining = DEFAULT_BUDGET - spent
            progress = min(spent / DEFAULT_BUDGET, 1.0)
            st.write(f"**{month}** - Spent: ₹{spent:,.0f} / Budget: ₹{DEFAULT_BUDGET:,}")
            st.progress(progress)
            st.write(f"Remaining: ₹{remaining:,.0f}")

        # ----- Category Summary -----
        st.subheader("📊 Category-wise Expenses")
        category_summary = filtered_df[filtered_df["Type"] == "Expense"].groupby("Category")["Amount"].sum().reset_index()
        st.dataframe(category_summary, use_container_width=True)

    # ----- View and Manage Transactions -----
    st.subheader("📄 All Transactions")
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True)
        
        # Delete Transaction
        with st.expander("🗑️ Delete Transaction"):
            delete_index = st.number_input("Enter transaction index to delete", min_value=0, max_value=len(filtered_df)-1, step=1)
            if st.button("Delete Transaction"):
                if delete_index in filtered_df.index:
                    df = delete_transaction(df, delete_index)
                else:
                    st.error("Invalid transaction index.")

    # ----- Export CSV -----
    st.download_button(
        label="📅 Export Filtered Data to CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_transactions.csv",
        mime="text/csv"
    )

elif auth_status is False:
    st.error("Username/password is incorrect")
elif auth_status is None:
    st.warning("Please enter your username and password")
