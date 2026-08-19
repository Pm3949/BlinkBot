"""
================================================================================
CUSTOM RETRIEVAL-AUGMENTED GENERATION (RAG) PIPELINE CORE (custom_rag.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module contains the primary engine logic that enables Retrieval-Augmented
Generation (RAG) capabilities in the RAGMate application without requiring external
large framework orchestrators (like LangChain). It handles the end-to-end processing:
1. File & Data Ingestion:
   - Parses document files (PDF, DOCX, CSV, TXT) and web page URLs.
   - Implements optical character recognition (OCR) fallback routines for scanned PDFs or images.
2. Context Segmentation (Chunking):
   - Implements naive chunk splitting, sentence-based semantic chunk boundary segmentations,
     and paragraph layout grouping.
3. Dense Vectorization & Embeddings:
   - Manages and caches SentenceTransformer models to convert text chunks into float arrays.
4. Advanced Retrieval Systems:
   - Hybrid Search: Combines cosine vector similarity (dense retrieval) with basic lexical
     matching term frequencies (sparse retrieval).
   - HyDE (Hypothetical Document Embeddings): Expands query keywords by using LLM completions
     to generate a hypothetical answer, then vectorize it.
   - Cross-Encoder Reranking: Reranks documents against query contexts.
   - MMR (Maximal Marginal Relevance): Deduplicates search contexts to return diverse result sets.

BEGINNER ALGORITHM BREAKDOWN:
- Vector Embeddings: An AI model converts text words into a list of numbers (e.g. 384 dimensions).
  This acts as coordinates in semantic space. The closeness of two vectors implies conceptual similarity.
- Cosine Similarity: Calculated as `(A . B) / (||A|| * ||B||)`. It measures the angle between
  two vectors. If the angle is 0, they are semantically identical.
- MMR: Selects items that are relevant to the query but are mathematically distinct from
  each other to ensure we don't present the same information repeatedly to the LLM.
"""

import csv
import fitz  # PyMuPDF library for fast PDF text and structural parsing
import logging
import math
import re
import requests
import docx  # python-docx library to parse Microsoft Word files
import os
from dotenv import load_dotenv
from collections import Counter

# HTML scraping parsing utility.
from bs4 import BeautifulSoup

# Load local system environment variables.
load_dotenv()

from utils.logger import get_department_logger

# Initialize module-level logger using the centralized departmental system.
logger = get_department_logger("knowledge_base")


