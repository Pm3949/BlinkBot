# server-python/main.py
import json
import logging
import os
import shutil
from pathlib import Path
import razorpay

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from schemas import InviteRequest

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from custom_rag import CustomRAGEngine
from database import get_db_connection
from schemas import ChatRequest, URLRequest, CheckoutRequest, RazorpayVerifyRequest, WidgetChatRequest

# --- LLM IMPORTS ---
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Custom RAGMate Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rag-mate-ashen.vercel.app/", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize RAG Engine
rag_engine = CustomRAGEngine()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

# ==========================================
# BACKGROUND TASKS
# ==========================================
def background_ingestion(document_id: int, agent_id: str, raw_text: str, strategy: str, embed_model: str, file_path: str = None):
    """Runs chunking + embedding in the background and updates document status."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.info("⚙️ Background task started for doc id: %s", document_id)

        if strategy == "naive":
            chunks = rag_engine.chunk_text_naive(raw_text)
        elif strategy == "paragraph":
            chunks = rag_engine.chunk_text_paragraph(raw_text)
        else:
            chunks = rag_engine.chunk_text_sentence(raw_text)

        if not chunks:
            raise ValueError("No chunks were produced from the uploaded content")

        vectors = rag_engine.vectorize(chunks, model_name=embed_model)

        for text, vector in zip(chunks, vectors):
            cursor.execute(
                "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
                (document_id, text, vector)
            )

        cursor.execute("UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,))
        conn.commit()
        logger.info("✅ Background task completed for doc id: %s", document_id)

    except Exception:
        logger.exception("Background ingestion failed for doc id %s", document_id)
        if conn and cursor:
            try:
                cursor.execute("UPDATE documents SET status = 'failed' WHERE id = %s", (document_id,))
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


def send_invite_email(to_email: str, workspace_name: str, invited_by: str, signup_url: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning("⚠️ SMTP settings are missing. Email not sent.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Invitation to join '{workspace_name}' workspace on RagMate"
        msg["From"] = f"RagMate Team <{smtp_user}>"
        msg["To"] = to_email

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <h2 style="color: #4f46e5; margin-bottom: 20px;">You are invited!</h2>
              <p>Hello,</p>
              <p><strong>{invited_by}</strong> has invited you to collaborate in the workspace <strong>{workspace_name}</strong> on RagMate.</p>
              <p>To accept this invitation and access the workspace, click the button below to sign up or log in:</p>
              <p style="text-align: center; margin: 30px 0;">
                <a href="{signup_url}" style="background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Accept Invitation</a>
              </p>
              <p style="font-size: 12px; color: #718096; margin-top: 30px;">
                If you did not expect this invitation, you can safely ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        
        logger.info(f"📧 Invite email sent successfully to {to_email}")
        return True
    except Exception:
        logger.exception(f"❌ Failed to send email to {to_email}")
        return False

def get_user_limits(user_id: str, cursor) -> dict:
    cursor.execute("SELECT plan_tier, limits FROM user_subscriptions WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    default_limits = {
        "agents": 1,
        "agent_messages": 1000,
        "storage_mb": 100,
        "chatbots": 0,
        "chatbot_messages": 0
    }
    if not row:
        return default_limits
    
    plan_tier, limits = row
    if plan_tier == "Pro":
        return { "agents": 5, "agent_messages": 10000, "storage_mb": 500, "chatbots": 2, "chatbot_messages": 5000 }
    elif plan_tier == "Enterprise":
        return { "agents": 20, "agent_messages": 100000, "storage_mb": 5000, "chatbots": 10, "chatbot_messages": 50000 }
    elif plan_tier == "Custom" and limits:
        return limits
    else:
        return default_limits


# ==========================================
# API ROUTES: DOCUMENTS & INGESTION
# ==========================================
# ==========================================
# API ROUTE: UPLOAD ANY FILE (.pdf, .txt, .docx, .csv)
# ==========================================
@app.post("/process-file")
async def process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), agent_id: str = Form(...)):
    """Upload a supported file, extract text, create a document row, and schedule ingestion."""
    allowed_exts = {"pdf", "txt", "docx", "csv"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(sorted(allowed_exts))} files are allowed.")

    safe_filename = os.path.basename(file.filename)
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s", (agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        # Check Storage Limit
        limits = get_user_limits(user_id, cursor)
        file_size = os.path.getsize(file_path)
        
        cursor.execute("""
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """, (user_id,))
        current_storage = cursor.fetchone()[0] or 0
        
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            os.remove(file_path)
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        raw_text = rag_engine.extract_text_from_file(str(file_path), safe_filename)

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (agent_id, safe_filename, file_size)
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(background_ingestion, document_id, agent_id, raw_text, strategy, embed_model, str(file_path))
        return {"message": f"{ext.upper()} uploaded successfully! Processing in background..."}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process uploaded file")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.post("/process-url")
async def process_url(req: URLRequest, background_tasks: BackgroundTasks):
    """Fetch a webpage, create a document row, and schedule ingestion."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, embedding_model, chunk_strategy FROM agents WHERE id = %s", (req.agent_id,))
        agent_row = cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id = agent_row[0]
        embed_model = agent_row[1] if agent_row[1] else "text-embedding-3-small"
        strategy = agent_row[2] if agent_row[2] else "sentence"

        raw_text = rag_engine.extract_text_from_url(req.url)
        file_size = len(raw_text.encode('utf-8'))

        # Check Storage Limit
        limits = get_user_limits(user_id, cursor)
        cursor.execute("""
            SELECT COALESCE(SUM(d.file_size_bytes), 0)
            FROM documents d
            JOIN agents a ON d.agent_id = a.id
            WHERE a.user_id = %s
        """, (user_id,))
        current_storage = cursor.fetchone()[0] or 0
        
        if current_storage + file_size > (limits["storage_mb"] * 1024 * 1024):
            raise HTTPException(status_code=403, detail="Storage limit exceeded. Please upgrade your plan.")

        cursor.execute(
            "INSERT INTO documents (agent_id, filename, status, file_size_bytes) VALUES (%s, %s, 'processing', %s) RETURNING id;",
            (req.agent_id, req.url, file_size)
        )
        document_id = cursor.fetchone()[0]
        conn.commit()

        background_tasks.add_task(background_ingestion, document_id, req.agent_id, raw_text, strategy, embed_model, None)
        return {"message": "URL scraped. Processing in background..."}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Failed to process URL")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/agents/{agent_id}/documents")
