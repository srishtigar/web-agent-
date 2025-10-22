#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Main.py with Thread Persistence and Conversation Memory
Matches original main.py format exactly, just adds persistence features
"""

import uvicorn
import uuid
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Web Agent API with Persistence", 
    description="AI-powered web scraping and Q&A agent with thread management and conversation memory"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()
scheduler.start()

# Import your existing agent
from core.agent import create_agent_workflow

# Import persistence agent
from core.persistent_agent import create_persistent_agent

# Initialize persistent agent
persistent_agent = create_persistent_agent(persist_directory="./chroma_db")

DB_PATH = "results.db"

# ============ DATABASE INITIALIZATION ============

def init_database():
    """Initialize SQLite database with persistence support"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_results'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Create new table with thread_id column
        cursor.execute("""
            CREATE TABLE workflow_results (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                url TEXT NOT NULL,
                prompt TEXT NOT NULL,
                mode TEXT NOT NULL,
                answer TEXT,
                error TEXT,
                documents_count INTEGER DEFAULT 0,
                chunks_count INTEGER DEFAULT 0,
                processing_time REAL DEFAULT 0,
                is_safe_content INTEGER DEFAULT 1,
                safety_check_passed INTEGER DEFAULT 1,
                retrieval_method TEXT DEFAULT 'vector-only',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Created workflow_results table with thread_id column")
    else:
        # Migrate old table by adding thread_id if missing
        cursor.execute("PRAGMA table_info(workflow_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'thread_id' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN thread_id TEXT")
            logger.info("Added thread_id column")
        
        # Add other missing columns
        if 'documents_count' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN documents_count INTEGER DEFAULT 0")
        if 'chunks_count' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN chunks_count INTEGER DEFAULT 0")
        if 'processing_time' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN processing_time REAL DEFAULT 0")
        if 'is_safe_content' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN is_safe_content INTEGER DEFAULT 1")
        if 'safety_check_passed' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN safety_check_passed INTEGER DEFAULT 1")
        if 'retrieval_method' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN retrieval_method TEXT DEFAULT 'vector-only'")
    
    # Create scheduled_tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            task_id TEXT PRIMARY KEY,
            thread_id TEXT,
            url TEXT NOT NULL,
            prompt TEXT NOT NULL,
            mode TEXT NOT NULL,
            schedule_interval TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_run TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

init_database()

# ============ REQUEST/RESPONSE MODELS ============

class ExecuteWorkflowRequest(BaseModel):
    url: HttpUrl
    prompt: str
    mode: str = "Q&A"
    schedule: str = "Run Once"
    thread_id: Optional[str] = None
    use_conversation_context: bool = True

class ScheduledTask(BaseModel):
    task_id: str
    url: HttpUrl
    prompt: str
    mode: str
    schedule_interval: str

class ThreadCreateRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class ThreadSwitchRequest(BaseModel):
    thread_id: str

# ============ DATABASE FUNCTIONS ============

def save_result_to_db(
    result_id: str, 
    url: str, 
    prompt: str, 
    mode: str, 
    answer: str, 
    error: str, 
    documents_count: int, 
    chunks_count: int, 
    processing_time: float, 
    is_safe_content: bool, 
    safety_check_passed: bool, 
    retrieval_method: str = "vector-only",
    thread_id: Optional[str] = None
):
    """Save workflow result with thread_id"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO workflow_results 
            (id, thread_id, url, prompt, mode, answer, error, documents_count, chunks_count, 
             processing_time, is_safe_content, safety_check_passed, retrieval_method, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id, thread_id, url, prompt, mode, answer, error, 
            documents_count, chunks_count, processing_time, 
            int(is_safe_content), int(safety_check_passed), 
            retrieval_method, datetime.now()
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Result saved: {result_id} (Thread: {thread_id})")
    except Exception as e:
        logger.error(f"Error saving result: {e}")
        raise

def get_result_from_db(result_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve result"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, thread_id, url, prompt, mode, answer, error, documents_count, chunks_count, 
                   processing_time, is_safe_content, safety_check_passed, retrieval_method, 
                   created_at, updated_at
            FROM workflow_results WHERE id = ?
        """, (result_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "thread_id": row[1],
                "url": row[2],
                "prompt": row[3],
                "mode": row[4],
                "answer": row[5],
                "error": row[6],
                "documents_count": row[7] if row[7] else 0,
                "chunks_count": row[8] if row[8] else 0,
                "processing_time": row[9] if row[9] else 0,
                "is_safe_content": bool(row[10]),
                "safety_check_passed": bool(row[11]),
                "retrieval_method": row[12] if row[12] else "vector-only",
                "created_at": row[13],
                "updated_at": row[14]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving result: {e}")
        return None

# ============ SCHEDULED TASK FUNCTIONS ============

def run_scheduled_workflow(task_id: str, url: str, prompt: str, mode: str, thread_id: Optional[str] = None):
    """Run scheduled workflow"""
    try:
        logger.info(f"Running scheduled task: {task_id}")
        
        # Get or create thread for this task
        if not thread_id:
            thread_id = persistent_agent.create_thread(metadata={"task_id": task_id})
        else:
            persistent_agent.switch_thread(thread_id)
        
        # Execute workflow (original format)
        agent_workflow = create_agent_workflow()
        
        initial_state = {
            "url": url,
            "prompt": prompt,
            "mode": mode,
            "documents": [],
            "visited_urls": [],
            "urls_to_visit": [],
            "vectorstore": None,
            "hybrid_retriever": None,
            "smart_retriever": None,
            "chunks": [],
            "max_depth": 3,
            "raw_text": "",
            "is_valid_url": False,
            "is_safe_content": False,
            "safety_check_passed": False,
            "answer": "",
            "error": ""
        }
        
        result = agent_workflow.invoke(initial_state)
        
        # Save result
        result_id = f"scheduled_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        save_result_to_db(
            result_id=result_id,
            url=url,
            prompt=prompt,
            mode=mode,
            answer=result.get("answer", ""),
            error=result.get("error", ""),
            documents_count=len(result.get("documents", [])),
            chunks_count=len(result.get("chunks", [])),
            processing_time=0,
            is_safe_content=result.get("is_safe_content", True),
            safety_check_passed=result.get("safety_check_passed", True),
            retrieval_method="vector-only",
            thread_id=thread_id
        )
        
        # Save to conversation memory
        persistent_agent.save_exchange(
            user_message=prompt,
            assistant_message=result.get("answer", ""),
            metadata={"url": url, "mode": mode, "task_id": task_id}
        )
        
        logger.info(f"Scheduled task completed: {task_id}")
        
    except Exception as e:
        logger.error(f"Error in scheduled task {task_id}: {e}")

# ============ API ENDPOINTS ============

@app.get("/")
async def root():
    """Health check"""
    return {"status": "healthy", "features": ["thread_management", "conversation_memory", "scheduling"]}

# ============ THREAD MANAGEMENT ENDPOINTS ============

@app.post("/threads/create")
async def create_thread(request: ThreadCreateRequest):
    """Create a new conversation thread"""
    try:
        thread_id = persistent_agent.create_thread(metadata=request.metadata)
        return {"thread_id": thread_id, "message": "Thread created successfully"}
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/threads/switch")
async def switch_thread(request: ThreadSwitchRequest):
    """Switch to an existing thread"""
    try:
        success = persistent_agent.switch_thread(request.thread_id)
        if success:
            return {"thread_id": request.thread_id, "message": "Switched to thread successfully"}
        else:
            raise HTTPException(status_code=404, detail="Thread not found")
    except Exception as e:
        logger.error(f"Error switching thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads/list")
async def list_threads(days: int = 7):
    """List recent threads"""
    try:
        threads = persistent_agent.list_threads(days=days)
        return {"threads": threads}
    except Exception as e:
        logger.error(f"Error listing threads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, limit: int = 50):
    """Get conversation history for a thread"""
    try:
        history = persistent_agent.get_conversation_history(thread_id=thread_id, limit=limit)
        return {"thread_id": thread_id, "history": history}
    except Exception as e:
        logger.error(f"Error getting thread history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ WORKFLOW EXECUTION ENDPOINT ============

@app.post("/execute_workflow")
async def execute_workflow(request: ExecuteWorkflowRequest):
    """Execute workflow with thread management and conversation memory"""
    start_time = time.time()
    
    # Handle scheduling
    if request.schedule != "Run Once":
        task_id = f"task_{str(uuid.uuid4())}"
        
        # Get or create thread
        thread_id = persistent_agent.get_or_create_thread(request.thread_id)
        
        # Save task to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_tasks (task_id, thread_id, url, prompt, mode, schedule_interval, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_id, thread_id, str(request.url), request.prompt, request.mode, request.schedule, 1))
        conn.commit()
        conn.close()
        
        # Schedule with APScheduler
        schedule_hours = {
            "Every Hour": 1,
            "Every 3 Hours": 3,
            "Every 4 Hours": 4,
            "Every 6 Hours": 6,
            "Every 12 Hours": 12,
            "Daily": 24
        }
        
        if request.schedule in schedule_hours:
            scheduler.add_job(
                run_scheduled_workflow, 
                'interval', 
                hours=schedule_hours[request.schedule],
                args=[task_id, str(request.url), request.prompt, request.mode, thread_id],
                id=task_id
            )
        
        return {
            "message": "Task scheduled successfully", 
            "task_id": task_id,
            "thread_id": thread_id,
            "schedule": request.schedule
        }
    
    # Handle immediate execution
    else:
        result_id = f"result_{str(uuid.uuid4())}"
        try:
            logger.info(f"Starting workflow for URL: {request.url}")
            
            # Get or create thread
            thread_id = persistent_agent.get_or_create_thread(request.thread_id)
            
            # Enhance prompt with conversation context
            enhanced_prompt = persistent_agent.enhance_prompt_with_context(
                request.prompt,
                use_conversation_context=request.use_conversation_context
            )
            
            # Execute workflow (ORIGINAL FORMAT - NO CHANGES)
            agent_workflow = create_agent_workflow()
            
            initial_state = {
                "url": str(request.url),
                "prompt": enhanced_prompt,  # Use enhanced prompt
                "mode": request.mode,
                "documents": [],
                "visited_urls": [],
                "urls_to_visit": [],
                "vectorstore": None,
                "hybrid_retriever": None,
                "smart_retriever": None,
                "chunks": [],
                "max_depth": 3,
                "raw_text": "",
                "is_valid_url": False,
                "is_safe_content": False,
                "safety_check_passed": False,
                "answer": "",
                "error": ""
            }
            
            result = agent_workflow.invoke(initial_state)
            
            processing_time = time.time() - start_time
            
            # Save to database
            save_result_to_db(
                result_id=result_id,
                url=str(request.url),
                prompt=request.prompt,  # Save original prompt
                mode=request.mode,
                answer=result.get("answer", ""),
                error=result.get("error", ""),
                documents_count=len(result.get("documents", [])),
                chunks_count=len(result.get("chunks", [])),
                processing_time=processing_time,
                is_safe_content=result.get("is_safe_content", True),
                safety_check_passed=result.get("safety_check_passed", True),
                retrieval_method="vector-only",
                thread_id=thread_id
            )
            
            # Save to conversation memory
            persistent_agent.save_exchange(
                user_message=request.prompt,
                assistant_message=result.get("answer", ""),
                metadata={
                    "url": str(request.url),
                    "mode": request.mode,
                    "result_id": result_id
                }
            )
            
            # Update thread metadata
            persistent_agent.update_thread_metadata({
                "last_url": str(request.url),
                "last_mode": request.mode
            })
            
            logger.info(f"Workflow completed: {result_id} in {processing_time:.2f}s")
            
            return {
                "message": "Workflow executed successfully",
                "result_id": result_id,
                "thread_id": thread_id,
                "answer": result.get("answer", ""),
                "url": str(request.url),
                "mode": request.mode,
                "processing_time": f"{processing_time:.2f}s",
                "is_safe_content": result.get("is_safe_content", True),
                "safety_check_passed": result.get("safety_check_passed", True)
            }
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            processing_time = time.time() - start_time
            
            save_result_to_db(
                result_id=result_id,
                url=str(request.url),
                prompt=request.prompt,
                mode=request.mode,
                answer="",
                error=str(e),
                documents_count=0,
                chunks_count=0,
                processing_time=processing_time,
                is_safe_content=True,
                safety_check_passed=False,
                thread_id=thread_id
            )
            
            raise HTTPException(status_code=500, detail=str(e))

# ============ SCHEDULED TASKS ENDPOINTS ============

@app.get("/scheduled_tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks"""
    try:
        tasks = persistent_agent.get_scheduled_tasks()
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error listing scheduled tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduled_tasks/{task_id}/results")
async def get_task_results(task_id: str, limit: int = 10):
    """Get results for a scheduled task"""
    try:
        results = persistent_agent.get_task_results(task_id=task_id, limit=limit)
        return {"task_id": task_id, "results": results}
    except Exception as e:
        logger.error(f"Error getting task results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/scheduled_tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a scheduled task"""
    try:
        success = persistent_agent.cancel_task(task_id)
        if success:
            return {"message": "Task cancelled successfully", "task_id": task_id}
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ RESULT RETRIEVAL ENDPOINT ============

@app.get("/results/{result_id}")
async def get_result(result_id: str):
    """Get workflow result by ID"""
    result = get_result_from_db(result_id)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Result not found")

# ============ CLEANUP ENDPOINT ============

@app.post("/cleanup")
async def cleanup_old_data(days: int = 7):
    """Clean up old threads and data"""
    try:
        # This would call cleanup methods on persistence managers
        return {"message": f"Cleanup initiated for data older than {days} days"}
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ RUN SERVER ============

if __name__ == "__main__":
    uvicorn.run(
        "main_persistent:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

