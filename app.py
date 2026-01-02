import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="SpareBank Pro Tracker", layout="wide", page_icon="🏦")

# --- CATEGORY BRAIN ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'vitus', 'fokus'],
        'Savings': ['småsparing'],
        'Travel': ['atb app', 'feriereiser', 'uber', 'taxi'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Support': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Transfers/Vipps': ['vipps', 'overføring', 'til:', 'betalt:'],
        'Income': ['lønn', 'salary', 'fra:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Other/Shopping'

# --- THE ROBUST SPAREBANK 1 PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    
    for page in reader.pages:
        text = page.extract_text()
        if not text: continue # Skip if page is empty/unreadable
        
        lines = text.split('\n')
        for line in lines:
            # Skip noise lines [cite: 13, 14, 20]
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo"]): continue
            
            # Find Norwegian currency pattern (e.g., 349,00 or 1.529,00) 
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            if amounts:
                # Logic: In SpareBank PDFs, 'Ut av konto' is often the first amount 
                amt_raw = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_raw)
                    if amt > 20000: continue # Skip balance totals 
                    
                    # Clean up the description 
                    desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                    if len(desc) > 3:
                        data.append({"Description": desc, "Amount": amt, "Category": get_category(desc)})
                except: continue
    return pd.DataFrame(data)

# --- DASHBOARD UI ---
st.title("🏦 SpareBank 1 Habit Pro")
st.markdown("Interactive analysis of your December spending and savings.")

with st.sidebar:
    st.header("⚙️ App Settings")
    files = st.file_uploader("Upload SpareBank 1 PDF", type=['pdf'], accept_multiple_files=True)
    st.divider()
    g_food = st.slider("Food Goal", 0, 10000, 4000)
    g_subs = st.slider("Subs Goal", 0, 5000, 1500)
    g_charity = st.slider("Charity Goal", 0, 2000, 500)

if files:
    all_df = []
    for f in files:
        res = parse_pdf(f)
        if not res.empty:
            all_df.append(res)
    
    if all_df:
        df = pd.concat(all_df).drop_duplicates()
        
        # Split data for better insights 
        spending = df[~df['Category'].isin(['Income', 'Savings'])]
        savings = df[df['Category'] == 'Savings']
        charity = df[df['Category'] == 'Charity/Support']

        # 1. Animated Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Spending", f"{spending['Amount'].sum():,.2f} NOK")
        c2.metric("Total Savings", f"{savings['Amount'].sum():,.2f} NOK", delta="On Track")
        c3.metric("Charity Contributions", f"{charity['Amount'].sum():,.2f} NOK")

        # 2. Interactive Sunburst (Animated Habits)
        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Interactive Spending Story")
            # This creates the animated "drill-down" effect 
            fig = px.sunburst(spending, path=['Category', 'Description'], values='Amount',
                             color='Category', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("Habit Scorecard")
            cat_totals = df.groupby('Category')['Amount'].sum()
            for name, goal in [("Food & Groceries", g_food), ("Subscriptions", g_subs), ("Charity/Support", g_charity)]:
                spent = cat_totals.get(name, 0)
                st.write(f"**{name}**")
                st.progress(min(spent/goal, 1.0) if goal > 0 else 0)
                st.caption(f"{spent:,.0f} / {goal:,.0f} NOK")

        st.subheader("Transaction Explorer")
        st.dataframe(df.sort_values(by="Amount", ascending=False), use_container_width=True)
    else:
        st.error("Still no data found. Please try converting your PDF to a CSV file in your bank portal.")
else:
    st.info("Upload your SpareBank 1 statement to begin.")
