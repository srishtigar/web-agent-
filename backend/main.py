import os
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

# Setup logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Web Agent API", 
    description="AI-powered web scraping and Q&A agent with enhanced semantic understanding, smart retrieval, and safety checks"
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

from core.agent import create_agent_workflow

DB_PATH = "results.db"

def init_database():
    """Initialize SQLite database with proper schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists and migrate if needed
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_results'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Create new table with all columns
        cursor.execute("""
            CREATE TABLE workflow_results (
                id TEXT PRIMARY KEY,
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
        logger.info("Created workflow_results table with all columns")
    else:
        # Migrate old table by adding missing columns if they don't exist
        cursor.execute("PRAGMA table_info(workflow_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'documents_count' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN documents_count INTEGER DEFAULT 0")
            logger.info("Added documents_count column")
        
        if 'chunks_count' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN chunks_count INTEGER DEFAULT 0")
            logger.info("Added chunks_count column")
        
        if 'processing_time' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN processing_time REAL DEFAULT 0")
            logger.info("Added processing_time column")
        
        # Safety check columns
        if 'is_safe_content' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN is_safe_content INTEGER DEFAULT 1")
            logger.info("Added is_safe_content column")
        
        if 'safety_check_passed' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN safety_check_passed INTEGER DEFAULT 1")
            logger.info("Added safety_check_passed column")
        
        # NEW: Retrieval method tracking
        if 'retrieval_method' not in columns:
            cursor.execute("ALTER TABLE workflow_results ADD COLUMN retrieval_method TEXT DEFAULT 'vector-only'")
            logger.info("Added retrieval_method column")
    
    # Create scheduled_tasks table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            task_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            prompt TEXT NOT NULL,
            mode TEXT NOT NULL,
            schedule_interval TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_run TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

init_database()

class ExecuteWorkflowRequest(BaseModel):
    url: HttpUrl
    prompt: str
    mode: str = "Q&A"  # "Q&A" or "Report"
    schedule: str = "Run Once"

class ScheduledTask(BaseModel):
    task_id: str
    url: HttpUrl
    prompt: str
    mode: str
    schedule_interval: str
    is_active: bool = True
    last_run: Optional[str] = None

def save_result_to_db(
    result_id: str, 
    url: str, 
    prompt: str, 
    mode: str, 
    answer: str, 
    error: str = "",
    documents_count: int = 0,
    chunks_count: int = 0,
    processing_time: float = 0,
    is_safe_content: bool = True,
    safety_check_passed: bool = True,
    retrieval_method: str = "vector-only"
):
    """Save workflow result with enhanced metadata including retrieval method and safety check results"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO workflow_results 
            (id, url, prompt, mode, answer, error, documents_count, chunks_count, processing_time, is_safe_content, safety_check_passed, retrieval_method, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id, url, prompt, mode, answer, error, 
            documents_count, chunks_count, processing_time, 
            int(is_safe_content), int(safety_check_passed), 
            retrieval_method, datetime.now()
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Result saved: {result_id} (Method: {retrieval_method}, Safe: {is_safe_content}, Passed: {safety_check_passed})")
    except Exception as e:
        logger.error(f"Error saving result: {e}")
        raise

def get_result_from_db(result_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve result with full details"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, url, prompt, mode, answer, error, documents_count, chunks_count, 
                   processing_time, is_safe_content, safety_check_passed, retrieval_method, 
                   created_at, updated_at
            FROM workflow_results WHERE id = ?
        """, (result_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "url": row[1],
                "prompt": row[2],
                "mode": row[3],
                "answer": row[4],
                "error": row[5],
                "documents_count": row[6] if row[6] else 0,
                "chunks_count": row[7] if row[7] else 0,
                "processing_time": row[8] if row[8] else 0,
                "is_safe_content": bool(row[9]),
                "safety_check_passed": bool(row[10]),
                "retrieval_method": row[11] if row[11] else "vector-only",
                "created_at": row[12],
                "updated_at": row[13]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving result: {e}")
        return None

def save_scheduled_task(task: ScheduledTask):
    """Save scheduled task"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scheduled_tasks (task_id, url, prompt, mode, schedule_interval, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task.task_id, str(task.url), task.prompt, task.mode, task.schedule_interval, 1))
        
        conn.commit()
        conn.close()
        logger.info(f"Task saved: {task.task_id}")
    except Exception as e:
        logger.error(f"Error saving task: {e}")
        raise

def update_task_last_run(task_id: str):
    """Update last run time"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE scheduled_tasks SET last_run = ? WHERE task_id = ?
        """, (datetime.now(), task_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating task: {e}")

def get_all_scheduled_tasks() -> List[Dict[str, Any]]:
    """Get all active scheduled tasks"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, url, prompt, mode, schedule_interval, is_active, created_at, last_run
            FROM scheduled_tasks WHERE is_active = 1
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row[0],
                "url": row[1],
                "prompt": row[2],
                "mode": row[3],
                "schedule_interval": row[4],
                "is_active": bool(row[5]),
                "created_at": row[6],
                "last_run": row[7]
            })
        
        return tasks
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        return []

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Web Agent API is running",
        "status": "healthy",
        "version": "4.0",
        "features": [
            "Enhanced RAG with Hybrid Retrieval",
            "Smart Multi-Query Retrieval (Auto-Detects Ambiguous Queries)",
            "Semantic Search",
            "Content Safety Checks",
            "Report Generation (2-LLM)",
            "Parallel URL Validation",
            "No Hallucinations",
            "Domain-Specific Extraction"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy"}

@app.post("/execute_workflow")
async def execute_workflow(request: ExecuteWorkflowRequest):
    """Execute workflow with enhanced quality, smart retrieval, and safety checks"""
    start_time = time.time()
    
    if request.schedule != "Run Once":
        task_id = f"task_{str(uuid.uuid4())}"
        new_task = ScheduledTask(
            task_id=task_id,
            url=request.url,
            prompt=request.prompt,
            mode=request.mode,
            schedule_interval=request.schedule
        )
        
        save_scheduled_task(new_task)
        
        schedule_hours = {
            "Every Hour": 1,
            "Every 3 Hours": 3,
            "Every 4 Hours": 4
        }
        
        if request.schedule in schedule_hours:
            scheduler.add_job(
                run_scheduled_workflow, 
                'interval', 
                hours=schedule_hours[request.schedule],
                args=[task_id, str(request.url), request.prompt, request.mode],
                id=task_id
            )
        
        return {
            "message": "Task scheduled successfully", 
            "task_id": task_id,
            "schedule": request.schedule
        }
    else:
        result_id = f"result_{str(uuid.uuid4())}"
        try:
            logger.info(f"Starting workflow for URL: {request.url}")
            logger.info(f"Mode: {request.mode}")
            
            agent_workflow = create_agent_workflow()
            
            # UPDATED: Added smart_retriever
            initial_state = {
                "url": str(request.url), 
                "prompt": request.prompt, 
                "mode": request.mode, 
                "documents": [], 
                "visited_urls": [], 
                "urls_to_visit": [], 
                "answer": "", 
                "error": "", 
                "vectorstore": None,
                "hybrid_retriever": None,
                "smart_retriever": None,  # NEW: Smart retriever with auto multi-query
                "chunks": [],
                "max_depth": 3,
                "raw_text": "",
                "is_valid_url": False,
                "is_safe_content": False,
                "safety_check_passed": False
            }
            
            config = {"recursion_limit": 50}
            result = agent_workflow.invoke(initial_state, config=config)
            
            processing_time = time.time() - start_time
            
            # Extract metadata
            docs_count = len(result.get("documents", []))
            is_safe = result.get("is_safe_content", False)
            safety_passed = result.get("safety_check_passed", False)
            
            # Determine retrieval method
            retrieval_method = "smart" if result.get("smart_retriever") else (
                "hybrid" if result.get("hybrid_retriever") else "vector-only"
            )
            
            save_result_to_db(
                result_id=result_id,
                url=str(request.url),
                prompt=request.prompt,
                mode=request.mode,
                answer=result.get("answer", ""),
                error=result.get("error", ""),
                documents_count=docs_count,
                chunks_count=0,
                processing_time=processing_time,
                is_safe_content=is_safe,
                safety_check_passed=safety_passed,
                retrieval_method=retrieval_method
            )
            
            logger.info(f"Workflow completed: {result_id} in {processing_time:.2f}s using {retrieval_method} retrieval")
            
            return {
                "message": "Workflow executed successfully", 
                "result_id": result_id,
                "answer": result.get("answer", ""),
                "url": str(request.url),
                "mode": request.mode,
                "processing_time": f"{processing_time:.2f}s",
                "documents_processed": docs_count,
                "retrieval_method": retrieval_method,
                "is_safe_content": is_safe,
                "safety_check_passed": safety_passed
            }
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error executing workflow: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            save_result_to_db(
                result_id=result_id,
                url=str(request.url),
                prompt=request.prompt,
                mode=request.mode,
                answer="",
                error=error_msg,
                processing_time=processing_time,
                is_safe_content=False,
                safety_check_passed=False,
                retrieval_method="none"
            )
            
            raise HTTPException(status_code=500, detail=error_msg)

@app.get("/results/{result_id}")
async def get_results(result_id: str):
    """Get result by ID"""
    result = get_result_from_db(result_id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Results not found")

@app.get("/results")
async def get_all_results():
    """Get all results (last 50) with safety and retrieval method information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, url, prompt, mode, answer, error, documents_count, chunks_count, 
                   processing_time, is_safe_content, safety_check_passed, retrieval_method,
                   created_at, updated_at
            FROM workflow_results ORDER BY updated_at DESC LIMIT 50
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            answer_preview = row[4][:200] + "..." if len(row[4]) > 200 else row[4]
            results.append({
                "id": row[0],
                "url": row[1],
                "prompt": row[2],
                "mode": row[3],
                "answer": answer_preview,
                "error": row[5],
                "documents_count": row[6] if row[6] else 0,
                "chunks_count": row[7] if row[7] else 0,
                "processing_time": row[8] if row[8] else 0,
                "is_safe_content": bool(row[9]),
                "safety_check_passed": bool(row[10]),
                "retrieval_method": row[11] if row[11] else "vector-only",
                "created_at": row[12],
                "updated_at": row[13]
            })
        
        return results
    except Exception as e:
        logger.error(f"Error retrieving results: {e}")
        return []

@app.get("/scheduled_tasks")
async def get_scheduled_tasks():
    """Get all scheduled tasks"""
    tasks = get_all_scheduled_tasks()
    return tasks

@app.delete("/scheduled_tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    """Delete task"""
    try:
        scheduler.remove_job(task_id)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scheduled_tasks SET is_active = 0 WHERE task_id = ?
        """, (task_id,))
        conn.commit()
        conn.close()
        
        return {"message": "Task deleted successfully", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")

def run_scheduled_workflow(task_id: str, url: str, prompt: str, mode: str):
    """Execute scheduled workflow"""
    start_time = time.time()
    
    logger.info(f"Running scheduled task {task_id}")
    result_id = f"scheduled_{task_id}_{str(uuid.uuid4())}"
    
    try:
        agent_workflow = create_agent_workflow()
        
        # UPDATED: Added smart_retriever
        initial_state = {
            "url": url, 
            "prompt": prompt, 
            "mode": mode, 
            "documents": [], 
            "visited_urls": [], 
            "urls_to_visit": [], 
            "answer": "", 
            "error": "", 
            "vectorstore": None,
            "hybrid_retriever": None,
            "smart_retriever": None,  # NEW: Smart retriever
            "chunks": [],
            "max_depth": 3,
            "raw_text": "",
            "is_valid_url": False,
            "is_safe_content": False,
            "safety_check_passed": False
        }
        
        config = {"recursion_limit": 50}
        result = agent_workflow.invoke(initial_state, config=config)
        
        processing_time = time.time() - start_time
        docs_count = len(result.get("documents", []))
        is_safe = result.get("is_safe_content", False)
        safety_passed = result.get("safety_check_passed", False)
        
        # Determine retrieval method
        retrieval_method = "smart" if result.get("smart_retriever") else (
            "hybrid" if result.get("hybrid_retriever") else "vector-only"
        )
        
        save_result_to_db(
            result_id=result_id,
            url=url,
            prompt=prompt,
            mode=mode,
            answer=result.get("answer", ""),
            error=result.get("error", ""),
            documents_count=docs_count,
            processing_time=processing_time,
            is_safe_content=is_safe,
            safety_check_passed=safety_passed,
            retrieval_method=retrieval_method
        )
        
        update_task_last_run(task_id)
        logger.info(f"Scheduled task {task_id} completed successfully using {retrieval_method} retrieval")
        
    except Exception as e:
        error_msg = f"Error running scheduled task {task_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        save_result_to_db(
            result_id=result_id,
            url=url,
            prompt=prompt,
            mode=mode,
            answer="",
            error=error_msg,
            processing_time=time.time() - start_time,
            is_safe_content=False,
            safety_check_passed=False,
            retrieval_method="none"
        )

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)