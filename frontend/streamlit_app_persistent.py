# -*- coding: utf-8 -*-
"""
Modern Professional Streamlit App with Green/Blue Design
Thread Management and Conversation Memory - Corporate Style
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Backend API URL
BACKEND_URL = "http://localhost:8000"

# Professional Green/Blue Color Scheme
PRIMARY_BLUE = "#1E88E5"  # Vibrant Blue
SECONDARY_BLUE = "#0D47A1"  # Deep Blue
PRIMARY_GREEN = "#00C853"  # Bright Green
SECONDARY_GREEN = "#00897B"  # Teal Green
ACCENT_CYAN = "#00ACC1"  # Cyan
SUCCESS_COLOR = "#4CAF50"  # Material Green
ERROR_COLOR = "#F44336"  # Material Red
WARNING_COLOR = "#FF9800"  # Material Orange
BACKGROUND_LIGHT = "#F5F7FA"  # Light Gray
BACKGROUND_WHITE = "#FFFFFF"
TEXT_PRIMARY = "#263238"  # Dark Blue Gray
TEXT_SECONDARY = "#546E7A"  # Medium Gray
BORDER_COLOR = "#CFD8DC"  # Light Border

# Custom CSS for modern professional styling
st.markdown("""
<style>
    /* Import modern fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    /* Global styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #F5F7FA 0%, #E8EAF6 100%);
        padding: 2rem 1rem;
    }
    
    /* Headers with gradient */
    h1 {
        font-family: 'Poppins', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1E88E5 0%, #00C853 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    h2 {
        font-family: 'Poppins', sans-serif;
        color: #263238;
        font-size: 1.8rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
    }
    
    h3 {
        font-family: 'Poppins', sans-serif;
        color: #1E88E5;
        font-size: 1.3rem;
        font-weight: 500;
        margin-bottom: 0.8rem;
    }
    
    h4 {
        font-family: 'Poppins', sans-serif;
        color: #00897B;
        font-size: 1.1rem;
        font-weight: 500;
    }
    
    /* Subtitle with gradient */
    .subtitle {
        font-size: 1.1rem;
        color: #546E7A;
        font-weight: 400;
        margin-bottom: 1.5rem;
    }
    
    /* Sidebar styling with gradient */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F5F7FA 100%);
        border-right: 2px solid #CFD8DC;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        background: linear-gradient(135deg, #1E88E5 0%, #00C853 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Primary buttons with gradient */
    .stButton > button {
        background: linear-gradient(135deg, #1E88E5 0%, #00C853 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(30, 136, 229, 0.25);
        letter-spacing: 0.3px;
    }
    
    .stButton > button:hover {
        box-shadow: 0 6px 20px rgba(30, 136, 229, 0.35);
        transform: translateY(-2px);
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(30, 136, 229, 0.3);
    }
    
    /* Primary button special styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00C853 0%, #1E88E5 100%);
        font-size: 1.15rem;
        padding: 0.85rem 2rem;
        box-shadow: 0 6px 16px rgba(0, 200, 83, 0.3);
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 8px 24px rgba(0, 200, 83, 0.4);
    }
    
    /* Input fields modern design */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #CFD8DC;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        font-size: 1rem;
        background-color: #FFFFFF;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1E88E5;
        box-shadow: 0 0 0 4px rgba(30, 136, 229, 0.12), 0 4px 8px rgba(0,0,0,0.08);
        outline: none;
    }
    
    /* Labels with modern styling */
    .stTextInput > label,
    .stTextArea > label,
    .stSelectbox > label,
    .stRadio > label,
    .stCheckbox > label {
        color: #263238;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.6rem;
        letter-spacing: 0.3px;
    }
    
    /* Select boxes */
    .stSelectbox > div > div {
        border: 2px solid #CFD8DC;
        border-radius: 8px;
        background-color: #FFFFFF;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #1E88E5;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background-color: #FFFFFF;
        padding: 0.8rem;
        border-radius: 8px;
        border: 1px solid #CFD8DC;
    }
    
    /* Checkbox */
    .stCheckbox {
        background-color: #FFFFFF;
        padding: 0.6rem;
        border-radius: 6px;
    }
    
    /* Success messages with green gradient */
    .stSuccess {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        color: #1B5E20;
        border-left: 5px solid #4CAF50;
        padding: 1.2rem;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.15);
    }
    
    /* Error messages */
    .stError {
        background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
        color: #B71C1C;
        border-left: 5px solid #F44336;
        padding: 1.2rem;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(244, 67, 54, 0.15);
    }
    
    /* Info messages with blue gradient */
    .stInfo {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        color: #0D47A1;
        border-left: 5px solid #1E88E5;
        padding: 1.2rem;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(30, 136, 229, 0.15);
    }
    
    /* Warning messages */
    .stWarning {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        color: #E65100;
        border-left: 5px solid #FF9800;
        padding: 1.2rem;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(255, 152, 0, 0.15);
    }
    
    /* Expander modern design */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%);
        border: 2px solid #CFD8DC;
        border-radius: 8px;
        font-weight: 600;
        color: #1E88E5;
        padding: 1rem;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #1E88E5;
        box-shadow: 0 4px 12px rgba(30, 136, 229, 0.15);
    }
    
    /* Divider */
    hr {
        border: none;
        border-top: 2px solid #CFD8DC;
        margin: 2.5rem 0;
        opacity: 0.6;
    }
    
    /* Thread buttons in sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%);
        color: #263238;
        border: 2px solid #CFD8DC;
        text-align: left;
        font-size: 0.9rem;
        padding: 0.8rem 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        font-weight: 500;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #E3F2FD 0%, #E8F5E9 100%);
        border-color: #1E88E5;
        box-shadow: 0 4px 12px rgba(30, 136, 229, 0.2);
    }
    
    /* Active thread indicator */
    .active-thread {
        border-left: 5px solid #00C853;
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        font-weight: 600;
    }
    
    /* Caption text */
    .caption {
        color: #546E7A;
        font-size: 0.85rem;
        font-weight: 400;
        font-style: italic;
    }
    
    /* Result container with card design */
    .result-container {
        background: linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%);
        border: 2px solid #CFD8DC;
        border-radius: 12px;
        padding: 2rem;
        margin-top: 2rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }
    
    /* Conversation message - User */
    .message-user {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-left: 5px solid #1E88E5;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(30, 136, 229, 0.12);
    }
    
    /* Conversation message - Assistant */
    .message-assistant {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border-left: 5px solid #00C853;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 200, 83, 0.12);
    }
    
    /* Guide box with card design */
    .guide-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%);
        border: 2px solid #CFD8DC;
        border-radius: 12px;
        padding: 1.8rem;
        margin-top: 1.5rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
    }
    
    .guide-box:hover {
        box-shadow: 0 6px 24px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .guide-box h4 {
        color: #1E88E5;
        margin-bottom: 1.2rem;
        font-size: 1.15rem;
        font-weight: 600;
    }
    
    .guide-box ul {
        list-style: none;
        padding-left: 0;
    }
    
    .guide-box li {
        padding: 0.7rem 0;
        border-bottom: 1px solid #E0E0E0;
        color: #263238;
        font-size: 0.95rem;
    }
    
    .guide-box li:last-child {
        border-bottom: none;
    }
    
    .guide-box li::before {
        content: "▸";
        color: #00C853;
        font-weight: bold;
        margin-right: 0.8rem;
        font-size: 1.1rem;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #1E88E5;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #1E88E5;
        font-weight: 700;
    }
    
    /* Status indicators */
    .status-active {
        color: #00C853;
        font-weight: 600;
    }
    
    .status-inactive {
        color: #546E7A;
        font-weight: 500;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #546E7A;
        font-size: 0.9rem;
        padding: 2rem 0;
        border-top: 2px solid #CFD8DC;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Web Agent - AI-Powered Website Analysis",
    page_icon="🌐",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'current_thread_id' not in st.session_state:
    st.session_state.current_thread_id = None
if 'threads' not in st.session_state:
    st.session_state.threads = []
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []


def create_new_thread() -> Optional[str]:
    """Create a new conversation thread"""
    try:
        response = requests.post(
            "{}{}".format(BACKEND_URL, "/threads/create"),
            json={"metadata": {"created_from": "streamlit"}},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("thread_id")
    except Exception as e:
        st.error("Error creating thread: {}".format(e))
    return None


def load_threads() -> List[Dict[str, Any]]:
    """Load available threads"""
    try:
        response = requests.get("{}{}".format(BACKEND_URL, "/threads/list?days=7"), timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get("threads", [])
    except Exception as e:
        st.error("Error loading threads: {}".format(e))
    return []


def load_conversation_history(thread_id: str) -> List[Dict[str, Any]]:
    """Load conversation history for a thread"""
    try:
        response = requests.get(
            "{}/threads/{}/history".format(BACKEND_URL, thread_id),
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("history", [])
    except Exception as e:
        st.error("Error loading history: {}".format(e))
    return []


def load_scheduled_tasks() -> List[Dict[str, Any]]:
    """Load scheduled tasks"""
    try:
        response = requests.get("{}{}".format(BACKEND_URL, "/scheduled_tasks"), timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get("tasks", [])
    except Exception as e:
        st.error("Error loading tasks: {}".format(e))
    return []


# Title and description
st.title("Web Agent")
st.markdown('<p class="subtitle">AI-Powered Website Analysis with Intelligent Conversation Memory</p>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar for thread management
with st.sidebar:
    st.header("Conversation Threads")
    
    # New thread button
    if st.button("+ New Conversation", use_container_width=True):
        new_thread_id = create_new_thread()
        if new_thread_id:
            st.session_state.current_thread_id = new_thread_id
            st.session_state.conversation_history = []
            st.success("New conversation created")
            st.rerun()
    
    # Refresh threads button
    if st.button("↻ Refresh Threads", use_container_width=True):
        st.session_state.threads = load_threads()
    
    # Load threads if not loaded
    if not st.session_state.threads:
        st.session_state.threads = load_threads()
    
    st.markdown("---")
    
    # Display threads
    if st.session_state.threads:
        st.subheader("Recent Conversations")
        
        for thread in st.session_state.threads[:10]:
            thread_id = thread.get("thread_id", "")
            created_at = thread.get("created_at", "")
            message_count = thread.get("message_count", 0)
            
            # Format display
            try:
                created_dt = datetime.fromisoformat(created_at)
                display_time = created_dt.strftime("%b %d, %H:%M")
            except:
                display_time = "Unknown"
            
            is_current = thread_id == st.session_state.current_thread_id
            
            # Use indicator for current thread
            indicator = "●" if is_current else "○"
            button_label = "{} {} ({} msgs)".format(indicator, display_time, message_count)
            
            if st.button(button_label, key="thread_{}".format(thread_id), use_container_width=True):
                st.session_state.current_thread_id = thread_id
                st.session_state.conversation_history = load_conversation_history(thread_id)
                st.rerun()
    else:
        st.info("No conversations yet. Create a new one to get started.")
    
    st.markdown("---")
    
    # Current thread info
    if st.session_state.current_thread_id:
        st.caption("**Current Thread ID:**")
        st.caption("`{}...`".format(st.session_state.current_thread_id[:12]))
    else:
        st.caption("**Current Thread:** None")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Ask a Question")
    
    # Display conversation history
    if st.session_state.conversation_history:
        with st.expander("📜 Conversation History", expanded=False):
            for msg in st.session_state.conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                try:
                    ts_dt = datetime.fromisoformat(timestamp)
                    ts_display = ts_dt.strftime("%H:%M:%S")
                except:
                    ts_display = ""
                
                if role == "user":
                    st.markdown('<div class="message-user"><strong>You</strong> <span class="caption">({})</span><br/>{}</div>'.format(ts_display, content), unsafe_allow_html=True)
                elif role == "assistant":
                    truncated = content[:500] + ("..." if len(content) > 500 else "")
                    st.markdown('<div class="message-assistant"><strong>Assistant</strong> <span class="caption">({})</span><br/>{}</div>'.format(ts_display, truncated), unsafe_allow_html=True)
    
    # User Inputs
    url = st.text_input(
        "Website URL:",
        placeholder="https://www.example.com",
        help="Enter the full URL including https://"
    )
    
    prompt = st.text_area(
        "Your Question or Prompt:",
        placeholder="What is this website about? You can ask follow-up questions in the same thread.",
        height=100,
        help="Ask any question. The agent remembers previous conversations in this thread."
    )
    
    # Mode selection
    col_mode, col_context = st.columns(2)
    
    with col_mode:
        mode = st.radio(
            "Mode:",
            ["Q&A", "Report"],
            index=0,
            horizontal=True,
            help="Q&A: Get specific answers | Report: Generate comprehensive report"
        )
    
    with col_context:
        use_context = st.checkbox(
            "Use Conversation Context",
            value=True,
            help="Include previous conversation history for follow-up questions"
        )
    
    # Schedule options
    schedule_options = [
        "Run Once",
        "Every Hour",
        "Every 3 Hours",
        "Every 4 Hours",
        "Every 6 Hours",
        "Every 12 Hours",
        "Daily"
    ]
    schedule = st.selectbox(
        "Schedule:",
        schedule_options,
        help="Choose how often to run this task"
    )
    
    # Generate button
    generate_button = st.button("Generate", type="primary", use_container_width=True)
    
    if generate_button:
        if not url or not prompt:
            st.error("Please enter both a URL and a prompt.")
        else:
            # Create thread if needed
            if not st.session_state.current_thread_id:
                thread_id = create_new_thread()
                if thread_id:
                    st.session_state.current_thread_id = thread_id
                else:
                    st.error("Failed to create thread")
                    st.stop()
            
            with st.spinner("Processing your request..."):
                try:
                    if schedule == "Run Once":
                        # Execute immediately
                        payload = {
                            "url": url,
                            "prompt": prompt,
                            "mode": mode,
                            "thread_id": st.session_state.current_thread_id,
                            "use_conversation_context": use_context
                        }
                        
                        response = requests.post(
                            "{}{}".format(BACKEND_URL, "/execute_workflow"),
                            json=payload,
                            timeout=120
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("✓ Request completed successfully")
                            
                            # Display result in styled container
                            st.markdown('<div class="result-container">', unsafe_allow_html=True)
                            st.subheader("Result:")
                            answer = result.get("answer", "No answer generated")
                            st.markdown("### Answer:")
                            st.write(answer)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Reload conversation history
                            st.session_state.conversation_history = load_conversation_history(
                                st.session_state.current_thread_id
                            )
                            
                            # Show result details in expander
                            with st.expander("View Full Details"):
                                st.json(result)
                        else:
                            st.error("Error: {} - {}".format(response.status_code, response.text))
                    
                    else:
                        # Schedule task
                        payload = {
                            "url": url,
                            "prompt": prompt,
                            "mode": mode,
                            "schedule": schedule,
                            "thread_id": st.session_state.current_thread_id
                        }
                        
                        response = requests.post(
                            "{}{}".format(BACKEND_URL, "/execute_workflow"),
                            json=payload,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("✓ Task scheduled successfully")
                            st.info("Task will run {}".format(schedule.lower()))
                            task_id = result.get("task_id", "N/A")
                            st.write("**Task ID:** `{}`".format(task_id))
                        else:
                            st.error("Error: {} - {}".format(response.status_code, response.text))
                
                except requests.exceptions.Timeout:
                    st.error("Request timed out. The website might be taking too long to process.")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend server. Make sure the server is running on {}".format(BACKEND_URL))
                except Exception as e:
                    st.error("An unexpected error occurred: {}".format(e))

with col2:
    st.header("Quick Guide")
    
    st.markdown("""
    <div class="guide-box">
        <h4>How to Use</h4>
        <ul>
            <li>Create or select a conversation thread</li>
            <li>Enter a website URL</li>
            <li>Ask a question about it</li>
            <li>Choose Q&A or Report mode</li>
            <li>Enable context for follow-ups</li>
            <li>Click Generate</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="guide-box">
        <h4>Follow-up Examples</h4>
        <ul>
            <li>What was the price again?</li>
            <li>Tell me more about that</li>
            <li>Compare this with previous URL</li>
            <li>Summarize the key points</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="guide-box">
        <h4>Key Features</h4>
        <ul>
            <li>Thread-based conversations</li>
            <li>Conversation memory</li>
            <li>Follow-up questions</li>
            <li>Scheduled automation</li>
            <li>Timestamp tracking</li>
            <li>Multi-mode analysis</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Scheduled Tasks Section
st.markdown("---")
st.header("Scheduled Tasks")

col_tasks_1, col_tasks_2 = st.columns([3, 1])

with col_tasks_2:
    if st.button("↻ Refresh Tasks", use_container_width=True):
        st.rerun()

# Load and display scheduled tasks
scheduled_tasks = load_scheduled_tasks()

if scheduled_tasks:
    for task in scheduled_tasks:
        task_id = task.get("task_id", "N/A")
        url_task = task.get("url", "N/A")
        prompt_task = task.get("prompt", "N/A")
        schedule_interval = task.get("schedule_interval", "N/A")
        is_active = task.get("is_active", False)
        last_run = task.get("last_run", "Never")
        
        status_indicator = "●" if is_active else "○"
        status_text = "Active" if is_active else "Inactive"
        status_class = "status-active" if is_active else "status-inactive"
        
        with st.expander("{} {} - {}...".format(status_indicator, schedule_interval, prompt_task[:50])):
            st.write("**Task ID:** `{}`".format(task_id))
            st.write("**URL:** {}".format(url_task))
            st.write("**Prompt:** {}".format(prompt_task))
            st.write("**Schedule:** {}".format(schedule_interval))
            st.markdown('<p class="{}">**Status:** {}</p>'.format(status_class, status_text), unsafe_allow_html=True)
            st.write("**Last Run:** {}".format(last_run))
            
            if st.button("Cancel Task", key="cancel_{}".format(task_id)):
                try:
                    response = requests.delete("{}/scheduled_tasks/{}".format(BACKEND_URL, task_id))
                    if response.status_code == 200:
                        st.success("Task cancelled successfully")
                        st.rerun()
                    else:
                        st.error("Failed to cancel task")
                except Exception as e:
                    st.error("Error: {}".format(e))
else:
    st.info("No scheduled tasks. Schedule a task by selecting a schedule option above.")

# Footer
st.markdown("---")
st.markdown('<div class="footer">Web Agent v2.0 | AI-Powered Website Analysis with Conversation Memory</div>', unsafe_allow_html=True)

