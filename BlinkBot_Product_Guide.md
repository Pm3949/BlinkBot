# BlinkBot Complete Product Guide & Platform Documentation

Welcome to the definitive platform documentation for BlinkBot, the zero-code AI operating system. This guide provides comprehensive, technical, and operational details about how BlinkBot behaves, how agents are configured, security standards, integrations, and deployment steps. It is structured to serve as an in-depth knowledge document for training your custom chatbots.

---

## 1. Executive Summary & Platform Overview
BlinkBot is a next-generation AI operating system that empowers businesses to design, collaborate, and deploy custom conversational AI agents grounded securely in private data. With BlinkBot, teams go from raw documents to production-ready, interactive chat widgets in under 10 minutes.

### Key Capabilities:
*   **Zero-Coding Required:** A visual, intuitive layout guides you through every step.
*   **Multi-Provider LLM Orchestration:** Plug and play your own keys from commercial or open-source providers.
*   **Built-in RAG Engine:** Automate document parsing, chunking, and vector embedding natively.
*   **Collaborative Multi-Agent Networks:** Build project groups where specialized bots work together under supervisor control.
*   **Self-Correcting Memory Patches:** Correct bot responses instantly directly in the chat interface.

---

## 2. Accounts, Security & Workspace Architecture
Every user is placed within a **Workspace**, which serves as the primary security boundary.

### Workspace Isolation & Data Security:
*   All data, uploaded resources, team permissions, and model configurations are securely isolated per workspace.
*   We enforce strict **Row-Level Security (RLS)** at the database layer. Workspace data from one team can never leak or be queried by another.
*   **Data Security & Key Encryption:** To prevent key exposure, sensitive attributes such as provider API keys, custom database connection strings, and native integrations are encrypted using AES/fernet keys before writing to Postgres and decrypted on the fly during retrieval.
*   **Data Privacy Commitment:** Your company documents are private to your workspace. BlinkBot never shares your data, and we **never use your proprietary records to train public AI models**.

### Roles & Permissions:
Access is governed by role permissions configured on the **Team** page:
*   **Admin:** Complete permissions to manage billing subscriptions, invite colleagues, view/configure keys, upload knowledge databases, and create/edit agents.
*   **Member:** Operational access to create agents, manage project folders, upload/sync documents, and use the testing Studio. Members cannot edit workspace billing or view admin API keys.
*   **Viewer:** Read-only access to view performance charts, review conversations, and monitor system analytics.
*   **Granular Permission Toggles:** Admins can turn specific system permissions (e.g., `canManageModels` or `canManageStudio`) on or off for individual team members.

---

## 3. Creating & Configuring AI Agents
Building a bot is handled via a visual 5-step wizard.

### Step 1: Identity & AI Auto-Configure
*   **Identity:** Assign the agent a display name, description, and primary language.
*   **AI Auto-Configure (Meta-Agent Prompting):** Instead of manually configuring system behavior, users can write a single, plain-English prompt. For example:
    > *"A customer support agent for an e-commerce store that responds in a friendly tone and outputs responses format in clean markdown lists."*
*   Our system's Meta-Agent automatically generates a targeted agent name, system instructions, and structural rules.

### Step 2: System Behavior & Prompts
*   **System Prompt:** Define the core rules, persona, and rules of engagement (e.g., "You are a customer agent. Never state you are an AI, do not hallucinate, and decline questions outside the knowledge documents.").
*   **Output Format:** Specify how the agent structures replies (JSON, Markdown, bullet points, etc.).

### Step 3: Knowledge Base & Retrieval-Augmented Generation (RAG)
Choose how files are processed and indexed:
*   **Embedding Models:** Choose between `all-MiniLM-L6-v2` (default high-efficiency local), `nomic-embed`, or `OpenAI Embeddings`.
*   **Chunking Strategies:** 
    *   *Sentence-based chunking:* Breaks documents down by punctuation boundaries (optimal for exact fact retrieval).
    *   *Paragraph-based chunking:* Groups cohesive paragraphs (optimal for contextual reasoning).
    *   *Fixed-size chunking:* Splits text into fixed character windows with custom overlaps (optimal for general semantic search).

### Step 4: Capabilities & Tools
Configure advanced capabilities and sandboxed environments:
*   **Python Code Sandbox (CSV Analyzer):** Allow the agent to run Python code dynamically within a secure sandbox VM to calculate complex mathematical equations, analyze datasets, and generate visual charts.

