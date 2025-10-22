import streamlit as st
import requests
import json
import time
from datetime import datetime

# Backend API URL
BACKEND_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    layout="wide", 
    page_title="Web Agent: AI-Powered Q&A", 
    page_icon="🤖"
)

# Title and description
st.title("🤖 Web Agent: AI-Powered Website Q&A and Reporting")
st.markdown("---")

# Create two columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Create New Request")
    
    # User Inputs
    url = st.text_input(
        "Enter Website URL:", 
        placeholder="https://www.example.com",
        help="Enter the full URL including https://"
    )
    
    prompt = st.text_area(
        "Enter Your Question/Prompt:", 
        placeholder="What is this website about?",
        height=100,
        help="Ask any question about the website content"
    )
    
    # Mode selection
    mode = st.radio(
        "Select Mode:", 
        ["Q&A", "Report"], 
        index=0, 
        horizontal=True,
        help="Q&A: Get specific answers | Report: Generate comprehensive report"
    )
    
    # Schedule options
    schedule_options = [
        "Run Once", 
        "Every Hour",
        "Every 3 Hours", 
        "Every 4 Hours"
    ]
    schedule = st.selectbox(
        "Select Schedule:", 
        schedule_options,
        help="Choose how often to run this task"
    )
    
    # Generate button
    generate_button = st.button("🚀 Generate", type="primary", use_container_width=True)
    
    if generate_button:
        if not url or not prompt:
            st.error("⚠️ Please enter both a URL and a prompt.")
        else:
            with st.spinner("🔄 Processing your request..."):
                try:
                    payload = {
                        "url": url,
                        "prompt": prompt,
                        "mode": mode,
                        "schedule": schedule
                    }
                    
                    response = requests.post(
                        "{}{}".format(BACKEND_URL, "/execute_workflow"), 
                        json=payload,
                        timeout=120  # 2 minute timeout for long-running requests
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ {}".format(result.get("message", "Request sent successfully!")))
                        
                        if schedule == "Run Once":
                            st.subheader("📊 Result:")
                            answer = result.get("answer", "No answer generated")
                            st.markdown("### Answer:")
                            st.write(answer)
                            
                            # Show result details in expander
                            with st.expander("📋 View Full Details"):
                                st.json(result)
                        else:
                            st.info("⏰ Task scheduled! Check 'Scheduled Tasks' section below to monitor.")
                            task_id = result.get("task_id", "N/A")
                            st.write("**Task ID:** `{}`".format(task_id))
                    else:
                        st.error("❌ Error: {} - {}".format(response.status_code, response.text))
                
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. The website might be taking too long to process.")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Cannot connect to backend server. Make sure the FastAPI server is running on {}".format(BACKEND_URL))
                except requests.exceptions.RequestException as e:
                    st.error("❌ Error connecting to backend: {}".format(str(e)))
                except json.JSONDecodeError:
                    st.error("⚠️ Error decoding response. Backend might have returned invalid JSON.")
                except Exception as e:
                    st.error("❌ An unexpected error occurred: {}".format(str(e)))

with col2:
    st.header("ℹ️ Quick Guide")
    st.markdown("""
    **How to use:**
    1. Enter a website URL
    2. Ask a question about it
    3. Choose Q&A or Report mode
    4. Select run frequency
    5. Click Generate
    
    **Examples:**
    - "What products are sold?"
    - "What is the price of X?"
    - "Summarize the main content"
    - "What are the latest news?"
    """)

st.markdown("---")

# Scheduled Tasks Section
st.header("⏰ Scheduled Tasks")

col_refresh, col_space = st.columns([1, 3])
with col_refresh:
    refresh_tasks = st.button("🔄 Refresh Tasks", use_container_width=True)

if refresh_tasks or 'tasks_loaded' not in st.session_state:
    st.session_state.tasks_loaded = True
    try:
        response = requests.get("{}/scheduled_tasks".format(BACKEND_URL), timeout=10)
        if response.status_code == 200:
            scheduled_tasks = response.json()
            if scheduled_tasks:
                st.success("✅ Found {} scheduled task(s)".format(len(scheduled_tasks)))
                for idx, task in enumerate(scheduled_tasks, 1):
                    with st.expander("📌 Task {}: {}".format(idx, task.get('url', 'N/A'))):
                        col_task1, col_task2 = st.columns(2)
                        with col_task1:
                            st.write("**URL:** {}".format(task.get('url', 'N/A')))
                            st.write("**Prompt:** {}".format(task.get('prompt', 'N/A')))
                            st.write("**Mode:** {}".format(task.get('mode', 'N/A')))
                        with col_task2:
                            st.write("**Schedule:** {}".format(task.get('schedule_interval', 'N/A')))
                            st.write("**Active:** {}".format('Yes' if task.get('is_active') else 'No'))
                            st.write("**Last Run:** {}".format(task.get('last_run', 'Never')))
                        
                        # Delete button
                        task_id = task.get('task_id')
                        if st.button("🗑️ Delete Task", key="delete_{}".format(task_id)):
                            try:
                                del_response = requests.delete("{}/scheduled_tasks/{}".format(BACKEND_URL, task_id))
                                if del_response.status_code == 200:
                                    st.success("✅ Task deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete task")
                            except Exception as e:
                                st.error("❌ Error: {}".format(str(e)))
            else:
                st.info("📭 No scheduled tasks found.")
        else:
            st.error("❌ Error fetching tasks: {}".format(response.status_code))
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI server is running.")
    except Exception as e:
        st.error("❌ Error fetching scheduled tasks: {}".format(str(e)))

st.markdown("---")

# Recent Results Section
st.header("📊 Recent Results")

col_refresh_results, col_space2 = st.columns([1, 3])
with col_refresh_results:
    refresh_results = st.button("🔄 Refresh Results", use_container_width=True)

if refresh_results or 'results_loaded' not in st.session_state:
    st.session_state.results_loaded = True
    try:
        response = requests.get("{}/results".format(BACKEND_URL), timeout=10)
        if response.status_code == 200:
            results = response.json()
            if results:
                st.success("✅ Found {} result(s)".format(len(results)))
                for idx, result in enumerate(results[:10], 1):  # Show last 10 results
                    with st.expander("📄 Result {}: {}".format(idx, result.get('url', 'N/A')[:50])):
                        col_res1, col_res2 = st.columns([2, 1])
                        with col_res1:
                            st.write("**URL:** {}".format(result.get('url', 'N/A')))
                            st.write("**Prompt:** {}".format(result.get('prompt', 'N/A')))
                            st.write("**Mode:** {}".format(result.get('mode', 'N/A')))
                        with col_res2:
                            st.write("**Created:** {}".format(result.get('created_at', 'N/A')))
                            st.write("**Updated:** {}".format(result.get('updated_at', 'N/A')))
                        
                        if result.get('error'):
                            st.error("**Error:** {}".format(result.get('error')))
                        else:
                            st.markdown("**Answer:**")
                            st.write(result.get('answer', 'No answer available'))
            else:
                st.info("📭 No results found yet. Run a workflow to see results here.")
        else:
            st.error("❌ Error fetching results: {}".format(response.status_code))
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI server is running.")
    except Exception as e:
        st.error("❌ Error fetching results: {}".format(str(e)))

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>🤖 Web Agent - AI-Powered Website Analysis</p>
    <p>Backend API: {}</p>
</div>
""".format(BACKEND_URL), unsafe_allow_html=True)