#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Persistent Agent - Matches Original Format
Just adds thread management and conversation memory to existing workflow
"""

import logging
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import persistence modules
try:
    from .thread_persistence import get_persistence_manager
    from .conversation_memory import get_memory_manager
    from .scheduler_automation import get_task_scheduler
except ImportError:
    from core.thread_persistence import get_persistence_manager
    from core.conversation_memory import get_memory_manager
    from core.scheduler_automation import get_task_scheduler

logger = logging.getLogger(__name__)


class PersistentAgent:
    """
    Simple wrapper that adds persistence to existing agent workflow.
    Does NOT modify the workflow - just adds thread and memory management.
    """
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        user_id: str = "default_user"
    ):
        """Initialize with persistence managers"""
        self.persist_directory = persist_directory
        self.user_id = user_id
        
        # Initialize managers
        self.persistence_manager = get_persistence_manager(persist_directory)
        self.memory_manager = get_memory_manager(persist_directory)
        self.task_scheduler = get_task_scheduler(persist_directory)
        
        # Current thread context
        self.current_thread_id: Optional[str] = None
        self.current_memory: Optional[Any] = None
        
        logger.info(f"Initialized PersistentAgent with persist_directory={persist_directory}")
    
    def create_thread(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new conversation thread"""
        thread_id = self.persistence_manager.create_thread(
            user_id=self.user_id,
            metadata=metadata or {}
        )
        
        # Initialize memory for this thread
        self.current_thread_id = thread_id
        self.current_memory = self.memory_manager.get_memory(thread_id)
        
        logger.info(f"Created new thread: {thread_id}")
        return thread_id
    
    def switch_thread(self, thread_id: str) -> bool:
        """Switch to an existing thread"""
        thread = self.persistence_manager.get_thread(thread_id)
        if not thread:
            logger.warning(f"Thread {thread_id} not found")
            return False
        
        self.current_thread_id = thread_id
        self.current_memory = self.memory_manager.get_memory(thread_id)
        
        logger.info(f"Switched to thread: {thread_id}")
        return True
    
    def get_or_create_thread(self, thread_id: Optional[str] = None) -> str:
        """Get existing thread or create new one"""
        if thread_id:
            if self.switch_thread(thread_id):
                return thread_id
        
        return self.create_thread()
    
    def enhance_prompt_with_context(
        self,
        prompt: str,
        use_conversation_context: bool = True
    ) -> str:
        """Add conversation context to prompt if enabled"""
        if use_conversation_context and self.current_memory:
            try:
                enhanced = self.current_memory.build_context_prompt(prompt)
                logger.info("Enhanced prompt with conversation context")
                return enhanced
            except Exception as e:
                logger.warning(f"Could not enhance prompt: {e}")
                return prompt
        return prompt
    
    def save_exchange(
        self,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save user-assistant exchange to memory"""
        if self.current_memory and self.current_thread_id:
            try:
                self.current_memory.add_exchange(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    metadata=metadata or {}
                )
                
                # Also save to thread persistence
                self.persistence_manager.add_message(
                    thread_id=self.current_thread_id,
                    role="user",
                    content=user_message
                )
                self.persistence_manager.add_message(
                    thread_id=self.current_thread_id,
                    role="assistant",
                    content=assistant_message
                )
            except Exception as e:
                logger.error(f"Error saving exchange: {e}")
    
    def update_thread_metadata(self, updates: Dict[str, Any]):
        """Update thread metadata"""
        if self.current_thread_id:
            try:
                self.persistence_manager.update_thread(
                    thread_id=self.current_thread_id,
                    updates=updates
                )
            except Exception as e:
                logger.error(f"Error updating thread: {e}")
    
    def get_conversation_history(
        self,
        thread_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        thread_id = thread_id or self.current_thread_id
        if not thread_id:
            return []
        
        return self.persistence_manager.get_conversation_history(thread_id, limit)
    
    def list_threads(self, days: int = 7) -> List[Dict[str, Any]]:
        """List recent threads"""
        return self.persistence_manager.list_threads(self.user_id, days)
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks"""
        return self.task_scheduler.list_active_tasks()
    
    def get_task_results(self, task_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get results for a scheduled task"""
        return self.task_scheduler.get_task_results(task_id, limit)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        return self.task_scheduler.cancel_task(task_id)
    
    def schedule_task(
        self,
        task_name: str,
        task_callback,
        schedule_interval: str,
        **metadata
    ) -> str:
        """Schedule a recurring task"""
        return self.task_scheduler.schedule_task(
            task_name=task_name,
            task_callback=task_callback,
            schedule_interval=schedule_interval,
            **metadata
        )


def create_persistent_agent(
    persist_directory: str = "./chroma_db",
    user_id: str = "default_user"
) -> PersistentAgent:
    """
    Factory function to create a persistent agent
    
    Args:
        persist_directory: Directory for ChromaDB storage
        user_id: User identifier
    
    Returns:
        PersistentAgent instance
    """
    return PersistentAgent(
        persist_directory=persist_directory,
        user_id=user_id
    )

