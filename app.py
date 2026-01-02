import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pypdf import PdfReader
import re

# --- APP CONFIG ---
st.set_page_config(page_title="SpareBank Pro Tracker", layout="wide", page_icon="🏦")

# --- IMPROVED CATEGORY ENGINE ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'vitus', 'fokus'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'feriereiser', 'uber', 'taxi', 'vy'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food'],
        'Charity/Donations': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Income': ['lønn', 'salary', 'fra:'],
        'Vipps/Transfers': ['vipps', 'overføring', 'til:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'Other/General'

# --- THE "FUZZY" SPAREBANK PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    for page in reader.pages:
        text = page.extract_text()
        # SpareBank 1 PDFs often merge lines. We split by newline and look for currency patterns.
        lines = text.split('\n')
        for line in lines:
            # Look for the Norwegian decimal pattern: digits followed by a comma and exactly two digits
            # Example: 349,00 or 1.529,00
            match = re.search(r'(\d+[\d\s.]*,\d{2})', line)
            if match:
                amt_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_str)
                    # Filter: Ignore large balance totals/acct numbers. Focus on spending (1 NOK to 20k NOK)
                    if 1.0 <= amt <= 20000.0:
                        # The description is usually the text before the amount
                        desc = line.split(match.group(1))[0].strip()
                        # Clean up prefix noise like *5887 or dates
                        desc = re.sub(r'^\*?\d{4}\s+\d{2}\.\d{2}\s+\w{3}\s+', '', desc)
                        
                        if len(desc) > 2:
                            data.append({"Description": desc, "Amount": amt, "Category": get_category(desc)})
                except: continue
    return pd.DataFrame(data)

# --- DASHBOARD UI ---
st.title("💎 Personal Economy Pro")
st.sidebar.header("🎯 Settings")
uploaded_files = st.sidebar.file_uploader("Upload SpareBank PDF", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        p_df = parse_pdf(f)
        if not p_df.empty:
            all_data.append(p_df)
    
    if all_data:
        df = pd.concat(all_data).drop_duplicates()
        spending_df = df[~df['Category'].isin(['Income', 'Savings'])]
        
        # --- ANIMATED VISUALS ---
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Interactive Spending Story")
            fig_sun = px.sunburst(spending_df, path=['Category', 'Description'], values='Amount',
                                 color='Category', template="plotly_dark", height=600)
            st.plotly_chart(fig_sun, use_container_width=True)
            
        with col2:
            st.subheader("Monthly Metrics")
            st.metric("Total Spending", f"{spending_df['Amount'].sum():,.2f} NOK")
            st.metric("Savings Habit", f"{df[df['Category'] == 'Savings']['Amount'].sum():,.2f} NOK")
            
            # Category List
            st.write("### Spending by Category")
            cat_totals = spending_df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
            st.table(cat_totals)

        st.subheader("📝 All Detected Transactions")
        st.dataframe(df, use_container_width=True)
    else:
        st.error("No transactions found. Your PDF might be an image/scan. Try selecting 'Save as PDF' from your online bank instead of scanning a paper copy.")
else:
    st.info("Upload your SpareBank 1 PDF to begin.")
