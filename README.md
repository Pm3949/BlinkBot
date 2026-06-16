# 🚀 RAGMate

RAGMate is an enterprise-grade AI Assistant platform that allows teams to build, manage, and deploy custom Retrieval-Augmented Generation (RAG) agents. Train agents on your own custom documents, interact with them in isolated team workspaces, and seamlessly deploy them via embeddable chat widgets!

## ✨ Key Features

*   **🧠 Custom AI Agents**: Create specialized AI agents powered by OpenAI, Groq, or Ollama. Customize their system prompts, temperatures, and chunking strategies.
*   **📚 Retrieval-Augmented Generation (RAG)**: Upload PDFs and TXT files to give your agents highly-specific context. Powered by PostgreSQL `pgvector`.
*   **🌐 Real-Time Web Search**: Enable the Web Search toggle to allow agents to seamlessly blend private vector knowledge with real-time web context via DuckDuckGo.
*   **🏢 Team Workspaces & RBAC**: Isolate agents, documents, and chat histories by workspace. Invite teammates with granular Role-Based Access Control (Admin, Editor, Teammate, Owner).
*   **🔔 Enterprise Real-Time Notifications**: A fully integrated notification bell powered by Supabase WebSockets. Teammates are instantly notified without page reloads when feedback is submitted, tickets are resolved, or agent settings are updated. Includes automated database cleanup via `pg_cron`.
*   **💬 Embeddable Chat Widgets**: Generate snippets to embed your AI agents directly onto external websites.

---

## 🛠️ Technology Stack

**Frontend (Client)**
*   React + Vite
*   Tailwind CSS + Lucide Icons (Premium Glassmorphism UI)
*   Zustand (State Management)
*   React Query / TanStack Query (Data Fetching)
*   Supabase JS Client (Realtime WebSockets)

**Backend (Server)**
*   FastAPI (Python)
*   LangChain (LLM Orchestration)
*   Pydantic (Strict API Validation)

**Database**
*   Supabase (PostgreSQL)
*   `pgvector` (Vector Embeddings)
*   `pg_cron` (Automated cleanup jobs)
*   Row Level Security (RLS) for multi-tenant isolation

---

## 🚀 Getting Started

### 1. Database Setup
Ensure you have a Supabase project running with `pgvector` enabled. 
Make sure the `supabase_realtime` publication is active for the `notifications` table.

### 2. Backend (FastAPI)
```bash
cd server-python
pip install -r requirements.txt
# Set your environment variables in .env (OPENAI_API_KEY, GROQ_API_KEY, SUPABASE_DB_URL, etc.)
uvicorn main:app --reload --port 8000
```

### 3. Frontend (React)
```bash
cd client
npm install
# Set your environment variables in .env (VITE_API_BASE_URL, VITE_SUPABASE_URL, etc.)
npm run dev
```

---

## 🤝 Contribution

When contributing, ensure all notification types are strictly validated through the `NotificationType` Enum in the FastAPI backend schemas!
