#!/usr/bin/env python3
"""
Diagnostic script to identify issues with the Web Agent
Run this to see what's wrong: python debug.py
"""

import sys
import os

print("=" * 70)
print("🔍 WEB AGENT DIAGNOSTIC TOOL")
print("=" * 70 + "\n")

# 1. Check Python version
print("✓ CHECKING PYTHON VERSION")
print(f"  Python: {sys.version}")
if sys.version_info < (3, 8):
    print("  ❌ Python 3.8+ required!")
    sys.exit(1)
print("  ✅ OK\n")

# 2. Check .env file
print("✓ CHECKING .env FILE")
if os.path.exists(".env"):
    print("  ✅ .env file found")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            print(f"  ✅ GEMINI_API_KEY found: {gemini_key[:8]}...{gemini_key[-4:]}")
        else:
            print("  ❌ GEMINI_API_KEY not set in .env")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Error reading .env: {e}")
        sys.exit(1)
else:
    print("  ❌ .env file not found!")
    print("  Create .env with: GEMINI_API_KEY=your_key")
    sys.exit(1)
print()

# 3. Check imports
print("✓ CHECKING IMPORTS")
modules_to_check = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("langchain_core", "LangChain Core"),
    ("langchain_google_genai", "Google GenAI"),
    ("langchain_huggingface", "HuggingFace"),
    ("langchain_community", "LangChain Community"),
    ("bs4", "BeautifulSoup"),
    ("apscheduler", "APScheduler"),
    ("langgraph", "LangGraph"),
]

missing_modules = []
for module, name in modules_to_check:
    try:
        __import__(module)
        print(f"  ✅ {name}")
    except ImportError as e:
        print(f"  ❌ {name} - MISSING")
        missing_modules.append(module)

if missing_modules:
    print(f"\n  Install missing: pip install {' '.join(missing_modules)}")
    sys.exit(1)
print()

# 4. Test core/agent.py import
print("✓ CHECKING CORE AGENT")
try:
    sys.path.insert(0, os.getcwd())
    from core.agent import create_agent_workflow
    print("  ✅ core/agent.py imports successfully")
except Exception as e:
    print(f"  ❌ Error importing core/agent.py:")
    print(f"     {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# 5. Test LLM initialization
print("✓ CHECKING LLM INITIALIZATION")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    gemini_key = os.getenv("GEMINI_API_KEY")
    os.environ["GOOGLE_API_KEY"] = gemini_key
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=gemini_key,
        temperature=0.1
    )
    print("  ✅ LLM initialized successfully")
except Exception as e:
    print(f"  ❌ Error initializing LLM:")
    print(f"     {type(e).__name__}: {str(e)}")
    print("\n  SOLUTION:")
    print("  1. Check your GEMINI_API_KEY is valid")
    print("  2. Make sure API is enabled on Google Cloud")
    print("  3. Try generating a new API key")
print()

# 6. Test embeddings initialization
print("✓ CHECKING EMBEDDINGS")
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    print("  ✅ Embeddings initialized successfully")
    print("  ⏳ (This might take 30-60 seconds first time)")
except Exception as e:
    print(f"  ❌ Error initializing embeddings:")
    print(f"     {type(e).__name__}: {str(e)}")
    print("\n  SOLUTION:")
    print("  1. Check internet connection")
    print("  2. Try: pip install --upgrade sentence-transformers")
print()

# 7. Test workflow creation
print("✓ CHECKING WORKFLOW CREATION")
try:
    workflow = create_agent_workflow()
    print("  ✅ Workflow created successfully")
except Exception as e:
    print(f"  ❌ Error creating workflow:")
    print(f"     {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# 8. Test database
print("✓ CHECKING DATABASE")
try:
    import sqlite3
    conn = sqlite3.connect("results.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    conn.close()
    print("  ✅ Database OK")
except Exception as e:
    print(f"  ❌ Database error: {e}")
    print("  Delete results.db and restart")
print()

# 9. Quick workflow test
print("✓ TESTING SIMPLE WORKFLOW")
try:
    print("  Testing with a simple URL...")
    initial_state = {
        "url": "https://example.com",
        "prompt": "What is this website about?",
        "mode": "Q&A",
        "documents": [],
        "visited_urls": [],
        "urls_to_visit": [],
        "answer": "",
        "error": "",
        "vectorstore": None,
        "max_depth": 3,
        "raw_text": ""
    }
    
    config = {"recursion_limit": 50}
    result = workflow.invoke(initial_state, config=config)
    
    if result.get("error"):
        print(f"  ⚠️  Error in workflow: {result.get('error')}")
    else:
        answer_preview = result.get("answer", "")[:100]
        print(f"  ✅ Workflow executed successfully!")
        print(f"  Answer preview: {answer_preview}...")
        
except Exception as e:
    print(f"  ❌ Workflow execution error:")
    print(f"     {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
print()

print("=" * 70)
print("✅ ALL CHECKS COMPLETED!")
print("=" * 70)
print("\nIf all checks passed, your setup is correct.")
print("Start the server with: python main.py")
print("\nIf you see errors above, follow the suggested solutions.")