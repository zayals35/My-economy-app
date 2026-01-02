import streamlit as st
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="Economy Insight Pro", layout="wide")

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🏦 Personal Economy Breakdown")
st.markdown("Analyze your spending habits and build a better financial future.")

# --- SIDEBAR: BUDGETS ---
with st.sidebar:
    st.header("⚙️ Settings")
    uploaded_files = st.file_uploader("Upload Bank Statements (PDF/CSV)", accept_multiple_files=True)
    
    st.header("🎯 Monthly Budgets")
    b_food = st.sidebar.slider("Groceries & Food", 0, 10000, 4000)
    b_subs = st.sidebar.slider("Subscriptions", 0, 3000, 1000)
    b_travel = st.sidebar.slider("Travel", 0, 10000, 2000)
    b_shopping = st.sidebar.slider("Shopping", 0, 10000, 3000)

budget_map = {
    "Food & Groceries": b_food,
    "Subscriptions": b_subs,
    "Travel": b_travel,
    "Shopping": b_shopping
}

# --- CATEGORIZATION LOGIC ---
def get_category(desc):
    d = str(desc).lower()
    if any(k in d for k in ['apple.com', 'adobe', 'openai', 'microsoft', 'netflix', 'spotify']): return 'Subscriptions'
    if any(k in d for k in ['legesenter', 'apotek', 'helse']): return 'Health'
    if 'småsparing' in d: return 'Savings'
    if any(k in d for k in ['atb', 'vy', 'fly', 'taxi', 'uber']): return 'Travel'
    if any(k in d for k in ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds']): return 'Food & Groceries'
    if any(k in d for k in ['vipps', 'overføring']): return 'Transfers'
    if any(k in d for k in ['lønn', 'salary']): return 'Income'
    return 'Shopping/Other'

# --- PDF PARSING ENGINE ---
def parse_bank_pdf(file):
    reader = PdfReader(file)
    extracted_data = []
    
    for page in reader.pages:
        text = page.extract_text()
        # Regex to find SpareBank 1 transaction patterns (Date Description Amount)
        # Looking for patterns like: "*5887 28.11 Nok 349.00 Apple.Com/Bill"
        lines = text.split('\n')
        for line in lines:
            # Simple check for Norwegian currency formatting in lines
            if "nok" in line.lower() or "småsparing" in line.lower():
                # Extract amount (looking for numbers with commas or dots)
                amounts = re.findall(r'\d+[.,]\d+', line)
                if amounts:
                    extracted_data.append({
                        "Dato": "Desember", # Simplified for now
                        "Forklaring": line.strip(),
                        "Amount": float(amounts[-1].replace('.', '').replace(',', '.'))
                    })
    return pd.DataFrame(extracted_data)

# --- MAIN APP LOGIC ---
if uploaded_files:
    all_data = []
    for file in uploaded_files:
        if file.name.endswith('.pdf'):
            df_pdf = parse_bank_pdf(file)
            all_data.append(df_pdf)
        else:
            df_csv = pd.read_csv(file, sep=None, engine='python')
            # Standardize CSV headers
            df_csv = df_csv.rename(columns={'Ut av konto': 'Amount', 'Forklaring': 'Forklaring'})
            all_data.append(df_csv)

    if all_data:
        df = pd.concat(all_data).drop_duplicates()
        df['Category'] = df['Forklaring'].apply(get_category)
        
        # Calculate Metrics
        total_spent = df[df['Category'] != 'Income']['Amount'].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("Total Spending Detected", f"{total_spent:,.2f} NOK")
        m2.metric("Savings Detected", f"{df[df['Category'] == 'Savings']['Amount'].sum():,.2f} NOK")

        # Budget Progress
        st.subheader("📊 Budget Tracking")
        summary = df.groupby('Category')['Amount'].sum()
        
        for cat, limit in budget_map.items():
            spent = summary.get(cat, 0)
            percent = min(spent/limit, 1.0) if limit > 0 else 0
            st.write(f"**{cat}** ({spent:,.0f} / {limit:,.0f} NOK)")
            st.progress(percent)

        # Charts
        st.divider()
        fig_pie = px.pie(df[df['Category'] != 'Income'], values='Amount', names='Category', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📝 Transaction List")
        st.dataframe(df[['Forklaring', 'Category', 'Amount']], use_container_width=True)

else:
    st.info("👋 Upload your SpareBank 1 PDF to see your economy breakdown!")
