import streamlit as st
import PyPDF2
from google import genai
from google.genai import types
from duckduckgo_search import DDGS
from pydantic import BaseModel
import time
import json
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Pydantic models for structured output
class Claim(BaseModel):
    claim: str
    context: str
    category: str

class ExtractedClaims(BaseModel):
    claims: list[Claim]

class VerificationResult(BaseModel):
    status: str
    explanation: str
    confidence_score: int
    trusted_source_found: bool

st.set_page_config(page_title="AI Fact-Checker", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Futuristic Enterprise SaaS UI
st.markdown("""
<style>
    /* Dark Theme & Neon Accents */
    :root {
        --bg-color: #0b0e14;
        --panel-bg: rgba(18, 22, 31, 0.7);
        --border-color: rgba(60, 110, 255, 0.3);
        --neon-blue: #00f2fe;
        --neon-purple: #4facfe;
        --text-main: #e2e8f0;
        --text-muted: #94a3b8;
    }
    
    /* Global Background */
    .stApp {
        background-color: var(--bg-color);
        background-image: 
            radial-gradient(at 0% 0%, rgba(0, 242, 254, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(79, 172, 254, 0.05) 0px, transparent 50%);
        color: var(--text-main);
    }

    /* Glassmorphism Cards */
    div[data-testid="stExpander"], div[data-testid="stMetric"], .css-1r6slb0, .css-1y4p8pa {
        background: var(--panel-bg) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Neon Typography */
    h1, h2, h3 {
        background: linear-gradient(90deg, var(--neon-blue) 0%, var(--neon-purple) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Metric Labels */
    div[data-testid="stMetricLabel"] > label {
        color: var(--text-muted) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.8rem !important;
    }
    
    /* Metric Values */
    div[data-testid="stMetricValue"] {
        color: var(--text-main) !important;
        font-weight: 800 !important;
    }

    /* Status Badges */
    .status-verified { color: #10b981; font-weight: 600; text-shadow: 0 0 10px rgba(16,185,129,0.3); }
    .status-inaccurate { color: #f59e0b; font-weight: 600; text-shadow: 0 0 10px rgba(245,158,11,0.3); }
    .status-false { color: #ef4444; font-weight: 600; text-shadow: 0 0 10px rgba(239,68,68,0.3); }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #1e3a8a 0%, #312e81 100%);
        border: 1px solid var(--neon-blue);
        color: white;
        border-radius: 6px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 1px;
    }
    .stButton > button:hover {
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.5);
        border-color: var(--neon-blue);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.title("FACT-CHECK PLATFORM v2.0")
st.markdown("<p style='color:#94a3b8; font-size: 1.1rem; margin-top: -15px; margin-bottom: 30px;'>Automated Truth Layer & Risk Analytics Engine</p>", unsafe_allow_html=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None

if not api_key:
    st.sidebar.header("System Config")
    api_key = st.sidebar.text_input("Enter API Key (Secure)", type="password")

# --- CORE FUNCTIONS ---
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])

def extract_claims(text, client):
    prompt = f"""
    Extract specific, verifiable claims from the text.
    Focus on stats, dates, financials, technical specs.
    Categorize each claim (e.g., Financial, Technical, Date, Operation).
    Text: {text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedClaims,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)["claims"]
    except Exception as e:
        return []

def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        return " ".join([res["body"] for res in results]) if results else "No data."
    except Exception as e:
        return ""

def verify_claim(claim, search_results, client):
    prompt = f"""
    Verify this claim using ONLY the web search results.
    Claim: "{claim['claim']}"
    Context: "{claim['context']}"
    Web Data: {search_results}
    
    Determine status:
    - Verified: Results support claim.
    - Inaccurate: Results show claim is partially wrong/outdated.
    - False: Results contradict claim.
    
    Provide explanation, confidence_score (0-100), and trusted_source_found (true/false based on quality of web data).
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VerificationResult,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        return {"status": "Error", "explanation": "Verification failed.", "confidence_score": 0, "trusted_source_found": False}

# --- UI LOGIC ---
uploaded_file = st.file_uploader("INGEST DOCUMENT (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if st.button("INITIALIZE ANALYSIS"):
        st.markdown("---")
        
        with st.spinner("Processing document embeddings..."):
            text = extract_text_from_pdf(uploaded_file)
            
        if not text.strip():
            st.error("Document is empty or unreadable.")
            st.stop()
            
        client = genai.Client(api_key=api_key)
        
        with st.spinner("Extracting knowledge graph & claims..."):
            claims = extract_claims(text[:20000], client)
            
        if not claims:
            st.warning("No significant claims detected.")
            st.stop()
            
        # Top Dashboard Metrics Placeholders
        dash_col1, dash_col2, dash_col3 = st.columns(3)
        metric_total = dash_col1.empty()
        metric_truth = dash_col2.empty()
        metric_risk = dash_col3.empty()
        
        metric_total.metric("Claims Analyzed", f"0 / {len(claims)}")
        metric_truth.metric("System Truth Score", "Processing...")
        metric_risk.metric("Misinformation Risk", "Analyzing...")
        
        st.markdown("### LIVE VERIFICATION FEED")
        feed_container = st.container()
        
        results_list = []
        verified_count = 0
        false_count = 0
        
        for i, claim in enumerate(claims):
            with feed_container:
                with st.expander(f"SCAN {i+1}: {claim['claim'][:80]}...", expanded=False):
                    col_info, col_ai = st.columns([1, 1.2])
                    
                    with col_info:
                        st.markdown("<p style='color:#4facfe; font-size:0.8rem; font-weight:bold; letter-spacing:1px;'>SOURCE NODE</p>", unsafe_allow_html=True)
                        st.markdown(f"**Statement:** {claim['claim']}")
                        st.markdown(f"**Context:** {claim['context']}")
                        st.markdown(f"**Tag:** `{claim.get('category', 'General')}`")
                        
                    with col_ai:
                        search_results = search_web(claim['claim'])
                        ver = verify_claim(claim, search_results, client)
                        
                        status = ver.get("status", "Error")
                        explanation = ver.get("explanation", "")
                        conf = ver.get("confidence_score", 0)
                        trusted = ver.get("trusted_source_found", False)
                        
                        if status == "Verified":
                            status_class = "status-verified"
                            verified_count += 1
                        elif status == "False":
                            status_class = "status-false"
                            false_count += 1
                        else:
                            status_class = "status-inaccurate"
                            false_count += 0.5 # Partial risk
                            
                        badge = "Trusted Source" if trusted else "Unverified Source"
                        
                        st.markdown("<p style='color:#00f2fe; font-size:0.8rem; font-weight:bold; letter-spacing:1px;'>AI REASONING ENGINE</p>", unsafe_allow_html=True)
                        st.markdown(f"Verdict: <span class='{status_class}'>{status.upper()}</span>", unsafe_allow_html=True)
                        
                        # Progress bar for confidence
                        st.progress(conf / 100.0, text=f"Confidence: {conf}% | {badge}")
                        
                        st.markdown(f"<div style='background: rgba(0,0,0,0.3); padding: 10px; border-radius: 5px; border-left: 3px solid #4facfe; font-size: 0.9rem;'>{explanation}</div>", unsafe_allow_html=True)
                        
                    results_list.append({
                        "Claim": claim['claim'],
                        "Category": claim.get('category', 'General'),
                        "Status": status,
                        "Confidence": conf,
                        "Explanation": explanation
                    })
                    
            # Update Dashboard Metrics live
            current_processed = i + 1
            truth_score = int((verified_count / current_processed) * 100)
            risk_score = "CRITICAL" if false_count > (current_processed * 0.3) else ("MODERATE" if false_count > 0 else "LOW")
            
            metric_total.metric("Claims Analyzed", f"{current_processed} / {len(claims)}")
            metric_truth.metric("System Truth Score", f"{truth_score}%")
            metric_risk.metric("Misinformation Risk", risk_score)
            
            time.sleep(1) # Small delay to respect rate limits
            
        st.markdown("---")
        st.markdown("### RISK ANALYTICS DASHBOARD")
        
        df = pd.DataFrame(results_list)
        
        # Analytics Columns
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Truth Score Gauge
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = truth_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Overall Truth Index", 'font': {'color': '#e2e8f0'}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickcolor': "#e2e8f0"},
                    'bar': {'color': "#00f2fe"},
                    'bgcolor': "rgba(0,0,0,0)",
                    'steps': [
                        {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.3)"},
                        {'range': [50, 80], 'color': "rgba(245, 158, 11, 0.3)"},
                        {'range': [80, 100], 'color': "rgba(16, 185, 129, 0.3)"}],
                }
            ))
            fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#e2e8f0"}, height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
        with chart_col2:
            # Misinformation Heatmap (Bar chart of status by category)
            fig_bar = px.histogram(df, x="Category", color="Status", 
                                   title="Claim Distribution by Category",
                                   color_discrete_map={"Verified": "#10b981", "Inaccurate": "#f59e0b", "False": "#ef4444", "Error": "#94a3b8"})
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': "#e2e8f0"}, height=300)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # Export Button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="EXPORT INTELLIGENCE REPORT (CSV)",
            data=csv,
            file_name='palantir_fact_report.csv',
            mime='text/csv',
        )

elif uploaded_file and not api_key:
    st.warning("SYSTEM LOCKED: Authentication Token Required.")
