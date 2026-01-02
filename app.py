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
        lines = page.extract_text().split('\n')
        for line in lines:
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo"]): continue
            # Find Norwegian currency pattern: 1.234,56
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            if amounts:
                amt_str = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_str)
                    if amt > 25000: continue # Skip large balance totals
                    desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                    if desc:
                        data.append({"Description": desc, "Amount": amt, "Category": get_category(desc)})
                except: continue
    return pd.DataFrame(data)

# --- MAIN DASHBOARD ---
st.title("💎 Personal Economy Pro")
st.sidebar.header("🎯 Set Your Goals")
goal_food = st.sidebar.slider("Food Budget (NOK)", 0, 10000, 4000)
goal_subs = st.sidebar.slider("Subs Budget (NOK)", 0, 5000, 1500)

uploaded_files = st.sidebar.file_uploader("Upload Statements", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    df = pd.concat([parse_pdf(f) for f in uploaded_files]).drop_duplicates()
    
    # 1. Top Metrics with Health Score
    spending_df = df[~df['Category'].isin(['Income', 'Savings'])]
    total_spent = spending_df['Amount'].sum()
    total_saved = df[df['Category'] == 'Savings']['Amount'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Monthly Spending", f"{total_spent:,.2f} NOK")
    m2.metric("Micro-Savings (Habit)", f"{total_saved:,.2f} NOK", delta="Great pace!", delta_color="normal")
    
    # Calculate Burn Rate Gauge
    sub_spent = df[df['Category'] == 'Subscriptions']['Amount'].sum()
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = sub_spent,
        title = {'text': "Subscription Burn Rate"},
        gauge = {'axis': {'range': [0, 3000]}, 'bar': {'color': "#00d4ff"}}
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
    m3.plotly_chart(fig_gauge, use_container_width=True)

    # 2. Sunburst Animated Breakdown
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Interactive Sunburst")
        fig_sun = px.sunburst(spending_df, path=['Category', 'Description'], values='Amount',
                             color='Category', color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_sun, use_container_width=True)
        st.caption("Click a category to zoom in on specific habits.")

    with c2:
        st.subheader("Budget Habits")
        food_spent = df[df['Category'] == 'Food & Groceries']['Amount'].sum()
        st.write(f"Food Progress: {food_spent:,.0f} / {goal_food:,.0f} NOK")
        st.progress(min(food_spent/goal_food, 1.0))
        
        if food_spent > goal_food:
            st.warning("🚨 Habit Alert: Your food spending is above your target!")
        else:
            st.success("✅ Habit Check: You are managing your food budget well.")
            st.balloons() # Celeberatory balloons for good habits

    st.subheader("📝 Transaction Explorer")
    st.dataframe(df.sort_values(by="Amount", ascending=False), use_container_width=True)

else:
    st.info("Upload your PDF to unlock your animated financial story.")
