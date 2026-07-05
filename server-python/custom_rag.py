"""
Core Engine for Retrieval-Augmented Generation (RAG).
Responsibility: Handles the end-to-end pipeline of converting raw files/URLs into
searchable vector embeddings, and provides a custom hybrid search mechanism to
retrieve relevant document chunks based on a user's query.
"""

import csv
import fitz  # PyMuPDF for fast PDF parsing
import logging
import math
import re
import requests
import docx
import os
from dotenv import load_dotenv
from collections import Counter

# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CustomRAGEngine:
    """
    Initializes the engine.
    We use a `models_cache` dictionary to keep embedding models in memory.
    Why? Loading a model (even a small one like MiniLM) takes time and CPU/RAM.
    By caching it, subsequent vectorization requests are instantaneous.
    """

    def __init__(self):
        """Initializes caches and keeps startup logging lightweight."""
        logger.info("🧠 Initializing Custom RAG Engine (Zero LangChain)...")
        self.models_cache = {}
        self.reranker_cache = {}
        logger.info("✅ Custom Engine Ready!")

    def _get_model(self, model_name: str):
        """
        Singleton-pattern-like loader for embedding models.
        Dynamically loads a model from HuggingFace on the first run and returns it
        from the cache on subsequent calls.
        """
        if model_name not in self.models_cache:
            logger.info("📥 Downloading/Loading embedding model: %s...", model_name)
            try:
                self.models_cache[model_name] = SentenceTransformer(model_name)
            except Exception as exc:
                # Critical error handling: If the model fails to load, the entire RAG pipeline is broken.
                raise RuntimeError(
                    f"Failed to load embedding model '{model_name}': {exc}"
                ) from exc
        return self.models_cache[model_name]

    def _get_reranker_model(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Singleton-pattern-like loader for CrossEncoder reranker models.
        """
        if model_name not in self.reranker_cache:
            logger.info("📥 Downloading/Loading reranker model: %s...", model_name)
            try:
                from sentence_transformers import CrossEncoder
                self.reranker_cache[model_name] = CrossEncoder(model_name)
            except Exception as exc:
                logger.error(f"Failed to load reranker model '{model_name}': {exc}")
                return None
        return self.reranker_cache[model_name]

    # ==========================================
    # 1. RAW DATA EXTRACTION (PDF PARSING)
    # ==========================================
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extracts raw text from PDFs.
        Edge Case Handled: Some PDFs are just scanned images (no selectable text).
        If PyMuPDF extracts less than 50 characters on a page, we assume it's a scan
        and fallback to Optical Character Recognition (OCR) using Tesseract.
        """
        logger.info("Extracting text from PDF: %s", file_path)
        doc = fitz.open(file_path)
        full_text = ""
        try:
            import pytesseract
            from PIL import Image

            for page in doc:
                text = page.get_text("text").strip()
                # If page has very little text, it might be a scanned image. Fall back to OCR!
                if len(text) < 50:
                    logger.info(
                        "Page %s has very little text. Attempting OCR fallback...",
                        page.number,
                    )
                    try:
                        # Convert the PDF page to a high-res image (200 DPI is a sweet spot for OCR accuracy vs speed)
                        pix = page.get_pixmap(dpi=200)  # Good DPI for OCR
                        img = Image.frombytes(
                            "RGB", [pix.width, pix.height], pix.samples
                        )
                        # Run the image through Tesseract to guess the text
                        ocr_text = pytesseract.image_to_string(img)
                        text = text + "\n" + ocr_text
                    except Exception as e:
                        logger.error("OCR Failed for PDF page %s: %s", page.number, e)
                full_text += text + "\n"
        finally:
            doc.close()

        return full_text

    def extract_text_from_image(self, file_path: str) -> str:
        """Runs Optical Character Recognition (OCR) on an image file."""
        logger.info("Extracting text from Image via OCR: %s", file_path)
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(file_path)
            return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("OCR Failed for image: %s", e)
            raise Exception(f"Failed to run OCR on image: {str(e)}")

    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """
        The main router for file ingestion.
        Determines the file type by its extension and delegates to the appropriate extractor.
        """
        if not filename or "." not in filename:
            raise ValueError("Filename must include a valid extension")
        ext = filename.split(".")[-1].lower()

        try:
            if ext == "pdf":
                return self.extract_text_from_pdf(file_path)

            elif ext in ["jpg", "jpeg", "png"]:
                return self.extract_text_from_image(file_path)

            elif ext == "txt":
                # Explicitly defining utf-8 encoding to prevent UnicodeDecodeErrors on special characters
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            elif ext == "docx":
                doc = docx.Document(file_path)
                return "\n".join(
                    [para.text for para in doc.paragraphs if para.text.strip()]
                )

            elif ext == "csv":
                rows = []
                with open(file_path, newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # Combine CSV columns into a readable format for the LLM (e.g., "Col1 | Col2 | Col3")
                        rows.append(" | ".join(row))
                return "\n".join(rows)

            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise Exception(f"Failed to read {ext} file: {str(e)}")

    def extract_text_from_url(self, url: str) -> str:
        """
        Fetches a webpage and extracts clean, readable text.
        Data Flow: Raw HTML -> Remove scripts/styles -> Extract visible text -> Clean whitespace.
        """
        try:
            logger.info("🌐 Scraping URL: %s...", url)
            # Edge Case Handled: Spoofing the User-Agent. Many sites block default Python `requests`
            # to prevent bot scraping. Pretending to be a Chrome browser bypasses basic protections.
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()  # Throws an exception if we get a 404, 403, 500, etc.

            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove tags that contain structural or behavioral data, not contextual content.
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract text, putting a space between HTML blocks to avoid words merging together
            text = soup.get_text(separator=" ", strip=True)

            # Regex to collapse multiple spaces, tabs, or newlines into a single space
            clean_text = re.sub(r"\s+", " ", text)
            return clean_text

        except Exception as e:
            raise Exception(f"Failed to extract text from URL: {str(e)}")

    # ==========================================
    # 2. CUSTOM CHUNK ALGORITHM
    # ==========================================
    # Why chunking? LLMs have a "context window" (token limit). We can't feed a 500-page book
    # into the prompt at once. We must break it down into chunks, embed them, and retrieve only the relevant ones.

    # ---------------------------------------------------------
    # CHUNKING STRATEGY 1: NAIVE SLIDING WINDOW (Legacy)
    # ---------------------------------------------------------
    def chunk_text_naive(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list:
        """
        Splits text purely by character count.
        Pros: Fast and guarantees specific chunk sizes.
        Cons: Might cut a sentence or word perfectly in half, losing semantic meaning.
        The `overlap` ensures context isn't completely lost at the boundaries.
        """
        logger.info("Chunking text (Size: %s, Overlap: %s)...", chunk_size, overlap)
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Defining the end of the current chunk
            end = start + chunk_size

            # Extract the substring
            chunk = text[start:end]
            chunks.append(chunk)

            # Step forward, but overlap with the previous chunk to maintain boundary context
            start += chunk_size - overlap

        return [c for c in chunks if c]

    # ---------------------------------------------------------
    # CHUNKING STRATEGY 2: SENTENCE WINDOW (Semantic)
    # ---------------------------------------------------------
    def chunk_text_sentence(
        self, text: str, sentences_per_chunk: int = 6, overlap: int = 2
    ) -> list:
        """
        A much smarter approach. Groups full sentences together so context is preserved.
        """
        # Regex Magic Explained:
        # `(?<=[.!?])\s+(?=[A-Z])` splits on punctuation followed by space and a capital letter.
        # `(?<!\bMr)` are Negative Lookbehinds. They prevent splitting on common abbreviations.
        # Without this, "Mr. Smith went home." would split into ["Mr", "Smith went home."]
        sentences = re.split(
            r"(?<!\bMr)(?<!\bDr)(?<!\bMs)(?<!\bMrs)(?<!\bProf)(?<=[.!?])\s+(?=[A-Z])",
            text,
        )
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        i = 0
        while i < len(sentences):
            # Join the next 'N' sentences together
            chunk = " ".join(sentences[i : i + sentences_per_chunk])
            chunks.append(chunk)
            # Move forward, but keep 'overlap' number of sentences
            i += sentences_per_chunk - overlap

        # Filter out tiny, useless chunks (less than 10 chars)
        return [c for c in chunks if len(c) > 10]

    # ---------------------------------------------------------
    # CHUNKING STRATEGY 3: PARAGRAPH / RECURSIVE
    # ---------------------------------------------------------
    def chunk_text_paragraph(self, text: str, max_length: int = 1200) -> list:
        """
        Splits text by natural paragraph breaks (\n\n), accumulating paragraphs until
        the chunk hits a maximum character limit. Excellent for well-formatted documents.
        """
        # Split the text into paragraphs (assuming double newline separates paragraphs)
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # If adding this paragraph exceeds the limit, save the current chunk and start a new one.
            if len(current_chunk) + len(para) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Don't forget to append the very last chunk!
        if current_chunk:
            # Accumulate text
            chunks.append(current_chunk.strip())

        return chunks

    # ==========================================
    # 3. DIRECT VECTORIZATION (EMBEDDINGS)
    # ==========================================
    # ---------------------------------------------------------
    # 1. VECTOR SEARCH (Meaning)
    # ---------------------------------------------------------
    def vectorize(self, chunks: list, model_name: str = "all-MiniLM-L6-v2") -> list:
        """
        Converts text chunks into dense mathematical vectors (arrays of floats).
        These vectors capture the semantic meaning of the text. E.g., the vector for "Dog"
        will be mathematically closer to "Puppy" than to "Car".
        """
        logger.info("Generating vectors for %s chunks...", len(chunks))
        # encode() returns a Numpy array. We convert it to a standard Python list of floats
        # because databases like Supabase (pgvector) expect standard arrays/lists.
        model = self._get_model(model_name)
        embeddings = model.encode(chunks).tolist()

        # `model.encode()` returns a Numpy array natively.
        # We must convert it to a standard Python list `.tolist()` because databases
        # (like pgvector in Supabase) cannot process raw Numpy objects over API requests.
        return embeddings

    def hybrid_search(
        self,
        query_text: str,
        query_vector: list,
        document_texts: list,
        document_vectors: list,
        alpha: float = 0.5,
        top_k: int = 5,
    ) -> list:
        """
        Advanced retrieval: Combines Semantic Search (Vector Math) with Lexical Search (Keyword Matching).
        Why? Semantic search is great for concepts ("capital of France"), but bad for exact matches
        (like order numbers or specific names e.g., "Invoice #12345"). Hybrid search solves this.

        `alpha` controls the weight. alpha=0.5 means 50% semantic, 50% keyword.
        """
        import numpy as np

        if not document_vectors:
            return []

        # --- Part 1: Semantic Scores (Cosine Similarity) ---
        q_vec = np.array(query_vector)
        # Calculate the magnitude (length) of the query vector
        q_norm = np.linalg.norm(q_vec)

        doc_vecs = np.array(document_vectors)
        # Calculate magnitudes for all document vectors at once (axis=1)
        doc_norms = np.linalg.norm(doc_vecs, axis=1)

        # Edge Case Handled: Avoid Division by Zero.
        # If an empty string was embedded, its norm might be 0. We change 0 to a tiny number (1e-10).
        doc_norms[doc_norms == 0] = 1e-10
        q_norm = q_norm if q_norm != 0 else 1e-10

        # Dot product calculates the angle between the query vector and doc vectors.
        dot_products = np.dot(doc_vecs, q_vec)
        # Cosine Similarity formula: (A . B) / (||A|| * ||B||)
        semantic_scores = dot_products / (doc_norms * q_norm)

        # --- Part 2: Keyword Scores (Simple Term Frequency) ---
        # Very basic lexical search: Count how many query words exist in the document chunk.
        query_words = set(re.findall(r"\w+", query_text.lower()))
        keyword_scores = []
        for doc in document_texts:
            doc_lower = doc.lower()
            score = sum(1 for w in query_words if w in doc_lower)
            keyword_scores.append(score)

        keyword_scores = np.array(keyword_scores)
        max_kw = np.max(keyword_scores)
        # Normalize keyword scores to be between 0 and 1, so they can be mathematically added to semantic scores.
        if max_kw > 0:
            keyword_scores = keyword_scores / max_kw

        # --- Part 3: Combine Scores ---
        # Weighted sum of both algorithms.
        final_scores = (alpha * semantic_scores) + ((1 - alpha) * keyword_scores)

        # --- Part 4: Sort and return top K ---
        # argsort() sorts ascending. We reverse it `[::-1]` to get highest scores first,
        # then take the top `top_k` results.
        top_indices = np.argsort(final_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({"chunk_index": int(idx), "score": float(final_scores[idx])})

        return results

    def rerank_documents(self, query: str, documents: list, top_k: int = 5, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> list:
        """
        Re-ranks a list of documents against a query using a CrossEncoder model.
        Expects `documents` to be a list of tuples or lists where the first element is the document text.
        Returns the top_k ranked documents.
        """
        if not documents:
            return []
            
        reranker = self._get_reranker_model(model_name)
        if not reranker:
            # Fallback to the original order if reranker fails to load
            logger.warning("Reranker failed to load, falling back to original search order.")
            return documents[:top_k]
            
        logger.info(f"Reranking {len(documents)} chunks...")
        
        # Prepare inputs for the CrossEncoder: list of [query, doc_text] pairs
        # We assume doc[0] contains the text. We decrypt it if necessary or assume it's raw text.
        # However, the decryption happens *after* retrieval in chat_handler. 
        # But wait! We need to decrypt the text BEFORE reranking, otherwise the CrossEncoder sees gibberish.
        from core.security import decrypt_key
        
        pairs = []
        for doc in documents:
            decrypted_text = decrypt_key(doc[0]) or doc[0]
            pairs.append([query, decrypted_text])
            
        # Score pairs
        scores = reranker.predict(pairs)
        
        # Combine documents with their new scores
        doc_scores = list(zip(documents, scores))
        
        # Sort by score descending
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the original document structures for the top_k
        return [doc for doc, score in doc_scores[:top_k]]

    def generate_hyde_query(self, query: str, llm) -> str:
        """
        Generates a Hypothetical Document Embeddings (HyDE) query.
        It uses the LLM to write a hypothetical answer to the query, and then returns
        the original query combined with the hypothetical answer to be vectorized.
        """
        logger.info("Generating HyDE query expansion...")
        prompt = f"""You are an expert answering questions. 
Please write a short, hypothetical answer to the following question. Do not include any explanations, just the factual answer.

Question: {query}
Answer:"""
        try:
            response = llm.invoke(prompt)
            hypothetical_answer = response.content.strip()
            # Combine the original query with the hypothetical answer
            return f"{query}\n{hypothetical_answer}"
        except Exception as e:
            logger.error(f"HyDE generation failed: {e}")
            return query # Fallback to original query

