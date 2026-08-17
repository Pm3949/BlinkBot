import React, { useState, useMemo } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Pencil, BarChart2, TrendingUp, DollarSign, Activity } from "lucide-react";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import { UploadCloud, Search, CheckCircle2, AlertCircle, Link2, Eye, FileText, Cloud, MessageSquare, Code, Globe, Loader2, Bot, Brain, Key, Sparkles, Network, Plus, Trash2, Settings2, Database, Blocks, Terminal, Library, ChevronDown, ChevronUp, Zap, Lock, ExternalLink, RefreshCw, Wrench, ArrowDown } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useRef, useEffect } from "react";
import { useWorkspacePermissions, useUserSettings, useUpdateUserSettings } from "../hooks/useSettings";
import { useActiveModels, useAvailableModels } from "../hooks/useModels";
import { useAuth } from "../context/AuthContext";
import { useProjectTools } from "../hooks/useAgents";
import { useDeleteDocument, useDocuments, useProcessUrl, useUploadDocument, useProcessConnector, useUpdateUrl, useProcessText, useUpdateText, useUpdateFile, useSyncConnector } from "../hooks/useDocuments";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { useUIStore } from "../store/useUIStore";
import { getWorkspaceTools, getAgentAttachedTools, attachToolToAgent, detachToolFromAgent } from "../services/workspaceToolsService";
import { Webhook, FileCode } from "lucide-react";

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, AreaChart, Area } from "recharts";

import { toast } from "sonner";
import { getAuthHeaders } from "../lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  providers,
  AVAILABLE_MODELS,
  EMBEDDING_MODELS,
  CHUNKING_STRATEGIES,
  LANGUAGES
} from "../components/agents/CreateAgentWizard";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const formatBytes = (bytes, decimals = 2) => {
  if (!bytes) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
};

const getDocumentSource = (doc) => {
  return doc.filename || doc.name || "Unknown Document";
};

