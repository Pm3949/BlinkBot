"""
Global Dependencies & Initializations.
Responsibility: Acts as a central hub for instantiating heavy, shared resources 
like the RAG Engine and Payment Gateways. This ensures they are only loaded 
once when the server starts, rather than every time an API endpoint is hit.
"""
import os
import razorpay
import logging
from pathlib import Path
from custom_rag import CustomRAGEngine

logger = logging.getLogger(__name__)


# ==========================================
# CORE ENGINE INITIALIZATION
# ==========================================
# Initialize the custom Retrieval-Augmented Generation engine.
rag_engine = CustomRAGEngine()

def warm_up_models_background():
    """
    Background loading helper.
    Spins up a background daemon thread to load heavy embedding and reranker models.
    This prevents blocking server boot and uvicorn hot-reloads during development.
    """
    import threading
    
    def load():
        try:
            logger.info("Concurrently loading embedding model 'all-MiniLM-L6-v2' in background...")
            rag_engine._get_model('all-MiniLM-L6-v2')
            
            logger.info("Concurrently loading reranker model 'cross-encoder/ms-marco-MiniLM-L-6-v2' in background...")
            rag_engine._get_reranker_model('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            logger.info("Background model loading complete. System is fully warm!")
        except Exception as e:
            logger.error(f"Failed to load models in background thread: {e}")

    threading.Thread(target=load, daemon=True).start()


# ==========================================
# DIRECTORY MANAGEMENT
# ==========================================
# Define and ensure the existence of a temporary directory for file uploads (PDFs, Audio, etc.)
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# PAYMENT GATEWAY (RAZORPAY)
# ==========================================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Conditionally initialize Razorpay. If keys aren't present (e.g., in a local dev environment),
# the app won't crash, it just won't be able to process payments.
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
