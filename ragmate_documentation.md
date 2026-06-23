# BlinkBot (formerly RAGMate) Comprehensive Documentation

This document provides a deep, granular analysis of the BlinkBot platform based on the source code, database schemas, and architectural patterns found in the repository.

---

## 1. Product Requirement Document (PRD)

### 1.1 Core Problem Statement
Enterprises and teams need a streamlined, secure way to build and deploy specialized Retrieval-Augmented Generation (RAG) AI agents. Organizations struggle to deploy generative AI tailored to their private knowledge bases without risking data leakage, lacking granular access control, or dealing with the engineering overhead of orchestrating various LLM providers, embedding models, and deployment workflows.

### 1.2 Target Audience
- **Enterprise Administrators & IT Teams**: Needing secure, isolated workspaces for different departments.
- **Business Operations & Sales Teams**: Requiring AI agents that can route queries and fetch real-time data.
- **Customer Support Teams**: Deploying agents that reference internal company documents (e.g., return policies, manuals) to answer support tickets accurately.
- **Individual Creators**: Building interactive personal portfolio assistants.

### 1.3 Detailed Use Cases & Examples (Derived from Codebase)
- **VendorVerse Navigator (Hierarchical Agent Network)**: A multi-tiered system where an "Intent Orchestrator" agent routes customer queries to specific supervisors (Sales Manager vs. Support Manager). These supervisors deploy sub-agents equipped with specialized tools (e.g., Live Inventory Checker, Delivery Tracker API, Pricing Negotiator) to handle complex, multi-step customer interactions.
- **Personal Portfolio Assistant**: A single-agent deployment configured to parse a user's uploaded CV and project data, allowing recruiters to dynamically query an applicant's skills and experience.

### 1.4 Core Platform Features
- **LLM Agnosticism**: Built-in support for OpenAI, Groq, and Gemini, allowing users to select their preferred model (e.g., `llama-3.3-70b-versatile` on Groq).
- **Advanced RAG Engine**: Native `pgvector` integration for highly accurate semantic search over uploaded PDFs and TXT files, with configurable chunking strategies (sentence vs. paragraph) and embedding models (e.g., `all-MiniLM-L6-v2`).
- **Real-Time Web Augmentation**: An integrated toggle allowing the agent to fetch live data via DuckDuckGo, blending static vector knowledge with real-time internet context.
- **Team Workspaces & RBAC**: Highly isolated workspaces where owners can invite members and assign roles (Admin, Member, Viewer) with granular feature toggles.
- **Embeddable Chat Widgets**: Generates dynamic Javascript snippets allowing users to deploy their specialized BlinkBot agents directly onto external websites.
- **Enterprise Notification System**: WebSocket-driven (Supabase Realtime) activity feeds and alerts.

---

## 2. Technical Requirement Document (TRD)

### 2.1 Frontend Architecture (Client & Admin)
- **Framework**: React 19 + Vite.
- **Styling & UI Library**: 
  - Tailwind CSS for utility-first styling.
  - Radix UI primitives (`@radix-ui/react-dialog`, `select`, `switch`) for accessible, unstyled component foundations.
  - Framer Motion for premium micro-animations and page transitions.
  - Lucide React for consistent iconography.
- **State Management**: 
  - **Zustand**: For global, synchronous client state (e.g., `useUIStore`, `useAgentStore`).
  - **TanStack React Query**: For asynchronous server state caching, pagination, and cache invalidation.
- **Routing**: React Router DOM (v7) implementing strict Protected, Role-based, and Permission-based layout wrappers.

### 2.2 Backend Architecture (Server)
- **Framework**: FastAPI (Python 3.x), utilizing asynchronous endpoints for high concurrency.
- **Modular Routers**: The backend is divided into specialized routers located in the `routers/` directory: `agents.py`, `auth.py`, `chat.py`, `chatbots.py`, `documents.py`, `workspaces.py`, `analytics.py`, etc.
- **AI/ML Integration**: 
  - **LangChain**: Orchestrates LLM chains, tool usage, and prompt templates.
  - **Sentence Transformers**: Generates local vector embeddings for document chunks.
- **Audio Processing**:
  - Speech-to-Text (STT): Utilizes Groq's Whisper API (`whisper-large-v3`).
  - Text-to-Speech (TTS): Utilizes `gTTS` to stream generated audio back to the client.
- **Background Jobs**: Utilizes `apscheduler` (BackgroundScheduler) to run automated cron tasks, such as cleaning up chat sessions older than 30 days.

### 2.3 Database & Infrastructure
- **Database**: PostgreSQL hosted on Supabase.
- **Extensions**: `vector` (pgvector) enabled for semantic similarity search.
- **Security**: Intensive use of PostgreSQL Row Level Security (RLS) to enforce tenant isolation at the database kernel level.

---

## 3. Application Flow Diagram

### 3.1 Onboarding & Workspace Initialization
1. A new user authenticates via Supabase Auth (Email/Password or Google OAuth).
2. Upon row insertion into `auth.users`, a PostgreSQL trigger (`handle_new_user`) executes.
3. The trigger automatically provisions a default personal Workspace (e.g., "John's Workspace") and inserts the user into `workspace_members` with 'Admin' privileges.

### 3.2 Agent Blueprint Creation (The Studio)
1. The user navigates to the Studio (`/studio`).
2. Using the `BlueprintConfigurator`, the user defines the agent's parameters: Name, System Prompt, Language, LLM Provider, and Embedding Strategy.
3. For advanced setups, users define multi-agent architectures using JSON blueprints, specifying parent-child relationships and assigned tools (e.g., REST APIs).

