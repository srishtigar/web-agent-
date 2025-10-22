# -*- coding: utf-8 -*-
"""
Scheduler Automation Module
Handles scheduled task execution with timestamp tracking and report generation
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ScheduledTaskResult:
    """
    Represents the result of a scheduled task execution.
    """
    
    def __init__(
        self,
        task_id: str,
        execution_id: str,
        url: str,
        prompt: str,
        mode: str,
        answer: str,
        error: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        processing_duration: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.task_id = task_id
        self.execution_id = execution_id
        self.url = url
        self.prompt = prompt
        self.mode = mode
        self.answer = answer
        self.error = error
        self.execution_time = execution_time or datetime.now()
        self.processing_duration = processing_duration
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "task_id": self.task_id,
            "execution_id": self.execution_id,
            "url": self.url,
            "prompt": self.prompt,
            "mode": self.mode,
            "answer": self.answer,
            "error": self.error,
            "execution_time": self.execution_time.isoformat(),
            "execution_time_formatted": self.execution_time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_duration": self.processing_duration,
            "metadata": self.metadata
        }
    
    def format_report(self) -> str:
        """
        Format the result as a user-friendly report with timestamp.
        
        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 80,
            "📊 SCHEDULED TASK REPORT",
            "=" * 80,
            "",
            f"🕐 Execution Time: {self.execution_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"⏱️  Processing Duration: {self.processing_duration:.2f} seconds",
            f"🔗 URL: {self.url}",
            f"❓ Query: {self.prompt}",
            f"📋 Mode: {self.mode}",
            "",
            "=" * 80,
            "📝 RESULT:",
            "=" * 80,
            ""
        ]
        
        if self.error:
            report_lines.extend([
                "❌ ERROR OCCURRED:",
                self.error,
                ""
            ])
        else:
            report_lines.extend([
                self.answer,
                ""
            ])
        
        report_lines.extend([
            "=" * 80,
            f"Task ID: {self.task_id}",
            f"Execution ID: {self.execution_id}",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


class TaskScheduler:
    """
    Manages scheduled task execution with APScheduler.
    """
    
    def __init__(self, results_directory: str = "./scheduled_results"):
        """
        Initialize the task scheduler.
        
        Args:
            results_directory: Directory to store task results
        """
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.results_directory = Path(results_directory)
        self.results_directory.mkdir(parents=True, exist_ok=True)
        
        # Store task metadata
        self.tasks_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Store execution results
        self.execution_history: Dict[str, List[ScheduledTaskResult]] = {}
        
        logger.info("TaskScheduler initialized and started")
    
    def schedule_task(
        self,
        task_id: str,
        url: str,
        prompt: str,
        mode: str,
        schedule_interval: str,
        task_function: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Schedule a new task.
        
        Args:
            task_id: Unique task identifier
            url: URL to process
            prompt: User prompt/query
            mode: Q&A or Report
            schedule_interval: Schedule type (Run Once, Every Hour, etc.)
            task_function: Function to execute (should accept task_id, url, prompt, mode)
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            # Parse schedule interval
            trigger = self._parse_schedule_interval(schedule_interval)
            
            if trigger is None:
                logger.error(f"Invalid schedule interval: {schedule_interval}")
                return False
            
            # Wrapper function to track execution
            def wrapped_task():
                execution_id = str(uuid.uuid4())
                start_time = datetime.now()
                
                logger.info(f"Executing scheduled task {task_id} (Execution: {execution_id})")
                
                try:
                    # Execute the actual task
                    result = task_function(task_id, url, prompt, mode)
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    # Create result object
                    task_result = ScheduledTaskResult(
                        task_id=task_id,
                        execution_id=execution_id,
                        url=url,
                        prompt=prompt,
                        mode=mode,
                        answer=result.get("answer", ""),
                        error=result.get("error"),
                        execution_time=start_time,
                        processing_duration=duration,
                        metadata=metadata
                    )
                    
                    # Store result
                    self._store_result(task_result)
                    
                    # Update task metadata
                    if task_id in self.tasks_metadata:
                        self.tasks_metadata[task_id]["last_execution"] = start_time.isoformat()
                        self.tasks_metadata[task_id]["execution_count"] = \
                            self.tasks_metadata[task_id].get("execution_count", 0) + 1
                    
                    logger.info(f"Task {task_id} completed successfully in {duration:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Error executing task {task_id}: {e}")
                    
                    # Store error result
                    task_result = ScheduledTaskResult(
                        task_id=task_id,
                        execution_id=execution_id,
                        url=url,
                        prompt=prompt,
                        mode=mode,
                        answer="",
                        error=str(e),
                        execution_time=start_time,
                        processing_duration=0.0,
                        metadata=metadata
                    )
                    self._store_result(task_result)
            
            # Schedule the task
            if schedule_interval == "Run Once":
                # Execute immediately for one-time tasks
                job = self.scheduler.add_job(
                    wrapped_task,
                    trigger='date',
                    run_date=datetime.now() + timedelta(seconds=1),
                    id=task_id,
                    replace_existing=True
                )
            else:
                job = self.scheduler.add_job(
                    wrapped_task,
                    trigger=trigger,
                    id=task_id,
                    replace_existing=True
                )
            
            # Store task metadata
            self.tasks_metadata[task_id] = {
                "task_id": task_id,
                "url": url,
                "prompt": prompt,
                "mode": mode,
                "schedule_interval": schedule_interval,
                "created_at": datetime.now().isoformat(),
                "last_execution": None,
                "execution_count": 0,
                "is_active": True,
                "job_id": job.id,
                **(metadata or {})
            }
            
            logger.info(f"Scheduled task {task_id} with interval: {schedule_interval}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")
            return False
    
    def _parse_schedule_interval(self, interval: str) -> Optional[Any]:
        """
        Parse schedule interval string to APScheduler trigger.
        
        Args:
            interval: Schedule interval string
            
        Returns:
            APScheduler trigger or None
        """
        interval_lower = interval.lower()
        
        if interval_lower == "run once":
            return None  # Handled separately
        elif interval_lower == "every hour":
            return IntervalTrigger(hours=1)
        elif interval_lower == "every 3 hours":
            return IntervalTrigger(hours=3)
        elif interval_lower == "every 4 hours":
            return IntervalTrigger(hours=4)
        elif interval_lower == "every 6 hours":
            return IntervalTrigger(hours=6)
        elif interval_lower == "every 12 hours":
            return IntervalTrigger(hours=12)
        elif interval_lower == "daily":
            return CronTrigger(hour=9, minute=0)  # 9 AM daily
        else:
            logger.warning(f"Unknown schedule interval: {interval}")
            return None
    
    def _store_result(self, result: ScheduledTaskResult) -> None:
        """
        Store task execution result.
        
        Args:
            result: Task result object
        """
        try:
            # Add to history
            if result.task_id not in self.execution_history:
                self.execution_history[result.task_id] = []
            
            self.execution_history[result.task_id].append(result)
            
            # Keep only last 50 executions per task
            if len(self.execution_history[result.task_id]) > 50:
                self.execution_history[result.task_id].pop(0)
            
            # Save to file
            result_file = self.results_directory / f"{result.task_id}_{result.execution_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            # Also save formatted report
            report_file = self.results_directory / f"{result.task_id}_{result.execution_id}_report.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result.format_report())
            
            logger.info(f"Stored result for task {result.task_id}, execution {result.execution_id}")
            
        except Exception as e:
            logger.error(f"Error storing result: {e}")
    
    def get_task_results(
        self, 
        task_id: str, 
        limit: Optional[int] = None
    ) -> List[ScheduledTaskResult]:
        """
        Get execution results for a task.
        
        Args:
            task_id: Task identifier
            limit: Maximum number of results to return
            
        Returns:
            List of task results
        """
        results = self.execution_history.get(task_id, [])
        
        if limit:
            results = results[-limit:]
        
        return results
    
    def get_latest_result(self, task_id: str) -> Optional[ScheduledTaskResult]:
        """
        Get the most recent result for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Latest result or None
        """
        results = self.execution_history.get(task_id, [])
        return results[-1] if results else None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Success status
        """
        try:
            self.scheduler.remove_job(task_id)
            
            if task_id in self.tasks_metadata:
                self.tasks_metadata[task_id]["is_active"] = False
            
            logger.info(f"Cancelled task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task metadata and status.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task information or None
        """
        return self.tasks_metadata.get(task_id)
    
    def list_active_tasks(self) -> List[Dict[str, Any]]:
        """
        List all active scheduled tasks.
        
        Returns:
            List of task metadata
        """
        return [
            task_info for task_info in self.tasks_metadata.values()
            if task_info.get("is_active", False)
        ]
    
    def shutdown(self) -> None:
        """
        Shutdown the scheduler gracefully.
        """
        logger.info("Shutting down TaskScheduler")
        self.scheduler.shutdown(wait=True)


# Singleton instance
_task_scheduler = None

def get_task_scheduler(results_directory: str = "./scheduled_results") -> TaskScheduler:
    """
    Get or create the singleton task scheduler instance.
    
    Args:
        results_directory: Directory for storing results
        
    Returns:
        TaskScheduler instance
    """
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler(results_directory)
    return _task_scheduler

