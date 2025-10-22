"""
Smart Retriever with Automatic Multi-Query Detection
Uses LangChain's MultiQueryRetriever when queries are ambiguous
"""

import logging
import re
from typing import List, Any, Optional
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class SmartRetriever:
    """
    Intelligent retriever that automatically uses MultiQueryRetriever for ambiguous queries.
    Falls back to standard retrieval for specific queries.
    """
    
    def __init__(
        self, 
        base_retriever,  # Can be vectorstore.as_retriever() or hybrid_retriever
        llm,
        enabled: bool = True,
        auto_detect: bool = True,
        parser_key: str = "lines"  # LangChain default
    ):
        """
        Args:
            base_retriever: Vector or hybrid retriever
            llm: Language model for query generation
            enabled: Enable/disable smart retrieval
            auto_detect: Auto-detect if query needs expansion
            parser_key: Parser for MultiQueryRetriever ('lines' or 'json')
        """
        self.base_retriever = base_retriever
        self.llm = llm
        self.enabled = enabled
        self.auto_detect = auto_detect
        self.parser_key = parser_key
        
        # Initialize MultiQueryRetriever
        try:
            self.multi_query_retriever = MultiQueryRetriever.from_llm(
                retriever=base_retriever,
                llm=llm,
                parser_key=parser_key
            )
            logger.info("✓ MultiQueryRetriever initialized")
        except Exception as e:
            logger.warning(f"MultiQueryRetriever init failed: {e}")
            self.multi_query_retriever = None
        
        # Patterns that indicate ambiguous queries
        self.ambiguous_patterns = [
            r'\b(is\s+this|is\s+it)\s+(good|bad|worth|better|best)\b',
            r'\b(what\s+about|how\s+about|tell\s+me\s+about)\b',
            r'^(summary|overview|details|info|information)$',
            r'\b(compare|comparison|vs|versus)\b',
            r'\b(should\s+i|can\s+i|would\s+you)\b',
            r'\b(explain|describe)\s+(this|it)\b',
        ]
    
    def is_query_ambiguous(self, query: str) -> bool:
        """
        Determine if query needs multi-query expansion.
        
        Args:
            query: User's query string
            
        Returns:
            True if query should use MultiQueryRetriever
        """
        if not self.auto_detect:
            return True  # Always use multi-query if auto_detect disabled
        
        query_lower = query.lower().strip()
        
        # Very short queries are often ambiguous
        if len(query_lower.split()) <= 3:
            return True
        
        # Check ambiguous patterns
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.info(f"🔍 Ambiguous query detected: '{query}'")
                return True
        
        # Generic question words without specifics
        generic_starters = ['what', 'how', 'why', 'when', 'where']
        if any(query_lower.startswith(word) for word in generic_starters):
            # Check if it has specific terms (dates, names, numbers)
            has_specifics = bool(re.search(r'\d+|[A-Z][a-z]+\s+[A-Z][a-z]+', query))
            if not has_specifics:
                return True
        
        return False
    
    def retrieve(self, query: str, k: int = 20) -> List[Document]:
        """
        Smart retrieval: Uses MultiQuery for ambiguous queries, standard for specific ones.
        
        Args:
            query: User's search query
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        try:
            if not self.enabled or self.multi_query_retriever is None:
                logger.info("📊 Standard retrieval (SmartRetriever disabled)")
                return self._standard_retrieve(query, k)
            
            # Decide retrieval strategy
            if self.is_query_ambiguous(query):
                logger.info("🔄 Using MultiQueryRetriever for: '{}'".format(query[:50]))
                return self._multi_query_retrieve(query, k)
            else:
                logger.info("📊 Using standard retrieval for: '{}'".format(query[:50]))
                return self._standard_retrieve(query, k)
                
        except Exception as e:
            logger.error(f"Error in smart retrieval: {e}")
            # Fallback to standard
            return self._standard_retrieve(query, k)
    
    def _multi_query_retrieve(self, query: str, k: int) -> List[Document]:
        """Use LangChain's MultiQueryRetriever"""
        try:
            # MultiQueryRetriever automatically generates variations and retrieves
            docs = self.multi_query_retriever.invoke(query)
            
            # Deduplicate (MultiQueryRetriever might return duplicates)
            unique_docs = self._deduplicate_docs(docs)
            
            logger.info(f"✓ MultiQuery retrieved {len(docs)} docs → {len(unique_docs)} unique")
            
            return unique_docs[:k]
            
        except Exception as e:
            logger.warning(f"MultiQuery failed, falling back: {e}")
            return self._standard_retrieve(query, k)
    
    def _standard_retrieve(self, query: str, k: int) -> List[Document]:
        """Standard retrieval without query expansion"""
        try:
            # Check if it's a hybrid retriever (has .retrieve method)
            if hasattr(self.base_retriever, 'retrieve'):
                docs = self.base_retriever.retrieve(query, k=k)
            else:
                # Standard vector retriever
                docs = self.base_retriever.invoke(query)[:k]
            
            return docs
            
        except Exception as e:
            logger.error(f"Standard retrieval error: {e}")
            return []
    
    def _deduplicate_docs(self, docs: List[Document]) -> List[Document]:
        """Remove duplicate documents based on content hash"""
        seen_hashes = set()
        unique_docs = []
        
        for doc in docs:
            content_hash = hash(doc.page_content.strip())
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs


def create_smart_retriever(
    base_retriever,
    llm,
    enabled: bool = True,
    auto_detect: bool = True
) -> SmartRetriever:
    """
    Factory function to create SmartRetriever.
    
    Args:
        base_retriever: Vectorstore retriever or hybrid retriever
        llm: Language model instance
        enabled: Enable smart retrieval globally
        auto_detect: Auto-detect ambiguous queries
        
    Returns:
        Configured SmartRetriever instance
    """
    smart_retriever = SmartRetriever(
        base_retriever=base_retriever,
        llm=llm,
        enabled=enabled,
        auto_detect=auto_detect
    )
    
    logger.info(f"✓ SmartRetriever created (enabled={enabled}, auto_detect={auto_detect})")
    
    return smart_retriever