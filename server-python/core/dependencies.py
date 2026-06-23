"""
Global Dependencies & Initializations.
Responsibility: Acts as a central hub for instantiating heavy, shared resources 
like the RAG Engine and Payment Gateways. This ensures they are only loaded 
once when the server starts, rather than every time an API endpoint is hit.
"""
import os
import razorpay
from pathlib import Path
from custom_rag import CustomRAGEngine

# ==========================================
# CORE ENGINE INITIALIZATION
# ==========================================
# Initialize the custom Retrieval-Augmented Generation engine.
rag_engine = CustomRAGEngine()

# Edge Case Handled: Cold Start Latency.
# Loading an embedding model into memory can take several seconds. If we wait until 
# the first user asks a question, that user will experience a lag spike.
# By forcing the engine to load the default model here, we "warm up" the cache,
# ensuring zero latency for the very first API request.
rag_engine._get_model('all-MiniLM-L6-v2')

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
