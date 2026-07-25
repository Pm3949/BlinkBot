"""
================================================================================
GLOBAL SERVICES DEPENDENCIES AND LIFECYCLE MANAGEMENT (dependencies.py)
================================================================================

OVERVIEW & ARCHITECTURE:
This module acts as the dependency injection and initialization manager for the RAGMate application.
It pre-initializes heavy, long-lived resources once during application boot to avoid instantiating them on every
request. It handles:
1. Custom RAG Engine: Sets up `CustomRAGEngine` instance (`rag_engine`).
2. Concurrent Model Warmup: Loads heavy sentence transformer models and cross-encoders on a separate
   background thread. This prevents uvicorn live reloads and startup server checks from timing out during
   local development.
3. File Upload Storage Management: Guarantees the existence of the `temp_uploads` folder.
4. Payment Gateways Initialization: Conditionally constructs the Razorpay SDK client.

HOW THE SCRIPT WORKS FROM TOP TO BOTTOM:
1. Imports:
   - `os`: Fetching environment variables.
   - `razorpay`: Razorpay payment gateway integration SDK.
   - `logging`: System diagnostics.
   - `Path` (from `pathlib`): Cross-platform file path management.
   - `CustomRAGEngine`: The main interface for custom indexing and search execution.

2. Global Initializations:
   - Constructs the singleton `rag_engine` instance.
   - Defines and runs the background thread warmup process.
   - Sets up the `temp_uploads` directory.
   - Configures the Razorpay SDK parameters.
"""

import os
import razorpay
import logging
from pathlib import Path
from custom_rag import CustomRAGEngine

# Initialize standard module-level logger.
logger = logging.getLogger(__name__)


# ==========================================
# CORE ENGINE INITIALIZATION
# ==========================================
# Create a singleton instance of the custom Retrieval-Augmented Generation engine.
# This object manages connection pools, configuration properties, and model caches.
rag_engine = CustomRAGEngine()

def warm_up_models_background():
    """
    Loads large AI models in a background daemon thread during application startup.

    Purpose:
        Sentence transformers and cross-encoder models are several hundred megabytes in size
        and take time to load into RAM/VRAM. Loading them in a background thread keeps the
        main ASGI application process responsive, preventing startup timeouts or hot-reload
        delays in local environments.

    Parameters:
        None.

    Returns:
        None.

    Side Effects / State Changes:
        - Spawns a background thread.
        - Warm-loads the 'all-MiniLM-L6-v2' and 'cross-encoder/ms-marco-MiniLM-L-6-v2' models into memory caches.

    Errors / Exceptions:
        - Catches all model-loading exceptions, logging them to the terminal.
    """
    import threading
    
    # Internal target function executed by the background thread.
    def load():
        try:
            # Load the sentence transformer model used to create vector embeddings.
            logger.info("Concurrently loading embedding model 'all-MiniLM-L6-v2' in background...")
            rag_engine._get_model('all-MiniLM-L6-v2')
            
            # Load the cross-encoder model used for reranking search results.
            logger.info("Concurrently loading reranker model 'cross-encoder/ms-marco-MiniLM-L-6-v2' in background...")
            rag_engine._get_reranker_model('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            logger.info("Background model loading complete. System is fully warm!")
        except Exception as e:
            # Handle download or model loading errors without crashing the main application.
            logger.error(f"Failed to load models in background thread: {e}")

    # Create and start the daemon thread.
    # daemon=True ensures this thread terminates automatically when the main server process stops.
    threading.Thread(target=load, daemon=True).start()


# ==========================================
# DIRECTORY MANAGEMENT
# ==========================================
# Define and ensure the existence of a temporary directory for file uploads (PDFs, Audio, etc.)
# Using Path from pathlib ensures correct path formatting across operating systems.
UPLOAD_DIR = Path("temp_uploads")
# parents=True creates parent folders if missing.
# exist_ok=True prevents errors if the directory already exists.
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# PAYMENT GATEWAY (RAZORPAY)
# ==========================================
# Fetch credentials for the Razorpay payment gateway API.
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Conditionally initialize Razorpay.
# If credentials are not configured, the application runs normally but payment endpoints will remain disabled.
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    # Initialize the client.
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    # Set to None if credentials are not configured.
    razorpay_client = None