class CustomRAGEngine:
    """
    Main engine class coordinating file loading, vector embeddings, indexing, and retrieval.
    """

    def __init__(self):
        """
        Initializes cached model dictionaries to keep models in memory.

        Purpose:
            Heavy models (like transformer architectures) take time to load from disk.
            Initializing caches in memory avoids reloading overhead on subsequent operations.

        Parameters:
            None.

        Returns:
            None.
        """
        logger.info("🧠 Initializing Custom RAG Engine (Zero LangChain)...")
        # Cache dictionary mapping model names to loaded SentenceTransformer instances.
        self.models_cache = {}
        # Cache dictionary mapping model names to loaded CrossEncoder instances.
        self.reranker_cache = {}
        logger.info("✅ Custom Engine Ready!")

    def _get_model(self, model_name: str):
        """
        Retrieves or downloads a SentenceTransformer model locally.
        """
        # If the model is not in the cache, load it.
        if model_name not in self.models_cache:
            logger.info(
                "📥 Downloading/Loading embedding model locally: %s...", model_name
            )
            try:
                # Load SentenceTransformer dynamically to avoid importing it if using cloud APIs.
                from sentence_transformers import SentenceTransformer

                # Load the model.
                self.models_cache[model_name] = SentenceTransformer(model_name)
            except ImportError as imp_err:
                raise ImportError(
                    "sentence_transformers is not installed. Ensure sentence_transformers is in requirements.txt if running locally, or configure HUGGINGFACE_API_KEY to use the cloud API."
                ) from imp_err
            except Exception as exc:
                # Raise a critical runtime error if the model fails to load.
                raise RuntimeError(
                    f"Failed to load embedding model '{model_name}': {exc}"
                ) from exc
        # Return the cached model.
        return self.models_cache[model_name]

    def _get_reranker_model(
        self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        """
        Retrieves or downloads a CrossEncoder reranker model.

        Purpose:
            Implements a singleton-like loader to reuse loaded reranker models.

        Parameters:
            model_name (str): The HuggingFace name of the reranker model.

        Returns:
            CrossEncoder or None: The loaded reranker model, or None if loading fails.

        Side Effects / State Changes:
            - Downloads model files if missing.
            - Adds the loaded model to the `reranker_cache` dictionary.
        """
        # If the model is not in the cache, load it.
        if model_name not in self.reranker_cache:
            if (
                os.getenv("HUGGINGFACE_API_KEY")
                or os.getenv("HF_TOKEN")
                or os.getenv("CLOUD_MODE", "").lower() == "true"
            ):
                logger.info("☁️ Cloud mode active. Skipping local reranker execution.")
                return None
            logger.info("📥 Downloading/Loading reranker model: %s...", model_name)
            try:
                # Import CrossEncoder inside the method to reduce startup import overhead.
                from sentence_transformers import CrossEncoder

                self.reranker_cache[model_name] = CrossEncoder(model_name)
            except Exception as exc:
                logger.error(f"Failed to load reranker model '{model_name}': {exc}")
                return None
        # Return the cached reranker model.
        return self.reranker_cache[model_name]

    # ==========================================
    # 1. RAW DATA EXTRACTION (PDF PARSING)
    # ==========================================

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extracts raw text from a PDF file.

        Purpose:
            Reads structural text from a PDF, falling back to OCR (pytesseract)
            if a page contains mostly image data (like scanned printouts).

        Parameters:
            file_path (str): Local path to the PDF file.

        Returns:
            str: The extracted text.

        Side Effects:
            - Spawns OCR sub-processes if scanned images are encountered.

        Errors / Exceptions:
            - Logs failures and returns extracted structural text if OCR fails.
        """
        logger.info("Extracting text from PDF: %s", file_path)
        # Open the PDF file using PyMuPDF.
        doc = fitz.open(file_path)
        full_text = ""
        try:
            # Import OCR libraries inside the method to reduce startup import overhead.
            import pytesseract
            from PIL import Image

            # Loop through each page in the PDF.
            for page in doc:
                # Extract text using PyMuPDF's built-in parser.
                text = page.get_text("text").strip()

                # Scanned Page Fallback: If build-in extraction returns very little text (< 50 chars),
                # assume it is a scanned image page and run OCR.
                if len(text) < 50:
                    logger.info(
                        "Page %s has very little text. Attempting OCR fallback...",
                        page.number,
                    )
                    try:
                        # Convert the page to an image. 200 DPI balances OCR speed and character recognition accuracy.
                        pix = page.get_pixmap(dpi=200)
                        # Load raw image bytes into PIL.
                        img = Image.frombytes(
                            "RGB", [pix.width, pix.height], pix.samples
                        )
                        # Execute optical character recognition using Tesseract.
                        ocr_text = pytesseract.image_to_string(img)
                        # Append the OCR results to the existing text.
                        text = text + "\n" + ocr_text
                    except Exception as e:
                        logger.error("OCR Failed for PDF page %s: %s", page.number, e)
                # Accumulate the text.
                full_text += text + "\n"
        finally:
            # Ensure the document handle is closed.
            doc.close()

        # Return the accumulated text.
        return full_text

    def extract_text_from_image(self, file_path: str) -> str:
        """
        Extracts text from image files.

        Parameters:
            file_path (str): Local path to the image file.

        Returns:
            str: The extracted text.

        Errors / Exceptions:
            - Raises Exception if OCR fails.
        """
        logger.info("Extracting text from Image via OCR: %s", file_path)
        try:
            import pytesseract
            from PIL import Image

            # Open the image using PIL.
            img = Image.open(file_path)
            # Run OCR on the image.
            return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("OCR Failed for image: %s", e)
            raise Exception(f"Failed to run OCR on image: {str(e)}")

    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """
        Extracts text from files based on their extension.

        Parameters:
            file_path (str): Local path to the file.
            filename (str): The filename, including the extension.

        Returns:
            str: The extracted text.

        Errors / Exceptions:
            - Raises ValueError if the format is unsupported or the filename is invalid.
            - Raises Exception for file read errors.
        """
        # Validate that the filename contains an extension.
        if not filename or "." not in filename:
            raise ValueError("Filename must include a valid extension")
        # Extract the extension suffix in lowercase.
        ext = filename.split(".")[-1].lower()

        try:
            # Route by file extension.
            if ext == "pdf":
                return self.extract_text_from_pdf(file_path)

            elif ext in ["jpg", "jpeg", "png"]:
                return self.extract_text_from_image(file_path)

            elif ext == "txt":
                # Open with UTF-8 encoding to prevent parsing failures on special characters.
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()

            elif ext == "docx":
                # Open the Microsoft Word document.
                doc = docx.Document(file_path)
                # Combine paragraph texts, filtering out empty entries.
                return "\n".join(
                    [para.text for para in doc.paragraphs if para.text.strip()]
                )

            elif ext == "csv":
                rows = []
                # Open the CSV file.
                with open(file_path, newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        # Format columns (e.g. "Col1 | Col2 | Col3") to help the LLM identify fields.
                        rows.append(" | ".join(row))
                # Return the combined CSV rows.
                return "\n".join(rows)

            elif ext in ["xlsx", "xls"]:
                import pandas as pd

                excel_file = pd.ExcelFile(file_path)
                sheet_texts = []
                for sheet in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    rows = []
                    rows.append(f"--- Sheet: {sheet} ---")
                    # Convert headers
                    headers = [str(c) for c in df.columns]
                    rows.append(" | ".join(headers))
                    # Convert rows
                    for _, row in df.iterrows():
                        row_vals = [str(val) for val in row.values]
                        rows.append(" | ".join(row_vals))
                    sheet_texts.append("\n".join(rows))
                return "\n\n".join(sheet_texts)

            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            raise Exception(f"Failed to read {ext} file: {str(e)}")

    def extract_text_from_url(self, url: str) -> str:
        """
        Scrapes text content from a web page URL.

        Parameters:
            url (str): The web page URL to scrape.

        Returns:
            str: Cleaned text content.

        Errors / Exceptions:
            - Raises Exception if request or scraping fails.
        """
        try:
            logger.info("🌐 Scraping URL: %s...", url)
            # Use a realistic User-Agent to bypass basic bot blockers.
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            # Fetch the page content. Timeout prevents hanging requests.
            response = requests.get(url, headers=headers, timeout=15)
            # Raise an error if the request returned a non-200 status code.
            response.raise_for_status()

            # Parse the HTML content.
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove structural, script, footer, header, and navigation tags.
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract clean visible text, inserting spaces to prevent words from merging.
            text = soup.get_text(separator=" ", strip=True)

            # Use regex to replace consecutive spaces, tabs, and newlines with a single space.
            clean_text = re.sub(r"\s+", " ", text)
            return clean_text

        except Exception as e:
            raise Exception(f"Failed to extract text from URL: {str(e)}")

    # ==========================================
    # 2. CUSTOM CHUNK ALGORITHMS
    # ==========================================

    def chunk_text_naive(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list:
        """
        Splits text by character count with a sliding window.

        Purpose:
            Simple chunking algorithm.
            Using an overlap preserves context at chunk boundaries.

        Parameters:
            text (str): Input text.
            chunk_size (int): Max character count per chunk.
            overlap (int): Overlap character count.

        Returns:
            list of str: Text chunks.
        """
        logger.info("Chunking text (Size: %s, Overlap: %s)...", chunk_size, overlap)
        chunks = []
        start = 0
        text_length = len(text)

        # Loop through the text by chunk_size minus overlap.
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap

        # Filter out empty chunks and return.
        return [c for c in chunks if c]

    def chunk_text_sentence(
        self, text: str, sentences_per_chunk: int = 6, overlap: int = 2
    ) -> list:
        """
        Splits text into chunks at sentence boundaries.

        Purpose:
            Groups complete sentences together, preserving semantic coherence.

        Parameters:
            text (str): Input text.
            sentences_per_chunk (int): Number of sentences per chunk.
            overlap (int): Number of overlapping sentences between chunks.

        Returns:
            list of str: Text chunks.
        """
        # Split text on punctuation followed by spaces and uppercase letters.
        # Negative lookbehinds prevent splitting on abbreviations (e.g. 'Mr.').
        sentences = re.split(
            r"(?<!\bMr)(?<!\bDr)(?<!\bMs)(?<!\bMrs)(?<!\bProf)(?<=[.!?])\s+(?=[A-Z])",
            text,
        )
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        i = 0
        # Group sentences into chunks with a sliding window.
        while i < len(sentences):
            chunk = " ".join(sentences[i : i + sentences_per_chunk])
            chunks.append(chunk)
            i += sentences_per_chunk - overlap

        # Filter out very small chunks.
        return [c for c in chunks if len(c) > 10]

    def chunk_text_paragraph(self, text: str, max_length: int = 1200) -> list:
        """
        Splits text on paragraph boundaries.

        Purpose:
            Keeps paragraphs together, combining consecutive paragraphs
            until they hit a maximum character limit.

        Parameters:
            text (str): Input text.
            max_length (int): Max character count per chunk.

        Returns:
            list of str: Text chunks.
        """
        # Split text on double newlines.
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        # Loop through paragraphs and combine them.
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # If adding this paragraph exceeds the limit, save the chunk and start a new one.
            if len(current_chunk) + len(para) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                # Add to the current chunk.
                current_chunk += "\n\n" + para if current_chunk else para

        # Append the last chunk if it contains data.
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    # ==========================================
    # 3. DIRECT VECTORIZATION (EMBEDDINGS)
    # ==========================================

    def vectorize(self, chunks: list, model_name: str = "all-MiniLM-L6-v2") -> list:
        """
        Converts text chunks into dense vector embeddings.
        Uses Cloudflare Workers AI or Hugging Face Serverless Inference API to prevent OOM errors on cloud hosts like Render.

        Parameters:
            chunks (list of str): Input text chunks.
            model_name (str): SentenceTransformer model name.

        Returns:
            list of list of float: Embeddings list.
        """
        logger.info("Generating vectors for %s chunks...", len(chunks))

        # 1. Try Cloudflare Workers AI if credentials are set
        cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        if cf_account_id and cf_api_token:
            logger.info("Using Cloudflare Workers AI for embeddings...")
            try:
                cf_model = "@cf/baai/bge-small-en-v1.5"
                cf_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{cf_model}"
                cf_headers = {"Authorization": f"Bearer {cf_api_token}"}
                response = requests.post(
                    cf_url, headers=cf_headers, json={"text": chunks}, timeout=30
                )
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("success") and "result" in res_json:
                        embeddings = res_json["result"]["data"]
                        # Ensure it is a 2D list of floats
                        if (
                            len(chunks) == 1
                            and embeddings
                            and not isinstance(embeddings[0], list)
                        ):
                            return [embeddings]
                        return embeddings
                logger.warning(
                    f"Cloudflare Workers AI failed with status {response.status_code}: {response.text}. Falling back to Hugging Face / Local."
                )
            except Exception as e:
                logger.error(
                    f"Error querying Cloudflare Workers AI API: {str(e)}. Falling back to Hugging Face / Local."
                )

        # 2. Fallback to Hugging Face Serverless Inference API
        # Standardize model name for Hugging Face
        hf_model = model_name
        if hf_model == "all-MiniLM-L6-v2":
            hf_model = "sentence-transformers/all-MiniLM-L6-v2"

        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{hf_model}"
        hf_token = (
            os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or ""
        ).strip()
        headers = {}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        try:
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": chunks, "options": {"wait_for_model": True}},
                timeout=30,
            )
            if response.status_code == 200:
                embeddings = response.json()
                # Ensure it is a list of lists of floats (sometimes Hugging Face returns a 1D list if only 1 input is sent)
                if (
                    len(chunks) == 1
                    and embeddings
                    and not isinstance(embeddings[0], list)
                ):
                    return [embeddings]
                return embeddings
            else:
                logger.warning(
                    f"Hugging Face cloud inference failed with status {response.status_code}: {response.text}. Falling back to local SentenceTransformer."
                )
        except Exception as e:
            logger.error(
                f"Error querying Hugging Face cloud embedding API: {str(e)}. Falling back to local SentenceTransformer."
            )

        # Raise an error if both Cloudflare and Hugging Face fail
        raise RuntimeError(
            "Cloud vectorization failed: Cloudflare and Hugging Face APIs are both unreachable or failed."
        )

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list,
        agent_id: str,
        top_k: int = 5,
    ) -> list:
        """
        Executes a native PostgreSQL vector similarity match utilizing pgvector,
        completely offloading the CPU-heavy NumPy cosine calculations to the database
        without blocking the async event loop.
        """
        from core.database import get_db_cursor_async
        from fastapi.concurrency import run_in_threadpool

        results = []
        try:
            async with get_db_cursor_async(commit=False) as cursor:
                await run_in_threadpool(
                    cursor.execute,
                    """
                    SELECT e.content, (1 - (e.embedding <=> %s::vector)) AS similarity
                    FROM document_embeddings e
                    JOIN documents d ON e.document_id = d.id
                    WHERE d.agent_id = %s
                    ORDER BY e.embedding <=> %s::vector ASC
                    LIMIT %s;
                    """,
                    (str(query_vector), agent_id, str(query_vector), top_k),
                )
                rows = await run_in_threadpool(cursor.fetchall)
                for idx, (content, score) in enumerate(rows):
                    results.append(
                        {"chunk_index": idx, "content": content, "score": float(score)}
                    )
        except Exception as e:
            logger.error(f"PostgreSQL pgvector hybrid search failed: {e}")

        return results

    def rerank_documents(
        self,
        query: str,
        documents: list,
        top_k: int = 5,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> list:
        """
        Reranks document chunks against a query using Cloudflare Workers AI or local CrossEncoder.

        Parameters:
            query (str): Query string.
            documents (list): Candidate documents (tuples/lists with text content at index 0).
            top_k (int): Number of results to return.
            model_name (str): CrossEncoder model name.

        Returns:
            list: Reranked documents.
        """
        if not documents:
            return []

        # Import decrypt_key to decrypt documents before scoring them.
        from core.security import decrypt_key

        # 1. Try Cloudflare Workers AI Reranker if credentials are set
        cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        if cf_account_id and cf_api_token:
            logger.info("Using Cloudflare Workers AI for reranking...")
            try:
                cf_model = "@cf/baai/bge-reranker-base"
                cf_url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account_id}/ai/run/{cf_model}"
                cf_headers = {"Authorization": f"Bearer {cf_api_token}"}

                query_str = str(query or "").strip()
                decrypted_docs = []
                for doc in documents:
                    if doc and len(doc) > 0:
                        val = decrypt_key(doc[0]) or doc[0] or ""
                        val = str(val).strip()
                        if val:
                            decrypted_docs.append(val)

                if not query_str or not decrypted_docs:
                    logger.warning("Query or documents are empty, skipping Cloudflare reranking.")
                    return documents[:top_k]

                cf_contexts = [{"text": doc} for doc in decrypted_docs]
                response = requests.post(
                    cf_url,
                    headers=cf_headers,
                    json={"query": query_str, "contexts": cf_contexts},
                    timeout=30
                )
                if response.status_code == 200:
                    res_json = response.json()
                    logger.info(f"Cloudflare Workers AI Reranker response: {res_json}")
                    if res_json.get("success") and "result" in res_json:
                        results = res_json["result"]
                        if isinstance(results, dict):
                            if "response" in results:
                                results = results["response"]
                            elif "data" in results:
                                results = results["data"]
                            elif "results" in results:
                                results = results["results"]
                        
                        if isinstance(results, list):
                            doc_scores = []
                            for item in results:
                                if isinstance(item, dict):
                                    idx = item.get("index") if item.get("index") is not None else item.get("id")
                                    score = item.get("score")
                                    if idx is not None and score is not None:
                                        doc_scores.append((documents[idx], score))
                                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                    idx = item[0]
                                    score = item[1]
                                    doc_scores.append((documents[idx], score))

                            doc_scores.sort(key=lambda x: x[1], reverse=True)
                            return [doc for doc, score in doc_scores[:top_k]]
                logger.warning(
                    f"Cloudflare Workers AI reranking failed with status {response.status_code}: {response.text}. Falling back to local/original order."
                )
            except Exception as e:
                logger.error(
                    f"Error querying Cloudflare Workers AI Reranker API: {str(e)}. Falling back to local/original order."
                )

        # 2. Fallback to local CrossEncoder model
        # Retrieve the CrossEncoder model.
        reranker = self._get_reranker_model(model_name)
        # Fallback if the model fails to load.
        if not reranker:
            logger.warning(
                "Reranker failed to load, falling back to original search order."
            )
            return documents[:top_k]

        logger.info(f"Reranking {len(documents)} chunks...")

        pairs = []
        # Prepare inputs for the CrossEncoder: [query, doc_text] pairs.
        for doc in documents:
            decrypted_text = decrypt_key(doc[0]) or doc[0]
            pairs.append([query, decrypted_text])

        # Generate relevance scores.
        scores = reranker.predict(pairs)

        # Pair documents with their scores.
        doc_scores = list(zip(documents, scores))

        # Sort documents by score in descending order.
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Return the sorted documents list.
        return [doc for doc, score in doc_scores[:top_k]]

    async def generate_hyde_query(self, query: str, llm) -> str:
        """
        Generates a Hypothetical Document Embeddings (HyDE) query expansion.

        Purpose:
            Uses an LLM to generate a hypothetical answer to the query.
            Vectorizing this answer can yield better retrieval results
            because it matches the semantic structure of document answers.

        Parameters:
            query (str): Original query.
            llm: Large Language Model instance.

        Returns:
            str: Original query appended with the hypothetical response.
        """
        logger.info("Generating HyDE query expansion...")
        prompt = f"""You are an expert answering questions. 
Please write a short, hypothetical answer to the following question. Do not include any explanations, just the factual answer.

Question: {query}
Answer:"""
        try:
            # Call the LLM to generate the hypothetical answer.
            response = await llm.ainvoke(prompt)
            content = response.content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(part["text"])
                    elif isinstance(part, str):
                        parts.append(part)
                    else:
                        parts.append(str(part))
                hypothetical_answer = "".join(parts).strip()
            else:
                hypothetical_answer = str(content).strip()
            # Combine the original query with the generated response.
            return f"{query}\n{hypothetical_answer}"
        except Exception as e:
            logger.error(f"HyDE generation failed: {e}")
            # Fall back to the original query if LLM generation fails.
            return query

    def apply_mmr(
        self,
        query: str,
        documents: list,
        top_k: int = 5,
        lambda_mult: float = 0.5,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> list:
        """
        Applies Maximal Marginal Relevance (MMR) to select diverse results.

        Purpose:
            Balances query relevance (similarity to query) with diversity
            (dissimilarity from already selected documents).
            This prevents returning repetitive chunks.

        Parameters:
            query (str): Query string.
            documents (list): Candidate documents (tuples/lists with text content at index 0).
            top_k (int): Number of results to return.
            lambda_mult (float): Relevance weight parameter (0.0 to 1.0).
            model_name (str): SentenceTransformer model name.

        Returns:
            list: Diverse subset of documents.
        """
        import numpy as np
        from core.security import decrypt_key

        if not documents:
            return []

        # If candidates count is less than top_k, no diversity filtering is needed.
        if len(documents) <= top_k:
            return documents

        logger.info(f"Applying MMR to {len(documents)} candidate chunks...")

        # 1. Extract and decrypt candidate text.
        texts = [decrypt_key(doc[0]) or doc[0] for doc in documents]

        # 2. Vectorize the query and all candidates.
        query_embedding = np.array(self.vectorize([query], model_name=model_name)[0])
        doc_embeddings = np.array(self.vectorize(texts, model_name=model_name))

        # Calculate magnitudes.
        q_norm = np.linalg.norm(query_embedding) or 1e-10
        doc_norms = np.linalg.norm(doc_embeddings, axis=1)
        doc_norms[doc_norms == 0] = 1e-10

        # Calculate Query-Document similarities.
        sim_to_query = np.dot(doc_embeddings, query_embedding) / (doc_norms * q_norm)

        # Calculate Document-Document similarity matrix.
        sim_matrix = np.dot(doc_embeddings, doc_embeddings.T)
        norm_matrix = np.outer(doc_norms, doc_norms)
        sim_matrix = sim_matrix / norm_matrix

        selected_indices = []
        unselected_indices = list(range(len(documents)))

        # 3. Iteratively select documents to maximize MMR.
        while len(selected_indices) < top_k and unselected_indices:
            if not selected_indices:
                # The first document selected is the one most relevant to the query.
                best_idx = unselected_indices[
                    np.argmax(sim_to_query[unselected_indices])
                ]
            else:
                best_idx = None
                max_mmr_score = -float("inf")

                # Calculate the MMR score for each unselected document.
                for idx in unselected_indices:
                    # Relevance value.
                    relevance = sim_to_query[idx]

                    # Redundancy value (max similarity to any already selected document).
                    redundancy = np.max(sim_matrix[idx, selected_indices])

                    # MMR Formula: lambda * relevance - (1 - lambda) * redundancy.
                    mmr_score = lambda_mult * relevance - (1 - lambda_mult) * redundancy

                    if mmr_score > max_mmr_score:
                        max_mmr_score = mmr_score
                        best_idx = idx

            # Add selected index and remove from candidate pool.
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)

        # Return documents at selected indices.
        return [documents[i] for i in selected_indices]
