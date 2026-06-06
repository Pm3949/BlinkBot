import csv
import fitz
import logging
import math
import re
import requests
import docx
from collections import Counter
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CustomRAGEngine:
    def __init__(self):
        """Initializes caches and keeps startup logging lightweight."""
        logger.info("🧠 Initializing Custom RAG Engine (Zero LangChain)...")
        self.models_cache = {}
        logger.info("✅ Custom Engine Ready!")

    def _get_model(self, model_name: str):
        """Loads a model dynamically or returns from cache if already loaded."""
        if model_name not in self.models_cache:
            logger.info("📥 Downloading/Loading embedding model: %s...", model_name)
            try:
                self.models_cache[model_name] = SentenceTransformer(model_name)
            except Exception as exc:
                raise RuntimeError(f"Failed to load embedding model '{model_name}': {exc}") from exc
        return self.models_cache[model_name]

    # ==========================================
    # 1. RAW DATA EXTRACTION (PDF PARSING)
    # ==========================================
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Opens a PDF and extracts raw text from every page.
        """

        logger.info("Extracting text from PDF: %s", file_path)
        doc = fitz.open(file_path)
        try:
            full_text = "\n".join([page.get_text("text") for page in doc])
        finally:
            doc.close()

        return full_text
    
    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Routes a file to the correct text extractor based on its extension."""
        if not filename or "." not in filename:
            raise ValueError("Filename must include a valid extension")
        ext = filename.split('.')[-1].lower()
        
        try:
            if ext == 'pdf':
                return self.extract_text_from_pdf(file_path)
            
            elif ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
            elif ext == 'docx':
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                
            elif ext == 'csv':
                rows = []
                with open(file_path, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        rows.append(" | ".join(row))
                return "\n".join(rows)

            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise Exception(f"Failed to read {ext} file: {str(e)}")
    
    def extract_text_from_url(self, url: str) -> str:
        """Fetches a webpage and extracts clean readable text from it."""
        try:
            logger.info("🌐 Scraping URL: %s...", url)
            # Headers dalna zaroori hai warna kuch websites bot samajh kar block kar deti hain
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status() # Agar 404/500 error aaye toh exception throw karega
            
            # HTML ko parse karo
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Faltu cheezein (scripts, styles, navbars) hata do
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            # Clean text nikal lo
            text = soup.get_text(separator=' ', strip=True)
            
            # Extra spaces ko clean karo
            clean_text = re.sub(r'\s+', ' ', text)
            return clean_text
            
        except Exception as e:
            raise Exception(f"Failed to extract text from URL: {str(e)}")

    # ==========================================
    # 2. CUSTOM CHUNK ALGORITHM
    # ==========================================
    # ---------------------------------------------------------
    # CHUNKING STRATEGY 1: NAIVE SLIDING WINDOW (Legacy)
    # ---------------------------------------------------------
    def chunk_text_naive(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
        """
        Splits a large string into smaller chunks with a sliding window overlap.
        We do this manually using string slicing.
        """
        logger.info("Chunking text (Size: %s, Overlap: %s)...", chunk_size, overlap)
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            #Defining the end of the current chunk
            end = start + chunk_size

            #Extract the substring
            chunk = text[start:end]
            chunks.append(chunk)

            #Move the start pointer forward, but step back by the iverlap amount
            start += (chunk_size - overlap)
        
        return [c for c in chunks if c]
    
    # ---------------------------------------------------------
    # CHUNKING STRATEGY 2: SENTENCE WINDOW (Semantic)
    # ---------------------------------------------------------
    def chunk_text_sentence(self, text: str, sentences_per_chunk: int = 6, overlap: int = 2) -> list:
        """
        Splits text safely by punctuation (., !, ?) so sentences are never cut in half.
        Groups them into windows (e.g., 6 sentences per chunk, 2 overlap).
        """
        # Regex magic: Split by period/exclamation/question mark followed by a space
        sentences = re.split(r'(?<!\bMr)(?<!\bDr)(?<!\bMs)(?<!\bMrs)(?<!\bProf)(?<=[.!?])\s+(?=[A-Z])', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        i = 0
        while i < len(sentences):
            # Join the next 'N' sentences together
            chunk = " ".join(sentences[i : i + sentences_per_chunk])
            chunks.append(chunk)
            # Move forward, but keep 'overlap' number of sentences
            i += (sentences_per_chunk - overlap)
        
        return [c for c in chunks if len(c) > 10]
    
    # ---------------------------------------------------------
    # CHUNKING STRATEGY 3: PARAGRAPH / RECURSIVE
    # ---------------------------------------------------------
    def chunk_text_paragraph(self, text: str, max_length: int = 1200) -> list: # FIXED NAME & TYPE
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para: continue

            if len(current_chunk) + len(para) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks # FIXED: Return missing tha!

    # ==========================================
    # 3. DIRECT VECTORIZATION (EMBEDDINGS)
    # ==========================================
    # ---------------------------------------------------------
    # 1. VECTOR SEARCH (Meaning)
    # ---------------------------------------------------------
    def vectorize(self, chunks: list, model_name: str = "all-MiniLM-L6-v2") -> list:
        """
        Converts text chunks into mathematical vectors (arrays of floats) 
        using a raw HuggingFace model.
        """
        logger.info("Generating vectors for %s chunks...", len(chunks))
        # encode() returns a Numpy array. We convert it to a standard Python list of floats
        # because databases like Supabase (pgvector) expect standard arrays/lists.
        model = self._get_model(model_name)
        embeddings = model.encode(chunks).tolist()
        
        return embeddings


    def hybrid_search(self, query_text: str, query_vector: list, document_texts: list, document_vectors: list, alpha: float = 0.5, top_k: int = 5) -> list:
        """
        Combines semantic search (Cosine Similarity) with a basic keyword search (simulated TF).
        Returns a list of dicts: {"chunk_index": int, "score": float}
        """
        import numpy as np
        
        if not document_vectors:
            return []

        # 1. Semantic Scores (Cosine Similarity)
        q_vec = np.array(query_vector)
        q_norm = np.linalg.norm(q_vec)
        
        doc_vecs = np.array(document_vectors)
        doc_norms = np.linalg.norm(doc_vecs, axis=1)
        
        # Avoid division by zero
        doc_norms[doc_norms == 0] = 1e-10
        q_norm = q_norm if q_norm != 0 else 1e-10
        
        dot_products = np.dot(doc_vecs, q_vec)
        semantic_scores = dot_products / (doc_norms * q_norm)
        
        # 2. Keyword Scores (Simple TF)
        query_words = set(re.findall(r'\w+', query_text.lower()))
        keyword_scores = []
        for doc in document_texts:
            doc_lower = doc.lower()
            score = sum(1 for w in query_words if w in doc_lower)
            keyword_scores.append(score)
            
        keyword_scores = np.array(keyword_scores)
        max_kw = np.max(keyword_scores)
        if max_kw > 0:
            keyword_scores = keyword_scores / max_kw
            
        # 3. Combine Scores
        final_scores = (alpha * semantic_scores) + ((1 - alpha) * keyword_scores)
        
        # 4. Sort and return top K
        top_indices = np.argsort(final_scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "chunk_index": int(idx),
                "score": float(final_scores[idx])
            })
            
        return results

    # ==========================================
