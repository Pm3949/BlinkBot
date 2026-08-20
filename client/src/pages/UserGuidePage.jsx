import React, { useState, useEffect } from 'react';
import { usePageSeo } from '../hooks/usePageSeo';
import { Link } from 'react-router-dom';
import { 
  ChevronLeft, BookOpen, Bot, Database, Globe, Users, BarChart3, 
  CreditCard, Settings, MessageSquare, Sparkles, Brain, Code,
  Upload, Layers, RefreshCw, Search, Shield, ChevronRight, Wrench, Volume2
} from 'lucide-react';
import Logo from '../components/shared/Logo';

const sections = [
  { id: "agent-config", label: "Agent Config & Database", icon: Settings },
  { id: "orchestration", label: "Orchestration (LangGraph)", icon: Brain },
  { id: "network-ui", label: "Interactive Network UI", icon: Layers },
  { id: "ingestion", label: "Ingestion & RAG Pipeline", icon: Database },
  { id: "tools-config", label: "Tools Config & Creation", icon: Wrench },
  { id: "backend-compilation", label: "Backend Tools Compilation", icon: Code },
  { id: "tool-examples", label: "Concrete Tool Examples", icon: BookOpen },
  { id: "widgets", label: "Widgets & Messaging", icon: Globe },
  { id: "multimodal", label: "Multimodal Utilities", icon: Volume2 },
  { id: "analytics", label: "Analytics & Workspaces", icon: BarChart3 },
];