async def get_documents(agent_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT d.id, d.filename, d.status, d.created_at, d.file_size_bytes, COUNT(e.id) as chunk_count
            FROM documents d
            LEFT JOIN document_embeddings e ON d.id = e.document_id
            WHERE d.agent_id = %s 
            GROUP BY d.id
            ORDER BY d.created_at DESC
        """, (agent_id,))
        docs = [{
            "id": r[0], 
            "filename": r[1], 
            "status": r[2], 
            "created_at": r[3],
            "file_size_bytes": r[4] or 0,
            "chunk_count": r[5] or 0
        } for r in cursor.fetchall()]
        return {"documents": docs}
    finally:
        cursor.close()
        conn.close()

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        return {"message": "Document and its memory completely deleted!"}
    finally:
        cursor.close()
        conn.close()

# ==========================================
# API ROUTES: ANALYTICS
# ==========================================
@app.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Top Level Metrics
        cursor.execute("SELECT COUNT(*) FROM agents WHERE user_id = %s", (user_id,))
        total_agents = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) 
            FROM documents d JOIN agents a ON d.agent_id = a.id WHERE a.user_id = %s
        """, (user_id,))
        doc_stats = cursor.fetchone()
        total_docs = doc_stats[0] or 0
        total_storage_mb = (doc_stats[1] or 0) / (1024 * 1024)

        cursor.execute("""
            SELECT COALESCE(SUM(message_count), 0) FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE a.user_id = %s
        """, (user_id,))
        total_widget_msgs = cursor.fetchone()[0] or 0

        # 2. Internal Message Time Series (Last 30 days)
        cursor.execute("""
            SELECT date_trunc('day', m.created_at)::date AS day, count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND m.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
        """, (user_id,))
        internal_series = [{"date": str(r[0]), "messages": r[1]} for r in cursor.fetchall()]

        # 3. Widget Message Time Series (Last 30 days)
        cursor.execute("""
            SELECT date_trunc('day', l.created_at)::date AS day, count(*) 
            FROM widget_message_logs l
            JOIN chatbots c ON l.chatbot_id = c.id
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s 
            AND l.created_at >= current_date - interval '30 days'
            GROUP BY day ORDER BY day ASC
        """, (user_id,))
        widget_series = [{"date": str(r[0]), "messages": r[1]} for r in cursor.fetchall()]

        # 4. Top Chatbots
        cursor.execute("""
            SELECT c.settings->>'name' as name, c.message_count 
            FROM chatbots c JOIN agents a ON c.agent_id = a.id 
            WHERE a.user_id = %s 
            ORDER BY c.message_count DESC LIMIT 5
        """, (user_id,))
        top_chatbots = [{"name": r[0] or "Unnamed Chatbot", "messages": r[1]} for r in cursor.fetchall()]

        return {
            "metrics": {
                "totalAgents": total_agents,
                "totalDocuments": total_docs,
                "storageUsedMB": round(total_storage_mb, 2),
                "totalWidgetMessages": total_widget_msgs
            },
            "internalSeries": internal_series,
            "widgetSeries": widget_series,
            "topChatbots": top_chatbots
        }
    except Exception as e:
        logger.exception("Failed to fetch analytics")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ==========================================
