"""
hybrid_retriever.py
Advanced Hybrid Retrieval System combining BM25 (keyword) + Vector (semantic) search
Provides better accuracy than vector-only retrieval
"""
import re
import logging
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import numpy as np

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines BM25 (keyword-based) and Vector (semantic) retrieval
    for superior document retrieval accuracy
    """
    
    def __init__(self, vectorstore, documents: List[Document], alpha: float = 0.5):
        """
        Initialize hybrid retriever
        
        Args:
            vectorstore: ChromaDB or any vectorstore with similarity_search
            documents: List of Document objects for BM25 indexing
            alpha: Weight balance (0=pure BM25, 1=pure vector, 0.5=balanced)
        """
        self.vectorstore = vectorstore
        self.documents = documents
        self.alpha = alpha  # Weight for combining scores
        
        # Build BM25 index
        self._build_bm25_index()
        
        logger.info("✅ Hybrid Retriever initialized (alpha={})".format(alpha))
    
    def _build_bm25_index(self):
        """Build BM25 index from documents"""
        try:
            # Tokenize documents for BM25
            tokenized_docs = []
            for doc in self.documents:
                # Simple word tokenization (you can use better tokenizers)
                tokens = doc.page_content.lower().split()
                tokenized_docs.append(tokens)
            
            # Create BM25 index
            self.bm25 = BM25Okapi(tokenized_docs)
            logger.info("✅ BM25 index built with {} documents".format(len(self.documents)))
            
        except Exception as e:
            logger.error("Error building BM25 index: {}".format(e))
            self.bm25 = None
    
    def retrieve(self, query: str, k: int = 20) -> List[Document]:
        """
        Hybrid retrieval combining BM25 and vector search
        
        Args:
            query: User query string
            k: Number of documents to retrieve
            
        Returns:
            List of top-k documents based on hybrid scores
        """
        try:
            logger.info("🔍 Hybrid retrieval for: '{}'".format(query[:50]))
            
            # 1. Vector Search (Semantic)
            vector_docs = self._vector_search(query, k * 2)  # Get more for reranking
            
            # 2. BM25 Search (Keyword)
            bm25_docs = self._bm25_search(query, k * 2)
            
            # 3. Combine and rerank
            hybrid_results = self._combine_results(vector_docs, bm25_docs, k)
            
            logger.info("✅ Retrieved {} hybrid results".format(len(hybrid_results)))
            return hybrid_results
            
        except Exception as e:
            logger.error("Error in hybrid retrieval: {}".format(e))
            # Fallback to vector-only search
            return self._vector_search(query, k)
    
    def _vector_search(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """Perform vector similarity search"""
        try:
            # Get documents with scores
            docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # Normalize scores to [0, 1] range
            if docs_and_scores:
                # Lower distance = higher similarity for most vectorstores
                # Normalize using min-max scaling
                scores = [score for _, score in docs_and_scores]
                max_score = max(scores) if scores else 1.0
                min_score = min(scores) if scores else 0.0
                score_range = max_score - min_score if max_score != min_score else 1.0
                
                normalized_results = []
                for doc, score in docs_and_scores:
                    # Convert distance to similarity (inverse and normalize)
                    normalized_score = 1 - ((score - min_score) / score_range)
                    normalized_results.append((doc, normalized_score))
                
                logger.info("📊 Vector search: {} results".format(len(normalized_results)))
                return normalized_results
            
            return []
            
        except Exception as e:
            logger.error("Vector search error: {}".format(e))
            return []
    
    def _bm25_search(self, query: str, k: int) -> List[Tuple[Document, float]]:
        """Perform BM25 keyword search"""
        try:
            if not self.bm25:
                logger.warning("BM25 index not available, skipping BM25 search")
                return []
            
            # Tokenize query
            tokenized_query = query.lower().split()
            
            # Get BM25 scores for all documents
            bm25_scores = self.bm25.get_scores(tokenized_query)
            
            # Get top-k documents with scores
            top_indices = np.argsort(bm25_scores)[-k:][::-1]  # Get top k indices
            
            # Normalize scores to [0, 1]
            max_score = max(bm25_scores) if len(bm25_scores) > 0 else 1.0
            
            results = []
            for idx in top_indices:
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    normalized_score = bm25_scores[idx] / max_score if max_score > 0 else 0.0
                    results.append((doc, normalized_score))
            
            logger.info("📊 BM25 search: {} results".format(len(results)))
            return results
            
        except Exception as e:
            logger.error("BM25 search error: {}".format(e))
            return []
    
    def _combine_results(
        self, 
        vector_results: List[Tuple[Document, float]], 
        bm25_results: List[Tuple[Document, float]], 
        k: int
    ) -> List[Document]:
        """
        Combine vector and BM25 results using weighted scoring
        
        Formula: final_score = alpha * vector_score + (1 - alpha) * bm25_score
        """
        try:
            # Create score dictionary
            doc_scores = {}
            
            # Add vector scores
            for doc, score in vector_results:
                doc_id = id(doc.page_content)  # Use content hash as ID
                doc_scores[doc_id] = {
                    'doc': doc,
                    'vector_score': score,
                    'bm25_score': 0.0
                }
            
            # Add BM25 scores
            for doc, score in bm25_results:
                doc_id = id(doc.page_content)
                if doc_id in doc_scores:
                    doc_scores[doc_id]['bm25_score'] = score
                else:
                    doc_scores[doc_id] = {
                        'doc': doc,
                        'vector_score': 0.0,
                        'bm25_score': score
                    }
            
            # Calculate hybrid scores
            hybrid_scores = []
            for doc_id, data in doc_scores.items():
                vector_score = data['vector_score']
                bm25_score = data['bm25_score']
                
                # Weighted combination
                final_score = (self.alpha * vector_score) + ((1 - self.alpha) * bm25_score)
                
                hybrid_scores.append((data['doc'], final_score))
            
            # Sort by hybrid score (descending)
            hybrid_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top-k documents
            top_docs = [doc for doc, score in hybrid_scores[:k]]
            
            logger.info("🎯 Hybrid reranking: {} → {} final results".format(
                len(doc_scores), len(top_docs)
            ))
            
            return top_docs
            
        except Exception as e:
            logger.error("Error combining results: {}".format(e))
            # Fallback: return vector results
            return [doc for doc, _ in vector_results[:k]]


class AdaptiveHybridRetriever(HybridRetriever):
    """
    Advanced hybrid retriever that adapts alpha based on query type
    """
    
    def retrieve(self, query: str, k: int = 20) -> List[Document]:
        """
        Adaptive retrieval - adjusts alpha based on query characteristics
        """
        # Detect query type and adjust alpha
        original_alpha = self.alpha
        self.alpha = self._detect_optimal_alpha(query)
        
        logger.info("🎯 Adaptive alpha: {} (original: {})".format(self.alpha, original_alpha))
        
        # Perform hybrid retrieval
        results = super().retrieve(query, k)
        
        # Restore original alpha
        self.alpha = original_alpha
        
        return results
    
    def _detect_optimal_alpha(self, query: str) -> float:
        """
        Detect optimal alpha based on query characteristics
        
        Rules:
        - Exact terms, numbers, names → Lower alpha (favor BM25)
        - Conceptual, semantic questions → Higher alpha (favor vector)
        - Balanced queries → Medium alpha
        """
        query_lower = query.lower()
        
        # Check for exact/keyword indicators
        keyword_indicators = [
            'what is the price', 'how much', 'when', 'where',
            'who', 'phone number', 'email', 'address',
            'list', 'name', 'number', 'date'
        ]
        
        # Check for semantic indicators
        semantic_indicators = [
            'explain', 'why', 'how does', 'what does it mean',
            'compare', 'difference between', 'similar to',
            'summarize', 'overview', 'about'
        ]
        
        keyword_count = sum(1 for indicator in keyword_indicators if indicator in query_lower)
        semantic_count = sum(1 for indicator in semantic_indicators if indicator in query_lower)
        
        # Has numbers or special patterns → favor BM25
        has_numbers = bool(re.search(r'\d+', query))
        has_quotes = '"' in query or "'" in query
        
        if keyword_count > semantic_count or has_numbers or has_quotes:
            return 0.3  # Favor BM25 (keyword search)
        elif semantic_count > keyword_count:
            return 0.7  # Favor vector (semantic search)
        else:
            return 0.5  # Balanced


def create_hybrid_retriever(
    vectorstore, 
    chunks: List[Document], 
    adaptive: bool = True,
    alpha: float = 0.5
) -> HybridRetriever:
    """
    Factory function to create hybrid retriever
    
    Args:
        vectorstore: Vector database (Chroma, etc.)
        chunks: List of document chunks
        adaptive: Use adaptive alpha adjustment
        alpha: Default alpha value (if not adaptive)
        
    Returns:
        HybridRetriever instance
    """
    try:
        if adaptive:
            retriever = AdaptiveHybridRetriever(vectorstore, chunks, alpha)
            logger.info("✅ Created Adaptive Hybrid Retriever")
        else:
            retriever = HybridRetriever(vectorstore, chunks, alpha)
            logger.info("✅ Created Standard Hybrid Retriever")
        
        return retriever
        
    except Exception as e:
        logger.error("Error creating hybrid retriever: {}".format(e))
        raise


# ============ UTILITY FUNCTIONS ============

def test_hybrid_retriever(vectorstore, documents, test_queries: List[str]):
    """
    Test function to compare vector-only vs hybrid retrieval
    """
    print("\n" + "="*70)
    print("TESTING HYBRID RETRIEVAL")
    print("="*70)
    
    hybrid = create_hybrid_retriever(vectorstore, documents, adaptive=True)
    
    for query in test_queries:
        print("\nQuery: '{}'".format(query))
        print("-" * 70)
        
        # Vector-only results
        vector_results = vectorstore.similarity_search(query, k=5)
        print("\nVector-only (top 3):")
        for i, doc in enumerate(vector_results[:3], 1):
            print("{}. {}...".format(i, doc.page_content[:100]))
        
        # Hybrid results
        hybrid_results = hybrid.retrieve(query, k=5)
        print("\nHybrid (top 3):")
        for i, doc in enumerate(hybrid_results[:3], 1):
            print("{}. {}...".format(i, doc.page_content[:100]))
    
    print("\n" + "="*70)


  