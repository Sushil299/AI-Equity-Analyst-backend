# -*- coding: utf-8 -*-
"""admin_app

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1-kL48zJMZD2sqabS-FeKumgjGmbYXeYY
"""

import streamlit as st
import requests
from datetime import datetime
import os
import io
import pandas as pd

# Backend URL
BACKEND_URL = "https://ai-equity-analyst.onrender.com"

st.title("📤 Admin Panel - Upload Documents")

# 🔹 Form for Uploading Individual Files
st.sidebar.header("Upload Financial Documents")

nse_ticker = st.sidebar.text_input("NSE Ticker")
company_name = st.sidebar.text_input("Company Name")

# 🔹 Annual Report Upload
annual_year = st.sidebar.selectbox("Annual Report for", ["FY25", "FY24", "FY23", "FY22"])
annual_file = st.sidebar.file_uploader("Upload Annual Report", type=["pdf"], key="annual")

# 🔹 Quarterly Report Upload
quarter_year = st.sidebar.selectbox("Quarterly Report for", ["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25"])
quarterly_file = st.sidebar.file_uploader("Upload Quarterly Report", type=["pdf"], key="quarterly")

# 🔹 Earnings Call Transcript Upload
earning_year = st.sidebar.selectbox("Earnings Call for", ["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25"])
earning_file = st.sidebar.file_uploader("Upload Earnings Call Transcript", type=["pdf"], key="earnings")

# 🔹 Investor Presentation Upload
presentation_year = st.sidebar.selectbox("Investor Presentation for", ["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25"])
presentation_file = st.sidebar.file_uploader("Upload Investor Presentation", type=["pdf"], key="presentation")

if st.sidebar.button("Submit"):
    if company_name and nse_ticker:
        uploaded = False
        for doc_type, file, period in [
            ("Annual Report", annual_file, annual_year),
            ("Quarterly Report", quarterly_file, quarter_year),
            ("Earnings Call Transcript", earning_file, earning_year),
            ("Investor Presentation", presentation_file, presentation_year)
        ]:
            if file:
                files = {"file": (file.name, file.getvalue(), "application/pdf")}
                data = {
                    "company_name": company_name,
                    "document_date": period,
                    "document_type": doc_type,
                }
                response = requests.post(f"{BACKEND_URL}/upload/", files=files, data=data)
                if response.status_code == 200:
                    st.sidebar.success(f"✅ {doc_type} uploaded successfully!")
                    uploaded = True
                else:
                    st.sidebar.error(f"❌ Upload failed for {doc_type}: {response.text}")

        if not uploaded:
            st.sidebar.warning("⚠️ No files uploaded. Please select at least one document.")
    else:
        st.sidebar.warning("⚠️ Please enter the NSE ticker and company name.")

# 🔹 Show Available Companies & Uploaded Documents
st.markdown("## 📄 Uploaded Company Documents")

response = requests.get(f"{BACKEND_URL}/admin-summary")
if response.status_code == 200:
    company_data = response.json().get("companies", [])
    if company_data:
        df = pd.DataFrame(company_data)
        st.table(df)
    else:
        st.warning("⚠️ No data available.")
else:
    st.error("❌ Failed to fetch company data.")