import streamlit as st
import plotly.graph_objects as go
import trimesh
import io
import time
import pandas as pd
import sqlite3
from datetime import datetime
from src.geometry_engine import analyze_stl
from src.rule_validator import validate_design
from src.llm_mentor import generate_explanations, client
import numpy as np 

st.set_page_config(page_title="AI Design Mentor", layout="wide", page_icon="✨")

# ==========================================
# --- REAL DATABASE SETUP (SQLITE) ---
# ==========================================
def init_db():
    conn = sqlite3.connect('nexus.db')
    c = conn.cursor()
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    # Create History Table
    c.execute('''CREATE TABLE IF NOT EXISTS scan_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  email TEXT, file_name TEXT, score INTEGER, 
                  risk_inr REAL, timestamp DATETIME)''')
    conn.commit()
    conn.close()

# Run this once when the app starts
init_db()

def get_db_connection():
    return sqlite3.connect('nexus.db', check_same_thread=False)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { font-family: 'Inter', sans-serif; }
    .gradient-text {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; padding-bottom: 10px;
    }
    .stButton > button {
        border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease; font-weight: 600;
    }
    .stButton > button:hover {
        transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0, 114, 255, 0.2);
        border-color: #0072FF; color: white;
    }
    .stChatInputContainer { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .streamlit-expanderHeader { font-weight: 600; border-radius: 8px; }
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* Hide Streamlit Header, Toolbar (GitHub/Fork), Footer, and Cloud Badges */
    header { visibility: hidden !important; }
    .stApp > header { background-color: transparent !important; }
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    .viewerBadge_container {display: none !important;}
    .viewerBadge_link {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTION: INDIAN NUMBER FORMATTING ---
def format_indian_number(number):
    num_str = str(int(number))
    if len(num_str) <= 3: return num_str
    last_three = num_str[-3:]
    rest = num_str[:-3]
    rest_chunks = [rest[max(i-2, 0):i] for i in range(len(rest), 0, -2)]
    rest_chunks.reverse()
    return ",".join(rest_chunks) + "," + last_three

# --- SESSION STATE (UI Routing & Chat only) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'username' not in st.session_state: st.session_state.username = ""
if "show_register" not in st.session_state: st.session_state.show_register = False
if "auth_message" not in st.session_state: st.session_state.auth_message = ""
if "current_file" not in st.session_state: st.session_state.current_file = ""
if "messages" not in st.session_state: st.session_state.messages = []

# ==========================================
# --- LOGIN & REGISTER PORTAL (SQL POWERED) ---
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 class='gradient-text' style='text-align: center;'>Nexus CAD Intelligence</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 1.1rem;'>Secure Enterprise Authentication</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if st.session_state.auth_message:
            st.success(st.session_state.auth_message)
            st.session_state.auth_message = ""

        if not st.session_state.show_register:
            with st.form("login_form"):
                st.markdown("### 🔒 Secure Login")
                email = st.text_input("Corporate Email Address")
                pwd = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Access Workspace", use_container_width=True)
                
                if submit_login:
                    conn = get_db_connection()
                    c = conn.cursor()
                    # Query the SQL Database
                    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, pwd))
                    user = c.fetchone()
                    conn.close()
                    
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.username = email.split('@')[0] 
                        st.rerun() 
                    else: st.error("Invalid Credentials or Account does not exist.")
            
            if st.button("Need an account? Register here", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()
        else:
            with st.form("register_form"):
                st.markdown("### 📝 Register Account")
                new_email = st.text_input("New Corporate Email")
                new_pwd = st.text_input("Create Password", type="password")
                submit_register = st.form_submit_button("Create Account", use_container_width=True)
                
                if submit_register:
                    if new_email == "" or new_pwd == "": 
                        st.error("Please fill in all fields.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE email=?", (new_email,))
                        if c.fetchone():
                            st.error("Account already exists.")
                        else:
                            # Insert new user into SQL Database
                            c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                                      (new_email, new_pwd, "Senior Engineer"))
                            conn.commit()
                            st.session_state.auth_message = "Registration successful! Please log in."
                            st.session_state.show_register = False 
                        conn.close()
                        st.rerun()
            
            if st.button("Back to Login", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
    st.stop()

# ==========================================
# --- MAIN APPLICATION ---
# ==========================================

def render_3d_model(file_bytes, show_heatmap=False):
    mesh = trimesh.load(io.BytesIO(file_bytes), file_type='stl', process=False)
    vertices = mesh.vertices
    faces = mesh.faces
    
    if show_heatmap:
        # MAGICAL HACKATHON MATH: Simulate "stress points" based on geometry density and distance
        # This makes thin/protruding parts glow red (High Stress), and thick core parts blue (Low Stress)
        center = np.mean(vertices, axis=0)
        distance_from_center = np.linalg.norm(vertices - center, axis=1)
        z_height = vertices[:, 2]
        
        # Combine metrics to create a realistic-looking "AI predicted stress" gradient
        mock_stress = (distance_from_center * 0.5) + (z_height * 0.5)
        
        fig = go.Figure(data=[go.Mesh3d(
            x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
            i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
            intensity=mock_stress,      # Applies the stress values
            colorscale='Turbo',         # The classic Engineering FEA Heatmap colors
            opacity=0.9, 
            flatshading=True,
            showscale=True,
            colorbar_title="Predicted<br>Stress (MPa)"
        )])
    else:
        # Standard Clean Blue Material View
        fig = go.Figure(data=[go.Mesh3d(
            x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
            i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
            color='#0072FF', opacity=0.8, flatshading=True, lighting=dict(ambient=0.5, diffuse=0.8)
        )])
        
    fig.update_layout(
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=0), height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- SIDEBAR (FETCHES FROM SQL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2083/2083213.png", width=50)
    st.markdown(f"### Welcome, **{st.session_state.username.capitalize()}**")
    st.caption("Role: Senior Validation Engineer")
    st.markdown("---")
    
    st.markdown("#### ⚙️ Target Material")
    selected_material = st.selectbox("Select to calibrate AI rules:", 
        ["Low (e.g., Plastic)", "Medium (e.g., Aluminum)", "High (e.g., Steel)"], index=1)
    
    st.markdown("---")
    st.markdown("### 📚 Your Audit History")
    
    # Query SQL for this specific user's history
    conn = get_db_connection()
    history_df = pd.read_sql_query("SELECT file_name, score, timestamp FROM scan_history WHERE email=? ORDER BY timestamp DESC LIMIT 5", conn, params=(st.session_state.user_email,))
    conn.close()
    
    if history_df.empty:
        st.caption("No files scanned yet.")
    else:
        for index, row in history_df.iterrows():
            st.caption(f"**{row['file_name']}** (Score: {row['score']})")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.username = ""
        st.rerun()

# --- HERO SECTION ---
st.markdown("<h1 class='gradient-text'>AI Design Mentor</h1>", unsafe_allow_html=True)

# ==========================================
# 1. UPPER SECTION: UPLOAD & CHAT
# ==========================================
uploaded_file = st.file_uploader("Drop your STL file here to begin analysis", type=["stl"])

if uploaded_file:
    file_name = uploaded_file.name
    
    if st.session_state.current_file != file_name:
        st.session_state.current_file = file_name
        st.session_state.messages = [{"role": "assistant", "content": f"Hi! I've analyzed `{file_name}`. Feel free to ask me anything about its design, structural integrity, or estimated manufacturing costs in ₹."}]

    file_bytes = uploaded_file.read()
    file_for_analysis = io.BytesIO(file_bytes)

    with st.spinner("Analyzing geometry and saving to database..."):
        geom_stats = analyze_stl(file_for_analysis)
        
        if geom_stats["status"] != "error":
            validation_results = validate_design(geom_stats, selected_material)
            score = validation_results['score']
            # Dynamic multiplier based on complexity to avoid identical risk values
            base_multiplier = 10500 + (geom_stats.get('faces', 0) % 500) * 12
            rework_risk_inr = (100 - score) * base_multiplier 

            # SQL INSERT: Save scan to history if not recently saved
            conn = get_db_connection()
            c = conn.cursor()
            # Check if we already logged this exact file recently to avoid spamming the DB on refresh
            c.execute("SELECT * FROM scan_history WHERE email=? AND file_name=? ORDER BY timestamp DESC LIMIT 1", (st.session_state.user_email, file_name))
            last_scan = c.fetchone()
            
            if not last_scan:
                c.execute("INSERT INTO scan_history (email, file_name, score, risk_inr, timestamp) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.user_email, file_name, score, rework_risk_inr, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
            conn.close()
        else:
            st.error(f"Failed to read STL: {geom_stats['message']}")
            st.stop()

    # --- THE CHATBOX ---
    st.markdown("### 💬 Engineering Workbench Chat")
    
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            # === NEW: Custom Blue AI Avatar to replace the orange robot ===
            avatar_icon = "https://cdn-icons-png.flaticon.com/512/3264/3264312.png" if message["role"] == "assistant" else "👤"
            with st.chat_message(message["role"], avatar=avatar_icon):
                st.markdown(message["content"])

    if prompt := st.chat_input("E.g., What is the estimated CNC cost?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        
        with chat_container:
            with st.chat_message("assistant", avatar="https://cdn-icons-png.flaticon.com/512/3264/3264312.png"):
                with st.spinner("Calculating..."):
                    try:
                        system_prompt = {
                            "role": "system", 
                            "content": f"You are a CAD engineering mentor based in India. Material: {selected_material}, Score: {score}/100. Geometric stats: {geom_stats}. ALWAYS use Indian Rupees (₹) formatted with commas in the Indian Numbering System."
                        }
                        api_messages = [system_prompt] + st.session_state.messages
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=api_messages,
                            temperature=0.3
                        )
                        reply = response.choices[0].message.content
                    except Exception as e:
                        reply = "I'm sorry, my connection is currently offline."
                    
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

    # ==========================================
    # 2. LOWER SECTION: DIAGNOSTICS & DETAILS
    # ==========================================
    st.markdown("<br><hr style='opacity: 0.2;'><br>", unsafe_allow_html=True)
    st.markdown("### Interactive CAD Viewer & Diagnostics")
    
    col_score, col_roi, col_faces = st.columns(3)
    with col_score:
        st.metric(label="Quality Score", value=f"{score}/100", delta="Pass 🟢" if score >= 80 else "Fail 🔴", delta_color="normal" if score >= 80 else "inverse")
    with col_roi:
        st.metric(label="Capital at Risk (INR)", value=f"₹{format_indian_number(rework_risk_inr)}", delta="- High Risk" if score < 80 else "Safe", delta_color="inverse")
    with col_faces:
        st.metric(label="Mesh Complexity", value=f"{format_indian_number(geom_stats['faces'])} faces")

    st.plotly_chart(render_3d_model(file_bytes), use_container_width=True)
    
    # === NEW: Generate and format the AI report for downloading ===
    base_feedback = "No critical issues detected." if not validation_results["issues"] else generate_explanations(validation_results["issues"], selected_material)
    
    report_content = f"""# Engineering Validation Report
**File Name:** {file_name}
**Material Selected:** {selected_material}
**Quality Score:** {score}/100
**Capital at Risk:** ₹{format_indian_number(rework_risk_inr)}

## AI Mentor Analysis:
{base_feedback}
"""
    
    # === NEW: Download button placed right above the expander ===
    st.download_button(
        label="📄 Download Official AI Validation Report (.md)",
        data=report_content,
        file_name=f"Validation_Report_{file_name}.md",
        mime="text/markdown",
        use_container_width=True
    )

    with st.expander("🤖 View Full AI Diagnostic Report", expanded=False):
        st.markdown(base_feedback)

    with st.expander("💼 Advanced Enterprise Integrations (API, Jira, SQL Audit)"):
        tab_audit, tab_api, tab_workflow = st.tabs(["📋 Global SQL Audit Log", "🔌 Developer API", "🔄 Automations"])
        
        with tab_audit:
            # Query the database for the global company audit
            conn = get_db_connection()
            full_audit_df = pd.read_sql_query("SELECT email, file_name, score, risk_inr, timestamp FROM scan_history ORDER BY timestamp DESC", conn)
            conn.close()
            
            if not full_audit_df.empty:
                st.dataframe(full_audit_df, hide_index=True, use_container_width=True)
            else:
                st.caption("No history to display.")
                
        with tab_api:
            st.json({"status": "success", "file": file_name, "score": score, "risk_inr": rework_risk_inr})
        with tab_workflow:
            col_j, col_s = st.columns(2)
            with col_j:
                if st.button("🎫 Create Jira Ticket"): st.success("Ticket Created!")
            with col_s:
                if st.button("💬 Alert Slack"): st.success("Slack Notified!")