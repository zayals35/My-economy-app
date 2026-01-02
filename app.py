import streamlit as st
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="Pro Finance Insight", layout="wide", page_icon="💰")

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; }
    .main-card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- ENHANCED CATEGORY ENGINE ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'microsoft', 'netflix', 'spotify', 'chatgpt', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'helse', 'vitus'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'vy', 'fly', 'taxi', 'uber', 'ruten'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Donations': ['yousuf', 'launchgood', 'dawah', 'relief', 'charity'],
        'Transfers/Vipps': ['vipps', 'overføring', 'til:'],
        'Income': ['lønn', 'salary', 'fra:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Shopping/Other'

# --- SPAREBANK 1 PDF PARSER ---
def parse_sparebank_pdf(file):
    reader = PdfReader(file)
    data = []
    
    for page in reader.pages:
        lines = page.extract_text().split('\n')
        for line in lines:
            # Skip noise like account headers and IBANs
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo", "Dato"]): continue
            
            # Find amounts (digits with comma or dot)
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            if amounts:
                # 'Ut av konto' logic: ignore the huge account numbers and balances
                amt_str = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                amt = float(amt_str)
                
                # Filter out system IDs or large balances that aren't expenses
                if amt > 20000: continue 
                
                # Extract description by removing the amount from the line
                desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                
                if desc:
                    data.append({"Description": desc, "Amount": amt, "Category": get_category(desc)})
    
    return pd.DataFrame(data)

# --- SIDEBAR & UPLOAD ---
st.title("💰 Universal Economy Breakdown")
st.sidebar.header("User Settings")
files = st.sidebar.file_uploader("Upload Bank Statements (PDF)", accept_multiple_files=True, type=['pdf'])

# Expanded Budgeting Feature
st.sidebar.subheader("Monthly Targets")
goal_food = st.sidebar.number_input("Food Goal (NOK)", value=4000)
goal_subs = st.sidebar.number_input("Subs Goal (NOK)", value=1000)
goal_charity = st.sidebar.number_input("Charity Goal (NOK)", value=500)

if files:
    dfs = [parse_sparebank_pdf(f) for f in files]
    df = pd.concat(dfs).drop_duplicates()
    
    # --- METRICS ---
    spending_only = df[~df['Category'].isin(['Income', 'Savings'])]
    savings_only = df[df['Category'] == 'Savings']
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Actual Spending", f"{spending_only['Amount'].sum():,.2f} NOK")
    m2.metric("Total Savings", f"{savings_only['Amount'].sum():,.2f} NOK")
    m3.metric("Charity Given", f"{df[df['Category'] == 'Charity/Donations']['Amount'].sum():,.2f} NOK")

    # --- VISUALS ---
    st.divider()
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("Spending Distribution")
        fig_pie = px.pie(spending_only, values='Amount', names='Category', hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("Goal Performance")
        cat_sums = df.groupby('Category')['Amount'].sum()
        
        # Display Progress for several categories
        targets = [("Food & Groceries", goal_food), ("Subscriptions", goal_subs), ("Charity/Donations", goal_charity)]
        for cat_name, goal_val in targets:
            spent = cat_sums.get(cat_name, 0)
            percent = min(spent/goal_val, 1.0) if goal_val > 0 else 0
            st.write(f"**{cat_name}**: {spent:,.0f} / {goal_val:,.0f} NOK")
            st.progress(percent)

    st.subheader("Detailed Breakdown")
    st.dataframe(df.sort_values(by="Amount", ascending=False), use_container_width=True)
else:
    st.info("Upload your PDF statement to see the breakdown of your Savings, Charity, and Subscriptions.")
