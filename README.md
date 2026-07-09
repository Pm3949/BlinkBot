# 🚀 BlinkBot (formerly RAGMate)

BlinkBot is an enterprise-grade AI Assistant platform that allows teams to build, manage, and deploy custom Retrieval-Augmented Generation (RAG) agents. Train agents on your own custom documents, interact with them in isolated team workspaces, and seamlessly deploy them via embeddable chat widgets!

## ✨ Currently Implemented Features

### 🧠 Advanced AI & Agent Architectures
*   **Multi-Model Support**: Native support for OpenAI, Groq, and Ollama.
*   **Dynamic Multi-Agent Routing (Intent Orchestrator)**: A "Master Agent" intelligently orchestrates and routes user queries to specialized sub-agents based on the context.
*   **Real-Time Streaming**: Token-by-token WebSocket streaming for low-latency chat interactions across the dashboard and external widgets.
*   **Voice Capabilities**: Built-in Text-to-Speech (Google TTS) and Speech-to-Text (Groq Whisper API) for multimodal interactions.

### 📚 Enterprise-Grade RAG Engine
*   **Advanced Retrieval**: Utilizes `pgvector` for semantic search, enhanced natively with **HyDE** (Hypothetical Document Embeddings) and **Cross-Encoder Reranking** for maximum contextual accuracy.
*   **Multi-Source Ingestion**: Upload PDFs, TXTs, or directly scrape URLs (via native `/process-url` support). 
*   **Google Drive Integration**: Connect and import files directly from Google Drive via OAuth2.
*   **Real-Time Web Search**: Agents can dynamically execute tools to blend private vector knowledge with real-time web context via DuckDuckGo.
*   **Custom API Connections (Action Webhooks)**: Dedicated API Manager to configure external REST API endpoints, allowing agents to execute actions (like creating Jira tickets or sending emails) natively.

### 🏢 Team & Workspace Management
*   **Isolated Workspaces & RBAC**: Isolate agents, documents, and chat histories. Granular Role-Based Access Control (Admin, Editor, Teammate, Owner) enforced at the UI, API, and Database (RLS) levels.
*   **Real-Time Notifications**: Fully integrated WebSocket notification bell powered by Supabase Realtime.
*   **Developer API**: Users can generate API keys to query their RAG agents programmatically from external applications.
*   **User Analytics**: Dedicated dashboards to track agent performance, message quotas, and billing metrics.

## 🛠️ Technology Stack

**Frontend (Client)**
*   React 19 + Vite
*   Tailwind CSS + Radix UI + Framer Motion (Premium Glassmorphism UI)
*   Zustand (State) + TanStack Query (Data Fetching)

**Backend (Server)**
*   FastAPI (Python) + LangChain + LangGraph
*   Groq / OpenAI / Ollama (LLM inference)
*   BackgroundTasks & APScheduler for cron jobs and data cleanup

**Database**
*   Supabase (PostgreSQL) + `pgvector` + `pg_cron`
*   Row Level Security (RLS) for strict multi-tenant isolation

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

## 🗺️ Roadmap / What's Next

While BlinkBot is highly capable, here are the next high-impact features planned:
1. **Chat Exports**: Add functionality for users to download chat histories as beautifully formatted PDFs or Markdown.
2. **Expanded Data Connectors**: Expand beyond Google Drive to include Notion, Slack, Confluence, and GitHub integrations.
3. **GraphRAG / MMR**: Implement Maximal Marginal Relevance for more diverse document retrieval.
