import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pypdf import PdfReader
import re

# --- APP CONFIG & THEME ---
st.set_page_config(page_title="Pro Habit Tracker", layout="wide", page_icon="💎")

# CSS for a professional Dark Mode look
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .metric-card { background-color: #1c2128; border: 1px solid #444c56; border-radius: 10px; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CATEGORY BRAIN ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'helse', 'vitus'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'vy', 'fly', 'taxi', 'uber', 'feriereiser'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Support': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Transfers/Vipps': ['vipps', 'overføring', 'til:', 'betalt:'],
        'Income': ['lønn', 'salary', 'fra:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Other/Shopping'

# --- SPAREBANK 1 PDF ENGINE ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    for page in reader.pages:
        text = page.extract_text()
        lines = text.split('\n')
        for line in lines:
            # Skip noise like account headers and IBANs
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo"]): continue
            
            # Find Norwegian currency pattern: 1.234,56 or 123,45
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            if amounts:
                # Use the first amount found as the transaction value
                amt_str = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_str)
                    if amt > 25000: continue # Skip large balance totals
                    
                    # Clean up the description
                    desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                    if desc:
                        data.append({
                            "Description": desc, 
                            "Amount": amt, 
                            "Category": get_category(desc)
                        })
                except: continue
    return pd.DataFrame(data)

# --- MAIN DASHBOARD ---
st.title("💎 Personal Economy Pro")

with st.sidebar:
    st.header("🎯 Set Your Goals")
    goal_food = st.slider("Food Budget (NOK)", 0, 10000, 4000)
    goal_subs = st.slider("Subs Budget (NOK)", 0, 5000, 1500)
    goal_charity = st.slider("Charity Budget (NOK)", 0, 5000, 500)
    uploaded_files = st.file_uploader("Upload Statements", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    # Build the database from uploaded PDFs
    all_data = []
    for f in uploaded_files:
        pdf_df = parse_pdf(f)
        if not pdf_df.empty:
            all_data.append(pdf_df)
    
    if all_data:
        df = pd.concat(all_data).drop_duplicates()
        
        # 1. Top Metrics with Health Score
        spending_df = df[~df['Category'].isin(['Income', 'Savings'])]
        total_spent = spending_df['Amount'].sum()
        total_saved = df[df['Category'] == 'Savings']['Amount'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Monthly Spending", f"{total_spent:,.2f} NOK")
        m2.metric("Micro-Savings Habit", f"{total_saved:,.2f} NOK", delta="Great pace!", delta_color="normal")
        
        # Calculate Burn Rate Gauge
        sub_spent = df[df['Category'] == 'Subscriptions']['Amount'].sum()
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = sub_spent,
            title = {'text': "Monthly Subscription Burn"},
            gauge = {'axis': {'range': [0, 3000]}, 'bar': {'color': "#00d4ff"}}
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
        m3.plotly_chart(fig_gauge, use_container_width=True)

        # 2. Animated Sunburst Chart
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Interactive Spending Story")
            fig_sun = px.sunburst(spending_df, path=['Category', 'Description'], values='Amount',
                                 color='Category', color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_sun, use_container_width=True)
            st.caption("Click a category to zoom in on specific habits.")

        with c2:
            st.subheader("Budget Performance")
            cat_sums = df.groupby('Category')['Amount'].sum()
            
            # Progress Bars for Habits
            habits = [("Food & Groceries", goal_food), ("Subscriptions", goal_subs), ("Charity/Support", goal_charity)]
            for name, goal in habits:
                spent = cat_sums.get(name, 0)
                st.write(f"**{name}**: {spent:,.0f} / {goal:,.0f} NOK")
                st.progress(min(spent/goal, 1.0) if goal > 0 else 0)

        st.subheader("📝 Transaction Explorer")
        st.dataframe(df.sort_values(by="Amount", ascending=False), use_container_width=True)
    else:
        st.error("Could not find transactions. Please ensure the PDF is a standard SpareBank 1 statement.")
else:
    st.info("Upload your PDF to unlock your animated financial story.")
