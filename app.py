import streamlit as st
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
import re
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Economy Info Hub", layout="wide", page_icon="📊")

# --- CATEGORY PATTERNS (Recognizing your specific expenses) ---
def get_category(desc):
    d = str(desc).lower()
    mapping = {
        'Subscriptions': ['apple.com', 'adobe', 'openai', 'chatgpt', 'microsoft', 'spotify', 'muslimi.com'],
        'Health': ['legesenter', 'apotek', 'vitus', 'fokus', 'lege'],
        'Savings': ['småsparing'],
        'Travel': ['atb', 'vy', 'fly', 'taxi', 'uber', 'ruten', 'feriereiser'],
        'Food & Groceries': ['kiwi', 'rema', 'coop', 'meny', 'mcdonalds', 'food', 'restaurant'],
        'Charity/Donations': ['yousuf', 'launchgood', 'dawah', 'relief'],
        'Income': ['lønn', 'salary', 'fra:'],
        'Vipps/Transfers': ['vipps', 'overføring', 'til:']
    }
    for cat, keywords in mapping.items():
        if any(k in d for k in keywords): return cat
    return 'General Shopping'

# --- ROBUST SPAREBANK TABLE PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    
    for page in reader.pages:
        text = page.extract_text()
        # SpareBank 1 specific: Data often follows a date like 0112 or 1512
        # This regex looks for: Date + Description + Amount (e.g., 1.529,00)
        lines = text.split('\n')
        for line in lines:
            # Skip non-transaction lines
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo", "Side"]): continue
            
            # Find the Norwegian currency pattern (e.g., 349,00)
            amounts = re.findall(r'(\d+[\d\s.]*,\d{2})', line)
            # Find the date pattern (e.g., 0112)
            dates = re.findall(r'(\d{4})', line)
            
            if amounts and dates:
                # 'Ut av konto' is the first amount on the line in your PDF
                amt_raw = amounts[0].replace(' ', '').replace('.', '').replace(',', '.')
                try:
                    amt = float(amt_raw)
                    if 1.0 <= amt < 25000.0: # Filter noise/account numbers
                        desc = re.sub(r'\d+[\d\s.]*,\d{2}.*', '', line).strip()
                        desc = re.sub(r'^\d{4}\s+', '', desc) # Remove date prefix
                        
                        month_idx = int(dates[0][2:4])
                        month_name = datetime(2025, month_idx, 1).strftime('%B')
                        
                        data.append({
                            "Month": month_name,
                            "Date": dates[0],
                            "Description": desc,
                            "Amount": amt,
                            "Category": get_category(desc)
                        })
                except: continue
    return pd.DataFrame(data)

# --- MAIN INTERFACE ---
st.title("📂 Financial Information Hub")

# 1. BROWSE & SUBMIT
with st.sidebar:
    st.header("📤 Upload Center")
    uploaded_files = st.file_uploader("Browse SpareBank PDFs", type=['pdf'], accept_multiple_files=True)
    st.info("You can upload multiple months at once.")

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df_temp = parse_pdf(f)
        if not df_temp.empty:
            all_data.append(df_temp)
    
    if all_data:
        master_df = pd.concat(all_data).drop_duplicates()
        
        # 2. MONTHLY CALENDAR SELECTOR
        available_months = sorted(master_df['Month'].unique(), key=lambda x: datetime.strptime(x, '%B'))
        selected_month = st.selectbox("📅 Select Month to Analyze", options=available_months)
        
        # Filter for selected month
        month_df = master_df[master_df['Month'] == selected_month]
        spending_df = month_df[~month_df['Category'].isin(['Income', 'Savings'])]

        # 3. DATA INTO GRAPHICS
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spending", f"{spending_df['Amount'].sum():,.2f} NOK")
        col2.metric("Total Savings", f"{month_df[month_df['Category'] == 'Savings']['Amount'].sum():,.2f} NOK")
        col3.metric("Charity Given", f"{month_df[month_df['Category'] == 'Charity/Donations']['Amount'].sum():,.2f} NOK")

        left, right = st.columns(2)
        with left:
            st.subheader("Spending by Category")
            fig_pie = px.pie(spending_df, values='Amount', names='Category', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with right:
            st.subheader("Daily Spending Spikes")
            daily = spending_df.groupby('Date')['Amount'].sum().reset_index()
            fig_bar = px.bar(daily, x='Date', y='Amount', labels={'Date': 'Day (DDMM)'})
            st.plotly_chart(fig_bar, use_container_width=True)

        # 4. INFO HUB SEARCH
        st.subheader("🔎 Transaction Search")
        query = st.text_input("Search for a keyword (e.g. 'Apple', 'Vipps', 'Lønn')...")
        if query:
            display_df = month_df[month_df['Description'].str.contains(query, case=False)]
        else:
            display_df = month_df
            
        st.dataframe(display_df[['Date', 'Description', 'Amount', 'Category']].sort_values('Date'), use_container_width=True)

    else:
        st.warning("Data found, but none matched transaction patterns. Please ensure this is a standard SpareBank 1 export.")
else:
    st.info("👋 Upload your first statement to build your info hub.")
