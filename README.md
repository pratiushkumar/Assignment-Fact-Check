# 🔍 FACT-CHECK PLATFORM v2.0
**Automated Truth Layer & Risk Analytics Engine**

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%202.5-orange.svg)

## Overview
The Fact-Check Platform is an AI-powered SaaS dashboard designed to automate claim verification from PDF documents. Marketing content often contains outdated or hallucinated statistics. This tool acts as a "Truth Layer," extracting verifiable claims (statistics, dates, financial figures) and cross-referencing them against live web data to flag inaccuracies.

## 🚀 Core Features
- **Automated Claim Extraction:** Intelligently identifies and categorizes claims (Financial, Technical, Date, General) directly from PDFs.
- **Live Web Verification:** Cross-references each claim with live web search results (DuckDuckGo Search API) to ensure real-time accuracy.
- **AI Reasoning Engine:** Provides a strict verdict (`Verified`, `Inaccurate`, `False`) alongside a detailed explanation and a **Confidence Score (0-100%)**.
- **Risk Analytics Dashboard:** Visualizes the overall system "Truth Score" and claim distribution using interactive Plotly gauges and heatmaps.
- **Data Export:** Download the final verification intelligence report as a CSV for offline analysis.
- **Enterprise UI:** Features a futuristic, dark-mode dashboard with glassmorphism components.

## 🛠️ Tech Stack
- **Framework:** Streamlit
- **LLM Engine:** Google GenAI (`gemini-2.5-flash`)
- **Web Search:** DuckDuckGo Search (`duckduckgo-search`)
- **Data Visualization:** Plotly & Pandas
- **Document Processing:** PyPDF2

## 💻 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/pratiushkumar/Assignment-Fact-Check.git
   cd Assignment-Fact-Check
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys:**
   Create a `.streamlit/secrets.toml` file in the root directory and add your Google Gemini API key:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## ☁️ Deployment
This application is fully compatible with **Streamlit Community Cloud**, **Render**, and **Vercel**. 
To deploy on Streamlit Cloud:
1. Connect your GitHub repository.
2. Set the main file path to `app.py`.
3. Add your `GEMINI_API_KEY` into the Streamlit Advanced Settings -> Secrets manager.