### Step 5: Model Choice & Provider Keys
Select your LLM engine and primary language settings:
*   **Groq:** Optimized for sub-second, hardware-accelerated responses.
*   **OpenAI:** Industry benchmark using GPT-4o and GPT-4o-mini.
*   **OpenRouter & HuggingFace:** Connect your keys to access open-source models like DeepSeek R1, Llama 3.3, Mistral, and Qwen at near-zero token costs.
*   **Google Gemini:** Gemini 1.5 Flash, optimized for massive context files.
*   **Anthropic:** Claude 3.5 Sonnet, optimized for deep multi-step reasoning.
*   **Model Agnostic:** Switch between models dynamically at any time without losing vector database indices or agent behaviors.

---

## 4. Multi-Agent Orchestration & State Graph
The core multi-agent execution pipeline is defined as a supervisor-based StateGraph machine:

### Shared Memory State (`GraphState`)
Defines the state properties carried across graph execution nodes:
```python
class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    active_agent_id: Optional[str]
    routed_agent_name: Optional[str]
    next_agent: Optional[str] # 'FINISH' or Sub-Agent UUID
```
Uses `operator.add` as a reducer to dynamically accumulate message logs over the duration of a transaction instead of overwriting history.

### Supervisor Routing Node (`supervisor_node`)
*   **Intelligent Traffic Controller:** Runs a specialized routing LLM to examine current conversational history.
*   **Input Sanitization:** Automatically parses and filters message history, converting messages into raw Human and AI messages while stripping tool call metadata. This ensures compatibility and prevents sequence validation errors on models like Gemini.
*   **JSON-based Decision Parsing:** Instructs the LLM to output a JSON object containing the target agent key (via `SUPERVISOR_LOOP_PROMPT`). If JSON parsing fails, it falls back to regex pattern matching for sub-agent names/IDs, defaulting to `FINISH` or routing to the master coordinator.

### Agent Execution Node (`agent_node`)
*   **Dynamic Binding:** Fetches LLM credentials, system prompts, embedding configurations, and tools for the chosen active agent. If tools are available, it binds them dynamically to the LLM client.
*   **Streamed Execution:** Uses asynchronous generation (`astream`) for token-by-token streaming back to the caller.
*   **Resiliency & Auto-Truncation Layer:** Intercepts `413 Payload Too Large`, `rate_limit`, or token context-limit exceptions. If an error is caught, it automatically truncates history messages to 2000 characters and retries execution.

### Tool Execution Node (`tool_node`)
*   Uses LangGraph's prebuilt `ToolNode` to execute pending tool calls (e.g., RAG vector search, DuckDuckGo search, or external Webhooks).
*   Records execution performance logs (elapsed times, success status, and error states).

---

## 5. Interactive Network UI Graph (React Flow & Dagre)
The multi-agent networks are rendered visually inside the dashboard:
*   **Interactive 2D Canvas:** Utilizes `@xyflow/react` and the `dagre` layout engine to map complex hierarchical nodes automatically in TB (Top-to-Bottom) or LR (Left-to-Right) alignments.
*   **Custom Node Types:**
    *   `masterNode`: Represents the central Network Manager.
    *   `agentNode`: Represents specialized sub-agents with activation toggles, model info, settings navigation, and quick deletion.
    *   `toolNode` (Amber-themed): Linked custom API integrations.
    *   `kbNode` (Teal-themed) & `docNode` (Sky-themed): Visual representation of the vector database context, allowing users to expand the KB node to view individual document nodes underneath.
*   **Interactive Edges:** Drag-and-drop handles enable user-created links between agents. Connecting handles triggers an API update (`updateAgentMutation`) modifying the agent's `parent_agent_id` parameter directly.
*   **Pulsing State Animations:** Listening to real-time WebSocket events (`agent_routing_decision`, `agent_tool_start`), the UI highlights the active routing pathway with animated gradients and pulsing glow effects, showing which agent or tool is currently executing.
*   **Sandbox Testing Drawer:** Integrates a testing playground (`StudioSandboxChat`) next to the canvas, allowing developers to test the network, trigger Human-in-the-loop approvals, and inspect LLM routing execution traces in real time.

---

## 6. Knowledge Base & RAG Ingestion Pipeline
The Knowledge Base is where agents get their intelligence:

*   **Chunked File Ingestion:** Designed to handle large files by uploading them in indexable chunks, merging them, and processing/vectorizing them asynchronously in the background.
*   **Multi-Source Ingestion support:**
    *   *Direct Uploads:* Support for PDF, TXT, and CSV formats. Documents are chunked and embedded in real-time.
    *   *Website Scraping & URL Ingestion:* Paste any public URL. BlinkBot automatically scrapes, extracts text, chunks, and indexes it into the vector storage just like a document.
    *   *Raw Text Ingestion:* Manually paste or type text directly into the dashboard.
*   **Real-time Ingestion Progress Streaming:** Real-time progress updates (e.g., uploading, chunking, embedding, vector-ready) sent via WebSockets (`/ws/documents/upload/status/{session_key}`).
*   **Batch Ingestion Management:** Parallel fetch requests (`/agents/batch-documents`) using `asyncio.gather` to query documents across multiple agents concurrently.

---

## 7. Custom Tools Configuration & Execution
The creation workbench allows developers to provision custom tools in several user-friendly ways:

### UI Layer & Tool Configuration
*   **cURL Paste Parsing:** Users can paste raw `curl` commands directly into the URL field. The frontend utilizes a custom JavaScript parser (`parseCurlCommand`) that tokenizes the shell string to extract the method, base URL, headers, and body payload.
*   **Dynamic Variable Extraction:** Endpoint paths containing variables like `/items/{id}` are parsed, and the UI automatically extracts `{id}` as a required path variable parameter.
*   **LLM Description Generator:** To guarantee the LLM selects the correct tool, descriptions are critical. Developers can hit the **AI Generate** button, which sends tool details to `/api/agents/generate-tool-description`. An LLM generates clear instructions and explicit parameter descriptions.
*   **Requires Manual Approval Breakpoint:** For sensitive write operations, developers can toggle "Require manual approval". This pauses the LangGraph execution path before the tool node and alerts the user in the WebSocket chat interface for approval.

### Detailed Backend Compilation & Execution
Custom tools created by users are dynamically compiled into LangChain-compatible tool instances at runtime:
*   **REST API Webhooks (`create_workspace_webhook_tool`):** 
    *   *Instruction Injection:* The LLM's system instruction description is generated by combining the developer's description with the expected JSON payload schema.
    *   *Dynamic Parameter Mapping:* Intercepts parameters matching `{var}` and replaces them in the target URL. GET payloads are encoded as query arguments, while POST/PUT/PATCH are passed as body payloads.
    *   *Real-Time Progress Logs:* Publishes execution updates directly to the frontend's WebSocket manager so clients see a visual trace.
    *   *Output Truncation:* Truncates the response payload if it exceeds 8,000 characters.
*   **Sandboxed Python Interpreter (`create_e2b_python_tool`):** 
    *   *AST (Abstract Syntax Tree) Meta Parsing:* The backend parses the Python script using Python's standard `ast` module to dynamically extract the tool function name, parameter arguments for validation schema model (`DynamicArgsSchema`), and docstring.
    *   *E2B Sandbox Container:* The execution wrapper runs the script within a remote, isolated sandbox container.
    *   *Timeout Guard:* Executes the sandbox process on a daemon thread limited to a maximum 20-second timeout.

### Custom Tool Examples

#### Example 1: GitHub Issue Creator (REST API Webhook)
*   **Tool Name:** `Create_GitHub_Issue`
*   **Tool Type:** `api_webhook`
*   **Developer Description:** *"Use this tool to automatically create a new task or bug report issue in the GitHub repository when a user requests it."*
*   **Configuration:**
    *   Base URL: `https://api.github.com`
    *   Endpoint Path: `/repos/{owner}/{repo}/issues`
    *   Method: `POST`
    *   Headers: `{"Accept": "application/vnd.github+json"}`
    *   Auth Token: `Bearer github_pat_12345...` (Masked in logs)
    *   Path Variables: `owner` (repo owner), `repo` (repository name).
    *   Query/Body Parameters: `title` (issue title), `body` (issue description).
    *   Requires Approval: `True`

#### Example 2: Financial Calculator (Custom Python Script)
*   **Tool Name:** `Compound_Interest_Calculator`
*   **Tool Type:** `python_code`
*   **Developer Description:** *"Compute compound interest formulas for users wanting future projection estimates based on interest, payments, and frequency."*
*   **Requires Approval:** `False`
*   **Code Content:**
    ```python
    from langchain_core.tools import tool

    @tool
    def calculate_compound_interest(principal: float, rate: float, years: int, annual_contribution: float = 0.0) -> str:
        """Calculates compound interest projection."""
        total = principal
        for _ in range(years):
            total = (total * (1 + rate)) + annual_contribution
        interest_earned = total - principal - (annual_contribution * years)
        return f"Future Value: ${total:,.2f} | Interest Earned: ${interest_earned:,.2f}"
    ```
