import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="IBIT Strategy Tracker", layout="wide")

TARGET_IBIT_SHARES = 1756

def load_portfolio(filepath):
    return pd.read_excel(filepath)

def fetch_market_data():
    ibit = yf.Ticker("IBIT")
    fbtc = yf.Ticker("FBTC")
    btc = yf.Ticker("BTC-USD")
    return {
        'IBIT_Price': ibit.history(period="1d").iloc[-1]['Close'],
        'FBTC_Price': fbtc.history(period="1d").iloc[-1]['Close'],
        'BTC_Price': btc.history(period="1d").iloc[-1]['Close']
    }

def calculate_current_ibits(df):
    return df[(df['Asset Type'] == 'IBIT Share')]['Quantity'].sum()

def calculate_option_delta_gain(df, ibit_price):
    options = df[df['Asset Type'] == 'Option']
    total_delta_equivalent = 0
    for _, row in options.iterrows():
        if ibit_price > row['Strike']:
            delta_est = 0.9 if ibit_price - row['Strike'] > 20 else 0.75
            total_delta_equivalent += delta_est * 100 * row['Quantity']
    return total_delta_equivalent

def draw_coin_progress(current, target):
    fig, ax = plt.subplots(figsize=(3, 3))
    percent = min(current / target, 1.0)
    wedges, _ = ax.pie([percent, 1 - percent], startangle=90, counterclock=False, colors=['#4CAF50', '#e0e0e0'])
    ax.legend(wedges, [f"{percent * 100:.1f}% of Goal"], loc="center")
    plt.setp(wedges, width=0.3)
    ax.set(aspect="equal", title="Progress to 1 BTC (1756 IBIT)")
    return fig

def analyze_options(df, ibit_price):
    records = []
    for _, row in df[df['Asset Type'] == 'Option'].iterrows():
        expiry = pd.to_datetime(row['Expiry']) if not pd.isnull(row['Expiry']) else None
        days_to_expiry = (expiry - datetime.now()).days if expiry else None
        itm = ibit_price > row['Strike']
        status, note = "Green", "No action necessary"

        if itm and days_to_expiry and days_to_expiry < 60:
            status, note = "Red", "Exercise or roll soon"
        elif itm and days_to_expiry and days_to_expiry < 120:
            status, note = "Orange", "Monitor for early exercise"
        elif not itm and days_to_expiry and days_to_expiry < 90:
            status, note = "Red", "Action needed immediately due to time decay"
        elif not itm:
            status, note = "Yellow", "Monitor – could move ITM with rally"

        records.append({
            'Option (Strike / Expiry)': f"${int(row['Strike'])} / {expiry.date() if expiry else 'N/A'}",
            'Quantity': row['Quantity'],
            'Status': status,
            'Commentary': note
        })
    return pd.DataFrame(records)

uploaded_file = st.file_uploader("📂 Upload your portfolio Excel file:", type=["xlsx"])

if uploaded_file:
    df = load_portfolio(uploaded_file)
    prices = fetch_market_data()

    ibit_shares = calculate_current_ibits(df)
    option_delta = calculate_option_delta_gain(df, prices['IBIT_Price'])
    total_shares = ibit_shares + option_delta / 100

    st.metric("IBIT Price", f"${prices['IBIT_Price']:.2f}")
    st.metric("BTC Price", f"${prices['BTC_Price']:.0f}")
    st.metric("FBTC Price", f"${prices['FBTC_Price']:.2f}")

    st.pyplot(draw_coin_progress(total_shares, TARGET_IBIT_SHARES))

    st.markdown(f"✅ Sanity Check — IBIT: {ibit_shares}, Options: {int(option_delta / 100)}, Total: {int(total_shares)} / {TARGET_IBIT_SHARES}")

    st.subheader("Option Commentary")
    table = analyze_options(df, prices['IBIT_Price'])

    def color_status(val):
        color = {"Green": "#d4edda", "Yellow": "#fff3cd", "Orange": "#ffeeba", "Red": "#f8d7da"}.get(val, "")
        return f"background-color: {color}"

    st.dataframe(table.style.applymap(color_status, subset=['Status']))

    st.subheader("Detailed Commentary with Rationale")
    rationale_df = pd.read_excel("IBIT_Option_Commentary_With_Rationale.xlsx")
    st.dataframe(rationale_df.style.applymap(color_status, subset=['Status']))

    st.subheader("Raw Portfolio Data")
    st.dataframe(df)
else:
    st.warning("Please upload your portfolio file to begin.")
