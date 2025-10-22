# -*- coding: utf-8 -*-
"""
Thread-based Persistence Manager using ChromaDB
Handles conversation threads, state checkpointing, and history management
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import chromadb
from chromadb.config import Settings
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ThreadPersistenceManager:
    """
    Manages conversation threads and state persistence using ChromaDB.
    Each thread represents a separate conversation context.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the persistence manager with ChromaDB.
        
        Args:
            persist_directory: Directory to store ChromaDB data
        """
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Collection for thread metadata
        try:
            self.threads_collection = self.client.get_or_create_collection(
                name="conversation_threads",
                metadata={"description": "Stores conversation thread metadata"}
            )
        except Exception as e:
            logger.error(f"Error creating threads collection: {e}")
            self.threads_collection = self.client.get_collection("conversation_threads")
        
        # Collection for conversation history
        try:
            self.history_collection = self.client.get_or_create_collection(
                name="conversation_history",
                metadata={"description": "Stores conversation messages and states"}
            )
        except Exception as e:
            logger.error(f"Error creating history collection: {e}")
            self.history_collection = self.client.get_collection("conversation_history")
        
        # Collection for checkpoints (LangGraph state snapshots)
        try:
            self.checkpoint_collection = self.client.get_or_create_collection(
                name="state_checkpoints",
                metadata={"description": "Stores LangGraph state checkpoints"}
            )
        except Exception as e:
            logger.error(f"Error creating checkpoint collection: {e}")
            self.checkpoint_collection = self.client.get_collection("state_checkpoints")
        
        logger.info(f"ThreadPersistenceManager initialized with directory: {persist_directory}")
    
    def create_thread(self, user_id: str = "default_user", metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new conversation thread.
        
        Args:
            user_id: User identifier
            metadata: Additional metadata for the thread
            
        Returns:
            thread_id: Unique thread identifier
        """
        thread_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        thread_data = {
            "thread_id": thread_id,
            "user_id": user_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0,
            "is_active": True,
            **(metadata or {})
        }
        
        try:
            self.threads_collection.add(
                documents=[json.dumps(thread_data)],
                metadatas=[thread_data],
                ids=[thread_id]
            )
            logger.info(f"Created new thread: {thread_id}")
            return thread_id
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            raise
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve thread metadata.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread metadata or None if not found
        """
        try:
            result = self.threads_collection.get(
                ids=[thread_id],
                include=["metadatas", "documents"]
            )
            
            if result["ids"]:
                return result["metadatas"][0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving thread {thread_id}: {e}")
            return None
    
    def list_threads(self, user_id: str = "default_user", days: int = 7) -> List[Dict[str, Any]]:
        """
        List all threads for a user within the specified time range.
        
        Args:
            user_id: User identifier
            days: Number of days to look back (default: 7 days)
            
        Returns:
            List of thread metadata dictionaries
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all threads for the user
            results = self.threads_collection.get(
                where={"user_id": user_id},
                include=["metadatas"]
            )
            
            # Filter by date and sort
            threads = []
            for metadata in results["metadatas"]:
                if metadata.get("created_at", "") >= cutoff_date:
                    threads.append(metadata)
            
            # Sort by updated_at descending
            threads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            logger.info(f"Found {len(threads)} threads for user {user_id} in last {days} days")
            return threads
        except Exception as e:
            logger.error(f"Error listing threads: {e}")
            return []
    
    def update_thread(self, thread_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update thread metadata.
        
        Args:
            thread_id: Thread identifier
            updates: Dictionary of fields to update
            
        Returns:
            Success status
        """
        try:
            current_thread = self.get_thread(thread_id)
            if not current_thread:
                logger.warning(f"Thread {thread_id} not found")
                return False
            
            # Merge updates
            current_thread.update(updates)
            current_thread["updated_at"] = datetime.now().isoformat()
            
            self.threads_collection.update(
                ids=[thread_id],
                documents=[json.dumps(current_thread)],
                metadatas=[current_thread]
            )
            
            logger.info(f"Updated thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating thread {thread_id}: {e}")
            return False
    
    def add_message(
        self, 
        thread_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the conversation history.
        
        Args:
            thread_id: Thread identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Additional metadata
            
        Returns:
            message_id: Unique message identifier
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message_data = {
            "message_id": message_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            **(metadata or {})
        }
        
        try:
            self.history_collection.add(
                documents=[content],
                metadatas=[message_data],
                ids=[message_id]
            )
            
            # Update thread message count
            thread = self.get_thread(thread_id)
            if thread:
                self.update_thread(thread_id, {
                    "message_count": thread.get("message_count", 0) + 1
                })
            
            logger.info(f"Added message {message_id} to thread {thread_id}")
            return message_id
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise
    
    def get_conversation_history(
        self, 
        thread_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a thread.
        
        Args:
            thread_id: Thread identifier
            limit: Maximum number of messages to retrieve (None = all)
            
        Returns:
            List of messages in chronological order
        """
        try:
            results = self.history_collection.get(
                where={"thread_id": thread_id},
                include=["metadatas", "documents"]
            )
            
            # Sort by timestamp
            messages = []
            for i, metadata in enumerate(results["metadatas"]):
                messages.append({
                    **metadata,
                    "content": results["documents"][i]
                })
            
            messages.sort(key=lambda x: x.get("timestamp", ""))
            
            if limit:
                messages = messages[-limit:]
            
            logger.info(f"Retrieved {len(messages)} messages from thread {thread_id}")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def save_checkpoint(
        self, 
        thread_id: str, 
        checkpoint_id: str, 
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a LangGraph state checkpoint.
        
        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier
            state: State dictionary to save
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        timestamp = datetime.now().isoformat()
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "thread_id": thread_id,
            "timestamp": timestamp,
            "state": json.dumps(state),
            **(metadata or {})
        }
        
        try:
            # Use composite ID for uniqueness
            composite_id = f"{thread_id}_{checkpoint_id}"
            
            self.checkpoint_collection.upsert(
                documents=[json.dumps(state)],
                metadatas=[checkpoint_data],
                ids=[composite_id]
            )
            
            logger.info(f"Saved checkpoint {checkpoint_id} for thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return False
    
    def get_checkpoint(self, thread_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific checkpoint.
        
        Args:
            thread_id: Thread identifier
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint state or None
        """
        try:
            composite_id = f"{thread_id}_{checkpoint_id}"
            
            result = self.checkpoint_collection.get(
                ids=[composite_id],
                include=["metadatas", "documents"]
            )
            
            if result["ids"]:
                metadata = result["metadatas"][0]
                state = json.loads(metadata["state"])
                return {
                    "checkpoint_id": checkpoint_id,
                    "thread_id": thread_id,
                    "timestamp": metadata["timestamp"],
                    "state": state
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")
            return None
    
    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent checkpoint for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Latest checkpoint or None
        """
        try:
            results = self.checkpoint_collection.get(
                where={"thread_id": thread_id},
                include=["metadatas", "documents"]
            )
            
            if not results["ids"]:
                return None
            
            # Find the latest by timestamp
            checkpoints = []
            for i, metadata in enumerate(results["metadatas"]):
                state = json.loads(metadata["state"])
                checkpoints.append({
                    "checkpoint_id": metadata["checkpoint_id"],
                    "thread_id": thread_id,
                    "timestamp": metadata["timestamp"],
                    "state": state
                })
            
            checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)
            return checkpoints[0] if checkpoints else None
        except Exception as e:
            logger.error(f"Error retrieving latest checkpoint: {e}")
            return None
    
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread and all associated data.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Success status
        """
        try:
            # Delete thread metadata
            self.threads_collection.delete(ids=[thread_id])
            
            # Delete conversation history
            history_results = self.history_collection.get(
                where={"thread_id": thread_id},
                include=["metadatas"]
            )
            if history_results["ids"]:
                self.history_collection.delete(ids=history_results["ids"])
            
            # Delete checkpoints
            checkpoint_results = self.checkpoint_collection.get(
                where={"thread_id": thread_id},
                include=["metadatas"]
            )
            if checkpoint_results["ids"]:
                self.checkpoint_collection.delete(ids=checkpoint_results["ids"])
            
            logger.info(f"Deleted thread {thread_id} and all associated data")
            return True
        except Exception as e:
            logger.error(f"Error deleting thread {thread_id}: {e}")
            return False
    
    def cleanup_old_threads(self, days: int = 7, user_id: str = "default_user") -> int:
        """
        Delete threads older than specified days.
        
        Args:
            days: Delete threads older than this many days
            user_id: User identifier
            
        Returns:
            Number of threads deleted
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            results = self.threads_collection.get(
                where={"user_id": user_id},
                include=["metadatas"]
            )
            
            deleted_count = 0
            for i, metadata in enumerate(results["metadatas"]):
                if metadata.get("created_at", "") < cutoff_date:
                    thread_id = results["ids"][i]
                    if self.delete_thread(thread_id):
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old threads")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old threads: {e}")
            return 0


# Singleton instance
_persistence_manager = None

def get_persistence_manager(persist_directory: str = "./chroma_db") -> ThreadPersistenceManager:
    """
    Get or create the singleton persistence manager instance.
    
    Args:
        persist_directory: Directory for ChromaDB storage
        
    Returns:
        ThreadPersistenceManager instance
    """
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = ThreadPersistenceManager(persist_directory)
    return _persistence_manager