*   *Compilation Process:* The AST parser reads this code, identifies parameters as function arguments, constructs a validation schema, and executes the projection inside an isolated E2B container when called by the agent.

#### Example 3: Customer Lookup Database Connector (Database Connector)
*   **Tool Name:** `Search_Customer_DB`
*   **Tool Type:** `database`
*   **Developer Description:** *"Connect to the read-only customer records database to pull account information, current subscription tier, and signup details."*
*   **Configuration:**
    *   Connection String: `postgresql://read_only_user:secure_pwd@db.mycompany.internal:5432/production_analytics`
    *   *Implementation Workflow:* Translates query requests into a safe database session utilizing `SQLDatabase.from_uri` from `langchain_community`. The agent can run raw SELECT statements to query records without direct credential exposure.

---

## 8. Low-Latency Messaging & Embedding Widgets
*   **Interactive WebSockets:** Bidirectional WebSocket chat paths (`/ws/chat/{client_id}`) for internal workspace testing.
*   **Embeddable Guest Chat Widgets:** Independent WebSocket chat endpoints (`/ws/widget/chat/{client_id}`) allowing anonymous visitors on third-party websites to converse with active chatbots.
*   **Developer REST Chat API:** Developer access endpoint (`/api/v1/chat`) utilizing customizable API keys header authorization (`x-api-key`) with built-in token-by-token streaming.
*   **Chat Management:** Session tracking, session history deletion, and automated daily data purging (cleanup cron scheduler targeting items >30 days old).

---

## 9. Multimodal Input/Output Utilities
*   **Text-to-Speech (TTS):** Generates audio streams from agent text responses using Google TTS (`/api/tts`).
*   **Speech-to-Text (STT):** Transcribes audio file uploads using Groq's Whisper API (`/stt`).

---

## 10. Analytics, Workspaces & Settings
*   **Token & Cost Analytics:** Tracks prompt tokens, completion tokens, cumulative costs, and daily usage statistics (last 30 days) per agent and user.
*   **Multi-Tenant Workspace Isolation:** Segregates datasets, chatbot profiles, and histories across distinct tenant workspaces.
*   **OAuth Integrations:** Native integrations for importing files directly from cloud storage solutions (Google Drive OAuth).
*   **Developer API Key Management:** Keys creation/deletion for programmatic access to chatbots.
*   **Blog Page Management:** A backend and frontend component specifically for writing, listing, and maintaining articles or blogs.

---

## 11. Self-Learning Loop & Memory Patches
Improve your agents continuously without code:
*   **Flagging Errors:** If an agent outputs a wrong or outdated answer, flag it directly inside the chat log.
*   **Memory Patches:** Admins write a corrected answer. This correction is stored as a memory patch and dynamically appended to the agent's system context. The bot instantly learns the correct response without retraining.

---

## 12. Billing, Quotas & Plans
BlinkBot offers simple pricing structures:
*   **Starter Plan (Free):** Includes 1 collaborative agent team, basic vector storage, and a monthly message limit.
*   **Pro & Business Plans:** Designed for scale, giving workspaces access to multiple projects, widgets, advanced commercial APIs, and increased storage.
*   **Custom Slider Builder:** Allows teams to drag sliders to select exact message quotas, storage sizes, and widget counts, calculating a custom price in real-time.
*   **Top-Up Packs:** Message top-up credits can be purchased at any time. These credits never expire and roll over month-to-month.
*   **Refund Policy:** All transactions, subscription payments, and top-up credit purchases are final. We do not offer refunds, money-back guarantees, or partial credits under any circumstances.

---

## 13. Frequently Asked Questions (FAQ)

### Q: Why does my bot say it doesn't know the answer?
**A:** BlinkBot is designed to avoid hallucinations. If the requested answer is not present in the processed vector database index, the bot will decline to answer. Ensure your documents have finished indexing. You can also enable Web Search Fallback to let the bot query the internet for missing facts.

### Q: Can I connect my own API key?
**A:** Yes! Enter your own OpenAI, Groq, or OpenRouter keys during the wizard. Your keys are encrypted at rest and used solely to run your bot's requests.

### Q: How is my data protected?
**A:** All workspace folders, files, and chats are isolated at the database layer using strict PostgreSQL Row-Level Security (RLS) policies.