# API ROUTES: SUPER ADMIN
# ==========================================
def check_super_admin(user_id: str, cursor):
    cursor.execute("SELECT is_super_admin FROM user_subscriptions WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="Super Admin access required")

@app.get("/admin/stats")
async def get_admin_stats(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute("SELECT COUNT(*) FROM auth.users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM workspaces")
        total_workspaces = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM agents")
        total_agents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chatbots")
        total_chatbots = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM documents")
        total_storage_mb = (cursor.fetchone()[0] or 0) / (1024 * 1024)

        return {
            "totalUsers": total_users,
            "totalWorkspaces": total_workspaces,
            "totalAgents": total_agents,
            "totalChatbots": total_chatbots,
            "totalStorageMB": round(total_storage_mb, 2)
        }
    except Exception as e:
        logger.exception("Failed to fetch admin stats")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.get("/admin/users")
async def get_admin_users(user_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(user_id, cursor)

        cursor.execute("""
            SELECT u.id, u.email, u.created_at, s.plan_tier, s.limits, s.is_super_admin
            FROM auth.users u
            LEFT JOIN user_subscriptions s ON u.id = s.user_id
            ORDER BY u.created_at DESC
        """)
        users = []
        for r in cursor.fetchall():
            users.append({
                "id": r[0],
                "email": r[1],
                "created_at": r[2],
                "plan_tier": r[3] or "Starter",
                "limits": r[4] or {},
                "is_super_admin": bool(r[5])
            })
        return {"users": users}
    except Exception as e:
        logger.exception("Failed to fetch admin users")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

class UpdateSubscriptionRequest(BaseModel):
    plan_tier: str
    admin_user_id: str

@app.post("/admin/users/{target_user_id}/subscription")
async def update_user_subscription(target_user_id: str, req: UpdateSubscriptionRequest):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        check_super_admin(req.admin_user_id, cursor)

        cursor.execute("""
            INSERT INTO user_subscriptions (user_id, plan_tier)
            VALUES (%s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET plan_tier = EXCLUDED.plan_tier, updated_at = now()
        """, (target_user_id, req.plan_tier))
        conn.commit()
        return {"message": "Subscription updated successfully"}
    except Exception as e:
        if conn: conn.rollback()
        logger.exception("Failed to update user subscription")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ==========================================
# API ROUTES: BILLING (RAZORPAY)
# ==========================================
@app.post("/create-razorpay-order")
async def create_razorpay_order(req: CheckoutRequest):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")
        
    if req.plan_tier == "Pro":
        monthly_total = 1900
        final_amount = (monthly_total * 12) * 0.8 if req.billing_cycle == 'annually' else monthly_total
    elif req.plan_tier == "Enterprise":
        monthly_total = 9900
        final_amount = (monthly_total * 12) * 0.8 if req.billing_cycle == 'annually' else monthly_total
    else:
        # Dynamic Pricing Formula (INR) for "Custom"
        base_price = 800
        agents_price = req.agents_limit * 400
        agent_msg_price = (req.agent_messages_limit / 1000.0) * 160
        storage_price = (req.storage_mb_limit / 100.0) * 50
        chatbots_price = req.chatbots_limit * 800
        chatbot_msg_price = (req.chatbot_messages_limit / 1000.0) * 200
        
        monthly_total = base_price + agents_price + agent_msg_price + storage_price + chatbots_price + chatbot_msg_price
        final_amount = (monthly_total * 12) * 0.8 if req.billing_cycle == 'annually' else monthly_total
        
    amount = int(final_amount * 100) # Razorpay expects paise
    
    try:
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{req.user_id[:8]}",
            "notes": {
                "user_id": req.user_id,
                "plan_tier": req.plan_tier,
                "billing_cycle": req.billing_cycle
            }
        })
        return {"order_id": order["id"], "amount": amount, "currency": "INR", "key": RAZORPAY_KEY_ID}
    except Exception as e:
        logger.exception("Razorpay order creation failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/razorpay/verify")
async def verify_razorpay_payment(req: RazorpayVerifyRequest):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay keys not configured")
        
    try:
        # Verify Signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        })
        
        # If no exception thrown, signature is valid.
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            limits_json = json.dumps({
                "agents": req.agents_limit,
                "agent_messages": req.agent_messages_limit,
                "storage_mb": req.storage_mb_limit,
                "chatbots": req.chatbots_limit,
                "chatbot_messages": req.chatbot_messages_limit
            })
            
            cursor.execute("""
                INSERT INTO user_subscriptions (user_id, plan_tier, billing_cycle, status, limits, updated_at)
                VALUES (%s, %s, %s, 'active', %s::jsonb, now())
                ON CONFLICT (user_id) DO UPDATE 
                SET plan_tier = EXCLUDED.plan_tier,
                    billing_cycle = EXCLUDED.billing_cycle,
                    status = 'active',
                    limits = EXCLUDED.limits,
                    updated_at = now();
            """, (req.user_id, req.plan_tier, req.billing_cycle, limits_json))
            conn.commit()
            logger.info(f"Subscription updated for user {req.user_id}")
        except Exception as e:
            logger.exception("Failed to update subscription in DB")
            raise HTTPException(status_code=500, detail="Database error during subscription update")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
        return {"status": "success"}
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# API ROUTES: CHAT & AGENTS
# ==========================================
@app.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """Stream an LLM response grounded in the uploaded documents."""
    if not req.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s",
            (req.agent_id,)
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")

        user_id, agent_name, system_prompt, provider, model, custom_api_key, embed_model = agent_data
        embed_model = embed_model or "text-embedding-3-small"

        # Check Message Limits
        limits = get_user_limits(user_id, cursor)
        cursor.execute("""
            SELECT count(*) 
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            JOIN agents a ON s.agent_id = a.id
            WHERE a.user_id = %s AND m.role = 'user' 
            AND date_trunc('month', m.created_at) = date_trunc('month', current_date)
        """, (user_id,))
        current_msg_count = cursor.fetchone()[0] or 0
        if current_msg_count >= limits["agent_messages"]:
            raise HTTPException(status_code=403, detail="Monthly message limit exceeded. Please upgrade your plan.")

        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        cursor.execute("""
            SELECT de.content, de.embedding
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = %s
        """, (req.agent_id,))
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [json.loads(row[1]) if isinstance(row[1], str) else row[1] for row in rows]

            query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=10,
            )

            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        prompt = f"""{system_prompt}
        You are a strict, professional AI assistant grounded ONLY in the provided documents.

        CRITICAL RULES:
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
        3. Format response beautifully in Markdown.
        4. Use the PREVIOUS CHAT HISTORY to understand context.
        5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
        6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {req.message}
        """

        async def stream_generator():
            try:
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Chat endpoint failed")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.post("/api/widget/chat")
async def widget_chat(req: WidgetChatRequest):
    """Stateless chat endpoint for external widgets."""
    if not req.chatbot_id:
        raise HTTPException(status_code=400, detail="chatbot_id is required")
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Get the agent_id linked to this chatbot
        cursor.execute("SELECT c.agent_id, c.settings, c.message_count, a.user_id FROM chatbots c JOIN agents a ON c.agent_id = a.id WHERE c.id = %s", (req.chatbot_id,))
        chatbot_data = cursor.fetchone()
        if not chatbot_data:
            raise HTTPException(status_code=404, detail="Chatbot not found")
        
        agent_id, settings, message_count, user_id = chatbot_data
        settings = settings or {}

        # Check Chatbot Message Limit
        limits = get_user_limits(user_id, cursor)
        cursor.execute("""
            SELECT COALESCE(SUM(message_count), 0)
            FROM chatbots c
            JOIN agents a ON c.agent_id = a.id
            WHERE a.user_id = %s
        """, (user_id,))
        total_widget_msgs = cursor.fetchone()[0] or 0
        if total_widget_msgs >= limits["chatbot_messages"]:
            raise HTTPException(status_code=403, detail="Monthly widget message limit exceeded. Please upgrade your plan.")

        # Increment widget message count and log it
        cursor.execute("UPDATE chatbots SET message_count = message_count + 1 WHERE id = %s", (req.chatbot_id,))
        cursor.execute("INSERT INTO widget_message_logs (chatbot_id) VALUES (%s)", (req.chatbot_id,))
        conn.commit()

        # 2. Get the agent config
        cursor.execute(
            "SELECT name, system_prompt, provider, model, api_key, embedding_model FROM agents WHERE id = %s",
            (agent_id,)
        )
        agent_data = cursor.fetchone()
        if not agent_data:
            raise HTTPException(status_code=404, detail="Underlying Agent not found")

        agent_name, system_prompt, provider, model, custom_api_key, embed_model = agent_data
        embed_model = embed_model or "text-embedding-3-small"

        # 3. Setup LLM
        if provider == "openai":
            key_to_use = custom_api_key or os.getenv("OPENAI_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
            llm = ChatOpenAI(model_name=model, api_key=key_to_use)
        else:
            key_to_use = custom_api_key or os.getenv("GROQ_API_KEY")
            if not key_to_use:
                raise HTTPException(status_code=400, detail="Groq API Key missing.")
            llm = ChatGroq(model_name=model, api_key=key_to_use)

        # 4. Fetch RAG Context
        cursor.execute("""
            SELECT de.content, de.embedding
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            WHERE d.agent_id = %s
        """, (agent_id,))
        rows = cursor.fetchall()

        context = "No specific documents found."
        if rows:
            doc_chunks = [row[0] for row in rows]
            doc_vectors = [json.loads(row[1]) if isinstance(row[1], str) else row[1] for row in rows]

            query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
            top_matches = rag_engine.hybrid_search(
                query_text=req.message,
                query_vector=query_vector,
                document_texts=doc_chunks,
                document_vectors=doc_vectors,
                alpha=0.7,
                top_k=10,
            )

            best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
            context = "\n\n---\n\n".join(best_chunks)

        # 5. Format Chat History (Stateless)
        history_items = req.history or []
        history_text = ""
        for msg in history_items[-6:]:
            role_name = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role_name}: {msg.get('content', '')}\n"
        if not history_text:
            history_text = "No previous conversation."

        # 6. Build Prompt
        prompt = f"""{system_prompt}
        You are a helpful customer support widget. You MUST answer the user's question based ONLY on the provided documents.

        CRITICAL RULES:
        1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
        2. If the answer is NOT in the context, DO NOT use general knowledge. Reply exactly: "I'm sorry, I cannot answer that based on the available information."
        3. Keep your answers relatively concise, as this is a chat widget. Format with Markdown if needed.

        CONTEXT DOCUMENTS:
        {context}

        PREVIOUS CHAT HISTORY:
        {history_text}

        CURRENT USER INPUT: {req.message}
        """

        async def stream_generator():
            try:
                for chunk in llm.stream(prompt):
                    if chunk.content:
                        yield chunk.content
            except Exception as exc:
                logger.exception("Streaming generation failed")
                yield f"\n\n⚠️ Error during generation: {str(exc)}"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as exc:
        logger.exception("Widget Chat endpoint failed")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM document_embeddings
            WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
        """,
        (agent_id,))
        cursor.execute("DELETE FROM documents WHERE agent_id = %s", (agent_id,))
        cursor.execute("""
            DELETE FROM chat_messages 
            WHERE session_id IN (SELECT id FROM chat_sessions WHERE agent_id = %s)
        """, 
        (agent_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE agent_id = %s", (agent_id,))
        cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        conn.commit()
        return {"message": "Agent and all its memory completely wiped!"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.delete("/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM widget_message_logs WHERE chatbot_id = %s", (chatbot_id,))
        cursor.execute("DELETE FROM chatbots WHERE id = %s", (chatbot_id,))
        conn.commit()
        return {"message": "Chatbot deleted successfully!"}
    except Exception as exc:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.post("/api/workspaces/invite")
async def invite_workspace_member(req: InviteRequest):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if member already exists in the workspace
        cursor.execute(
            "SELECT id FROM workspace_members WHERE workspace_id = %s AND email = %s",
            (req.workspace_id, req.email)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User is already invited or is a member of this workspace.")

        # Insert placeholder record
        cursor.execute(
            """
            INSERT INTO workspace_members (workspace_id, email, name, role, permissions)
            VALUES (%s, %s, %s, %s, '{"agents": false, "database": false, "notes": false}'::jsonb)
            RETURNING id;
            """,
            (req.workspace_id, req.email, req.email.split("@")[0], req.role)
        )
        conn.commit()

        # Send Real Email (Redirect user to local frontend dashboard or login page)
        signup_url = f"http://localhost:5173/login?email={req.email}&invite=true"
        send_invite_email(
            to_email=req.email,
            workspace_name=req.workspace_name,
            invited_by=req.invited_by_name,
            signup_url=signup_url
        )

        return {"message": "Invitation sent successfully!"}
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Modular RAGMate Server on Port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# # server-python/main.py
# import os
# import json
# import shutil
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request    
# from fastapi.responses import StreamingResponse
# from fastapi.middleware.cors import CORSMiddleware
# from schemas import ChatRequest, URLRequest

# # --- CUSTOM MODULES IMPORT ---
# from database import get_db_connection
# from schemas import ChatRequest, URLRequest
# from custom_rag import CustomRAGEngine 

# # --- LLM IMPORTS ---
# from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI

# app = FastAPI(title="Custom RAGMate Backend")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "temp_uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # Initialize RAG Engine
# rag_engine = CustomRAGEngine()

# # ==========================================
# # BACKGROUND TASKS
# # ==========================================
# def background_ingestion(document_id: int, agent_id: str, raw_text: str, strategy: str, embed_model: str, file_path: str = None):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         print(f"⚙️ Background Task Started for Doc ID: {document_id}")
        
#         if strategy == "naive": chunks = rag_engine.chunk_text_naive(raw_text)
#         elif strategy == "paragraph": chunks = rag_engine.chunk_text_paragraph(raw_text)
#         else: chunks = rag_engine.chunk_text_sentence(raw_text)
        
#         vectors = rag_engine.vectorize(chunks, model_name=embed_model)
        
#         for text, vector in zip(chunks, vectors):
#             cursor.execute(
#                 "INSERT INTO document_embeddings (document_id, content, embedding) VALUES (%s, %s, %s::vector);",
#                 (document_id, text, vector)
#             )
            
#         cursor.execute("UPDATE documents SET status = 'completed' WHERE id = %s", (document_id,))
#         conn.commit()
#         print(f"✅ Background Task Completed for Doc ID: {document_id}")

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         if conn: 
#             cursor = conn.cursor()
#             cursor.execute("UPDATE documents SET status = 'failed' WHERE id = %s", (document_id,))
#             conn.commit()
#     finally:
#         if conn: conn.close()
#         if file_path and os.path.exists(file_path): 
#             os.remove(file_path)

# # ==========================================
# # API ROUTES: DOCUMENTS & INGESTION
# # ==========================================
# # ==========================================
# # API ROUTE: UPLOAD ANY FILE (.pdf, .txt, .docx, .csv)
# # ==========================================
# @app.post("/process-file") # Route name changed
# async def process_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), agent_id: str = Form(...)):
    
#     # Check allowed extensions
#     allowed_exts = ['pdf', 'txt', 'docx', 'csv']
#     ext = file.filename.split('.')[-1].lower()
    
#     if ext not in allowed_exts:
#         raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_exts)} files are allowed.")
        
#     file_path = os.path.join(UPLOAD_DIR, file.filename)
    
#     with open(file_path, "wb") as buffer: 
#         shutil.copyfileobj(file.file, buffer)
        
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT embedding_model, chunking_strategy FROM agents WHERE id = %s", (agent_id,))
#         agent_row = cursor.fetchone()
#         embed_model = agent_row[0] if agent_row and agent_row[0] else "all-MiniLM-L6-v2"
#         strategy = agent_row[1] if agent_row and agent_row[1] else "sentence"
        
#         # Call the new Universal Extractor
#         raw_text = rag_engine.extract_text_from_file(file_path, file.filename)
        
#         cursor.execute(
#             "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
#             (agent_id, file.filename)
#         )
#         document_id = cursor.fetchone()[0]
#         conn.commit()
        
#         background_tasks.add_task(background_ingestion, document_id, agent_id, raw_text, strategy, embed_model, file_path)
#         return {"message": f"{ext.upper()} uploaded successfully! Processing in background..."}
#     finally:
#         conn.close()

# @app.post("/process-url")
# async def process_url(req: URLRequest, background_tasks: BackgroundTasks):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT embedding_model, chunking_strategy FROM agents WHERE id = %s", (req.agent_id,))
#         agent_row = cursor.fetchone()
#         embed_model = agent_row[0] if agent_row and agent_row[0] else "all-MiniLM-L6-v2"
#         strategy = agent_row[1] if agent_row and agent_row[1] else "sentence"
        
#         raw_text = rag_engine.extract_text_from_url(req.url)
        
#         cursor.execute(
#             "INSERT INTO documents (agent_id, filename, status) VALUES (%s, %s, 'processing') RETURNING id;",
#             (req.agent_id, req.url)
#         )
#         document_id = cursor.fetchone()[0]
#         conn.commit()
        
#         background_tasks.add_task(background_ingestion, document_id, req.agent_id, raw_text, strategy, embed_model, None)
#         return {"message": "URL scraped. Processing in background..."}
#     finally:
#         conn.close()

# @app.get("/agents/{agent_id}/documents")
# async def get_documents(agent_id: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT id, filename, status, created_at FROM documents WHERE agent_id = %s ORDER BY created_at DESC", (agent_id,))
#         docs = [{"id": r[0], "filename": r[1], "status": r[2], "created_at": r[3]} for r in cursor.fetchall()]
#         return {"documents": docs}
#     finally:
#         conn.close()

# @app.delete("/documents/{doc_id}")
# async def delete_document(doc_id: str):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("DELETE FROM document_embeddings WHERE document_id = %s", (doc_id,))
#         cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
#         conn.commit()
#         return {"message": "Document and its memory completely deleted!"}
#     finally:
#         conn.close()

# # ==========================================
# # API ROUTES: CHAT & AGENTS
# # ==========================================
# @app.post("/chat")
# async def chat_with_agent(req: ChatRequest):
#     # Agar frontend se khali request aayi hai (invalid data), toh yahan se return kar do
#     if not req.agent_id or not req.message:
#         return {"status": "ignored", "message": "Invalid request payload"}

#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         cursor.execute(
#             "SELECT name, system_prompt, llm_provider, llm_model, api_key, embedding_model FROM agents WHERE id = %s", 
#             (req.agent_id,) 
#         )
#         agent_data = cursor.fetchone()
#         if not agent_data: raise HTTPException(status_code=404, detail="Agent not found")
        
#         agent_name, system_prompt, llm_provider, llm_model, custom_api_key, embed_model = agent_data
#         if not embed_model: embed_model = "all-MiniLM-L6-v2"

#         if llm_provider == 'openai':
#             key_to_use = custom_api_key if custom_api_key else os.getenv("OPENAI_API_KEY")
#             if not key_to_use: raise HTTPException(status_code=400, detail="OpenAI API Key missing.")
#             llm = ChatOpenAI(model_name=llm_model, api_key=key_to_use)
#         else:
#             key_to_use = custom_api_key if custom_api_key else os.getenv("GROQ_API_KEY")
#             if not key_to_use: raise HTTPException(status_code=400, detail="Groq API Key missing.")
#             llm = ChatGroq(model_name=llm_model, api_key=key_to_use)

#         cursor.execute("""
#             SELECT de.content, de.embedding 
#             FROM document_embeddings de
#             JOIN documents d ON de.document_id = d.id
#             WHERE d.agent_id = %s
#         """, (req.agent_id,))
#         rows = cursor.fetchall()
        