### 3.3 Knowledge Ingestion (RAG Setup)
1. The user navigates to the Knowledge Base (`/knowledge`) and uploads a PDF.
2. The React client posts the file to the FastAPI `/api/documents/upload` endpoint.
3. FastAPI parses the document (via `pymupdf`), chunks the text according to the agent's strategy, and generates 384-dimensional vector embeddings.
4. The chunks and vectors are stored in the `document_embeddings` table, linking them to the specific `document_id`.

### 3.4 Chat Execution & LLM Inference
1. The user submits a query in the Chat interface (`/chat`).
2. FastAPI processes the request at `/api/chat/message`:
   - **Vector Search**: Queries `pgvector` to find text chunks with the highest cosine similarity to the user's prompt.
   - **Web Search**: If enabled, scrapes DuckDuckGo for live context.
   - **Prompt Assembly**: The retrieved context, web data, and chat history are injected into the agent's base system prompt.
   - **Inference**: Langchain routes the compiled prompt to the selected LLM.
3. The LLM response is returned to the client (with streaming capabilities) and logged in `chat_messages`.

---

## 4. UI/UX Detailed Breakdown

### 4.1 Design Philosophy
The application utilizes a **Premium Glassmorphism** aesthetic. The UI focuses on responsive layouts, readable typography (Tailwind typography plugin), and visual feedback loops (toast notifications via `sonner`, skeleton loaders while data fetches).

### 4.2 Key Pages & Components
- **Global App Shell**: Includes an expandable `AppSidebar` and a top `AppHeader`. The header contains a dynamic `WorkspaceSwitcher` and a `NotificationBell` connected to Supabase Realtime for instant updates.
- **Dashboard (`/dashboard`)**: Displays analytical insights via `KPICard` components, a `RecentAgents` table, and an `ActivityFeed` showing recent teammate actions.
- **Studio (`/studio`)**: Houses the `CreateAgentWizard`, splitting complex configurations into digestible steps (Prompting, Knowledge, Output Formatting).
- **Chat Interface (`/chat`)**: 
  - **ChatSidebar**: Manages historical sessions.
  - **MessageBubble**: Renders markdown output, code syntax highlighting, and inline images.
  - **ContextPanel**: A sliding panel that allows users to debug the exact vector chunks the AI referenced to generate its answer, ensuring transparency.
  - **FeedbackModal**: Allows users to rate responses and log feedback.

---

## 5. Detailed Backend Schema

*Referencing `database_schema.sql` and `supabase_data.sql`*

### 5.1 Organizational Tables
- **`workspaces`**: `id` (UUID), `name`, `owner_id`, `created_at`.
- **`workspace_members`**: `id`, `workspace_id`, `user_id`, `role` (Admin, Member, Viewer), `permissions` (JSONB).
  *Note: The `permissions` JSONB object stores granular toggles like `{"agents": true, "database": false}`.*

### 5.2 Agent & Knowledge Tables
- **`agents`**: `id`, `user_id`, `workspace_id`, `name`, `system_prompt`, `provider`, `model`, `api_key`, `embedding_model`, `chunk_strategy`, `is_active`.
- **`documents`**: `id`, `agent_id`, `filename`, `status` (e.g., 'completed', 'processing').
- **`document_embeddings`**: `id` (BIGINT), `document_id`, `content` (TEXT), `embedding` (VECTOR(384)).

### 5.3 Communication Tables
- **`chat_sessions`**: `id`, `user_id`, `agent_id`, `workspace_id`, `title`, `pinned`.
- **`chat_messages`**: `id`, `session_id`, `role` (user/assistant), `content`, `latency`.

### 5.4 Application Settings
- **`user_settings`**: `user_id`, `openai_api_key`, `groq_api_key`, `gemini_api_key`, `two_factor_enabled`.
- **`user_subscriptions`**: Tracks SaaS billing tiers (`plan_tier`, `billing_cycle`, `status`).

---

## 6. Comprehensive Security & Access Control

### 6.1 Authentication
- Managed by Supabase Auth (JWT). 
- `AuthContext.jsx` acts as the source of truth for the client, securely managing tokens and executing automated workflows like claiming pending workspace invites upon login.

### 6.2 Client-Side Route Guards
The React router implements strict hierarchical access control wrappers:
1. **`ProtectedRoute.jsx`**: Global wrapper ensuring a valid user session exists.
2. **`RoleRoute.jsx`**: Validates rank hierarchy (`Owner` [4] > `Admin` [3] > `Member` [2] > `Viewer` [1]). Renders an `AccessDeniedScreen` if the user's rank is below the required threshold.
3. **`PermissionRoute.jsx`**: Checks specific JSONB feature flags (e.g., `canManageAgents`). Workspace Admins automatically bypass these checks.

### 6.3 Server-Side API Security (FastAPI)
- **Rate Limiting**: Utilizes the `slowapi` library to enforce strict rate limits on expensive endpoints (like LLM inference and document uploading) to prevent DDoS attacks and control API costs.
- **CORS Policies**: Internal API routes strictly validate the `Origin` header against `FRONTEND_URL` and `ADMIN_URL`. Public widget endpoints (`/api/widget`) use a custom `PublicCORSMiddleware` to allow `*` origins, enabling cross-domain widget embedding safely.

### 6.4 Database Row Level Security (RLS)
The absolute final line of defense is implemented directly in PostgreSQL. If an API vulnerability occurs, the database engine still prevents cross-tenant data leakage.
- Example Policy: 
  ```sql
  CREATE POLICY "Users can view workspaces they are members of" ON workspaces
    FOR SELECT TO authenticated
    USING (id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()) OR owner_id = auth.uid());
  ```
- All operational tables (`agents`, `notes`, `workspaces`, `user_settings`) enforce these RLS policies.