const StatusBadge = ({ status }) => {
  const styles = {
    completed: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    processing: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    failed: "bg-red-500/10 text-red-500 border-red-500/20",
  };
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${styles[status] || "bg-muted text-muted-foreground border-border"}`}>
      {label}
    </span>
  );
};

export default function AgentSettingsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { agentId } = useParams();

  // Use agent passed via router state
  const agent = location.state?.agent;

  const queryClient = useQueryClient();

  const fileInputRef = useRef(null);
  const { user } = useAuth();
  const { canManageStudio } = useWorkspacePermissions();
  const [sourceTab, setSourceTab] = useState("files");
  const [connectingTo, setConnectingTo] = useState(null);
  const [url, setUrl] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [previewDoc, setPreviewDoc] = useState(null);
  const [expandedEndpoints, setExpandedEndpoints] = useState({});
  const [expandedDatabases, setExpandedDatabases] = useState({});

  const selectedAgentId = agent?.id;

  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const [workspaceTools, setWorkspaceTools] = useState([]);
  const [attachedToolIds, setAttachedToolIds] = useState(new Set());
  const [loadingTools, setLoadingTools] = useState(false);
  const [isBrowseModalOpen, setIsBrowseModalOpen] = useState(false);
  const [isAddDropdownOpen, setIsAddDropdownOpen] = useState(false);

  useEffect(() => {
    const loadWorkspaceToolsData = async () => {
      if (!activeWorkspaceId || !selectedAgentId) return;
      setLoadingTools(true);
      try {
        const [allTools, attached] = await Promise.all([
          getWorkspaceTools(activeWorkspaceId),
          getAgentAttachedTools(selectedAgentId)
        ]);
        setWorkspaceTools(allTools);
        setAttachedToolIds(new Set(attached.map(t => t.id)));
      } catch (err) {
        console.error("Error loading tools data:", err);
      } finally {
        setLoadingTools(false);
      }
    };
    loadWorkspaceToolsData();
  }, [activeWorkspaceId, selectedAgentId]);

  const handleToggleTool = async (toolId, isAttached) => {
    try {
      if (isAttached) {
        await detachToolFromAgent(selectedAgentId, toolId);
        setAttachedToolIds(prev => {
          const next = new Set(prev);
          next.delete(toolId);
          return next;
        });
        toast.success("Tool detached successfully");
      } else {
        await attachToolToAgent(selectedAgentId, toolId);
        setAttachedToolIds(prev => {
          const next = new Set(prev);
          next.add(toolId);
          return next;
        });
        toast.success("Tool attached successfully");
      }
    } catch (err) {
      toast.error(err.message || "Failed to update tool attachment");
    }
  };


  const { data: documents = [], isError, isLoading, error } = useDocuments(selectedAgentId);
  const uploadMutation = useUploadDocument(selectedAgentId);
  const processUrlMutation = useProcessUrl(selectedAgentId);
  const deleteMutation = useDeleteDocument(selectedAgentId);
  const processConnectorMutation = useProcessConnector(selectedAgentId);
  const updateUrlMutation = useUpdateUrl(selectedAgentId);
  const processTextMutation = useProcessText(selectedAgentId);
  const updateTextMutation = useUpdateText(selectedAgentId);
  const updateFileMutation = useUpdateFile(selectedAgentId);
  const syncConnectorMutation = useSyncConnector(selectedAgentId);

  // Editing & creation state
  const [editingDoc, setEditingDoc] = useState(null);
  const [isUrlEditOpen, setIsUrlEditOpen] = useState(false);
  const [isTextEditOpen, setIsTextEditOpen] = useState(false);
  const [textFilename, setTextFilename] = useState("");
  const [textContent, setTextContent] = useState("");
  const [editUrlValue, setEditUrlValue] = useState("");
  const [newTextFilename, setNewTextFilename] = useState("");
  const [newTextContent, setNewTextContent] = useState("");

  // Re-upload target
  const [replaceTargetDocId, setReplaceTargetDocId] = useState(null);
  const replaceFileInputRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  // WebSocket for Document Ingestion Status Updates
  useEffect(() => {
    if (!selectedAgentId) return;

    const wsBaseUrl = API_URL.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsBaseUrl}/ws/documents/upload/status/${selectedAgentId}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const { status, filename, detail } = data;

        if (status === "chunking") toast.loading(`Chunking ${filename}...`, { id: filename });
        else if (status === "embeddings") toast.loading(`Generating embeddings for ${filename}...`, { id: filename });
        else if (status === "indexing") toast.loading(`Indexing ${filename}...`, { id: filename });
        else if (status === "completed") {
          toast.success(`Successfully processed ${filename}!`, { id: filename });
          queryClient.invalidateQueries({ queryKey: ["documents", selectedAgentId] });
        } else if (status === "failed") {
          toast.error(`Processing failed for ${filename}: ${detail}`, { id: filename });
          queryClient.invalidateQueries({ queryKey: ["documents", selectedAgentId] });
        }
      } catch (err) { }
    };

    return () => ws.close();
  }, [selectedAgentId, queryClient]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (!normalizedSearch) return documents;
    return documents.filter((doc) => getDocumentSource(doc).toLowerCase().includes(normalizedSearch));
  }, [documents, searchTerm]);

  const isMutating = uploadMutation.isPending || processUrlMutation.isPending || deleteMutation.isPending || processConnectorMutation.isPending;

  const handleFileChange = async (event) => {
    if (!canManageStudio) return toast.error("No permission to upload files.");
    const files = Array.from(event.target.files || []);
    if (files.length === 0 || !selectedAgentId) return;
    try {
      const uploadPromises = files.map((file) => uploadMutation.mutateAsync({ agentId: selectedAgentId, file }));
      await Promise.all(uploadPromises);
      toast.success(files.length > 1 ? `${files.length} files uploaded` : "File uploaded");
      
      const hasCsv = files.some(f => f.name.toLowerCase().endsWith('.csv') || f.type === 'text/csv');
      if (hasCsv && !formData.code_interpreter_enabled) {
        toast("CSV uploaded, but Code Sandbox is disabled.", {
          description: "The agent will not be able to execute Python code or parse CSV data without the Sandbox enabled.",
          action: {
            label: "Enable Sandbox",
            onClick: () => {
              updateField("code_interpreter_enabled", true);
              const payload = {
                name: formData.name.trim(),
                description: formData.description.trim(),
                llm_provider: formData.provider,
                llm_model: formData.model,
                embedding_model: formData.embedding_model,
                chunk_strategy: formData.chunk_strategy,
                system_prompt: formData.system_prompt.trim(),
                output_format: formData.output_format.trim(),
                api_key: selectedModel?.requiresKey ? formData.api_key.trim() : null,
                language: formData.language,
                web_search_enabled: formData.web_search_enabled,
                code_interpreter_enabled: true,
                databases: formData.databases,
                native_integrations: formData.native_integrations,
                endpoints: formData.endpoints,
              };
              updateAgentMutation.mutate(payload);
            }
          }
        });
      }
    } catch (e) {
      toast.error(e.message || "Failed to upload.");
    } finally {
      event.target.value = "";
    }
  };

  const handleProcessUrl = async () => {
    if (!canManageStudio) return toast.error("No permission to scrape.");
    const trimmedUrl = url.trim();
    if (!selectedAgentId || !trimmedUrl) return toast.error("Enter a valid URL.");
    try {
      await processUrlMutation.mutateAsync({ agentId: selectedAgentId, url: trimmedUrl });
      setUrl("");
      toast.success("Website queued for processing");
    } catch (e) {
      toast.error(e.message || "Failed to scrape.");
    }
  };

  const handleDelete = async (documentId) => {
    try {
      await deleteMutation.mutateAsync(documentId);
      toast.success("Document deleted");
    } catch (e) {
      toast.error(e.message || "Unable to delete document.");
    }
  };

  const handleCreateText = async (filename, text) => {
    if (!canManageStudio) return toast.error("No permission.");
    try {
      await processTextMutation.mutateAsync({ filename, text });
      toast.success("Text snippet queued for ingestion");
    } catch (e) {
      toast.error(e.message || "Failed to create text snippet.");
    }
  };

  const handleEditClick = (doc) => {
    setEditingDoc(doc);
    if (doc.filename.startsWith("http://") || doc.filename.startsWith("https://")) {
      setEditUrlValue(doc.filename);
      setIsUrlEditOpen(true);
    } else if (doc.filename.endsWith(".txt")) {
      toast.loading("Loading text content...", { id: "load-text" });
      const token = localStorage.getItem("access_token");
      fetch(`${API_URL}/api/documents/${doc.id}/view`, {
        headers: { "Authorization": `Bearer ${token}` }
      })
      .then(r => r.text())
      .then(t => {
        toast.dismiss("load-text");
        setTextContent(t);
        setTextFilename(doc.filename);
        setIsTextEditOpen(true);
      })
      .catch(() => {
        toast.error("Failed to load text content", { id: "load-text" });
        setTextContent("");
        setTextFilename(doc.filename);
        setIsTextEditOpen(true);
      });
    }
  };

  const handleUpdateUrl = async () => {
    if (!editingDoc) return;
    try {
      await updateUrlMutation.mutateAsync({ docId: editingDoc.id, url: editUrlValue });
      setIsUrlEditOpen(false);
      toast.success("URL updated and queued for re-scraping");
    } catch (e) {
      toast.error(e.message || "Failed to update URL.");
    }
  };

  const handleUpdateText = async () => {
    if (!editingDoc) return;
    try {
      await updateTextMutation.mutateAsync({ docId: editingDoc.id, filename: textFilename, text: textContent });
      setIsTextEditOpen(false);
      toast.success("Text snippet updated and queued for re-embedding");
    } catch (e) {
      toast.error(e.message || "Failed to update text snippet.");
    }
  };

  const handleReplaceFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !replaceTargetDocId) return;
    try {
      await updateFileMutation.mutateAsync({ docId: replaceTargetDocId, file });
      toast.success("File replaced and queued for re-embedding");
      setReplaceTargetDocId(null);
    } catch (e) {
      toast.error(e.message || "Failed to replace file.");
    }
  };

  const handleSyncConnectorClick = async (docId) => {
    try {
      await syncConnectorMutation.mutateAsync({ docId });
      toast.success("Connector sync triggered");
    } catch (e) {
      toast.error(e.message || "Failed to sync connector.");
    }
  };

  const handleConnect = async (connectorId, connectorName) => {
    if (!canManageStudio) return toast.error("No permission.");
    if (connectorId === "gdrive") {
      toast.info("Google Drive connection initiated.");
      // GDrive logic stripped for brevity inside the modal script unless explicitly needed
      return;
    }
    setConnectingTo(connectorId);
    try {
      await processConnectorMutation.mutateAsync({ agentId: selectedAgentId, connectorId });
      toast.success(`Connected to ${connectorName}`);
    } catch (e) {
      toast.error(e.message || `Failed to connect.`);
    } finally {
      setConnectingTo(null);
    }
  };

  const { data: globalConnections = [] } = useProjectTools(agent?.project_id);
  const [activeTab, setActiveTab] = useState("identity");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [toolsSubView, setToolsSubView] = useState("hub");

  const [agentMemory, setAgentMemory] = useState([]);
  const [loadingMemory, setLoadingMemory] = useState(false);

  const fetchMemory = async () => {
    // Memory list rendering is retired, keeping placeholder to prevent build breaks
    setAgentMemory([]);
  };

  useEffect(() => {
    if (activeTab === "memory") {
      fetchMemory();
    }
  }, [activeTab, selectedAgentId]);

  const handleDeleteMemoryItem = async (itemId) => {
    try {
      const res = await fetch(`${API_URL}/api/feedback/${itemId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (res.ok) {
        toast.success("Memory entry removed successfully!");
        fetchMemory();
      } else {
        toast.error("Failed to remove memory entry.");
      }
    } catch (err) {
      toast.error("Failed to remove memory entry.");
    }
  };

  const handleClearAllMemory = async () => {
    if (!window.confirm("Are you sure you want to permanently wipe all conversation history, chat threads, and logs for this agent? This action is irreversible.")) return;
    try {
      const res = await fetch(`${API_URL}/api/agents/${selectedAgentId}/chat_sessions`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (res.ok) {
        toast.success("Agent conversation history wiped successfully!");
        setAgentMemory([]);
      } else {
        toast.error("Failed to wipe agent conversation history.");
      }
    } catch (err) {
      toast.error("Failed to wipe agent conversation history.");
    }
  };

  const handleOptimizePrompt = async () => {
    if (!formData.system_prompt.trim()) {
      toast.error("Please enter a draft prompt to optimize.");
      return;
    }
    setIsOptimizing(true);
    try {
      const response = await fetch(`${API_URL}/api/agents/optimize-prompt`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          draft_prompt: formData.system_prompt,
          llm_provider: formData.provider,
          llm_model: formData.model,
          custom_api_key: formData.api_key || ""
        })
      });
      if (!response.ok) throw new Error("Failed to optimize prompt");
      const data = await response.json();
      updateField("system_prompt", data.optimized_prompt);
      toast.success("Prompt optimized successfully!");
    } catch (err) {
      toast.error("Failed to optimize prompt. Please try again.");
    } finally {
      setIsOptimizing(false);
    }
  };

  const [generatingDescriptionIdx, setGeneratingDescriptionIdx] = useState(null);

  const handleGenerateDescription = async (idx) => {
    const ep = formData.endpoints[idx];
    if (!ep.name || !ep.name.trim()) {
      toast.error("Please provide at least the Endpoint Name to generate a description.");
      return;
    }
    setGeneratingDescriptionIdx(idx);
    try {
      const response = await fetch(`${API_URL}/api/agents/generate-tool-description`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          tool_name: ep.name,
          path: ep.path || "",
          method: ep.method || "GET",
          payload_format: ep.payload_format || "",
          expected_output: ep.expected_output || "",
          llm_provider: formData.provider,
          llm_model: formData.model,
          custom_api_key: formData.api_key || ""
        })
      });
      if (!response.ok) throw new Error("Failed to generate description");
      const data = await response.json();
      const newEps = [...formData.endpoints];
      newEps[idx].description = data.description;
      updateField("endpoints", newEps);
      toast.success("Description generated successfully!");
    } catch (err) {
      toast.error("Failed to generate description. Please try again.");
    } finally {
      setGeneratingDescriptionIdx(null);
    }
  };

  const [analytics, setAnalytics] = useState(null);
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(false);

  const fetchAnalytics = async () => {
    if (!selectedAgentId) return;
    setIsAnalyticsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/agents/${selectedAgentId}/analytics`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setIsAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "analytics") {
      fetchAnalytics();
    }
  }, [activeTab, selectedAgentId]);

  const dailyDataWithCumulative = useMemo(() => {
    if (!analytics || !analytics.daily) return [];
    let runningSum = 0;
    return analytics.daily.map(day => {
      runningSum += day.cost;
      return {
        ...day,
        cumulative_cost: runningSum
      };
    });
  }, [analytics]);

  const totalCalls = useMemo(() => {
    if (!analytics || !analytics.daily) return 0;
    return analytics.daily.reduce((sum, day) => sum + (day.calls || 0), 0);
  }, [analytics]);

  const avgCostPerQuery = useMemo(() => {
    if (!analytics || !analytics.totals || totalCalls === 0) return 0;
    return analytics.totals.estimated_cost / totalCalls;
  }, [analytics, totalCalls]);

  const [validationErrors, setValidationErrors] = useState({});

  const prefillPayloadTemplate = (idx) => {
    const newEps = [...formData.endpoints];
    const method = newEps[idx].method || "GET";
    if (method === "GET" || method === "DELETE") {
      newEps[idx].payload_format = JSON.stringify({ id: "{id}" }, null, 2);
      newEps[idx].expected_output = JSON.stringify({ success: true, data: { status: "active" } }, null, 2);
    } else {
      newEps[idx].payload_format = JSON.stringify({ name: "John Doe", email: "john@example.com" }, null, 2);
      newEps[idx].expected_output = JSON.stringify({ status: "success", id: 123 }, null, 2);
    }
    updateField("endpoints", newEps);
    toast.success("Sample template pre-filled!");
  };



  const [formData, setFormData] = useState({
    name: agent?.name || "",
    description: agent?.description || "",
    provider: agent?.llm_provider || "groq",
    model: agent?.llm_model || "llama-3.3-70b-versatile",
    embedding_model: agent?.embedding_model || "all-MiniLM-L6-v2",
    chunk_strategy: agent?.chunk_strategy || "sentence",
    system_prompt: agent?.system_prompt || "",
    output_format: agent?.output_format || "",
    api_key: agent?.api_key || "",
    language: agent?.language || "en",
    web_search_enabled: agent?.web_search_enabled || false,
    endpoints: agent?.endpoints || [],
    databases: agent?.databases || [],
    code_interpreter_enabled: agent?.code_interpreter_enabled || false,
    native_integrations: agent?.native_integrations || [],
    memory_enabled: agent?.memory_enabled !== false,
  });

  const { data: activeModelsData, isLoading: isModelsLoading } = useAvailableModels();
  const { data: userSettings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();
  const [showCustomOverride, setShowCustomOverride] = useState(false);

  const isProviderKeyPresent = (provider) => {
    if (formData.api_key?.trim()) return true;
    const keyName = `${provider}_api_key`;
    return Boolean(userSettings?.[keyName]?.trim());
  };

  const dynamicModels = useMemo(() => {
    if (activeModelsData?.providers) {
      const formatted = {};
      Object.keys(activeModelsData.providers).forEach((prov) => {
        formatted[prov] = activeModelsData.providers[prov].map((m) => ({
          id: m.model_id,
          name: m.name,
          requiresKey: m.requires_key,
          description: m.description,
          credits_per_1k_tokens: m.credits_per_1k_tokens,
          tier_badge: m.tier_badge,
          user_id: m.user_id,
          input_cost_per_1m: m.input_cost_per_1m,
          output_cost_per_1m: m.output_cost_per_1m,
        }));
      });
      return formatted;
    }
    return AVAILABLE_MODELS;
  }, [activeModelsData]);

  const dynamicProviders = useMemo(() => {
    if (activeModelsData?.providers) {
      const activeProviders = Object.keys(activeModelsData.providers);
      const displayNames = {
        groq: "Groq",
        openai: "OpenAI",
        openrouter: "OpenRouter",
        huggingface: "HuggingFace",
        anthropic: "Anthropic",
        gemini: "Gemini",
        ollama: "Ollama",
        custom_openai: "Custom Server"
      };
      return activeProviders.map(p => ({
        id: p,
        name: displayNames[p] || p.toUpperCase()
      }));
    }
    return providers;
  }, [activeModelsData]);

  const currentModels = useMemo(
    () => dynamicModels[formData.provider] || AVAILABLE_MODELS[formData.provider] || [],
    [formData.provider, dynamicModels]
  );

  const selectedModel = currentModels.find(
    (model) => model.id === formData.model
  );

  const updateField = (key, value) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
      ...(key === "provider"
        ? {
          model:
            (dynamicModels[value] || AVAILABLE_MODELS[value])?.find((availableModel) => availableModel.id)?.id || prev.model,
        }
        : {}),
    }));
  };

  const updateAgentMutation = useMutation({
    mutationFn: async (payload) => {
      const response = await fetch(`${API_URL}/api/agents/${agent.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('Failed to update agent');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents", agent.workspace_id] });
      queryClient.invalidateQueries({ queryKey: ["agent-projects-sub-agents"] });
      toast.success("Agent settings updated");
      // Stay on page after save
      // navigate(-1);
    },
    onError: () => {
      toast.error("Failed to update agent settings");
    }
  });

  const handleSave = () => {
    setValidationErrors({});

    if (!formData.name.trim()) {
      toast.error("Agent name is required.");
      return;
    }

    const errors = {};

    // Validate API Endpoints
    const endpoints = formData.endpoints || [];
    for (let i = 0; i < endpoints.length; i++) {
      const ep = endpoints[i];
      if (!ep.name || !ep.name.trim()) {
        toast.error(`API Endpoint #${i + 1}: Name is required.`);
        errors[`endpoint_${i}_name`] = true;
      }
      if (!ep.path || !ep.path.trim()) {
        toast.error(`API Endpoint "${ep.name || 'Unnamed'}": Path is required.`);
        errors[`endpoint_${i}_path`] = true;
      }
      if (!agent?.project_id && (!ep.base_url || !ep.base_url.trim())) {
        toast.error(`API Endpoint "${ep.name || 'Unnamed'}": Base URL is required.`);
        errors[`endpoint_${i}_base_url`] = true;
      }
      if (agent?.project_id && (!ep.connection_id || !ep.connection_id.trim())) {
        toast.error(`API Endpoint "${ep.name || 'Unnamed'}": API Connection is required.`);
        errors[`endpoint_${i}_connection_id`] = true;
      }
      if (!ep.description || !ep.description.trim()) {
        toast.error(`API Endpoint "${ep.name || 'Unnamed'}": Description is required.`);
        errors[`endpoint_${i}_description`] = true;
      }
    }

    // Validate Databases
    const dbs = formData.databases || [];
    for (let i = 0; i < dbs.length; i++) {
      const db = dbs[i];
      if (!db.name || !db.name.trim()) {
        toast.error(`Database #${i + 1}: Name is required.`);
        errors[`database_${i}_name`] = true;
      }
      if (!db.connection_string || !db.connection_string.trim()) {
        toast.error(`Database "${db.name || 'Unnamed'}": Connection String is required.`);
        errors[`database_${i}_connection_string`] = true;
      }
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }



    // If API key was typed, also save it to common DB user_settings so Models page and all agents benefit
    if (selectedModel?.requiresKey && formData.api_key?.trim() && formData.provider) {
      const keyName = `${formData.provider}_api_key`;
      updateSettingsMutation.mutate({ [keyName]: formData.api_key.trim() });
    }

    const payload = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      llm_provider: formData.provider,
      llm_model: formData.model,
      embedding_model: formData.embedding_model,
      chunk_strategy: formData.chunk_strategy,
      system_prompt: formData.system_prompt.trim(),
      output_format: formData.output_format.trim(),
      api_key: selectedModel?.requiresKey ? formData.api_key.trim() : null,
      language: formData.language,
      web_search_enabled: formData.web_search_enabled,
      code_interpreter_enabled: formData.code_interpreter_enabled,
      databases: formData.databases,
      native_integrations: formData.native_integrations,
      endpoints: formData.endpoints,
      memory_enabled: formData.memory_enabled,
    };

    updateAgentMutation.mutate(payload);
  };

  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)] bg-background">
        <h2 className="text-xl font-bold mb-4">Agent not found</h2>
        <p className="text-muted-foreground mb-6">Please navigate from the Studio or Chat page to edit agent settings.</p>
        <button onClick={() => navigate(-1)} className="px-4 py-2 bg-primary text-primary-foreground rounded-xl">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-background overflow-hidden relative">
      {/* Header */}
      <div className="h-16 shrink-0 border-b border-border/50 bg-card flex items-center justify-between px-6 z-10 shadow-sm relative">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-muted text-muted-foreground transition-colors"
            title="Go Back"
          >
            <ArrowLeft size={18} />
          </button>

          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <Settings2 size={18} />
          </div>
          <div>
            <h2 className="text-lg font-bold leading-tight">{agent?.name} Settings</h2>
            <p className="text-xs text-muted-foreground">Configure behavior, knowledge, and capabilities</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="rounded-xl px-6" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button className="rounded-xl px-8 shadow-md" onClick={handleSave} disabled={updateAgentMutation.isPending}>
            {updateAgentMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 shrink-0 border-r border-border/50 bg-muted/10 p-4 space-y-1 overflow-y-auto h-full">
          {(() => {
            const isCoreManagerAgent = agent?.name === "Network Manager" || agent?.name === "General Assistant";
            const settingsTabs = isCoreManagerAgent
              ? [
                  { id: "identity", label: "Identity", icon: Bot },
                  { id: "behavior", label: "Behavior", icon: Brain },
                  { id: "model", label: "Model & AI", icon: Sparkles },
                  { id: "memory", label: "Memory", icon: Activity },
                  { id: "analytics", label: "Cost & Analytics", icon: BarChart2 },
                ]
              : [
                  { id: "identity", label: "Identity", icon: Bot },
                  { id: "behavior", label: "Behavior", icon: Brain },
                  { id: "model", label: "Model & AI", icon: Sparkles },
                  { id: "memory", label: "Memory", icon: Activity },
                  { id: "knowledge-base", label: "Knowledge Base", icon: Library },
                  { id: "tools", label: "Tools", icon: Wrench },
                  { id: "analytics", label: "Cost & Analytics", icon: BarChart2 },
                ];

            return settingsTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium ${activeTab === tab.id
                  ? "bg-primary text-primary-foreground shadow-md"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ));
          })()}
        </div>

        {/* Content */}
        <div className="flex-1 bg-background relative flex flex-col h-full overflow-hidden">
          <div className="flex-1 overflow-y-auto p-8 lg:p-12">
            <div className="w-full mx-auto">

              {activeTab === 'identity' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Identity</h3>
                    <p className="text-muted-foreground text-sm mt-1">Configure basic information about this agent.</p>
                  </div>
                  <div className="space-y-5 bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div>
                      <label className="block text-sm font-semibold mb-1.5">Agent Name</label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => updateField("name", e.target.value)}
                        className="w-full bg-background border border-border rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold mb-1.5">Description</label>
                      <input
                        type="text"
                        value={formData.description}
                        onChange={(e) => updateField("description", e.target.value)}
                        className="w-full bg-background border border-border rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold mb-1.5">Primary Language</label>
                      <Select value={formData.language} onValueChange={(val) => updateField("language", val)}>
                        <SelectTrigger className="w-full rounded-xl py-5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {LANGUAGES.map((l) => (
                            <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'model' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h3 className="text-2xl font-bold flex items-center gap-2">
                        <Brain className="text-primary" size={24} /> AI Model & Intelligence Engine
                      </h3>
                      <p className="text-muted-foreground text-sm mt-1">
                        Configure the primary LLM engine, embedding model, and inference parameters powering this agent.
                      </p>
                    </div>
                    {activeModelsData && (
                      <div className="p-3 px-4 bg-card border border-border flex items-center gap-3 shrink-0 shadow-sm rounded-2xl">
                        <Zap className="text-primary" size={16} />
                        <div>
                          <div className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Wallet Balance</div>
                          <div className="text-sm font-black text-foreground">
                            ${(activeModelsData.credit_balance || 0).toFixed(2)} Credits
                          </div>
                        </div>
                        {(activeModelsData.credit_balance || 0) <= 0 && (
                          <button
                            onClick={() => window.location.href = "/billing"}
                            className="ml-2 px-2.5 py-1 text-[11px] font-bold text-white bg-primary rounded-lg hover:bg-primary/90 transition-colors"
                          >
                            Top Up
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Main Container */}
                  <div className="space-y-6 bg-card p-6 sm:p-8 rounded-3xl border border-border shadow-md">
                    {/* Provider Selection */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                        1. Select AI Provider Platform
                      </label>
                      {isModelsLoading ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                          {Array.from({ length: 6 }).map((_, i) => (
                            <div
                              key={i}
                              className="h-16 rounded-2xl bg-muted/50 animate-pulse border border-border/40"
                            />
                          ))}
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                          {dynamicProviders.map((p) => {
                            const isSelected = formData.provider === p.id;
                            return (
                              <button
                                key={p.id}
                                type="button"
                                onClick={() => updateField("provider", p.id)}
                                className={`p-3.5 rounded-2xl border text-center transition-all relative flex flex-col justify-center items-center h-16 ${
                                  isSelected
                                    ? "border-primary bg-primary/10 text-primary font-bold shadow-sm ring-1 ring-primary"
                                    : "border-border/70 hover:border-primary/40 bg-background text-muted-foreground hover:text-foreground font-semibold"
                                }`}
                              >
                                <h4 className="text-xs capitalize">{p.name}</h4>
                                {isSelected && (
                                  <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-primary" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Specific Model Selection */}
                    <div className="pt-2 border-t border-border/50 space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
                          2. Select Specific Model
                        </label>
                        {isModelsLoading ? (
                          <div className="h-4 w-28 rounded-full bg-muted/60 animate-pulse" />
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Available: {currentModels.length} models
                          </span>
                        )}
                      </div>

                      {isModelsLoading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {Array.from({ length: 4 }).map((_, i) => (
                            <div
                              key={i}
                              className="p-5 rounded-2xl border border-border/40 bg-muted/20 animate-pulse space-y-3"
                            >
                              {/* Badge + Lock row */}
                              <div className="flex items-center justify-between">
                                <div className="h-4 w-20 rounded-full bg-muted/70" />
                                <div className="h-4 w-14 rounded-full bg-muted/50" />
                              </div>
                              {/* Model name */}
                              <div className="h-4 w-3/4 rounded-full bg-muted/70" />
                              {/* Model ID */}
                              <div className="h-3 w-1/2 rounded-full bg-muted/50" />
                              {/* Description lines */}
                              <div className="space-y-1.5 mt-1">
                                <div className="h-3 w-full rounded-full bg-muted/40" />
                                <div className="h-3 w-5/6 rounded-full bg-muted/40" />
                              </div>
                              {/* Footer divider + burn rate */}
                              <div className="pt-3 border-t border-border/30 mt-2 space-y-2">
                                <div className="h-3 w-2/3 rounded-full bg-muted/50" />
                                <div className="h-3 w-1/2 rounded-full bg-muted/40" />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {currentModels.map((m) => {
                          const isSelected = formData.model === m.id;
                          const isSystem = !m.user_id;
                          const walletBalance = activeModelsData?.credit_balance || 0;
                          
                          const isByokActive = activeModelsData?.allow_byok && activeModelsData?.byok_status?.[formData.provider.toLowerCase()];
                          
                          const isLockedByWallet = isSystem && walletBalance <= 0 && !isByokActive;
                          const isLockedByKey = m.requiresKey && !isProviderKeyPresent(formData.provider);
                          const isLocked = isLockedByWallet || isLockedByKey;

                          const costFactor = m.credits_per_1k_tokens || 0;
                          
                          let runwayText = "";
                          if (isByokActive) {
                            runwayText = "⚡ Unlimited (BYOK Active)";
                          } else if (isSystem) {
                            if (walletBalance <= 0) {
                              runwayText = "⚠️ 0 Credits remaining (Top up required)";
                            } else {
                              const est = Math.floor(walletBalance / (costFactor * 1.5 || 0.15));
                              runwayText = `~${est} Messages runway`;
                            }
                          } else {
                            runwayText = "⚡ Custom Endpoints ($0 Platform Cost)";
                          }

                          // Badging
                          let badgeStyle = "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
                          let badgeText = m.tier_badge || "⚡ Low Burn";
                          if (costFactor > 0.20 && costFactor <= 1.00) {
                            badgeStyle = "bg-blue-500/10 text-blue-500 border-blue-500/20";
                            badgeText = m.tier_badge || "⚖️ Balanced";
                          } else if (costFactor > 1.00) {
                            badgeStyle = "bg-purple-500/10 text-purple-500 border-purple-500/20";
                            badgeText = m.tier_badge || "🔥 High Reasoning";
                          }

                          return (
                            <div
                              key={m.id}
                              onClick={() => {
                                if (isLockedByWallet) {
                                  toast.error("Please top up your wallet on the Billing Page to use this system model.");
                                  return;
                                }
                                if (isLockedByKey) {
                                  toast.error("Please provide the provider API key below to unlock this model.");
                                  return;
                                }
                                updateField("model", m.id);
                              }}
                              className={`p-5 rounded-2xl border transition-all cursor-pointer relative flex flex-col justify-between ${
                                isSelected
                                  ? "border-primary bg-primary/5 ring-1 ring-primary shadow-sm"
                                  : isLocked
                                  ? "border-border/40 bg-muted/20 opacity-60"
                                  : "border-border hover:border-primary/50 bg-background"
                              }`}
                            >
                              <div>
                                <div className="flex items-center justify-between gap-2 mb-2">
                                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${badgeStyle}`}>
                                    {badgeText}
                                  </span>
                                  {isLocked && (
                                    <span className="text-[11px] text-red-500 font-semibold flex items-center gap-1">
                                      <Lock size={12} /> Locked
                                    </span>
                                  )}
                                </div>
                                <h4 className="font-bold text-sm text-foreground">{m.name}</h4>
                                <code className="text-[10px] text-muted-foreground font-mono block mt-1">{m.id}</code>
                                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                                  {m.description || "Versatile intelligence engine optimized for fast completions."}
                                </p>
                              </div>
                              <div className="pt-3 border-t border-border/40 mt-4 flex flex-col gap-2">
                                <div className="flex items-center justify-between text-[11px] relative group/price">
                                  <div className="flex items-center gap-1">
                                    <span className="text-muted-foreground font-medium">Burn Rate:</span>
                                    {(() => {
                                      const inCost = m.input_cost_per_1m || 0;
                                      const outCost = m.output_cost_per_1m || 0;
                                      const costSum = inCost + outCost;
                                      let inputCoeff = costFactor;
                                      let outputCoeff = costFactor;
                                      if (costSum > 0) {
                                        inputCoeff = (inCost / costSum) * 2.0 * costFactor;
                                        outputCoeff = (outCost / costSum) * 2.0 * costFactor;
                                      }
                                      return (
                                        <>
                                          <span className="font-bold text-foreground cursor-help underline decoration-dotted decoration-muted-foreground/50">
                                            {costFactor.toFixed(2)} cr / 1k tokens
                                          </span>
                                          <div className="absolute bottom-full left-0 mb-2 hidden group-hover/price:block w-56 p-3 bg-zinc-950 border border-border/60 text-zinc-100 rounded-xl shadow-2xl z-50 text-[10px] leading-relaxed transition-all">
                                            <div className="font-bold text-primary mb-1">Pricing Split (per 1k tokens):</div>
                                            <div className="flex justify-between py-0.5 border-b border-zinc-800">
                                              <span>Input (Context):</span>
                                              <span className="font-mono font-bold text-emerald-400">{inputCoeff.toFixed(3)} cr</span>
                                            </div>
                                            <div className="flex justify-between py-0.5 mt-0.5">
                                              <span>Output (Gen):</span>
                                              <span className="font-mono font-bold text-blue-400">{outputCoeff.toFixed(3)} cr</span>
                                            </div>
                                          </div>
                                        </>
                                      );
                                    })()}
                                  </div>
                                </div>
                                <div className="text-[11px] font-semibold text-primary/90 mt-1">
                                  {runwayText}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      )}
                    </div>

                    {/* API Key Status / Custom Key Input */}
                    {selectedModel?.requiresKey ? (() => {
                      const keyName = `${formData.provider}_api_key`;
                      const savedKey = userSettings?.[keyName]?.trim();
                      const hasSavedKey = Boolean(savedKey);

                      if (hasSavedKey && !showCustomOverride && !formData.api_key?.trim()) {
                        return (
                          <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 flex items-center justify-between gap-4 text-xs text-emerald-500 font-medium">
                            <div className="flex items-center gap-3">
                              <CheckCircle2 size={18} className="shrink-0" />
                              <div>
                                <div className="font-bold text-sm capitalize">{formData.provider} API Key Active</div>
                                <div className="text-[11px] text-emerald-500/80 font-mono">
                                  ••••••••••••{savedKey.slice(-4)} (Saved in Common Workspace Database)
                                </div>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => setShowCustomOverride(true)}
                              className="text-xs font-semibold text-muted-foreground hover:text-foreground underline bg-transparent border-none cursor-pointer"
                            >
                              Custom Key Override
                            </button>
                          </div>
                        );
                      }

                      return (
                        <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 space-y-3 shadow-inner">
                          <div className="flex items-center justify-between">
                            <label className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-2">
                              <Key size={16} /> {formData.provider.toUpperCase()} Provider API Key
                            </label>
                            <button
                              type="button"
                              onClick={() => navigate("/models")}
                              className="text-xs text-amber-600 hover:underline font-medium flex items-center gap-1 bg-transparent border-none p-0 cursor-pointer"
                            >
                              Manage Credentials Hub
                            </button>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Key entered here will automatically be saved to the common workspace DB so all models & agents use it.
                          </p>
                          <input
                            type="password"
                            value={formData.api_key || ""}
                            onChange={(e) => updateField("api_key", e.target.value)}
                            placeholder="Paste your API key here..."
                            className="w-full bg-background border border-input rounded-xl px-4 py-2.5 text-xs font-mono focus:ring-2 focus:ring-amber-500/30 transition-all outline-none"
                          />
                        </div>
                      );
                    })() : (
                      <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 flex items-center gap-3 text-xs text-emerald-500 font-medium">
                        <Zap size={16} className="shrink-0" />
                        <div>
                          <div className="font-bold">Included in Workspace Plan</div>
                          <div className="text-[11px] text-emerald-500/80">No API key required for this model. Direct inference enabled.</div>
                        </div>
                      </div>
                    )}

                    {/* Embedding Model Selection */}
                    <div className="pt-4 border-t border-border/50 space-y-3">
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                        <FileText size={16} className="text-primary" />
                        3. Vector Embedding Model
                      </label>
                      <p className="text-xs text-muted-foreground">
                        Used for document chunking, semantic indexing, and knowledge retrieval.
                      </p>
                      <Select value={formData.embedding_model} onValueChange={(val) => updateField("embedding_model", val)}>
                        <SelectTrigger className="w-full rounded-2xl py-6 px-4 border-input bg-background font-medium">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {EMBEDDING_MODELS.map((em) => (
                            <SelectItem key={em.id} value={em.id} disabled={em.disabled} className="py-2.5">
                              {em.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'behavior' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Behavior & Output</h3>
                    <p className="text-muted-foreground text-sm mt-1">Control how the agent thinks and responds.</p>
                  </div>

                  <div className="space-y-5 bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-semibold">System Prompt</label>
                        <button
                          type="button"
                          onClick={handleOptimizePrompt}
                          disabled={isOptimizing}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-primary bg-primary/10 border border-primary/20 rounded-xl hover:bg-primary/20 active:scale-95 disabled:opacity-50 disabled:pointer-events-none transition-all"
                        >
                          {isOptimizing ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Optimizing...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5" />
                              Optimize Prompt
                            </>
                          )}
                        </button>
                      </div>
                      <p className="text-[13px] text-muted-foreground mb-3">The core instructions, personality, and rules for this agent.</p>
                      <textarea
                        value={formData.system_prompt}
                        onChange={(e) => updateField("system_prompt", e.target.value)}
                        placeholder="You are a helpful assistant..."
                        rows={14}
                        className="w-full font-mono text-sm bg-background border border-border rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-primary/20 transition-all outline-none"
                      />
                    </div>

                    <div className="pt-4 border-t border-border mt-2">
                      <label className="text-sm font-semibold mb-1 flex items-center gap-2">
                        <Code size={16} className="text-indigo-500" />
                        Output Format Instructions
                      </label>
                      <p className="text-[13px] text-muted-foreground mb-3">Define strict formatting rules (e.g. JSON schema, Markdown tables, UI injections).</p>
                      <textarea
                        value={formData.output_format}
                        onChange={(e) => updateField("output_format", e.target.value)}
                        placeholder="Always respond in valid JSON format like: { 'status': 'success' }"
                        rows={12}
                        className="w-full font-mono text-sm bg-indigo-500/5 border border-indigo-500/20 rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-indigo-500/20 transition-all outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'tools' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  {/* Built-in Capabilities (System Tools) */}
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-xl font-bold">Built-in Capabilities</h3>
                      <p className="text-muted-foreground text-sm mt-0.5">Toggle native core integrations directly for this agent.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {workspaceTools.filter(t => t.is_system).map((tool) => {
                        const isAttached = attachedToolIds.has(tool.id);
                        return (
                          <div key={tool.id} className="p-4 bg-card/60 border border-border/80 rounded-2xl flex items-center justify-between shadow-sm hover:shadow-md transition duration-200">
                            <div className="flex items-center gap-3.5">
                              <div className="p-2.5 bg-muted rounded-xl">
                                {tool.tool_type === "api_webhook" && <Webhook size={18} className="text-primary" />}
                                {tool.tool_type === "database" && <Database size={18} className="text-emerald-500" />}
                                {tool.tool_type === "oauth" && <Key size={18} className="text-purple-500" />}
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <h4 className="text-sm font-bold text-foreground">{tool.name}</h4>
                                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                                    System
                                  </span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1 max-w-[280px]">
                                  {tool.configuration?.description || "Core system capabilities extension."}
                                </p>
                              </div>
                            </div>
                            
                            {/* Premium Toggle Switch */}
                            <button
                              type="button"
                              onClick={() => handleToggleTool(tool.id, isAttached)}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${isAttached ? "bg-primary" : "bg-muted"}`}
                            >
                              <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${isAttached ? "translate-x-5" : "translate-x-0"}`} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Divider and Custom Tools Section */}
                  <div className="border-t border-border/50 pt-8 space-y-4">
                    <div>
                      <h3 className="text-xl font-bold">Connected Custom Tools</h3>
                      <p className="text-muted-foreground text-sm mt-0.5">APIs, databases, and Python scripts attached to this agent.</p>
                    </div>

                    {loadingTools ? (
                      <div className="flex items-center justify-center p-8">
                        <Loader2 className="animate-spin text-primary" size={24} />
                      </div>
                    ) : workspaceTools.filter(t => !t.is_system && attachedToolIds.has(t.id)).length === 0 ? (
                      <div className="rounded-3xl border-2 border-dashed border-border bg-card p-12 text-center flex flex-col items-center justify-center space-y-4">
                        <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                          <Wrench size={24} />
                        </div>
                        <div>
                          <h4 className="font-bold text-base text-foreground">No custom tools connected</h4>
                          <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                            Add workspace tools from the library below to attach external capabilities.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {workspaceTools
                          .filter(t => !t.is_system && attachedToolIds.has(t.id))
                          .map((tool) => (
                            <div key={tool.id} className="p-4 bg-card border border-border/80 rounded-2xl flex items-center justify-between shadow-sm hover:shadow-md transition duration-200">
                              <div className="flex items-center gap-3.5">
                                <div className="p-2.5 bg-muted rounded-xl">
                                  {tool.tool_type === "api_webhook" && <Webhook size={18} className="text-primary" />}
                                  {tool.tool_type === "database" && <Database size={18} className="text-emerald-500" />}
                                  {tool.tool_type === "oauth" && <Key size={18} className="text-purple-500" />}
                                  {tool.tool_type === "python_code" && <FileCode size={18} className="text-indigo-500" />}
                                </div>
                                <div>
                                  <h4 className="text-sm font-bold text-foreground">{tool.name}</h4>
                                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1 max-w-[280px]">
                                    {tool.tool_type === "api_webhook" && (tool.configuration?.description || `Webhook: ${tool.configuration?.method} ${tool.configuration?.path}`)}
                                    {tool.tool_type === "database" && (tool.configuration?.description || `Database Connection`)}
                                    {tool.tool_type === "oauth" && `OAuth Integration`}
                                    {tool.tool_type === "python_code" && `Python Script (BYOC)`}
                                  </p>
                                </div>
                              </div>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleTool(tool.id, true)}
                                className="text-xs text-red-500 hover:text-red-600 hover:bg-red-500/10 rounded-xl"
                              >
                                Remove
                              </Button>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>

                  {/* Available Workspace Library Section */}
                  <div className="border-t border-border/50 mt-10 pt-8 space-y-5">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                      <div>
                        <h4 className="text-xl font-bold text-foreground">Workspace Custom Tools Library</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">Click "Attach" to grant this agent access to custom integrations.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => navigate("/tools")}
                        className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
                      >
                        Manage Custom Tools <ExternalLink size={12} />
                      </button>
                    </div>

                    <div className="space-y-3">
                      {loadingTools ? (
                        <div className="flex items-center justify-center p-4">
                          <Loader2 className="animate-spin text-primary" size={20} />
                        </div>
                      ) : workspaceTools.filter(t => !t.is_system && !attachedToolIds.has(t.id)).length === 0 ? (
                        <div className="text-center p-6 bg-muted/20 border border-dashed border-border rounded-xl text-muted-foreground text-xs">
                          All available workspace custom tools are currently connected to this agent.
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {workspaceTools
                            .filter(t => !t.is_system && !attachedToolIds.has(t.id))
                            .map((tool) => (
                              <div key={tool.id} className="p-4 bg-card hover:bg-card/80 border border-border/80 rounded-2xl flex items-center justify-between transition-all duration-200 hover:shadow-sm">
                                <div className="flex items-center gap-3.5">
                                  <div className="p-2.5 bg-muted rounded-xl">
                                    {tool.tool_type === "api_webhook" && <Webhook size={18} className="text-primary" />}
                                    {tool.tool_type === "database" && <Database size={18} className="text-emerald-500" />}
                                    {tool.tool_type === "oauth" && <Key size={18} className="text-purple-500" />}
                                    {tool.tool_type === "python_code" && <FileCode size={18} className="text-indigo-500" />}
                                  </div>
                                  <div>
                                    <h4 className="text-sm font-bold text-foreground">{tool.name}</h4>
                                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1 max-w-[500px]">
                                      {tool.tool_type === "api_webhook" && (tool.configuration?.description || `REST API: ${tool.configuration?.method} ${tool.configuration?.path}`)}
                                      {tool.tool_type === "database" && (tool.configuration?.description || `Database Connection`)}
                                      {tool.tool_type === "oauth" && `OAuth Integration`}
                                      {tool.tool_type === "python_code" && `Python Script (BYOC)`}
                                    </p>
                                  </div>
                                </div>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleToggleTool(tool.id, false)}
                                  className="rounded-xl px-4 font-semibold text-xs transition"
                                >
                                  Attach
                                </Button>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}


              {activeTab === 'knowledge-base' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold">Knowledge Base</h3>
                      <p className="text-muted-foreground text-sm mt-1">Configure how the agent retrieves information from its vector store and the web.</p>
                    </div>
                  </div>

                  {/* Settings */}
                  <div className="space-y-5 bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div>
                      <label className="block text-sm font-semibold mb-1.5 flex items-center gap-2">
                        <Sparkles size={16} className="text-muted-foreground" />
                        Chunking Strategy
                      </label>
                      <Select value={formData.chunk_strategy} onValueChange={(val) => updateField("chunk_strategy", val)}>
                        <SelectTrigger className="w-full rounded-xl py-5">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CHUNKING_STRATEGIES.map((cs) => (
                            <SelectItem key={cs.id} value={cs.id}>{cs.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Documents & Ingestion */}
                  <div className="grid lg:grid-cols-12 gap-6 pt-4 border-t border-border mt-6">

                    {/* Left: Sources Input */}
                    <div className="lg:col-span-4 flex flex-col gap-6">
                      <div className="glass-card p-6 flex-1 rounded-2xl border border-border">
                        <h3 className="font-semibold text-lg mb-4">Add Knowledge</h3>

                        <div className="flex bg-muted p-1 rounded-xl mb-6 overflow-x-auto gap-1">
                          <button onClick={() => setSourceTab("files")} className={`flex-1 py-2 text-xs font-medium rounded-lg whitespace-nowrap px-2 ${sourceTab === "files" ? "bg-background shadow" : "text-muted-foreground"}`}>Files</button>
                          <button onClick={() => setSourceTab("website")} className={`flex-1 py-2 text-xs font-medium rounded-lg whitespace-nowrap px-2 ${sourceTab === "website" ? "bg-background shadow" : "text-muted-foreground"}`}>Website</button>
                          <button onClick={() => setSourceTab("text")} className={`flex-1 py-2 text-xs font-medium rounded-lg whitespace-nowrap px-2 ${sourceTab === "text" ? "bg-background shadow" : "text-muted-foreground"}`}>Custom Text</button>
                          <button onClick={() => setSourceTab("connectors")} className={`flex-1 py-2 text-xs font-medium rounded-lg whitespace-nowrap px-2 ${sourceTab === "connectors" ? "bg-background shadow" : "text-muted-foreground"}`}>Apps</button>
                        </div>

                        {sourceTab === "files" && (
                          <div className="border-2 border-dashed border-primary/20 rounded-[28px] p-6 flex flex-col items-center justify-center text-center bg-primary/5">
                            <UploadCloud size={30} className="text-primary mb-3" />
                            <h4 className="font-semibold">Drop files here</h4>
                            <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT, CSV</p>
                            <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.csv" className="hidden" onChange={handleFileChange} />
                            <input ref={replaceFileInputRef} type="file" accept=".pdf,.docx,.txt,.csv,.png,.jpg,.jpeg" className="hidden" onChange={handleReplaceFileChange} />
                            <button onClick={() => fileInputRef.current?.click()} disabled={!selectedAgentId || isMutating} className="mt-4 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm disabled:opacity-60">
                              {uploadMutation.isPending ? "Uploading..." : "Browse Files"}
                            </button>
                          </div>
                        )}

                        {sourceTab === "website" && (
                          <div className="mt-2">
                            <label className="text-xs font-medium block mb-2">Website URL</label>
                            <div className="relative">
                              <Globe size={14} className="absolute left-3 top-3 text-slate-400" />
                              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com" className="w-full border border-border bg-card rounded-xl pl-9 py-2 text-sm" />
                            </div>
                            <button onClick={handleProcessUrl} disabled={!selectedAgentId || isMutating} className="w-full mt-3 py-2 rounded-xl border border-border hover:bg-muted disabled:opacity-60 text-sm font-medium">
                              {processUrlMutation.isPending ? "Scraping..." : "Scrape Website"}
                            </button>
                          </div>
                        )}

                        {sourceTab === "text" && (
                          <div className="space-y-3 mt-2">
                            <div>
                              <label className="text-xs font-medium block mb-1">Snippet Title / Filename</label>
                              <input
                                value={newTextFilename}
                                onChange={(e) => setNewTextFilename(e.target.value)}
                                placeholder="e.g. return_policy.txt"
                                className="w-full border border-border bg-card rounded-xl px-3 py-2 text-sm"
                              />
                            </div>
                            <div>
                              <label className="text-xs font-medium block mb-1">Text Content</label>
                              <textarea
                                value={newTextContent}
                                onChange={(e) => setNewTextContent(e.target.value)}
                                placeholder="Paste custom text or knowledge here..."
                                rows={5}
                                className="w-full border border-border bg-card rounded-xl px-3 py-2 text-sm resize-none"
                              />
                            </div>
                            <button
                              onClick={() => {
                                if (!newTextFilename.trim() || !newTextContent.trim()) return toast.error("Please provide a title and text content");
                                handleCreateText(newTextFilename.trim(), newTextContent.trim());
                                setNewTextFilename("");
                                setNewTextContent("");
                              }}
                              disabled={!selectedAgentId || isMutating}
                              className="w-full py-2 rounded-xl bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-60 text-sm font-medium"
                            >
                              {processTextMutation.isPending ? "Indexing..." : "Index Text Snippet"}
                            </button>
                          </div>
                        )}

                        {sourceTab === "connectors" && (
                          <div className="space-y-3">
                            {[
                              { id: "gdrive", name: "Google Drive", icon: Cloud, color: "text-blue-500", bg: "bg-blue-500/10" },
                              { id: "notion", name: "Notion", icon: FileText, color: "text-slate-700", bg: "bg-slate-500/10" },
                            ].map((connector) => (
                              <div key={connector.id} className="flex items-center justify-between p-3 rounded-xl border border-border bg-background">
                                <div className="flex items-center gap-3">
                                  <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${connector.bg}`}>
                                    <connector.icon size={16} className={connector.color} />
                                  </div>
                                  <div className="font-semibold text-sm">{connector.name}</div>
                                </div>
                                <button onClick={() => handleConnect(connector.id, connector.name)} disabled={isMutating || connectingTo === connector.id} className="px-3 py-1.5 bg-primary/10 text-primary text-xs font-semibold rounded-lg">
                                  {connectingTo === connector.id ? "..." : "Connect"}
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right: Data Table */}
                    <div className="lg:col-span-8 flex flex-col gap-6">
                      <div className="glass-card rounded-2xl border border-border overflow-hidden flex-1">
                        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/20">
                          <h4 className="font-semibold text-sm">Indexed Documents</h4>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                queryClient.invalidateQueries({ queryKey: ["documents", selectedAgentId] });
                                toast.success("Knowledge sources refreshed");
                              }}
                              className="p-1.5 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition"
                              title="Refresh knowledge list"
                            >
                              <RefreshCw size={14} />
                            </button>
                            <div className="relative w-48">
                              <Search size={14} className="absolute left-3 top-2.5 text-muted-foreground" />
                              <input value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Search..." className="w-full bg-background border border-border rounded-lg pl-8 py-1.5 text-sm" />
                            </div>
                          </div>
                        </div>

                        <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                          <table className="w-full">
                            <thead className="sticky top-0 bg-background z-10 border-b border-border">
                              <tr className="text-left">
                                <th className="px-4 py-3 text-xs font-semibold text-muted-foreground">Source</th>
                                <th className="px-4 py-3 text-xs font-semibold text-muted-foreground">Status</th>
                                <th className="px-4 py-3 text-xs font-semibold text-muted-foreground">Size</th>
                                <th className="px-4 py-3"></th>
                              </tr>
                            </thead>
                            <tbody>
                              {isLoading && <tr><td colSpan={4} className="p-4 text-center"><Loader2 size={16} className="animate-spin mx-auto" /></td></tr>}
                              {!isLoading && filteredDocuments.length === 0 && <tr><td colSpan={4} className="p-8 text-center text-sm text-muted-foreground">No documents indexed yet.</td></tr>}
                              {!isLoading && filteredDocuments.map((doc) => {
                                const isUrl = doc.filename.startsWith("http://") || doc.filename.startsWith("https://");
                                const isText = doc.filename.endsWith(".txt");
                                const isConnector = doc.filename.includes("Sync");
                                return (
                                  <tr key={doc.id} className="border-b border-border hover:bg-muted/50">
                                    <td className="px-4 py-3 text-sm flex items-center gap-2"><FileText size={14} className="text-primary" /> <span className="truncate max-w-[150px]">{getDocumentSource(doc)}</span></td>
                                    <td className="px-4 py-3"><StatusBadge status={doc.status} /></td>
                                    <td className="px-4 py-3 text-xs text-muted-foreground">{formatBytes(doc.file_size_bytes)}</td>
                                    <td className="px-4 py-3 text-right">
                                      <div className="flex items-center justify-end gap-2">
                                        {(isUrl || isText) && (
                                          <button onClick={() => handleEditClick(doc)} className="p-1.5 rounded-lg hover:bg-primary/10 text-primary" title="Edit source">
                                            <Pencil size={14} />
                                          </button>
                                        )}
                                        {(!isUrl && !isText && !isConnector) && (
                                          <button onClick={() => { setReplaceTargetDocId(doc.id); setTimeout(() => replaceFileInputRef.current?.click(), 100); }} className="p-1.5 rounded-lg hover:bg-primary/10 text-primary" title="Upload new version">
                                            <UploadCloud size={14} />
                                          </button>
                                        )}
                                        {isConnector && (
                                          <button onClick={() => handleSyncConnectorClick(doc.id)} disabled={syncConnectorMutation.isPending} className="p-1.5 rounded-lg hover:bg-emerald-500/10 text-emerald-500" title="Sync now">
                                            <Zap size={14} className={syncConnectorMutation.isPending ? "animate-spin" : ""} />
                                          </button>
                                        )}
                                        <button onClick={() => handleDelete(doc.id)} disabled={deleteMutation.isPending} className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-500" title="Delete document">
                                          <Trash2 size={14} />
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'memory' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Conversation Memory</h3>
                    <p className="text-muted-foreground text-sm mt-1">Configure whether the agent retains chat history context for follow-up questions.</p>
                  </div>

                  {/* Toggle Card */}
                  <div className="bg-card p-6 rounded-2xl border border-border shadow-sm flex items-center justify-between">
                    <div className="space-y-1 pr-6">
                      <div className="font-semibold text-base flex items-center gap-2">
                        <Brain className="w-5 h-5 text-indigo-500" />
                        Enable Conversation Memory
                      </div>
                      <p className="text-[13px] text-muted-foreground leading-relaxed">
                        When enabled, the agent remembers the context of previous messages in the chat session to understand reference pronouns and follow-up prompts. When disabled, each message starts a fresh, independent turn.
                      </p>
                    </div>
                    <div>
                      <button
                        type="button"
                        onClick={() => updateField("memory_enabled", !formData.memory_enabled)}
                        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
                          formData.memory_enabled ? "bg-primary" : "bg-muted"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-background shadow ring-0 transition duration-200 ease-in-out ${
                            formData.memory_enabled ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>
                  </div>

                  {/* Clear Memory Panel */}
                  <div className="bg-card rounded-2xl border border-red-500/20 shadow-sm overflow-hidden">
                    <div className="p-6 bg-red-500/5 border-b border-red-500/10">
                      <h4 className="font-bold text-lg text-red-500 flex items-center gap-2">
                        <Trash2 size={20} />
                        Clear Agent Memory Logs
                      </h4>
                      <p className="text-[13px] text-muted-foreground mt-1">Permanently erase the conversation logs and active chat threads for this agent.</p>
                    </div>

                    <div className="p-6 space-y-4">
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Clearing the agent's memory will delete all stored chat sessions, history threads, and messages linked to this agent. This action is irreversible and the agent will start with a completely blank slate.
                      </p>
                      <Button
                        type="button"
                        variant="destructive"
                        onClick={handleClearAllMemory}
                        className="rounded-xl font-semibold px-6"
                      >
                        Wipe Conversation History
                      </Button>
                    </div>
                  </div>
                </div>
              )}


              {activeTab === 'analytics' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Cost & Token Analytics</h3>
                    <p className="text-muted-foreground text-sm mt-1">Monitor the token economics and API costs associated with this agent.</p>
                  </div>

                  {isAnalyticsLoading ? (
                    <div className="flex items-center justify-center p-12">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                  ) : analytics ? (
                    <div className="space-y-6">
                      {/* Metric Cards Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-card border border-border p-5 rounded-2xl shadow-sm space-y-2">
                          <div className="flex items-center justify-between text-muted-foreground">
                            <span className="text-sm font-semibold">Total Usage Cost</span>
                            <div className="p-2 rounded-xl bg-green-500/10 text-green-500">
                              <DollarSign size={16} />
                            </div>
                          </div>
                          <div className="text-3xl font-extrabold">${analytics.totals.estimated_cost.toFixed(4)}</div>
                          <p className="text-[11px] text-muted-foreground">Based on typical model input/output rates.</p>
                        </div>

                        <div className="bg-card border border-border p-5 rounded-2xl shadow-sm space-y-2">
                          <div className="flex items-center justify-between text-muted-foreground">
                            <span className="text-sm font-semibold">Total Tokens Consumed</span>
                            <div className="p-2 rounded-xl bg-primary/10 text-primary">
                              <TrendingUp size={16} />
                            </div>
                          </div>
                          <div className="text-3xl font-extrabold">{analytics.totals.total_tokens.toLocaleString()}</div>
                          <p className="text-[11px] text-muted-foreground">Prompt: {analytics.totals.prompt_tokens.toLocaleString()} | Completion: {analytics.totals.completion_tokens.toLocaleString()}</p>
                        </div>

                        <div className="bg-card border border-border p-5 rounded-2xl shadow-sm space-y-2">
                          <div className="flex items-center justify-between text-muted-foreground">
                            <span className="text-sm font-semibold">Cost per User Query</span>
                            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500">
                              <Activity size={16} />
                            </div>
                          </div>
                          <div className="text-3xl font-extrabold">${avgCostPerQuery.toFixed(5)}</div>
                          <p className="text-[11px] text-muted-foreground">Across a total of {totalCalls.toLocaleString()} LLM queries.</p>
                        </div>
                      </div>

                      {analytics.daily.length === 0 ? (
                        <div className="text-center p-12 border border-dashed border-border rounded-2xl text-muted-foreground text-sm">
                          No usage logged yet. Start a chat session with this agent to begin cost tracking.
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          {/* Token Burn Stacked Bar Chart */}
                          <div className="bg-card border border-border p-6 rounded-2xl space-y-3">
                            <div>
                              <h4 className="text-sm font-semibold text-foreground">Token Burn Timeline</h4>
                              <p className="text-xs text-muted-foreground">Visual breakdown of daily prompt and completion tokens.</p>
                            </div>
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={analytics.daily} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                                  <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} />
                                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} />
                                  <Tooltip 
                                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "12px" }}
                                    labelStyle={{ fontWeight: "bold", color: "hsl(var(--foreground))" }}
                                  />
                                  <Legend verticalAlign="top" height={36} iconType="circle" />
                                  <Bar dataKey="prompt_tokens" name="Prompt Tokens" stackId="a" fill="hsl(var(--primary))" radius={[0, 0, 0, 0]} />
                                  <Bar dataKey="completion_tokens" name="Completion Tokens" stackId="a" fill="hsl(var(--primary) / 0.5)" radius={[4, 4, 0, 0]} />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>

                          {/* Cumulative Cost Area Chart */}
                          <div className="bg-card border border-border p-6 rounded-2xl space-y-3">
                            <div>
                              <h4 className="text-sm font-semibold text-foreground">Cumulative Costs</h4>
                              <p className="text-xs text-muted-foreground">Running accumulation of API cost metrics over time.</p>
                            </div>
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={dailyDataWithCumulative} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                  <defs>
                                    <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="5%" stopColor="rgb(34, 197, 94)" stopOpacity={0.2}/>
                                      <stop offset="95%" stopColor="rgb(34, 197, 94)" stopOpacity={0}/>
                                    </linearGradient>
                                  </defs>
                                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                                  <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} />
                                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} tickFormatter={(value) => `$${value.toFixed(3)}`} />
                                  <Tooltip 
                                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "12px" }}
                                    formatter={(value) => [`$${value.toFixed(5)}`, "Cumulative Cost"]}
                                    labelStyle={{ fontWeight: "bold", color: "hsl(var(--foreground))" }}
                                  />
                                  <Area type="monotone" dataKey="cumulative_cost" stroke="rgb(34, 197, 94)" fillOpacity={1} fill="url(#colorCost)" strokeWidth={2} />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center p-8 border border-dashed border-border rounded-2xl text-muted-foreground">
                      Could not fetch analytics. Please try again.
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </div>
      </div>
      {/* ──────────────── MODAL: EDIT URL KNOWLEDGE ──────────────── */}
      <Dialog open={isUrlEditOpen} onOpenChange={setIsUrlEditOpen}>
        <DialogContent className="sm:max-w-md rounded-3xl p-6 space-y-6">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">Edit Scraped URL</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold block mb-1">Target Link URL</label>
              <input
                value={editUrlValue}
                onChange={(e) => setEditUrlValue(e.target.value)}
                placeholder="https://example.com"
                className="w-full border border-border bg-card rounded-xl px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={handleUpdateUrl}
              disabled={updateUrlMutation.isPending}
              className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              {updateUrlMutation.isPending ? "Re-scraping..." : "Save and Re-scrape"}
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ──────────────── MODAL: EDIT TEXT KNOWLEDGE ──────────────── */}
      <Dialog open={isTextEditOpen} onOpenChange={setIsTextEditOpen}>
        <DialogContent className="sm:max-w-xl rounded-3xl p-6 space-y-6">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">Edit Custom Text Snippet</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold block mb-1">Snippet Filename</label>
              <input
                value={textFilename}
                onChange={(e) => setTextFilename(e.target.value)}
                placeholder="filename.txt"
                className="w-full border border-border bg-card rounded-xl px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">Content</label>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Content text..."
                rows={10}
                className="w-full border border-border bg-card rounded-xl px-3 py-2 text-sm resize-none"
              />
            </div>
            <button
              onClick={handleUpdateText}
              disabled={updateTextMutation.isPending}
              className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-60"
            >
              {updateTextMutation.isPending ? "Updating vectors..." : "Save and Update Snippet"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
