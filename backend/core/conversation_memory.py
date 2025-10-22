# -*- coding: utf-8 -*-
"""
Conversation Memory Module
Provides semantic memory and context management for follow-up questions
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import chromadb
from chromadb.config import Settings
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation memory with semantic search capabilities.
    Enables the agent to remember and reference previous conversations.
    """
    
    def __init__(
        self, 
        thread_id: str,
        persist_directory: str = "./chroma_db/memory",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_context_messages: int = 10
    ):
        """
        Initialize conversation memory for a specific thread.
        
        Args:
            thread_id: Thread identifier
            persist_directory: Directory for memory storage
            embedding_model: HuggingFace embedding model
            max_context_messages: Maximum messages to include in context
        """
        self.thread_id = thread_id
        self.persist_directory = persist_directory
        self.max_context_messages = max_context_messages
        
        # Create thread-specific directory
        self.thread_dir = Path(persist_directory) / thread_id
        self.thread_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize ChromaDB for semantic memory
        try:
            self.vectorstore = Chroma(
                collection_name=f"memory_{thread_id}",
                embedding_function=self.embeddings,
                persist_directory=str(self.thread_dir)
            )
            logger.info(f"Initialized conversation memory for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error initializing memory vectorstore: {e}")
            raise
        
        # In-memory cache for recent messages
        self.message_cache: List[Dict[str, Any]] = []
    
    def add_exchange(
        self, 
        user_message: str, 
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a user-assistant exchange to memory.
        
        Args:
            user_message: User's message
            assistant_message: Assistant's response
            metadata: Additional metadata (url, mode, etc.)
        """
        try:
            # Create combined document for semantic search
            exchange_text = f"User: {user_message}\nAssistant: {assistant_message}"
            
            exchange_metadata = {
                "thread_id": self.thread_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "type": "exchange",
                **(metadata or {})
            }
            
            # Add to vectorstore
            doc = Document(
                page_content=exchange_text,
                metadata=exchange_metadata
            )
            self.vectorstore.add_documents([doc])
            
            # Add to cache
            self.message_cache.append({
                "user": user_message,
                "assistant": assistant_message,
                "metadata": exchange_metadata
            })
            
            # Keep cache size manageable
            if len(self.message_cache) > self.max_context_messages:
                self.message_cache.pop(0)
            
            logger.info(f"Added exchange to memory for thread {self.thread_id}")
        except Exception as e:
            logger.error(f"Error adding exchange to memory: {e}")
    
    def add_context(
        self, 
        context_type: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add contextual information to memory (e.g., scraped content, analysis results).
        
        Args:
            context_type: Type of context (url_content, analysis, etc.)
            content: Context content
            metadata: Additional metadata
        """
        try:
            context_metadata = {
                "thread_id": self.thread_id,
                "type": context_type,
                **(metadata or {})
            }
            
            doc = Document(
                page_content=content,
                metadata=context_metadata
            )
            self.vectorstore.add_documents([doc])
            
            logger.info(f"Added {context_type} context to memory")
        except Exception as e:
            logger.error(f"Error adding context to memory: {e}")
    
    def search_memory(
        self, 
        query: str, 
        k: int = 5,
        filter_type: Optional[str] = None
    ) -> List[Document]:
        """
        Semantic search through conversation memory.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_type: Filter by context type (exchange, url_content, etc.)
            
        Returns:
            List of relevant documents
        """
        try:
            search_kwargs = {"k": k}
            
            if filter_type:
                search_kwargs["filter"] = {"type": filter_type}
            
            results = self.vectorstore.similarity_search(query, **search_kwargs)
            logger.info(f"Found {len(results)} relevant memories for query")
            return results
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    def get_recent_context(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent conversation exchanges from cache.
        
        Args:
            limit: Maximum number of exchanges to return
            
        Returns:
            List of recent exchanges
        """
        if limit is None:
            limit = self.max_context_messages
        
        return self.message_cache[-limit:]
    
    def build_context_prompt(
        self, 
        current_query: str,
        include_semantic: bool = True,
        semantic_k: int = 3
    ) -> str:
        """
        Build a context-aware prompt including relevant conversation history.
        
        Args:
            current_query: Current user query
            include_semantic: Whether to include semantically relevant context
            semantic_k: Number of semantic results to include
            
        Returns:
            Enhanced prompt with context
        """
        context_parts = []
        
        # Add recent conversation history
        recent = self.get_recent_context(limit=5)
        if recent:
            context_parts.append("## Recent Conversation History:")
            for i, exchange in enumerate(recent, 1):
                context_parts.append(f"\n**Exchange {i}:**")
                context_parts.append(f"User: {exchange['user']}")
                context_parts.append(f"Assistant: {exchange['assistant'][:200]}...")
        
        # Add semantically relevant context
        if include_semantic:
            relevant_docs = self.search_memory(current_query, k=semantic_k)
            if relevant_docs:
                context_parts.append("\n## Relevant Context from Previous Conversations:")
                for i, doc in enumerate(relevant_docs, 1):
                    context_parts.append(f"\n**Context {i}:**")
                    context_parts.append(doc.page_content[:300])
        
        # Build final prompt
        if context_parts:
            context_str = "\n".join(context_parts)
            enhanced_prompt = f"""{context_str}

## Current Query:
{current_query}

Please answer the current query, taking into account the conversation history and relevant context above. If this is a follow-up question, reference previous information appropriately."""
            return enhanced_prompt
        
        return current_query
    
    def get_conversation_summary(self) -> str:
        """
        Generate a summary of the conversation so far.
        
        Returns:
            Conversation summary
        """
        if not self.message_cache:
            return "No conversation history yet."
        
        summary_parts = [f"Conversation Summary (Thread: {self.thread_id})"]
        summary_parts.append(f"Total exchanges: {len(self.message_cache)}")
        summary_parts.append("\nRecent topics:")
        
        for i, exchange in enumerate(self.message_cache[-3:], 1):
            summary_parts.append(f"{i}. {exchange['user'][:100]}")
        
        return "\n".join(summary_parts)
    
    def clear_memory(self) -> None:
        """
        Clear all memory for this thread.
        """
        try:
            # Clear vectorstore
            self.vectorstore.delete_collection()
            
            # Reinitialize
            self.vectorstore = Chroma(
                collection_name=f"memory_{self.thread_id}",
                embedding_function=self.embeddings,
                persist_directory=str(self.thread_dir)
            )
            
            # Clear cache
            self.message_cache.clear()
            
            logger.info(f"Cleared memory for thread {self.thread_id}")
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
    
    def to_langchain_messages(self, limit: Optional[int] = None) -> List[BaseMessage]:
        """
        Convert conversation history to LangChain message format.
        
        Args:
            limit: Maximum number of exchanges to convert
            
        Returns:
            List of LangChain messages
        """
        recent = self.get_recent_context(limit=limit)
        messages = []
        
        for exchange in recent:
            messages.append(HumanMessage(content=exchange["user"]))
            messages.append(AIMessage(content=exchange["assistant"]))
        
        return messages


class MemoryManager:
    """
    Manages multiple conversation memories across different threads.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db/memory"):
        """
        Initialize the memory manager.
        
        Args:
            persist_directory: Base directory for memory storage
        """
        self.persist_directory = persist_directory
        self.active_memories: Dict[str, ConversationMemory] = {}
        logger.info("MemoryManager initialized")
    
    def get_memory(self, thread_id: str) -> ConversationMemory:
        """
        Get or create conversation memory for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            ConversationMemory instance
        """
        if thread_id not in self.active_memories:
            self.active_memories[thread_id] = ConversationMemory(
                thread_id=thread_id,
                persist_directory=self.persist_directory
            )
        
        return self.active_memories[thread_id]
    
    def remove_memory(self, thread_id: str) -> None:
        """
        Remove memory for a thread from active cache.
        
        Args:
            thread_id: Thread identifier
        """
        if thread_id in self.active_memories:
            del self.active_memories[thread_id]
            logger.info(f"Removed memory for thread {thread_id} from cache")
    
    def clear_all_memories(self) -> None:
        """
        Clear all active memories.
        """
        for memory in self.active_memories.values():
            memory.clear_memory()
        self.active_memories.clear()
        logger.info("Cleared all active memories")


# Singleton instance
_memory_manager = None

def get_memory_manager(persist_directory: str = "./chroma_db/memory") -> MemoryManager:
    """
    Get or create the singleton memory manager instance.
    
    Args:
        persist_directory: Base directory for memory storage
        
    Returns:
        MemoryManager instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(persist_directory)
    return _memory_manager