#         context = "No specific documents found."
        
#         if rows:
#             doc_chunks = [row[0] for row in rows]
#             doc_vectors = [json.loads(row[1]) if isinstance(row[1], str) else row[1] for row in rows]
            
#             query_vector = rag_engine.vectorize([req.message], model_name=embed_model)[0]
#             top_matches = rag_engine.hybrid_search(
#                 query_text=req.message, query_vector=query_vector,
#                 document_texts=doc_chunks, document_vectors=doc_vectors,
#                 alpha=0.7, top_k=10
#             )
            
#             best_chunks = [doc_chunks[match["chunk_index"]] for match in top_matches]
#             context = "\n\n---\n\n".join(best_chunks)

#         history_text = ""
#         for msg in req.history[-6:]: 
#             role_name = "User" if msg["role"] == "user" else "Assistant"
#             history_text += f"{role_name}: {msg['content']}\n"
#         if not history_text: history_text = "No previous conversation."

#         cursor.close()
#         conn.close()
#         conn = None 

#         prompt = f"""{system_prompt}
#         You are a strict, professional AI assistant grounded ONLY in the provided documents. 

#         CRITICAL RULES:
#         1. For factual questions, ONLY answer using the provided CONTEXT DOCUMENTS.
#         2. If the answer is NOT in the context, DO NOT use general knowledge. Reply EXACTLY: "I'm sorry, but I can only answer questions based on the uploaded documents."
#         3. Format response beautifully in Markdown.
#         4. Use the PREVIOUS CHAT HISTORY to understand context.
#         5. CHIT-CHAT RULE: For casual greetings, respond naturally in 1-2 sentences.
#         6. DETAIL RULE: For summaries/essays, provide highly detailed answers.

#         CONTEXT DOCUMENTS:
#         {context}

#         PREVIOUS CHAT HISTORY:
#         {history_text}

#         CURRENT USER INPUT: {req.message}
#         """

#         async def stream_generator():
#             try:
#                 for chunk in llm.stream(prompt):
#                     if chunk.content:
#                         yield chunk.content
#             except Exception as e:
#                 yield f"\n\n⚠️ Error during generation: {str(e)}"

#         return StreamingResponse(stream_generator(), media_type="text/plain")

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         if conn: conn.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         if conn: conn.close()

# @app.delete("/agents/{agent_id}")
# async def delete_agent(agent_id: str):
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("""
#             DELETE FROM document_embeddings 
#             WHERE document_id IN (SELECT id FROM documents WHERE agent_id = %s)
#         """, (agent_id,))
#         cursor.execute("DELETE FROM documents WHERE agent_id = %s", (agent_id,))
#         cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
#         conn.commit()
#         return {"message": "Agent and all its memory completely wiped!"}
#     except Exception as e:
#         if conn: conn.rollback()
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         if conn: conn.close()

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting Modular RAGMate Server on Port 8000...")
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
