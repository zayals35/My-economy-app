import streamlit as st
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
import re
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Economy Info Hub", layout="wide", page_icon="📊")

# Custom CSS for a clean, professional "Hub" look
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1e1e1e; }
    .metric-container { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- SMART CATEGORIZATION ---
def get_category(desc):
    d = str(desc).lower()
    # Patterns directly from your SpareBank statement
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

# --- SPAREBANK 1 PDF PARSER ---
def parse_pdf(file):
    reader = PdfReader(file)
    data = []
    
    for page in reader.pages:
        text = page.extract_text()
        lines = text.split('\n')
        
        for line in lines:
            # Skip noise like IBAN, account headers, or empty lines
            if any(x in line for x in ["4212.02.65827", "IBAN", "Saldo", "Referanse", "Side"]): continue
            
            # Pattern: Description followed by Norwegian amount format (e.g., 349,00)
            match = re.search(r'(.*?)\s+(\d+[\d\s.]*,\d{2})', line)
            
            # Pattern: Also look for dates in DDMM format (e.g. 0112)
            date_match = re.search(r'(\d{4})', line)
            
            if match:
                desc_raw = match.group(1).strip()
                amt_raw = match.group(2).replace(' ', '').replace('.', '').replace(',', '.')
                date_str = date_match.group(1) if date_match else "0101" # Default to Jan 1st if missing
                
                try:
                    amt = float(amt_raw)
                    # Filter out system IDs and balance totals (usually > 20k or < 1)
                    if 1.0 <= amt < 20000.0:
                        # Attempt to format date into a readable Month
                        month_int = int(date_str[2:4])
                        month_name = datetime(2025, month_int, 1).strftime('%B')
                        
                        data.append({
                            "Month": month_name,
                            "Date_Code": date_str,
                            "Description": re.sub(r'^\d{4}\s+', '', desc_raw), # Clean date prefix
                            "Amount": amt,
                            "Category": get_category(desc_raw)
                        })
                except: continue
    return pd.DataFrame(data)

# --- MAIN UI ---
st.title("📂 Economy Information Hub")
st.markdown("Upload multiple monthly statements to build your financial archive.")

# 1. BROWSE & SUBMIT (Sidebar)
with st.sidebar:
    st.header("📤 Document Upload")
    uploaded_files = st.file_uploader("Upload SpareBank 1 PDFs", type=['pdf'], accept_multiple_files=True)
    st.info("Upload files for different months (e.g., Nov, Dec) to see the full timeline.")

if uploaded_files:
    # Build Master Data
    all_data = []
    for f in uploaded_files:
        df_temp = parse_pdf(f)
        if not df_temp.empty:
            all_data.append(df_temp)
    
    if all_data:
        master_df = pd.concat(all_data).drop_duplicates()
        
        # 2. MONTHLY CALENDAR SELECTOR
        available_months = master_df['Month'].unique()
        selected_month = st.selectbox("📅 Select Month to View", options=available_months)
        
        # Filter data based on selected month
        month_df = master_df[master_df['Month'] == selected_month]
        spending_df = month_df[~month_df['Category'].isin(['Income', 'Savings'])]

        # 3. DATA TO GRAPHICS
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spent", f"{spending_df['Amount'].sum():,.2f} NOK")
        col2.metric("Total Saved", f"{month_df[month_df['Category'] == 'Savings']['Amount'].sum():,.2f} NOK")
        col3.metric("Charity Given", f"{month_df[month_df['Category'] == 'Charity/Donations']['Amount'].sum():,.2f} NOK")

        c_left, c_right = st.columns(2)
        
        with c_left:
            st.subheader(f"Spending Breakdown: {selected_month}")
            fig_pie = px.pie(spending_df, values='Amount', names='Category', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:
            st.subheader("Daily Spending Trend")
            daily_trend = spending_df.groupby('Date_Code')['Amount'].sum().reset_index()
            fig_bar = px.bar(daily_trend, x='Date_Code', y='Amount', 
                             labels={'Date_Code': 'Day (DDMM)', 'Amount': 'NOK'},
                             color_discrete_sequence=['#00d4ff'])
            st.plotly_chart(fig_bar, use_container_width=True)

        # 4. SEARCHABLE INFO HUB
        st.subheader("📝 Transaction Details")
        search_query = st.text_input("Search description (e.g., 'Apple', 'Vipps', 'Ticket')...")
        
        if search_query:
            display_df = month_df[month_df['Description'].str.contains(search_query, case=False)]
        else:
            display_df = month_df
            
        st.dataframe(display_df[['Date_Code', 'Description', 'Amount', 'Category']].sort_values('Date_Code'), 
                     use_container_width=True)

    else:
        st.error("No transaction data found. Please ensure you are uploading standard digital PDF statements.")
else:
    st.info("👋 Welcome! Upload your bank statements in the sidebar to populate your info hub.")
