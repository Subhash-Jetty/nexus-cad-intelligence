import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# 1. Load the .env file for local development
load_dotenv() 

# 2. Get the key — try Streamlit secrets first (cloud), then fall back to .env (local)
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

# 3. Check if key exists and initialize the client pointing to Groq
if not api_key:
    client = None
    print("Warning: API Key not found in environment.")
else:
    # MAGIC HAPPENS HERE: We tell the OpenAI library to talk to Groq's servers
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1" 
    )

def generate_explanations(issues_list, material):
    """Takes deterministic issues and asks the LLM to explain them."""
    if not client:
        return "AI Mentor is currently offline (Missing API Key)."
    
    if not issues_list:
        return "No issues detected. The design looks robust!"

    # We now tell the AI exactly what material we are using!
    prompt = f"""
    You are a Senior Mechanical Engineer reviewing a CAD design intended to be manufactured from **{material}**. 
    The automated system flagged the following issues: {issues_list}.
    
    For EACH issue, provide a brief, professional response structured exactly like this:
    - **Issue:** [Name of issue]
    - **Why it matters:** [1-2 sentences explaining the physics/manufacturing risk for this specific material]
    - **How to fix it:** [Actionable advice for the CAD designer]
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[
                {"role": "system", "content": "You are a helpful, expert AI CAD mentor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Generation failed: {str(e)}"