export default function UserGuidePage() {
  usePageSeo('User Guide', 'Complete guide to building, configuring, and deploying custom AI chatbots with BlinkBot. From document upload to embedding a live widget.');
  const [activeSection, setActiveSection] = useState("agent-config");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Nav */}
      <nav className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="flex items-center justify-between px-6 md:px-8 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
              <ChevronLeft size={20} />
            </Link>
            <Logo />
          </div>
          <Link to="/login" className="btn-primary px-5 py-2 rounded-full text-sm font-bold shadow-lg shadow-primary/20">
            Get Started
          </Link>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 md:px-8 flex gap-8">
        {/* Sticky TOC Sidebar */}
        <aside className="hidden lg:block w-72 shrink-0">
          <nav className="sticky top-24 py-8 space-y-1 max-h-[calc(100vh-6rem)] overflow-y-auto pr-4">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-3 px-3">On this page</h3>
            {sections.map(({ id, label, icon: Icon }) => (
              <a
                key={id}
                href={`#${id}`}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  activeSection === id 
                    ? 'bg-primary/10 text-primary font-semibold' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <Icon size={14} className="shrink-0" />
                <span className="truncate">{label}</span>
              </a>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 py-12 pb-24">
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <BookOpen className="text-primary" size={20} />
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight">User Guide</h1>
            </div>
            <p className="text-muted-foreground text-lg">Everything you need to know to build, optimize, and deploy custom AI agents with BlinkBot.</p>
          </div>

          <div className="space-y-16">
            {/* 1. Agent Configuration & Database Management */}
            <GuideSection id="agent-config" title="Agent Configuration & Database Management" icon={Settings}>
              <h4 className="font-bold text-foreground mt-4 mb-2">Custom Settings Schema</h4>
              <p>
                A single agent profile contains core attributes validated via Pydantic:
              </p>
              <ul className="list-disc pl-5 space-y-1.5 text-muted-foreground text-sm">
                <li><strong>llm_provider & llm_model:</strong> Supported providers like OpenAI, Groq, Gemini, and Ollama.</li>
                <li><strong>system_prompt & output_format:</strong> Core behavior and restriction guidelines.</li>
                <li><strong>chunk_strategy:</strong> Document partitioning method (e.g., semantic or sentence).</li>
                <li><strong>web_search_enabled & code_interpreter_enabled:</strong> Toggles for DuckDuckGo web search integration and local sandboxed Python code execution.</li>
                <li><strong>endpoints, databases, and native_integrations:</strong> Connectors for external APIs, database objects, and applications (e.g., Slack, Google Drive).</li>
              </ul>

              <h4 className="font-bold text-foreground mt-6 mb-2">Data Security & Key Encryption</h4>
              <p>
                To prevent key exposure, sensitive attributes such as provider API keys, custom database connection lists, and native integrations are encrypted using AES/fernet keys before writing to Postgres and decrypted on the fly during retrieval.
              </p>
            </GuideSection>

            {/* 2. Multi-Agent Orchestration (LangGraph State Machine) */}
            <GuideSection id="orchestration" title="Multi-Agent Orchestration (LangGraph State Machine)" icon={Brain}>
              <p>
                The core multi-agent execution pipeline is defined as supervisor-based StateGraph machine:
              </p>

              <h4 className="font-bold text-foreground mt-6 mb-2">Shared Memory State (GraphState)</h4>
              <p>
                Defined as a typed dictionary carrying properties across execution nodes:
              </p>
              <pre className="p-4 bg-muted rounded-xl font-mono text-xs overflow-x-auto my-3 text-foreground">
{`class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    active_agent_id: Optional[str]
    routed_agent_name: Optional[str]
    next_agent: Optional[str] # 'FINISH' or Sub-Agent UUID`}
              </pre>
              <p>
                Uses <strong>operator.add</strong> as a reducer to dynamically accumulate message logs over the duration of a transaction instead of overwriting history.
              </p>

              <h4 className="font-bold text-foreground mt-6 mb-2">Supervisor Routing Node (supervisor_node)</h4>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm">
                <li><strong>Intelligent Traffic Controller:</strong> Runs a specialized routing LLM to examine current conversational history.</li>
                <li><strong>Input Sanitization:</strong> Automatically parses and filters message history, converting messages into raw Human and AI messages while stripping tool call metadata. This ensures compatibility and prevents sequence validation errors on models like Gemini.</li>
                <li><strong>JSON-based Decision Parsing:</strong> Instructs the LLM to output a JSON object containing the target agent key (via SUPERVISOR_LOOP_PROMPT). If JSON parsing fails, it falls back to regex pattern matching for sub-agent names/IDs, defaulting to FINISH or routing to the master coordinator.</li>
              </ul>

              <h4 className="font-bold text-foreground mt-6 mb-2">Agent Execution Node (agent_node)</h4>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm">
                <li><strong>Dynamic Binding:</strong> Fetches LLM credentials, system prompts, embedding configurations, and tools for the chosen active agent. If tools are available, it binds them dynamically to the LLM client.</li>
                <li><strong>Streamed Execution:</strong> Uses asynchronous generation (astream) for token-by-token streaming back to the caller.</li>
                <li><strong>Resiliency & Auto-Truncation Layer:</strong> Intercepts 413 Payload Too Large, rate_limit, or token context-limit exceptions. If an error is caught, it automatically truncates history messages to 2000 characters and retries execution.</li>
              </ul>

              <h4 className="font-bold text-foreground mt-6 mb-2">Tool Execution Node (tool_node)</h4>
              <p>
                Uses LangGraph's prebuilt ToolNode to execute pending tool calls (e.g., RAG vector search, DuckDuckGo search, or external Webhooks). Records execution performance logs (elapsed times, success status, and error states).
              </p>
            </GuideSection>

            {/* 3. Interactive Network UI Graph (React Flow & Dagre) */}
            <GuideSection id="network-ui" title="Interactive Network UI Graph (React Flow & Dagre)" icon={Layers}>
              <p>
                The multi-agent networks are rendered visually inside the dashboard:
              </p>
              <ul className="list-disc pl-5 space-y-3 text-muted-foreground text-sm mt-3">
                <li><strong>Interactive 2D Canvas:</strong> Utilizes @xyflow/react and the dagre layout engine to map complex hierarchical nodes automatically in TB (Top-to-Bottom) or LR (Left-to-Right) alignments.</li>
                <li><strong>Custom Node Types:</strong>
                  <ul className="list-disc pl-5 mt-1.5 space-y-1">
                    <li><strong>masterNode:</strong> Represents the central Network Manager.</li>
                    <li><strong>agentNode:</strong> Represents specialized sub-agents with activation toggles, model info, settings navigation, and quick deletion.</li>
                    <li><strong>toolNode (Amber-themed):</strong> Linked custom API integrations.</li>
                    <li><strong>kbNode (Teal-themed) & docNode (Sky-themed):</strong> Visual representation of the vector database context, allowing users to expand the KB node to view individual document nodes underneath.</li>
                  </ul>
                </li>
                <li><strong>Interactive Edges:</strong> Drag-and-drop handles enable user-created links between agents. Connecting handles triggers an API update (updateAgentMutation) modifying the agent's parent_agent_id parameter directly.</li>
                <li><strong>Pulsing State Animations:</strong> Listening to real-time WebSocket events (agent_routing_decision, agent_tool_start), the UI highlights the active routing pathway with animated gradients and pulsing glow effects, showing which agent or tool is currently executing.</li>
                <li><strong>Sandbox Testing Drawer:</strong> Integrates a testing playground (StudioSandboxChat) next to the canvas, allowing developers to test the network, trigger Human-in-the-loop approvals, and inspect LLM routing execution traces in real time.</li>
              </ul>
            </GuideSection>

            {/* 4. Document Ingestion & RAG Ingestion Pipeline */}
            <GuideSection id="ingestion" title="Document Ingestion & RAG Ingestion Pipeline" icon={Database}>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm mt-3">
                <li><strong>Chunked File Ingestion:</strong> Designed to handle large files by uploading them in indexable chunks, merging them, and processing/vectorizing them asynchronously in the background.</li>
                <li><strong>Multi-Source Ingestion support:</strong>
                  <ul className="list-disc pl-5 mt-1.5 space-y-1">
                    <li><strong>Direct Uploads:</strong> Upload single files (PDF/TXT) via standard forms.</li>
                    <li><strong>URL/Web Ingestion:</strong> Scrapes target webpage content directly via scraper tools.</li>
                    <li><strong>Raw Text Ingestion:</strong> Manually paste or type text directly into the dashboard.</li>
                  </ul>
                </li>
                <li><strong>Real-time Ingestion Progress Streaming:</strong> Real-time progress updates (e.g., uploading, chunking, embedding, vector-ready) sent via WebSockets (/ws/documents/upload/status/{"{session_key}"}).</li>
                <li><strong>Batch Ingestion Management:</strong> Parallel fetch requests (/agents/batch-documents) using asyncio.gather to query documents across multiple agents concurrently.</li>
              </ul>
            </GuideSection>

            {/* 5. How Tools are Configured & Created (UI Layer) */}
            <GuideSection id="tools-config" title="How Tools are Configured & Created (UI Layer)" icon={Wrench}>
              <p>
                The creation workbench allows developers to provision custom tools in several user-friendly ways:
              </p>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm mt-3">
                <li><strong>cURL Paste Parsing:</strong> Users can paste raw curl commands directly into the URL field. The frontend utilizes a custom JavaScript parser (parseCurlCommand) that tokenizes the shell string to extract: HTTP Method, Base URL, headers, and query/body parameters.</li>
                <li><strong>Dynamic Variable Extraction:</strong> Endpoint paths containing variables like /items/{"{id}"} are parsed, and the UI automatically extracts {"{id}"} as a required path variable parameter.</li>
                <li><strong>LLM Description Generator:</strong> To guarantee the LLM selects the correct tool, descriptions are critical. Developers can hit the AI Generate button, which sends tool details to /api/agents/generate-tool-description to generate clear instructions and parameter-level descriptions.</li>
                <li><strong>Requires Manual Approval Breakpoint:</strong> For sensitive write operations, developers can toggle "Require manual approval". This pauses the LangGraph execution path before the tool node and alerts the user in the WebSocket chat interface for approval.</li>
              </ul>
            </GuideSection>

            {/* 6. Detailed Backend Compilation & Execution */}
            <GuideSection id="backend-compilation" title="Detailed Backend Compilation & Execution" icon={Code}>
              <p>
                Custom tools created by users are dynamically compiled into LangChain-compatible tool instances at runtime:
              </p>
              <h4 className="font-bold text-foreground mt-4 mb-2">REST API Webhooks (create_workspace_webhook_tool)</h4>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm">
                <li><strong>Instruction Injection:</strong> The LLM's system instruction description is generated by combining the developer's description with the expected JSON payload schema.</li>
                <li><strong>Dynamic Parameter Mapping:</strong> Intercepts parameters matching {"{var}"} and replaces them in the target URL. GET payloads are encoded as query arguments, while POST/PUT/PATCH are passed as body payloads.</li>
                <li><strong>Real-Time Progress Logs:</strong> It publishes execution updates directly to the frontend's WebSocket manager so clients see a visual trace of the loading webhook URL.</li>
                <li><strong>Output Truncation:</strong> To protect context window limits, the response payload is truncated if it exceeds 8,000 characters.</li>
              </ul>

              <h4 className="font-bold text-foreground mt-6 mb-2">Sandboxed Python Interpreter (create_e2b_python_tool)</h4>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm">
                <li><strong>AST (Abstract Syntax Tree) Meta Parsing:</strong> The backend parses the Python script using Python's standard ast module to dynamically extract the tool function name (annotated with @tool), parameters schema model, and the function docstring.</li>
                <li><strong>E2B Sandbox Container:</strong> The execution wrapper runs the script within a remote, isolated sandbox container.</li>
                <li><strong>Timeout Guard:</strong> Executes the sandbox process on a daemon thread limited to a maximum 20-second timeout.</li>
              </ul>
            </GuideSection>

            {/* 7. Concrete Tool Examples */}
            <GuideSection id="tool-examples" title="Concrete Tool Examples" icon={BookOpen}>
              <div className="space-y-6">
                <div className="bg-card border border-border/50 p-5 rounded-xl">
                  <h5 className="font-bold text-foreground mb-2">Example 1: GitHub Issue Creator (REST API Webhook)</h5>
                  <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground leading-relaxed">
                    <li><strong>Tool Name:</strong> `Create_GitHub_Issue`</li>
                    <li><strong>Tool Type:</strong> `api_webhook`</li>
                    <li><strong>Developer Description:</strong> "Use this tool to automatically create a new task or bug report issue in the GitHub repository when a user requests it."</li>
                    <li><strong>Configuration:</strong>
                      <ul className="list-disc pl-5 mt-1">
                        <li>Base URL: `https://api.github.com`</li>
                        <li>Endpoint Path: `/repos/{owner}/{repo}/issues`</li>
                        <li>Method: `POST`</li>
                        <li>Headers: `{"Accept": "application/vnd.github+json"}`</li>
                        <li>Path Variables: `owner` (repo owner), `repo` (repository name).</li>
                        <li>Query/Body Parameters: `title` (required string), `body` (optional string).</li>
                      </ul>
                    </li>
                    <li><strong>Requires Approval:</strong> `True`</li>
                  </ul>
                </div>

                <div className="bg-card border border-border/50 p-5 rounded-xl">
                  <h5 className="font-bold text-foreground mb-2">Example 2: Financial Calculator (Custom Python Script)</h5>
                  <ul className="list-disc pl-5 space-y-1.5 text-xs text-muted-foreground leading-relaxed">
                    <li><strong>Tool Name:</strong> `Compound_Interest_Calculator`</li>
                    <li><strong>Tool Type:</strong> `python_code`</li>
                    <li><strong>Developer Description:</strong> "Compute compound interest formulas for users wanting future projection estimates based on interest, payments, and frequency."</li>
                    <li><strong>Requires Approval:</strong> `False`</li>
                    <li><strong>Code Content:</strong>
                      <pre className="p-3 bg-muted rounded-lg font-mono text-[10px] overflow-x-auto mt-2">
{`from langchain_core.tools import tool

@tool
def calculate_compound_interest(principal: float, rate: float, years: int, annual_contribution: float = 0.0) -> str:
    """
    Calculates compound interest projection.
    Parameters:
      principal: Initial investment amount.
      rate: Annual interest rate as a decimal (e.g. 0.08 for 8%).
      years: Investment duration in years.
      annual_contribution: Optional yearly contribution added at year-end.
    """
    total = principal
    for _ in range(years):
        total = (total * (1 + rate)) + annual_contribution
    interest_earned = total - principal - (annual_contribution * years)
    return f"Future Value: \${total:,.2f} | Interest Earned: \${interest_earned:,.2f}"`}
                      </pre>
                    </li>
                    <li><strong>Compilation Process:</strong> The AST parser reads this code, identifies parameters as function arguments, constructs a validation schema, and executes the projection inside an isolated E2B container when called by the agent.</li>
                  </ul>
                </div>

                <div className="bg-card border border-border/50 p-5 rounded-xl">
                  <h5 className="font-bold text-foreground mb-2">Example 3: Customer Lookup Database Connector (Database Connector)</h5>
                  <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground leading-relaxed">
                    <li><strong>Tool Name:</strong> `Search_Customer_DB`</li>
                    <li><strong>Tool Type:</strong> `database`</li>
                    <li><strong>Developer Description:</strong> "Connect to the read-only customer records database to pull account information, current subscription tier, and signup details."</li>
                    <li><strong>Configuration Connection String:</strong> `postgresql://read_only_user:secure_pwd@db.mycompany.internal:5432/production_analytics`</li>
                    <li><strong>Implementation Workflow:</strong> Translates query requests into a safe database session utilizing `SQLDatabase.from_uri` from `langchain_community`. The agent can run raw SELECT statements to query records without direct credential exposure.</li>
                  </ul>
                </div>
              </div>
            </GuideSection>

            {/* 8. Low-Latency Messaging & Embedding Widgets */}
            <GuideSection id="widgets" title="Low-Latency Messaging & Embedding Widgets" icon={Globe}>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm mt-3">
                <li><strong>Interactive WebSockets:</strong> Bidirectional WebSocket chat paths (/ws/chat/{"{client_id}"}) for internal workspace testing.</li>
                <li><strong>Embeddable Guest Chat Widgets:</strong> Independent WebSocket chat endpoints (/ws/widget/chat/{"{client_id}"}) allowing anonymous visitors on third-party websites to converse with active chatbots.</li>
                <li><strong>Developer REST Chat API:</strong> Developer access endpoint (/api/v1/chat) utilizing customizable API keys header authorization (x-api-key) with built-in token-by-token streaming.</li>
                <li><strong>Chat Management:</strong> Session tracking, session history deletion, and automated daily data purging (cleanup cron scheduler targeting items &gt;30 days old).</li>
              </ul>
            </GuideSection>

            {/* 9. Multimodal Input/Output Utilities */}
            <GuideSection id="multimodal" title="Multimodal Input/Output Utilities" icon={Volume2}>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm mt-3">
                <li><strong>Text-to-Speech (TTS):</strong> Generates audio streams from agent text responses using Google TTS (/api/tts).</li>
                <li><strong>Speech-to-Text (STT):</strong> Transcribes audio file uploads using Groq's Whisper API (/stt).</li>
              </ul>
            </GuideSection>

            {/* 10. Analytics, Workspaces & Settings */}
            <GuideSection id="analytics" title="Analytics, Workspaces & Settings" icon={BarChart3}>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground text-sm mt-3">
                <li><strong>Token & Cost Analytics:</strong> Tracks prompt tokens, completion tokens, cumulative costs, and daily usage statistics (last 30 days) per agent and user.</li>
                <li><strong>Multi-Tenant Workspace Isolation:</strong> Segregates datasets, chatbot profiles, and histories across distinct tenant workspaces.</li>
                <li><strong>OAuth Integrations:</strong> Native integrations for importing files directly from cloud storage solutions (Google Drive OAuth).</li>
                <li><strong>Developer API Key Management:</strong> Keys creation/deletion for programmatic access to chatbots.</li>
                <li><strong>Blog Page Management:</strong> A backend and frontend component specifically for writing, listing, and maintaining articles or blogs.</li>
              </ul>
            </GuideSection>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ═══════════════════════ SUB-COMPONENTS ═══════════════════════ */

function GuideSection({ id, title, icon: Icon, children }) {
  return (
    <section id={id} className="scroll-mt-24 space-y-4">
      <h2 className="text-2xl font-bold flex items-center gap-3 border-b border-border/50 pb-3">
        <Icon size={22} className="text-primary" />
        {title}
      </h2>
      <div className="text-muted-foreground leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  );
}

function InfoBox({ title, children, variant = "info" }) {
  const colors = variant === "tip" 
    ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-700 dark:text-emerald-400"
    : "bg-primary/5 border-primary/20 text-primary";
  return (
    <div className={`mt-4 p-4 rounded-xl border ${colors}`}>
      <h4 className="text-sm font-bold mb-2">{title}</h4>
      <div className="text-foreground">{children}</div>
    </div>
  );
}

function PlanCard({ name, price, features, highlight }) {
  return (
    <div className={`p-4 rounded-xl border text-center ${highlight ? 'border-primary bg-primary/5' : 'border-border/50 bg-card'}`}>
      <h4 className="font-bold">{name}</h4>
      <p className="text-2xl font-extrabold my-2">{price}</p>
      <ul className="text-xs text-muted-foreground space-y-1">
        {features.map((f, i) => <li key={i}>{f}</li>)}
      </ul>
    </div>
  );
}

function FAQItem({ q, a }) {
  return (
    <div className="bg-card border border-border/50 p-5 rounded-xl">
      <h4 className="font-bold mb-2 text-foreground">{q}</h4>
      <p className="text-sm text-muted-foreground leading-relaxed">{a}</p>
    </div>
  );
}
