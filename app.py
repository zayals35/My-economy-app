import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="SpareBank Pro Tracker", layout="wide", page_icon="🏦")

# Professional Dark Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; }
    </style>
    """, unsafe_allow_html=True)

# --- ADVANCED CATEGORY ENGINE ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'vitus', 'fokus', 'lege'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'vy', 'fly', 'taxi', 'uber', 'ruten', 'feriereiser'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Support': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Income': ['lønn', 'salary', 'fra:'],
        'Vipps/Transfers': ['vipps', 'overføring', 'til:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Other/Shopping'

# --- THE "MASTER" SPAREBANK PDF PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    
    for page in reader.pages:
        text = page.extract_text()
        lines = text.split('\n')
        
        for line in lines:
            # Skip headers and balance info
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo", "Referanse", "Side"]): continue
            
            # SpareBank 1 Pattern: Date Description Amount
            # We look for amounts formatted like 349,00 or 1.529,00
            # This regex captures the description and the currency amount separately
            match = re.search(r'(.*?)\s+(\d+[\d\s.]*,\d{2})', line)
            
            if match:
                desc_raw = match.group(1).strip()
                amt_raw = match.group(2).replace(' ', '').replace('.', '').replace(',', '.')
                
                try:
                    amt = float(amt_raw)
                    # Filter out dates misread as amounts and account totals
                    if 5.0 <= amt < 25000.0:
                        # Clean up prefix noise (like dates 0112 at the start of desc)
                        clean_desc = re.sub(r'^\d{4}\s+', '', desc_raw)
                        
                        data.append({
                            "Description": clean_desc,
                            "Amount": amt,
                            "Category": get_category(clean_desc)
                        })
                except: continue
    
    return pd.DataFrame(data)

# --- DASHBOARD UI ---
st.title("🏦 SpareBank 1 Pro Habit Tracker")

with st.sidebar:
    st.header("⚙️ Settings")
    uploaded_files = st.file_uploader("Upload SpareBank PDFs", type=['pdf'], accept_multiple_files=True)
    st.divider()
    g_food = st.slider("Food Goal (NOK)", 0, 10000, 4000)
    g_subs = st.slider("Subscription Goal (NOK)", 0, 3000, 1000)
    g_charity = st.slider("Charity Goal (NOK)", 0, 2000, 500)

if uploaded_files:
    all_df = []
    for f in uploaded_files:
        res = parse_pdf(f)
        if not res.empty:
            all_df.append(res)
    
    if all_df:
        df = pd.concat(all_df).drop_duplicates()
        
        # Filtering logic
        spending = df[~df['Category'].isin(['Income', 'Savings'])]
        savings_total = df[df['Category'] == 'Savings']['Amount'].sum()
        
        # 1. Top Metrics with Gauge Animation
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Monthly Spending", f"{spending['Amount'].sum():,.2f} NOK")
        c2.metric("Micro-Savings (Habit)", f"{savings_total:,.2f} NOK")
        
        # Gauge for Subscriptions
        sub_spent = df[df['Category'] == 'Subscriptions']['Amount'].sum()
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = sub_spent,
            title = {'text': "Subs Burn Rate"},
            gauge = {'axis': {'range': [0, 2000]}, 'bar': {'color': "#00d4ff"}}
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor="rgba(0,0,0,0)")
        c3.plotly_chart(fig_gauge, use_container_width=True)

        # 2. Animated Sunburst Chart
        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Interactive Spending Story")
            fig_sun = px.sunburst(spending, path=['Category', 'Description'], values='Amount',
                                 color='Category', template="plotly_dark", height=500)
            st.plotly_chart(fig_sun, use_container_width=True)
            st.caption("Click a category to zoom in on specific vendors.")

        with col_right:
            st.subheader("Budget Scorecard")
            cat_totals = df.groupby('Category')['Amount'].sum()
            goals = [("Food & Groceries", g_food), ("Subscriptions", g_subs), ("Charity/Support", goal_charity if 'goal_charity' in locals() else g_charity)]
            
            for name, goal in goals:
                spent = cat_totals.get(name, 0)
                st.write(f"**{name}**: {spent:,.0f} / {goal:,.0f} NOK")
                st.progress(min(spent/goal, 1.0) if goal > 0 else 0)

        st.subheader("📝 Full Transaction List")
