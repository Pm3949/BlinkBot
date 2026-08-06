import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { 
  Webhook, 
  Database as DbIcon, 
  Key, 
  Terminal, 
  Plus, 
  ArrowLeft, 
  AlertCircle, 
  FileCode,
  Save,
  X
} from "lucide-react";
import { useUIStore } from "../store/useUIStore";
import { createWorkspaceTool, updateWorkspaceTool, getWorkspaceTools } from "../services/workspaceToolsService";
import { toast } from "sonner";

const PYTHON_BOILERPLATE = `from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Describe what this tool does so the agent knows when to use it."""
    # Write your custom logic here
    return "Result"`;

export default function CreateToolPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editId = searchParams.get("edit");
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);

  // Core State
  const [toolType, setToolType] = useState("api_webhook"); // 'api_webhook', 'database', 'oauth', 'python_code'
  const [toolName, setToolName] = useState("");
  const [description, setDescription] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [isMethodDropdownOpen, setIsMethodDropdownOpen] = useState(false);

  // API Webhook Config
  const [baseUrl, setBaseUrl] = useState("");
  const [path, setPath] = useState("");
  const [method, setMethod] = useState("GET");
  const [apiKey, setApiKey] = useState("");
  const [headers, setHeaders] = useState("{}");
  const [payloadFormat, setPayloadFormat] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");

  // Database Config
  const [connectionString, setConnectionString] = useState("");

  // OAuth Config
  const [oauthProvider, setOauthProvider] = useState("github");

  // Python Code Config
  const [codeContent, setCodeContent] = useState(PYTHON_BOILERPLATE);

  // UI Error Banner State (for validation failures)
  const [errorBanner, setErrorBanner] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editId || !activeWorkspaceId) return;
    const fetchToolData = async () => {
      try {
        const toolsData = await getWorkspaceTools(activeWorkspaceId);
        const targetTool = toolsData.find(t => t.id === editId);
        if (targetTool) {
          setToolType(targetTool.tool_type);
          setToolName(targetTool.name);
          setDescription(targetTool.configuration?.description || "");
          setRequiresApproval(targetTool.requires_approval || false);
          
          if (targetTool.tool_type === "api_webhook") {
            setBaseUrl(targetTool.configuration?.base_url || "");
            setPath(targetTool.configuration?.path || "");
            setMethod(targetTool.configuration?.method || "GET");
            setApiKey(targetTool.configuration?.api_key || "");
            setHeaders(JSON.stringify(targetTool.configuration?.headers || {}, null, 2));
            setPayloadFormat(targetTool.configuration?.payload_format || "");
            setExpectedOutput(targetTool.configuration?.expected_output || "");
          } else if (targetTool.tool_type === "database") {
            setConnectionString(targetTool.configuration?.connection_string || "");
          } else if (targetTool.tool_type === "oauth") {
            setOauthProvider(targetTool.configuration?.provider || "github");
          } else if (targetTool.tool_type === "python_code") {
            setCodeContent(targetTool.code_content || "");
          }
        }
      } catch (err) {
        console.error("Failed to load tool for editing:", err);
        toast.error("Failed to load tool details");
      }
    };
    fetchToolData();
  }, [editId, activeWorkspaceId]);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!activeWorkspaceId) {
      toast.error("No active workspace selected");
      return;
    }
    if (!toolName.trim()) {
      toast.error("Tool name is required");
      return;
    }

    setSaving(true);
    setErrorBanner(null);

    // Format configuration
    let configuration = {};
    if (toolType === "api_webhook") {
      let parsedHeaders = {};
      try {
        parsedHeaders = JSON.parse(headers);
      } catch (err) {
        toast.error("Headers must be valid JSON");
        setSaving(false);
        return;
      }
      configuration = {
        base_url: baseUrl,
        path: path,
        method: method,
        api_key: apiKey,
        headers: parsedHeaders,
        description: description,
        payload_format: payloadFormat,
        expected_output: expectedOutput,
        requires_approval: requiresApproval
      };
    } else if (toolType === "database") {
      if (!connectionString.trim()) {
        toast.error("Database connection URI is required");
        setSaving(false);
        return;
      }
      configuration = { connection_string: connectionString };
    } else if (toolType === "oauth") {
      configuration = { provider: oauthProvider };
    } else if (toolType === "python_code") {
      configuration = { description: description || "Custom sandboxed Python code tool execution." };
    }

    const payload = {
      name: toolName,
      tool_type: toolType,
      configuration,
      code_content: toolType === "python_code" ? codeContent : null,
      requires_approval: requiresApproval
    };

    try {
      if (editId) {
        await updateWorkspaceTool(activeWorkspaceId, editId, payload);
        toast.success("Tool updated successfully");
      } else {
        await createWorkspaceTool(activeWorkspaceId, payload);
        toast.success("Tool created and deployed successfully");
      }
      navigate("/tools");
    } catch (err) {
      setErrorBanner(err.message || "Failed to save tool");
      toast.error("Tool deployment failed. See error details.");
    } finally {
      setSaving(false);
    }
  };

  const handleAIGenerateDescription = async () => {
    if (!toolName.trim()) {
      toast.error("Please enter a tool name first to generate a description");
      return;
    }
    const loadingToastId = toast.loading("Generating description via LLM...");
    try {
      const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const { getAuthHeaders } = await import("../lib/api");
      const headers = getAuthHeaders();
      const res = await fetch(`${API_URL}/api/agents/generate-tool-description`, {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          tool_name: toolName,
          path: path || "/",
          method: method || "GET",
          payload_format: payloadFormat || "",
          expected_output: expectedOutput || "",
          llm_provider: "groq",
          llm_model: "llama-3.3-70b-versatile"
        })
      });
      if (!res.ok) throw new Error("Failed to generate description");
      const data = await res.json();
      if (data?.description) {
        setDescription(data.description);
        toast.success("AI Description generated!", { id: loadingToastId });
      } else {
        throw new Error("No description returned");
      }
    } catch (err) {
      console.error(err);
      let aiDesc = "";
      if (toolType === "api_webhook") {
        aiDesc = `Use this tool to trigger HTTP ${method} requests to ${toolName}. Purpose: allow retrieving or modifying resources at endpoint ${path || '/'}. Useful for fetching live JSON data or executing actions.`;
      } else if (toolType === "database") {
        aiDesc = `Query the ${toolName} PostgreSQL database to retrieve relational data. Allows execution of read-only SELECT queries to fetch production statistics.`;
      } else if (toolType === "oauth") {
        aiDesc = `Authenticate and trigger actions with third-party service ${oauthProvider} linked via ${toolName}.`;
      } else if (toolType === "python_code") {
        aiDesc = `Run secure sandboxed Python logic for ${toolName}. Solves advanced numeric calculations, string manipulations, or algorithmic tasks.`;
      }
      setDescription(aiDesc);
      toast.error("Failed to generate description via LLM. Used a local fallback description instead.", { id: loadingToastId });
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] -m-6 overflow-hidden bg-background text-foreground animate-in fade-in duration-200">
      {/* Sticky Header */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-card/50 backdrop-blur px-8 py-4 shrink-0">
        <div className="flex items-center gap-3">
          <button 
            type="button"
            onClick={() => navigate("/tools")}
            className="p-2 hover:bg-muted rounded-xl transition text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Workspace</span>
              <span>/</span>
              <span>Tools Library</span>
              <span>/</span>
              <span className="text-foreground font-semibold">{editId ? "Edit Tool" : "New Tool"}</span>
            </div>
            <h1 className="text-lg font-bold mt-0.5">{editId ? "Edit Workspace Tool" : "Tool Creation Workbench"}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/tools")}
            className="px-4 py-2 text-sm font-semibold hover:bg-muted transition rounded-xl"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2.5 bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-sm transition rounded-xl shadow-md flex items-center gap-2 disabled:opacity-50"
          >
            <Save size={16} /> {saving ? "Deploying..." : editId ? "Update & Deploy Tool" : "Save & Deploy Tool"}
          </button>
        </div>
      </header>

      {/* Main Two-Column View */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column: Metadata & Selector */}
        <aside className="w-96 border-r border-border bg-card/25 p-6 overflow-y-auto space-y-6 flex flex-col shrink-0">
          <div>
            <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground mb-3">1. Select Tool Type</h3>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setToolType("api_webhook")}
                className={`w-full p-3 rounded-xl border text-left flex items-center gap-3 transition ${toolType === "api_webhook" ? "border-primary bg-primary/5 text-primary font-semibold" : "border-border hover:bg-muted/50 text-foreground"}`}
              >
                <Webhook size={18} className={toolType === "api_webhook" ? "text-primary" : "text-muted-foreground"} />
                <span>REST API Webhook</span>
              </button>

              <button
                type="button"
                onClick={() => setToolType("python_code")}
                className={`w-full p-3 rounded-xl border text-left flex items-center gap-3 transition ${toolType === "python_code" ? "border-indigo-500 bg-indigo-500/5 text-indigo-400 font-semibold" : "border-border hover:bg-muted/50 text-foreground"}`}
              >
                <FileCode size={18} className={toolType === "python_code" ? "text-indigo-400" : "text-muted-foreground"} />
                <span>Custom Python Script</span>
              </button>

              <button
                type="button"
                onClick={() => setToolType("database")}
                className={`w-full p-3 rounded-xl border text-left flex items-center gap-3 transition ${toolType === "database" ? "border-emerald-500 bg-emerald-500/5 text-emerald-400 font-semibold" : "border-border hover:bg-muted/50 text-foreground"}`}
              >
                <DbIcon size={18} className={toolType === "database" ? "text-emerald-400" : "text-muted-foreground"} />
                <span>Database Connector</span>
              </button>

              <button
                type="button"
                onClick={() => setToolType("oauth")}
                className={`w-full p-3 rounded-xl border text-left flex items-center gap-3 transition ${toolType === "oauth" ? "border-purple-500 bg-purple-500/5 text-purple-400 font-semibold" : "border-border hover:bg-muted/50 text-foreground"}`}
              >
                <Key size={18} className={toolType === "oauth" ? "text-purple-400" : "text-muted-foreground"} />
                <span>App Connector (OAuth)</span>
              </button>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-border/50">
            <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground">2. Tool Info</h3>
            
            <div>
              <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Tool Name</label>
              <input
                required
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="e.g., Stripe API, Local Calculator"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-bold text-muted-foreground uppercase">LLM Instructions</label>
                <button
                  type="button"
                  onClick={handleAIGenerateDescription}
                  className="text-xs font-bold text-primary hover:text-primary/95 flex items-center gap-1.5 bg-primary/10 border border-primary/20 px-3 py-1.5 rounded-xl transition"
                >
                  ✨ AI Generate
                </button>
              </div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                placeholder="Describe what this tool does so the LLM agent understands when and how to call it."
              />
            </div>

            {toolType === "api_webhook" && (
              <div 
                onClick={() => setRequiresApproval(!requiresApproval)}
                className={`p-4 rounded-xl border transition-all duration-200 flex items-center justify-between cursor-pointer select-none ${requiresApproval ? "border-primary bg-primary/5 animate-in fade-in duration-100" : "border-border bg-card/40 hover:bg-card/70"}`}
              >
                <div className="space-y-1 pr-4">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-foreground">Require manual approval</span>
                    <div className="relative group/tooltip inline-block">
                      <div className="text-muted-foreground hover:text-foreground cursor-help p-0.5">
                        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                      </div>
                      {/* Tooltip Content */}
                      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover/tooltip:block bg-card border border-border text-[11px] text-muted-foreground p-3 rounded-xl w-64 shadow-2xl leading-relaxed z-50 animate-in fade-in duration-150">
                        The agent will pause execution of this REST Webhook and request explicit human confirmation in the chat interface before sending the request.
                      </div>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground leading-normal">
                    Prevents automated execution of sensitive write operations or database queries.
                  </p>
                </div>
                
                {/* Custom Inline Switch Toggle */}
                <div className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-200 shrink-0 ${requiresApproval ? "bg-primary" : "bg-muted-foreground/30"}`}>
                  <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ${requiresApproval ? "translate-x-4" : "translate-x-0"}`} />
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Right Column: Code Editor / Form Canvas */}
        <main className="flex-1 bg-background p-8 overflow-y-auto flex flex-col justify-between">
          <div className="space-y-6 flex-1 flex flex-col">
            {errorBanner && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-2.5">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span className="font-bold">Deployment Rejected:</span>
                  <p className="mt-1 font-mono text-xs">{errorBanner}</p>
                </div>
              </div>
            )}

            {toolType === "python_code" ? (
              <div className="flex-1 flex flex-col space-y-4">
                <div className="flex-1 flex flex-col border border-border rounded-2xl overflow-hidden min-h-[300px]">
                  <div className="px-4 py-2 border-b border-border bg-card/40 flex justify-between items-center text-xs text-muted-foreground shrink-0">
                    <span className="font-mono">main.py (Sandboxed execution)</span>
                    <span>Ready</span>
                  </div>
                  <textarea
                    required
                    value={codeContent}
                    onChange={(e) => setCodeContent(e.target.value)}
                    className="w-full flex-1 p-4 bg-card/25 text-foreground text-sm font-mono focus:outline-none resize-none leading-relaxed whitespace-pre font-medium"
                    placeholder="# Write your custom python tool here..."
                  />
                </div>

                <div className="p-4 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs flex items-center gap-2.5 shrink-0">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>Runs in a secure, isolated cloud sandbox. Networking and core OS system modules are disabled.</span>
                </div>
              </div>
            ) : toolType === "api_webhook" ? (
              <div className="space-y-5 bg-card/20 border border-border p-6 rounded-2xl">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="sm:col-span-1">
                    <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">HTTP Method</label>
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setIsMethodDropdownOpen(!isMethodDropdownOpen)}
                        className="w-full flex items-center justify-between border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary font-semibold text-left transition-all duration-200"
                      >
                        <span className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${
                            method === "GET" ? "bg-blue-500" :
                            method === "POST" ? "bg-emerald-500" :
                            method === "PUT" ? "bg-amber-500" :
                            method === "PATCH" ? "bg-purple-500" : "bg-red-500"
                          }`} />
                          {method}
                        </span>
                        <svg className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${isMethodDropdownOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      {isMethodDropdownOpen && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setIsMethodDropdownOpen(false)} />
                          <div className="absolute left-0 right-0 mt-2 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-1 duration-100">
                            {[
                              { val: "GET", color: "bg-blue-500", labelColor: "text-blue-400" },
                              { val: "POST", color: "bg-emerald-500", labelColor: "text-emerald-400" },
                              { val: "PUT", color: "bg-amber-500", labelColor: "text-amber-400" },
                              { val: "PATCH", color: "bg-purple-500", labelColor: "text-purple-400" },
                              { val: "DELETE", color: "bg-red-500", labelColor: "text-red-400" }
                            ].map((item) => (
                              <button
                                key={item.val}
                                type="button"
                                onClick={() => {
                                  setMethod(item.val);
                                  setIsMethodDropdownOpen(false);
                                }}
                                className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-muted text-left text-sm font-semibold transition-colors duration-150"
                              >
                                <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                                <span className={item.labelColor}>{item.val}</span>
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Base URL</label>
                    <input
                      required
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder="https://api.stripe.com"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Endpoint Path</label>
                  <input
                    required
                    value={path}
                    onChange={(e) => setPath(e.target.value)}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                    placeholder="/v1/charges"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">API Key / Token (Header Auth)</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                    placeholder="Bearer sk_live_..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Custom Headers (JSON)</label>
                  <textarea
                    value={headers}
                    onChange={(e) => setHeaders(e.target.value)}
                    rows={3}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm font-mono focus:outline-none"
                    placeholder='{ "Content-Type": "application/json" }'
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Payload JSON Format</label>
                    <input
                      value={payloadFormat}
                      onChange={(e) => setPayloadFormat(e.target.value)}
                      className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                      placeholder='{"limit": 10}'
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Expected JSON Response</label>
                    <input
                      value={expectedOutput}
                      onChange={(e) => setExpectedOutput(e.target.value)}
                      className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                      placeholder='{"data": []}'
                    />
                  </div>
                </div>
              </div>
            ) : toolType === "database" ? (
              <div className="bg-card/20 border border-border p-6 rounded-2xl space-y-4">
                <div>
                  <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">PostgreSQL Database Connection URI</label>
                  <input
                    required
                    type="password"
                    value={connectionString}
                    onChange={(e) => setConnectionString(e.target.value)}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                    placeholder="postgresql://user:password@localhost:5432/db_name"
                  />
                  <p className="text-[10px] text-muted-foreground mt-2">
                    Credentials are stored securely. Agents will have read-only SQL queries access to tables.
                  </p>
                </div>
              </div>
            ) : (
              <div className="bg-card/20 border border-border p-6 rounded-2xl space-y-4">
                <div>
                  <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">OAuth Application Provider</label>
                  <select
                    value={oauthProvider}
                    onChange={(e) => setOauthProvider(e.target.value)}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                  >
                    <option value="github">GitHub</option>
                    <option value="slack">Slack Workspace</option>
                  </select>
                  <p className="text-[10px] text-muted-foreground mt-2 flex items-center gap-1">
                    <AlertCircle size={12} className="text-amber-500 shrink-0" />
                    Make sure users connect their OAuth tokens in their main dashboard account integrations.
                  </p>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
