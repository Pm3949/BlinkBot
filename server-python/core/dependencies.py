import os
import razorpay
from pathlib import Path
from custom_rag import CustomRAGEngine

# Initialize RAG Engine
rag_engine = CustomRAGEngine()
# Warm up the default embedding model for zero latency
rag_engine._get_model('all-MiniLM-L6-v2')

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
