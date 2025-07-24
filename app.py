import streamlit as st
import pandas as pd
import altair as alt
import streamlit_authenticator as stauth

# --- USER AUTHENTICATION SETUP ---

names = ['Jasvir']  # Your name(s)
usernames = ['jasvir']  # Your username(s)

# Paste your bcrypt-hashed passwords here
passwords = [
    '$2b$12$6rZEgET4hsHeyouvNjr/Hug1nSQx9jmumZSbSOsaxvxYW8WdylRH2'
]

authenticator = stauth.Authenticate(
    names, usernames, passwords,
    'my_cookie', 'my_signature_key',
    cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    st.title(f"Welcome, {name}! 🎉")
    
    authenticator.logout('Logout', 'sidebar')

    # Initialize or load data
    if 'accounts' not in st.session_state:
        st.session_state.accounts = pd.DataFrame(columns=['Date', 'Account', 'Category', 'Amount', 'Description'])

    st.header("Add a new account entry")

    with st.form("account_form", clear_on_submit=True):
        date = st.date_input("Date")
        account = st.text_input("Account Name")
        category = st.selectbox("Category", ['Income', 'Expense', 'Savings', 'Investment'])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        description = st.text_area("Description (optional)")
        submitted = st.form_submit_button("Add Entry")

    if submitted:
        new_entry = {
            'Date': date,
            'Account': account,
            'Category': category,
            'Amount': amount,
            'Description': description
        }
        st.session_state.accounts = pd.concat([st.session_state.accounts, pd.DataFrame([new_entry])], ignore_index=True)
        st.success("Entry added!")

    # Display data
    if not st.session_state.accounts.empty:
        st.header("Your account entries")
        st.dataframe(st.session_state.accounts)

        # Summary chart
        st.header("Summary by Category")
        summary = st.session_state.accounts.groupby(['Category']).Amount.sum().reset_index()

        chart = alt.Chart(summary).mark_bar().encode(
            x='Category',
            y='Amount',
            color='Category'
        )
        st.altair_chart(chart, use_container_width=True)

        # CSV Export
        csv = st.session_state.accounts.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Export as CSV",
            data=csv,
            file_name='accounts.csv',
            mime='text/csv'
        )
    else:
        st.info("No account entries yet. Add some above!")

elif authentication_status == False:
    st.error("Username/password is incorrect")

else:
    st.warning("Please enter your username and password")
