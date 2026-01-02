import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="SpareBank Pro Tracker", layout="wide", page_icon="🏦")

# --- CATEGORY ENGINE ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'vitus', 'fokus'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'feriereiser', 'uber', 'taxi', 'vy'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Support': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Income': ['lønn', 'salary', 'fra:'],
        'Vipps/Transfers': ['vipps', 'overføring', 'til:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Other/General'

# --- SPAREBANK 1 PDF PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    for page in reader.pages:
        lines = page.extract_text().split('\n')
        for line in lines:
            # 1. Ignore headers and large balance numbers
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo", "Dato"]): continue
            
            # 2. Find Norwegian currency pattern: looks for digits followed by ,00 or ,XX
            # We look for amounts between 1,00 and 15.000,00
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            if amounts:
                # The first amount in a transaction line is usually 'Ut av konto'
                amt_str = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_str)
                    # 3. Filter out non-spending numbers (dates, acct numbers, huge balances)
                    if amt > 20000 or amt < 1.0: continue 
                    
                    # 4. Clean description
                    desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                    if len(desc) > 3:
                        data.append({"Description": desc, "Amount": amt, "Category": get_category(desc)})
                except: continue
    return pd.DataFrame(data)

# --- DASHBOARD UI ---
st.title("💎 Personal Economy Pro")
st.sidebar.header("🎯 Set Your Goals")
goal_food = st.sidebar.slider("Food Budget", 0, 10000, 4000)
goal_subs = st.sidebar.slider("Subs Budget", 0, 5000, 1500)
goal_charity = st.sidebar.slider("Charity Budget", 0, 5000, 1000)

uploaded_files = st.sidebar.file_uploader("Upload SpareBank PDF", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    dfs = [parse_pdf(f) for f in uploaded_files]
    df = pd.concat(dfs).drop_duplicates()
    
    if not df.empty:
        # Separate Spending from Savings/Income
        spending_df = df[~df['Category'].isin(['Income', 'Savings'])]
        
        # 1. Animated Gauge for Subscription 'Burn Rate'
        sub_total = df[df['Category'] == 'Subscriptions']['Amount'].sum()
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = sub_total,
            title = {'text': "Monthly Subscriptions Burn"},
            gauge = {'axis': {'range': [0, 3000]}, 'bar': {'color': "#00d4ff"}}
        ))
        fig_gauge.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 2. Sunburst Breakdown (Interactive!)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Interactive Spending Story")
            fig_sun = px.sunburst(spending_df, path=['Category', 'Description'], values='Amount',
                                 color='Category', template="plotly_dark")
            st.plotly_chart(fig_sun, use_container_width=True)
            st.caption("Click a category to see specific vendors.")

        with col2:
            st.subheader("Goal Performance")
            cat_sums = df.groupby('Category')['Amount'].sum()
            targets = [("Food & Groceries", goal_food), ("Subscriptions", goal_subs), ("Charity/Support", goal_charity)]
            
            for name, goal in targets:
                spent = cat_sums.get(name, 0)
                st.write(f"**{name}**: {spent:,.0f} / {goal:,.0f} NOK")
                st.progress(min(spent/goal, 1.0) if goal > 0 else 0)

        st.subheader("📝 Transaction Explorer")
        st.dataframe(df.sort_values(by="Amount", ascending=False), use_container_width=True)
    else:
        st.error("Could not find transactions. Please ensure you are uploading the digital SpareBank PDF.")
else:
    st.info("Upload your SpareBank 1 PDF to unlock your animated financial story.")
