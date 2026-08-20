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

### Workspace Isolation:
*   All data, uploaded resources, team permissions, and model configurations are securely isolated per workspace.
*   We enforce strict **Row-Level Security (RLS)** at the database layer. Workspace data from one team can never leak or be queried by another.
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

## 4. Knowledge Base Operations
The Knowledge Base is where agents get their intelligence:
*   **Document Uploads:** Support for PDF, TXT, and CSV formats. Documents are chunked and embedded in real-time.
*   **Website Scraping:** Paste any public URL. BlinkBot automatically scrapes, extracts text, chunks, and indexes it into the vector storage just like a document.
*   **Vector Sync:** Track status in real-time. If you modify source text, click **Sync** to re-index immediately.

---

## 5. Agent Networks & Studio Collaboration
*   **The Studio:** An interactive testing ground where you can chat with agents, inspect search logs, review sources cited, and test updates immediately.
*   **Agent Projects (Networks):** Group multiple specialized bots to collaborate. For example, a supervisor node (Intent Orchestrator) routes complex customer requests to dedicated sub-agents (e.g., routing billing queries to the Billing Bot, and tech issues to the Support Bot).

---

## 6. Website Deployment & Chat Widgets
You can convert any bot into an embeddable website widget.

### Customization Options:
*   **Visual Editor:** Customize theme colors, header text, welcome greetings, widget positions (bottom-right/bottom-left), custom icons, border radius, and font typography.
*   **Allowed Domains:** Secure your widget by restricting loading to specified domains only, preventing unauthorized script execution.
*   **Developer API Keys:** Generate keys to query the bot server-side using cURL/REST endpoints.
*   **HTML Script Tag Integration:**
    ```html
    <!-- BlinkBot Chatbot Widget -->
    <script defer src="https://blinkbot.in/widget.js"
      data-chatbot-id="19802bcc-68a2-46c2-86fc-7e17049cfaa3"
      data-api-url="https://api.blinkbot.in">
    </script>
    ```

---

## 7. Self-Learning Loop & Memory Patches
Improve your agents continuously without code:
*   **Flagging Errors:** If an agent outputs a wrong or outdated answer, flag it directly inside the chat log.
*   **Memory Patches:** Admins write a corrected answer. This correction is stored as a memory patch and dynamically appended to the agent's system context. The bot instantly learns the correct response without retraining.

---

## 8. Billing, Quotas & Plans
BlinkBot offers simple pricing structures:
*   **Starter Plan (Free):** Includes 1 collaborative agent team, basic vector storage, and a monthly message limit.
*   **Pro & Business Plans:** Designed for scale, giving workspaces access to multiple projects, widgets, advanced commercial APIs, and increased storage.
*   **Custom Slider Builder:** Allows teams to drag sliders to select exact message quotas, storage sizes, and widget counts, calculating a custom price in real-time.
*   **Top-Up Packs:** Message top-up credits can be purchased at any time. These credits never expire and roll over month-to-month.
*   **Refund Policy:** All transactions, subscription payments, and top-up credit purchases are final. We do not offer refunds, money-back guarantees, or partial credits under any circumstances.

---

## 9. Frequently Asked Questions (FAQ)

### Q: Why does my bot say it doesn't know the answer?
**A:** BlinkBot is designed to avoid hallucinations. If the requested answer is not present in the processed vector database index, the bot will decline to answer. Ensure your documents have finished indexing. You can also enable Web Search Fallback to let the bot query the internet for missing facts.

### Q: Can I connect my own API key?
**A:** Yes! Enter your own OpenAI, Groq, or OpenRouter keys during the wizard. Your keys are encrypted at rest and used solely to run your bot's requests.

### Q: How is my data protected?
**A:** All workspace folders, files, and chats are isolated at the database layer using strict PostgreSQL Row-Level Security (RLS) policies.
