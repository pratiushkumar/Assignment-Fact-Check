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

st.set_page_config(page_title="Fact-Check Agent", layout="wide")

st.title("Fact-Checking Web App (Truth Layer)")
st.write("Upload a Document to extract specific claims, cross-reference them with live web data, and verify their accuracy.")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None

if not api_key:
    st.sidebar.header("Configuration")
    st.sidebar.info("To hide this input, set `GEMINI_API_KEY` in Streamlit secrets.")
    api_key = st.sidebar.text_input("Enter your Google Gemini API Key", type="password")
    st.sidebar.markdown("[Get a Gemini API Key](https://aistudio.google.com/app/apikey)")

uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def extract_claims(text, client):
    prompt = f"""
    You are an expert fact-checker. Please read the following text and extract all specific, verifiable claims.
    Focus on: statistics, dates, financial figures, technical specifications, and absolute statements.
    Also provide a short 'category' for each claim (e.g., Financial, Date, Technical, General).
    
    Text:
    {text}
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
        st.error(f"Error extracting claims: {e}")
        return []

def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        return " ".join([res["body"] for res in results]) if results else "No results found."
    except Exception as e:
        return f"Error during web search: {e}"

def verify_claim(claim, search_results, client):
    prompt = f"""
    You are a professional fact-checker. Verify the following claim using ONLY the provided web search results.
    
    Claim to verify: "{claim['claim']}"
    Context of claim: "{claim['context']}"
    
    Web Search Results:
    {search_results}
    
    Determine if the claim is:
    - Verified: The search results support the claim.
    - Inaccurate: The search results show the claim is partially wrong, outdated, or misleading.
    - False: The search results directly contradict the claim, or there is no evidence found to support it.
    
    Provide a brief explanation including the actual facts from the search results.
    Also provide a 'confidence_score' from 0 to 100 representing how confident you are in this assessment based on the search results.
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
        return {"status": "Error", "explanation": str(e), "confidence_score": 0}

if uploaded_file and api_key:
    if st.button("Start Fact-Checking"):
        with st.spinner("Extracting text from PDF..."):
            text = extract_text_from_pdf(uploaded_file)
        
        if not text.strip():
            st.error("Could not extract any text from the PDF.")
            st.stop()
            
        client = genai.Client(api_key=api_key)
        
        with st.spinner("Extracting claims..."):
            claims = extract_claims(text[:20000], client)
            
        if not claims:
            st.warning("No verifiable claims found in the document.")
            st.stop()
            
        st.subheader(f"Found {len(claims)} claims. Verifying...")
        
        progress_bar = st.progress(0)
        results_list = []
        
        for i, claim in enumerate(claims):
            # Using an expander for a cleaner UI
            with st.expander(f"Claim {i+1}: {claim['claim'][:70]}...", expanded=True):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("**Statement:**")
                    st.info(claim['claim'])
                    st.markdown(f"**Context:** {claim['context']}")
                    st.markdown(f"**Category:** {claim.get('category', 'General')}")
                
                with col2:
                    # Search web
                    with st.spinner("Searching web..."):
                        search_results = search_web(claim['claim'])
                    
                    # Verify
                    with st.spinner("Verifying claim..."):
                        verification = verify_claim(claim, search_results, client)
                    
                    status = verification.get("status", "Error")
                    explanation = verification.get("explanation", "No explanation provided.")
                    confidence = verification.get("confidence_score", 0)
                    
                    st.markdown("**Verification Result:**")
                    if status == "Verified":
                        st.success(f"Status: {status} (Confidence: {confidence}%)\n\n{explanation}")
                    elif status == "Inaccurate":
                        st.warning(f"Status: {status} (Confidence: {confidence}%)\n\n{explanation}")
                    elif status == "False":
                        st.error(f"Status: {status} (Confidence: {confidence}%)\n\n{explanation}")
                    else:
                        st.info(f"Status: {status} (Confidence: {confidence}%)\n\n{explanation}")
                
                results_list.append({
                    "Claim": claim['claim'],
                    "Context": claim['context'],
                    "Category": claim.get('category', 'General'),
                    "Status": status,
                    "Confidence Score": confidence,
                    "Explanation": explanation
                })
                
            progress_bar.progress((i + 1) / len(claims))
            time.sleep(1) # Small delay to respect rate limits
            
        st.success("Fact-checking complete!")
        
        # Data Export Feature
        st.markdown("### Export Results")
        df = pd.DataFrame(results_list)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name='fact_check_results.csv',
            mime='text/csv',
        )

elif uploaded_file and not api_key:
    st.warning("Please enter your Google Gemini API key in the sidebar to proceed.")
