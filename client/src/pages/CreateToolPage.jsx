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
import { createWorkspaceTool, updateWorkspaceTool, getWorkspaceTools, testDatabaseConnection } from "../services/workspaceToolsService";
import { toast } from "sonner";

const PYTHON_BOILERPLATE = `from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Describe what this tool does so the agent knows when to use it."""
    # Write your custom logic here
    return "Result"`;

const parseCurlCommand = (curlString) => {
  if (!curlString || typeof curlString !== 'string') return null;
  const str = curlString.trim();
  if (!str.toLowerCase().startsWith('curl ')) return null;

  let method = 'GET';
  let url = '';
  let headers = {};
  let body = '';
  let auth = '';

  const regex = /[^\s"']+|"([^"]*)"|'([^']*)'/g;
  const tokens = [];
  let match;
  while ((match = regex.exec(str)) !== null) {
    tokens.push(match[1] || match[2] || match[0]);
  }

  for (let i = 1; i < tokens.length; i++) {
    const token = tokens[i];
    
    if (token === '-X' || token === '--request') {
      method = tokens[++i]?.toUpperCase() || 'GET';
    } else if (token === '-H' || token === '--header') {
      const headerStr = tokens[++i];
      if (headerStr) {
        const colonIdx = headerStr.indexOf(':');
        if (colonIdx > 0) {
          const key = headerStr.substring(0, colonIdx).trim();
          const val = headerStr.substring(colonIdx + 1).trim();
          headers[key] = val;
        }
      }
    } else if (token === '-d' || token === '--data' || token === '--data-raw' || token === '--data-binary') {
      body = tokens[++i] || '';
      if (method === 'GET') method = 'POST';
    } else if (token === '-u' || token === '--user') {
      auth = tokens[++i] || '';
    } else if (token.startsWith('http://') || token.startsWith('https://')) {
      url = token;
    } else if (tokens[i - 1] === '--url') {
      url = token;
    }
  }

  let baseUrl = '';
  let path = '';
  if (url) {
    try {
      const parsedUrl = new URL(url);
      baseUrl = `${parsedUrl.protocol}//${parsedUrl.host}`;
      path = parsedUrl.pathname + parsedUrl.search;
    } catch (e) {
      baseUrl = url;
    }
  }

  return { method, baseUrl, path, headers, body, auth };
};

const parseConnectionString = (uri) => {
  if (!uri || !uri.startsWith("postgresql://")) {
    return { host: "", port: "5432", database: "", user: "", password: "" };
  }
  try {
    const cleanUri = uri.replace("postgresql://", "");
    const atIdx = cleanUri.indexOf("@");
    if (atIdx === -1) return { host: "", port: "5432", database: "", user: "", password: "" };
    
    const credentials = cleanUri.substring(0, atIdx);
    const hostDb = cleanUri.substring(atIdx + 1);
    
    const [user, password] = credentials.split(":");
    
    const slashIdx = hostDb.indexOf("/");
    let hostPort = hostDb;
    let database = "";
    if (slashIdx !== -1) {
      hostPort = hostDb.substring(0, slashIdx);
      database = hostDb.substring(slashIdx + 1);
    }
    
    const colonIdx = hostPort.indexOf(":");
    let host = hostPort;
    let port = "5432";
    if (colonIdx !== -1) {
      host = hostPort.substring(0, colonIdx);
      port = hostPort.substring(colonIdx + 1);
    }
    
    return { host, port, database, user, password };
  } catch (e) {
    return { host: "", port: "5432", database: "", user: "", password: "" };
  }
};

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
  const [pathVars, setPathVars] = useState([]);
  const [queryParams, setQueryParams] = useState([]);
  const [expectedOutput, setExpectedOutput] = useState("");
  const [isTestingWebhook, setIsTestingWebhook] = useState(false);
  const [isTestingDb, setIsTestingDb] = useState(false);

  // Database Config
  const [connectionString, setConnectionString] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [dbHost, setDbHost] = useState("");
  const [dbPort, setDbPort] = useState("5432");
  const [dbName, setDbName] = useState("");
  const [dbUser, setDbUser] = useState("");
  const [dbPassword, setDbPassword] = useState("");
  const [dbMode, setDbMode] = useState("form"); // "form" or "uri"

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
            const pf = targetTool.configuration?.payload_format || "";
            const eps = targetTool.configuration?.end_point_suffix || "";
            setPayloadFormat(pf);

            const pVars = [];
            const qParams = [];

            const parseParamStr = (jsonStr) => {
              if (!jsonStr || !jsonStr.trim().startsWith("{")) return {};
              try {
                return JSON.parse(jsonStr);
              } catch (e) {
                return {};
              }
            };

            const parsedPf = parseParamStr(pf);
            const parsedEps = parseParamStr(eps);

            Object.entries(parsedPf).forEach(([key, val]) => {
              let required = true;
              let type = "string";
              let desc = val;
              if (typeof val === "string") {
                if (val.includes("(optional)")) {
                  required = false;
                  desc = desc.replace("(optional)", "").trim();
                }
                const firstWord = desc.split(" ")[0].toLowerCase();
                if (["string", "integer", "number", "boolean", "object", "array"].includes(firstWord)) {
                  type = firstWord;
                  desc = desc.substring(firstWord.length).replace(/^-/, "").trim();
                }
              }
              qParams.push({ name: key, type, required, description: desc });
            });

            Object.entries(parsedEps).forEach(([key, val]) => {
              let required = true;
              let type = "string";
              let desc = val;
              if (typeof val === "string") {
                if (val.includes("(optional)")) {
                  required = false;
                  desc = desc.replace("(optional)", "").trim();
                }
                const firstWord = desc.split(" ")[0].toLowerCase();
                if (["string", "integer", "number", "boolean", "object", "array"].includes(firstWord)) {
                  type = firstWord;
                  desc = desc.substring(firstWord.length).replace(/^-/, "").trim();
                }
              }
              pVars.push({ name: key, type, required, description: desc });
            });

            // Legacy fallback if eps is missing but path contains variables inside pf keys
            if (pVars.length === 0 && Object.keys(parsedPf).length > 0) {
              const currentPath = targetTool.configuration?.path || "";
              const finalQParams = [];
              qParams.forEach(obj => {
                const isPathVar = currentPath.includes(`{${obj.name}}`) || obj.name.includes("{") || obj.name.includes("}");
                if (isPathVar) {
                  pVars.push(obj);
                } else {
                  finalQParams.push(obj);
                }
              });
              setQueryParams(finalQParams);
            } else {
              setQueryParams(qParams);
            }
            
            setPathVars(pVars);
            setExpectedOutput(targetTool.configuration?.expected_output || "");
          } else if (targetTool.tool_type === "database") {
            const connStr = targetTool.configuration?.connection_string || "";
            setConnectionString(connStr);
            const parsedConn = parseConnectionString(connStr);
            setDbHost(parsedConn.host);
            setDbPort(parsedConn.port);
            setDbName(parsedConn.database);
            setDbUser(parsedConn.user);
            setDbPassword(parsedConn.password);
            if (connStr && !parsedConn.host) {
              setDbMode("uri");
            } else {
              setDbMode("form");
            }
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
      let finalPayloadFormat = "";
      let finalEndPointSuffix = "";

      if (queryParams.length > 0) {
        const payloadObj = {};
        queryParams.forEach(p => {
          if (!p.name.trim()) return;
          let desc = p.type;
          if (!p.required) desc += " (optional)";
          if (p.description) desc += ` - ${p.description}`;
          payloadObj[p.name.trim()] = desc;
        });
        finalPayloadFormat = JSON.stringify(payloadObj, null, 2);
      }

      if (pathVars.length > 0) {
        const suffixObj = {};
        pathVars.forEach(p => {
          if (!p.name.trim()) return;
          let desc = p.type;
          if (!p.required) desc += " (optional)";
          if (p.description) desc += ` - ${p.description}`;
          suffixObj[p.name.trim()] = desc;
        });
        finalEndPointSuffix = JSON.stringify(suffixObj, null, 2);
      }

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
        payload_format: finalPayloadFormat,
        end_point_suffix: finalEndPointSuffix,
        expected_output: expectedOutput,
        requires_approval: requiresApproval
      };
    } else if (toolType === "database") {
      let finalConnStr = connectionString;
      if (dbHost.trim() && dbName.trim() && dbUser.trim() && dbPassword.trim()) {
        finalConnStr = `postgresql://${dbUser.trim()}:${dbPassword.trim()}@${dbHost.trim()}:${dbPort.trim()}/${dbName.trim()}`;
      }
      if (!finalConnStr.trim()) {
        toast.error("Database connection details are required");
        setSaving(false);
        return;
      }
      configuration = { connection_string: finalConnStr };
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
        const newTool = await createWorkspaceTool(activeWorkspaceId, payload);
        toast.success("Tool created and deployed successfully");
        if (newTool && newTool.id) {
          navigate(`${window.location.pathname}?edit=${newTool.id}`, { replace: true });
        }
      }
    } catch (err) {
      setErrorBanner(err.message || "Failed to save tool");
      toast.error("Tool deployment failed. See error details.");
    } finally {
      setSaving(false);
    }
  };

  const handleUrlPaste = (e) => {
    const pastedText = e.clipboardData.getData('text');
    if (!pastedText.trim().toLowerCase().startsWith('curl ')) return;
    
    const parsed = parseCurlCommand(pastedText);
    if (parsed) {
      e.preventDefault();
      
      toast.success("cURL command parsed successfully!");
      if (parsed.method) setMethod(parsed.method);
      if (parsed.baseUrl) setBaseUrl(parsed.baseUrl);
      
      let cleanPath = parsed.path || "";
      const qParams = [];
      const pVars = [];
      
      // 1. Parse query string parameters from URL
      if (parsed.path && parsed.path.includes("?")) {
        const queryStart = parsed.path.indexOf("?");
        cleanPath = parsed.path.substring(0, queryStart);
        const searchStr = parsed.path.substring(queryStart);
        const urlParams = new URLSearchParams(searchStr);
        for (const [key, val] of urlParams.entries()) {
          let type = "string";
          if (!isNaN(val) && val.trim() !== "") {
            type = Number.isInteger(parseFloat(val)) ? "integer" : "number";
          } else if (val.toLowerCase() === "true" || val.toLowerCase() === "false") {
            type = "boolean";
          }
          qParams.push({ name: key, type, required: false, description: `Pasted query value: ${val}` });
        }
      }
      if (cleanPath) setPath(cleanPath);
      
      // 2. Detect dynamic path variables in Endpoint Path (e.g. {id} or {endpoint_suffix})
      const pathVarsMatched = cleanPath.match(/\{([^}]+)\}/g);
      if (pathVarsMatched) {
        pathVarsMatched.forEach(match => {
          const name = match.replace(/[{}]/g, "");
          pVars.push({ name, type: "string", required: true, description: `Dynamic endpoint path variable` });
        });
      }
      
      // 3. Parse request body if it's a JSON payload
      if (parsed.body) {
        try {
          const parsedBody = JSON.parse(parsed.body);
          if (parsedBody && typeof parsedBody === "object" && !Array.isArray(parsedBody)) {
            Object.entries(parsedBody).forEach(([key, val]) => {
              let type = typeof val;
              if (type === "number") {
                type = Number.isInteger(val) ? "integer" : "number";
              }
              if (type !== "string" && type !== "integer" && type !== "boolean" && type !== "object" && type !== "array") {
                type = "string";
              }
              if (!qParams.some(p => p.name === key)) {
                qParams.push({ name: key, type, required: true, description: `Request body parameter` });
              }
            });
          }
        } catch (e) {
          // fallback payload string
          setPayloadFormat(parsed.body);
        }
      }
      
      setPathVars(pVars);
      setQueryParams(qParams);
      
      if (Object.keys(parsed.headers).length > 0) {
        setHeaders(JSON.stringify(parsed.headers, null, 2));
      }
    }
  };

  const handleTestWebhook = async () => {
    if (!baseUrl) {
      toast.error("Base URL is required to test.");
      return;
    }
    
    setIsTestingWebhook(true);
    let parsedHeaders = {};
    try {
      if (headers && headers.trim() !== "") {
        parsedHeaders = JSON.parse(headers);
      }
    } catch (e) {
      toast.error("Headers must be valid JSON");
      setIsTestingWebhook(false);
      return;
    }
    
    if (apiKey) {
      parsedHeaders["Authorization"] = apiKey;
    }

    const fullUrl = `${baseUrl}${path && !path.startsWith('/') ? '/' + path : path || ''}`;
    
    try {
      const options = {
        method: method,
        headers: parsedHeaders,
      };
      
      if (method !== "GET" && method !== "HEAD" && payloadFormat) {
        options.body = payloadFormat;
      }
      
      const res = await fetch(fullUrl, options);
      const data = await res.json().catch(() => null);
      
      if (data) {
        setExpectedOutput(JSON.stringify(data, null, 2));
        toast.success(`Tested successfully! Responded with status ${res.status}`);
      } else {
        setExpectedOutput(`{"status": ${res.status}}`);
        toast.success(`Tested successfully! (No JSON returned)`);
      }
    } catch (err) {
      console.error("Test Webhook Error:", err);
      toast.error("Test failed. Check console for CORS or network errors.");
    } finally {
      setIsTestingWebhook(false);
    }
  };

  const handleTestDb = async () => {
    let connStr = connectionString;
    if (dbMode === "form") {
      if (!dbHost.trim() || !dbName.trim() || !dbUser.trim() || !dbPassword.trim()) {
        toast.error("Please fill in all connection details before testing");
        return;
      }
      connStr = `postgresql://${dbUser.trim()}:${dbPassword.trim()}@${dbHost.trim()}:${dbPort.trim()}/${dbName.trim()}`;
    }
    
    if (!connStr.trim()) {
      toast.error("Database connection string is required");
      return;
    }
    
    setIsTestingDb(true);
    const id = toast.loading("Testing database connection...");
    try {
      const res = await testDatabaseConnection(connStr);
      if (res.status === "success") {
        toast.success(res.message || "Database connected successfully!", { id });
      } else {
        toast.error(res.message || "Connection failed", { id });
      }
    } catch (err) {
      toast.error(err.message || "Failed to establish connection", { id });
    } finally {
      setIsTestingDb(false);
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
          llm_model: "openai/gpt-oss-120b",
          path_variables: pathVars.map(v => v.name),
          query_parameters: queryParams.map(v => v.name)
        })
      });
      if (!res.ok) throw new Error("Failed to generate description");
      const data = await res.json();
      if (data?.description) {
        setDescription(data.description);
        
        // Update path variables descriptions
        if (data.path_variables && typeof data.path_variables === "object") {
          setPathVars(prev => prev.map(v => {
            const cleanName = v.name.trim();
            // Match exact key, key without curly braces, or key with curly braces
            const keyWithoutBraces = cleanName.replace(/[{}]/g, "");
            const keyWithBraces = `{${keyWithoutBraces}}`;
            const aiDesc = data.path_variables[cleanName] || data.path_variables[keyWithoutBraces] || data.path_variables[keyWithBraces] || "";
            if (aiDesc) {
              return { ...v, description: aiDesc };
            }
            return v;
          }));
        }

        // Update query parameters descriptions
        if (data.query_parameters && typeof data.query_parameters === "object") {
          setQueryParams(prev => prev.map(p => {
            const cleanName = p.name.trim();
            const aiDesc = data.query_parameters[cleanName] || "";
            if (aiDesc) {
              return { ...p, description: aiDesc };
            }
            return p;
          }));
        }

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
                <div className="bg-primary/10 border border-primary/20 p-4 rounded-xl flex items-start gap-3 animate-in fade-in zoom-in-95 duration-200">
                  <Terminal size={18} className="text-primary mt-0.5 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-primary mb-1">Magic cURL Import</h4>
                    <p className="text-xs text-foreground/80 leading-relaxed">Paste a <span className="font-mono text-primary bg-primary/10 px-1 rounded">cURL</span> command directly into the <strong>Base URL</strong> field to automatically extract and populate all fields below.</p>
                  </div>
                </div>

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
                      onPaste={handleUrlPaste}
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
                  <div className="col-span-full space-y-6">
                    {/* PATH VARIABLES SECTION */}
                    <div className="bg-primary/5 border border-primary/20 p-6 rounded-2xl">
                      <div className="flex justify-between items-center mb-4">
                        <div>
                          <label className="block text-sm font-bold text-primary uppercase">Path Variables</label>
                          <p className="text-xs text-primary/85 mt-1">Parameters that dynamically replace {`{}`} in your Endpoint Path.</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setPathVars([...pathVars, { name: "", type: "string", required: true, description: "" }])}
                          className="text-xs font-bold text-primary hover:text-primary/95 flex items-center gap-1.5 bg-primary/10 border border-primary/20 px-3.5 py-2 rounded-xl transition"
                        >
                          <Plus size={14} /> Add Path Var
                        </button>
                      </div>
                      
                      {pathVars.length === 0 ? (
                        <div className="text-center p-6 border border-dashed border-primary/30 rounded-xl bg-primary/5 text-primary/80 text-sm">
                          No path variables defined. Add one if your URL path contains dynamic variables.<br/>
                          <span className="text-xs text-primary/65 font-mono mt-1.5 block">Example: If path is "/api/v1/products/{`{id}`}", add a variable named "id".</span>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {pathVars.map((param, index) => (
                            <div key={`path-${index}`} className="flex items-start gap-3 p-4 border border-primary/30 bg-background rounded-xl">
                              <div className="flex-1 grid grid-cols-12 gap-3">
                                <div className="col-span-4">
                                  <input
                                    placeholder="Name (e.g. endpoint_suffix)"
                                    value={param.name}
                                    onChange={e => {
                                      const newParams = [...pathVars];
                                      newParams[index].name = e.target.value;
                                      setPathVars(newParams);
                                    }}
                                    className="w-full border border-border rounded-lg p-2.5 bg-background text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                                  />
                                </div>
                                <div className="col-span-8">
                                  <input
                                    placeholder="Description (What does this do?)"
                                    value={param.description}
                                    onChange={e => {
                                      const newParams = [...pathVars];
                                      newParams[index].description = e.target.value;
                                      setPathVars(newParams);
                                    }}
                                    className="w-full border border-border rounded-lg p-2.5 bg-background text-foreground text-sm focus:outline-none"
                                  />
                                </div>
                              </div>
                              <button
                                type="button"
                                onClick={() => {
                                  const newParams = [...pathVars];
                                  newParams.splice(index, 1);
                                  setPathVars(newParams);
                                }}
                                className="p-2.5 bg-red-500/10 text-red-500 rounded-lg hover:bg-red-500/20 shrink-0"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* API PARAMETERS SECTION */}
                    <div className="border border-border p-6 rounded-2xl bg-card/10">
                      <div className="flex justify-between items-center mb-4">
                        <div>
                          <label className="block text-sm font-bold text-muted-foreground uppercase">Query & Body Parameters</label>
                          <p className="text-xs text-muted-foreground mt-1">Parameters sent in the URL query string or request body.</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setQueryParams([...queryParams, { name: "", type: "string", required: true, description: "" }])}
                          className="text-xs font-bold text-foreground hover:bg-muted flex items-center gap-1.5 bg-background border border-border px-3.5 py-2 rounded-xl transition"
                        >
                          <Plus size={14} /> Add Parameter
                        </button>
                      </div>
                      
                      {queryParams.length === 0 ? (
                        <div className="text-center p-6 border border-dashed border-border rounded-xl bg-card/30 text-muted-foreground text-sm animate-in fade-in duration-200">
                          No query or body parameters defined.<br/>
                          <span className="text-xs text-muted-foreground/75 font-mono mt-1.5 block">Example: Add "limit" (Integer) or "min_range" (Integer) to let the AI filter results dynamically.</span>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {queryParams.map((param, index) => (
                            <div key={`query-${index}`} className="flex items-start gap-3 p-4 border border-border bg-card/30 rounded-xl">
                              <div className="flex-1 grid grid-cols-12 gap-3">
                                <div className="col-span-3">
                                  <input
                                    placeholder="Name (e.g. limit)"
                                    value={param.name}
                                    onChange={e => {
                                      const newParams = [...queryParams];
                                      newParams[index].name = e.target.value;
                                      setQueryParams(newParams);
                                    }}
                                    className="w-full border border-border rounded-lg p-2.5 bg-background text-foreground text-sm focus:outline-none"
                                  />
                                </div>
                                <div className="col-span-3">
                                  <select
                                    value={param.type}
                                    onChange={e => {
                                      const newParams = [...queryParams];
                                      newParams[index].type = e.target.value;
                                      setQueryParams(newParams);
                                    }}
                                    className="w-full border border-border rounded-lg p-2.5 bg-background text-foreground text-sm focus:outline-none"
                                  >
                                    <option value="string">String</option>
                                    <option value="integer">Integer</option>
                                    <option value="boolean">Boolean</option>
                                    <option value="object">Object</option>
                                    <option value="array">Array</option>
                                  </select>
                                </div>
                                <div className="col-span-5">
                                  <input
                                    placeholder="Description"
                                    value={param.description}
                                    onChange={e => {
                                      const newParams = [...queryParams];
                                      newParams[index].description = e.target.value;
                                      setQueryParams(newParams);
                                    }}
                                    className="w-full border border-border rounded-lg p-2.5 bg-background text-foreground text-sm focus:outline-none"
                                  />
                                </div>
                                <div className="col-span-1 flex items-center justify-center pt-2">
                                  <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={param.required}
                                      onChange={e => {
                                        const newParams = [...queryParams];
                                        newParams[index].required = e.target.checked;
                                        setQueryParams(newParams);
                                      }}
                                      className="rounded border-border text-foreground focus:ring-primary h-4 w-4"
                                    />
                                    <span className="text-xs font-bold text-muted-foreground uppercase">Req</span>
                                  </label>
                                </div>
                              </div>
                              <button
                                type="button"
                                onClick={() => {
                                  const newParams = [...queryParams];
                                  newParams.splice(index, 1);
                                  setQueryParams(newParams);
                                }}
                                className="p-2.5 bg-red-500/10 text-red-500 rounded-lg hover:bg-red-500/20 shrink-0"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Expected JSON Response</label>
                    <textarea
                      value={expectedOutput}
                      onChange={(e) => setExpectedOutput(e.target.value)}
                      rows={4}
                      className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm font-mono focus:outline-none resize-y"
                      placeholder='{"data": []}'
                    />
                  </div>
                </div>
                
                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={handleTestWebhook}
                    disabled={isTestingWebhook || !baseUrl}
                    className="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary font-bold text-sm transition rounded-xl flex items-center gap-2 disabled:opacity-50"
                  >
                    {isTestingWebhook ? "Testing..." : "Test Request & Auto-fill Output"}
                  </button>
                </div>
              </div>
            ) : toolType === "database" ? (
              <div className="bg-card/20 border border-border p-6 rounded-2xl space-y-5 animate-in fade-in duration-200">
                {/* Tabs to toggle mode */}
                <div className="flex border-b border-border mb-2">
                  <button
                    type="button"
                    onClick={() => setDbMode("form")}
                    className={`pb-2.5 px-4 font-bold text-xs uppercase tracking-wider transition-all duration-200 border-b-2 ${
                      dbMode === "form"
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Structured Form
                  </button>
                  <button
                    type="button"
                    onClick={() => setDbMode("uri")}
                    className={`pb-2.5 px-4 font-bold text-xs uppercase tracking-wider transition-all duration-200 border-b-2 ${
                      dbMode === "uri"
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Connection URI String
                  </button>
                </div>

                {dbMode === "uri" ? (
                  <div className="space-y-4 animate-in fade-in duration-150">
                    <div>
                      <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">PostgreSQL Database Connection URI</label>
                      <input
                        required={dbMode === "uri"}
                        type="password"
                        value={connectionString}
                        onChange={(e) => {
                          const val = e.target.value;
                          setConnectionString(val);
                          const parsed = parseConnectionString(val);
                          setDbHost(parsed.host);
                          setDbPort(parsed.port);
                          setDbName(parsed.database);
                          setDbUser(parsed.user);
                          setDbPassword(parsed.password);
                        }}
                        className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        placeholder="postgresql://user:password@localhost:5432/db_name"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-5 animate-in fade-in duration-150">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Database Type</label>
                        <select
                          value={dbType}
                          onChange={(e) => setDbType(e.target.value)}
                          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                        >
                          <option value="postgresql">PostgreSQL</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Host / Server Address</label>
                        <input
                          required={dbMode === "form"}
                          value={dbHost}
                          onChange={(e) => {
                            const val = e.target.value;
                            setDbHost(val);
                            if (val && dbName && dbUser && dbPassword) {
                              setConnectionString(`postgresql://${dbUser.trim()}:${dbPassword.trim()}@${val.trim()}:${dbPort.trim()}/${dbName.trim()}`);
                            }
                          }}
                          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                          placeholder="e.g. ec2-18-233-32-61.compute-1.amazonaws.com"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Port</label>
                        <input
                          required={dbMode === "form"}
                          value={dbPort}
                          onChange={(e) => {
                            const val = e.target.value;
                            setDbPort(val);
                            if (dbHost && dbName && dbUser && dbPassword) {
                              setConnectionString(`postgresql://${dbUser.trim()}:${dbPassword.trim()}@${dbHost.trim()}:${val.trim()}/${dbName.trim()}`);
                            }
                          }}
                          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                          placeholder="5432"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Database Name</label>
                        <input
                          required={dbMode === "form"}
                          value={dbName}
                          onChange={(e) => {
                            const val = e.target.value;
                            setDbName(val);
                            if (dbHost && val && dbUser && dbPassword) {
                              setConnectionString(`postgresql://${dbUser.trim()}:${dbPassword.trim()}@${dbHost.trim()}:${dbPort.trim()}/${val.trim()}`);
                            }
                          }}
                          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                          placeholder="e.g. d3j5s5ce29g1sb"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">User Name</label>
                        <input
                          required={dbMode === "form"}
                          value={dbUser}
                          onChange={(e) => {
                            const val = e.target.value;
                            setDbUser(val);
                            if (dbHost && dbName && val && dbPassword) {
                              setConnectionString(`postgresql://${val.trim()}:${dbPassword.trim()}@${dbHost.trim()}:${dbPort.trim()}/${dbName.trim()}`);
                            }
                          }}
                          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                          placeholder="e.g. hynvocnxbhzfrq"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-muted-foreground mb-1.5 uppercase">Password</label>
                      <input
                        required={dbMode === "form"}
                        type="password"
                        value={dbPassword}
                        onChange={(e) => {
                          const val = e.target.value;
                          setDbPassword(val);
                          if (dbHost && dbName && dbUser && val) {
                            setConnectionString(`postgresql://${dbUser.trim()}:${val.trim()}@${dbHost.trim()}:${dbPort.trim()}/${dbName.trim()}`);
                          }
                        }}
                        className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none"
                        placeholder="Database user password"
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={handleTestDb}
                    disabled={isTestingDb}
                    className="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary font-bold text-sm transition rounded-xl flex items-center gap-2 disabled:opacity-50"
                  >
                    {isTestingDb ? "Testing Connection..." : "Test Connection"}
                  </button>
                </div>

                <p className="text-[10px] text-muted-foreground leading-relaxed mt-2">
                  Credentials are stored securely. RAGMate agents will only execute read-only queries (SELECT) to retrieve Relational Database schemas and records.
                </p>
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
