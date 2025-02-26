# -*- coding: utf-8 -*-
"""backend

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1UMPFrnSiYVrOpvw5fv4SMpnmB-e-CE9z
"""

import os
import datetime
import psycopg2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF for PDF text extraction
import google.generativeai as genai

# ✅ Initialize FastAPI
app = FastAPI(title="AI Equity Research API")

# ✅ PostgreSQL Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")  # Set this in Render's environment variables
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# ✅ Ensure Tables Exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    document_date TEXT NOT NULL,
    document_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS final_analysis (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    document_date TEXT NOT NULL,
    final_summary TEXT NOT NULL,
    UNIQUE(company_name, document_date)
);
""")
conn.commit()

# ✅ Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Set in Render's environment variables
genai.configure(api_key=GEMINI_API_KEY)

# ✅ Extract Text from PDF Without Storing the File
def extract_text_from_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes.read(), filetype="pdf")
    return "\n".join([page.get_text("text") for page in doc])

# ✅ API: Upload & Process File
@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    document_date: str = Form(...),
    document_type: str = Form(...)
):
    try:
        # ✅ Extract text from PDF
        text = extract_text_from_pdf(file)

        # ✅ Store extracted text in `summaries` table
        cursor.execute("""
            INSERT INTO summaries (company_name, document_date, document_type, filename, summary)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_name, document_date, document_type) DO UPDATE
            SET filename = EXCLUDED.filename, summary = EXCLUDED.summary
        """, (company_name, document_date, document_type, file.filename, text))
        conn.commit()

        # ✅ Fetch all existing summaries for this company & period
        cursor.execute("""
            SELECT summary FROM summaries WHERE company_name = %s AND document_date = %s
        """, (company_name, document_date))
        all_summaries = [row[0] for row in cursor.fetchall()]

        # ✅ Combine all document summaries
        combined_text = "\n\n".join(all_summaries)

        # ✅ Generate AI Analysis Only When a New File is Uploaded
        ai_prompt = f"""
        Generate a structured **equity research report** for {company_name} for the period {document_date}.

        **1. Executive Summary**
        **2. Key Financial Highlights** (Show in Markdown table)
        **3. Business & Operational Highlights**
        **4. Market & Competitive Positioning**
        **5. Valuation & Outlook**

        **Data Sources:**
        {combined_text}
        """
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(ai_prompt)

        final_analysis = response.text

        # ✅ Store AI-generated report in `final_analysis` table
        cursor.execute("""
            INSERT INTO final_analysis (company_name, document_date, final_summary)
            VALUES (%s, %s, %s)
            ON CONFLICT (company_name, document_date) DO UPDATE
            SET final_summary = EXCLUDED.final_summary
        """, (company_name, document_date, final_analysis))
        conn.commit()

        return {"message": "✅ File uploaded & AI analysis updated successfully."}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

# ✅ API: Fetch Precomputed AI Report (No Re-Analysis)
@app.get("/summary/{company_name}/{document_date}")
async def get_summary(company_name: str, document_date: str):
    cursor.execute("""
        SELECT final_summary FROM final_analysis WHERE company_name = %s AND document_date = %s
    """, (company_name, document_date))

    row = cursor.fetchone()
    if not row:
        return {"message": "No precomputed analysis found for this company and period."}

    return {"Company Name": company_name, "Period": document_date, "Comprehensive Analysis": row[0]}

# ✅ API: Fetch All Companies (For Dropdown in UI)
@app.get("/companies")
async def get_companies():
    cursor.execute("SELECT DISTINCT company_name FROM summaries")
    companies = [row[0] for row in cursor.fetchall()]
    return {"companies": companies} if companies else {"message": "No companies found."}

# ✅ API: Admin Panel - View Uploaded Documents
@app.get("/admin-summary")
async def get_admin_summary():
    cursor.execute("""
        SELECT company_name,
               MAX(CASE WHEN document_type = 'Annual Report' THEN 'Yes' ELSE 'No' END) AS annual_report,
               MAX(CASE WHEN document_type = 'Quarterly Report' THEN 'Yes' ELSE 'No' END) AS quarterly_report,
               MAX(CASE WHEN document_type = 'Earnings Call Transcript' THEN 'Yes' ELSE 'No' END) AS earnings_call,
               MAX(CASE WHEN document_type = 'Investor Presentation' THEN 'Yes' ELSE 'No' END) AS investor_presentation,
               MIN(document_date) AS created_date,
               MAX(document_date) AS last_updated_date
        FROM summaries
        GROUP BY company_name
    """)
    rows = cursor.fetchall()

    return {"companies": [{"Company Name": row[0], "Annual Report": row[1], "Quarterly Report": row[2],
                           "Earnings Call Transcript": row[3], "Investor Presentation": row[4],
                           "Created Date": row[5], "Last Updated Date": row[6]} for row in rows]}

# ✅ API: Debug - View Raw Data (For Admin Use)
@app.get("/debug-summaries")
async def debug_summaries():
    cursor.execute("SELECT * FROM summaries")
    data = cursor.fetchall()
    return {"data": data}