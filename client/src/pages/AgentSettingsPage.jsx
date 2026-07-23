import React, { useState, useMemo } from "react";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, Pencil } from "lucide-react";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import { UploadCloud, Search, CheckCircle2, AlertCircle, Link2, Eye, FileText, Cloud, MessageSquare, Code, Globe, Loader2, Bot, Brain, Key, Sparkles, Network, Plus, Trash2, Settings2, Database, Blocks, Terminal, Library, ChevronDown, ChevronUp, Zap, Lock, ExternalLink, RefreshCw } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useRef, useEffect } from "react";
import { useWorkspacePermissions, useUserSettings, useUpdateUserSettings } from "../hooks/useSettings";
import { useActiveModels } from "../hooks/useModels";
import { useAuth } from "../context/AuthContext";
import { useProjectTools } from "../hooks/useAgents";
import { useDeleteDocument, useDocuments, useProcessUrl, useUploadDocument, useProcessConnector, useUpdateUrl, useProcessText, useUpdateText, useUpdateFile, useSyncConnector } from "../hooks/useDocuments";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";

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

  const [formData, setFormData] = useState({
    name: agent?.name || "",
    description: agent?.description || "",
    provider: agent?.llm_provider || "groq",
    model: agent?.llm_model || "llama-3.1-8b-instant",
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
  });

  const { data: activeModelsData } = useActiveModels();
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
    if (!formData.name.trim()) {
      toast.error("Agent name is required.");
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
      endpoints: formData.endpoints,
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
          {[
            { id: "identity", label: "Identity", icon: Bot },
            { id: "behavior", label: "Behavior", icon: Brain },
            { id: "model", label: "Model & AI", icon: Sparkles },
            { id: "knowledge-base", label: "Knowledge Base", icon: Library },
            { id: "endpoints", label: "API Endpoints", icon: Network },
            { id: "integrations", label: "Integrations", icon: Blocks },
            { id: "databases", label: "Databases", icon: Database },
            { id: "code-interpreter", label: "Code Interpreter", icon: Terminal },
          ].map((tab) => (
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
          ))}
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
                  <div>
                    <h3 className="text-2xl font-bold flex items-center gap-2">
                      <Brain className="text-primary" size={24} /> AI Model & Intelligence Engine
                    </h3>
                    <p className="text-muted-foreground text-sm mt-1">
                      Configure the primary LLM engine, embedding model, and inference parameters powering this agent.
                    </p>
                  </div>

                  {/* Main Container */}
                  <div className="space-y-6 bg-card p-6 sm:p-8 rounded-3xl border border-border shadow-md">
                    {/* Provider Selection */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                        1. Select AI Provider Platform
                      </label>
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
                    </div>

                    {/* Specific Model Selection */}
                    <div className="pt-2 border-t border-border/50 space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
                          2. Select Specific Model
                        </label>
                        <span className="text-xs text-muted-foreground">
                          Available: {currentModels.length} models
                        </span>
                      </div>

                      <Select value={formData.model} onValueChange={(val) => updateField("model", val)}>
                        <SelectTrigger className="w-full rounded-2xl py-6 px-4 border-input bg-background font-medium">
                          <SelectValue placeholder="Choose an AI model..." />
                        </SelectTrigger>
                        <SelectContent className="max-h-72">
                          {currentModels.map((m) => {
                            const isEnabled = !m.requiresKey || isProviderKeyPresent(formData.provider);
                            return (
                              <SelectItem key={m.id} value={m.id} disabled={!isEnabled} className="py-2.5">
                                <div className="flex items-center justify-between gap-4 w-full">
                                  <span className="font-semibold text-sm">{m.name}</span>
                                  {!isEnabled ? (
                                    <span className="text-[11px] text-amber-500 font-medium flex items-center gap-1">
                                      <Lock size={12} /> Key Required
                                    </span>
                                  ) : m.requiresKey ? (
                                    <span className="text-[11px] text-emerald-500 font-medium flex items-center gap-1">
                                      <CheckCircle2 size={12} /> Key Ready
                                    </span>
                                  ) : (
                                    <span className="text-[11px] text-emerald-500 font-medium flex items-center gap-1">
                                      <Zap size={12} /> Free Included
                                    </span>
                                  )}
                                </div>
                              </SelectItem>
                            );
                          })}
                        </SelectContent>
                      </Select>
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
                      <label className="block text-sm font-semibold mb-1">System Prompt</label>
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

              {activeTab === 'endpoints' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold">API Endpoints</h3>
                      <p className="text-muted-foreground text-sm mt-1">Configure specific API endpoints this agent can call.</p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        updateField("endpoints", [
                          ...formData.endpoints,
                          { connection_id: "", name: "New Endpoint", path: "", method: "GET", description: "", payload_format: "", expected_output: "" }
                        ]);
                        setExpandedEndpoints(prev => ({...prev, [formData.endpoints.length]: true}));
                      }}
                    >
                      <Plus className="w-4 h-4 mr-2" /> Add Endpoint
                    </Button>
                  </div>

                  {formData.endpoints.length === 0 ? (
                    <div className="text-center p-10 bg-muted/20 border border-dashed border-border rounded-2xl text-muted-foreground">
                      No endpoints configured. Click 'Add Endpoint' to give this agent external API access.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {formData.endpoints.map((ep, idx) => {
                        const isExpanded = !!expandedEndpoints[idx];
                        return (
                        <div key={idx} className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                          <div 
                            className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors"
                            onClick={() => setExpandedEndpoints(prev => ({...prev, [idx]: !prev[idx]}))}
                          >
                            <div className="flex items-center gap-3">
                              <span className={`px-2 py-0.5 text-xs font-bold rounded-md ${ep.method === 'GET' ? 'bg-blue-100 text-blue-700' : ep.method === 'POST' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                                {ep.method || 'GET'}
                              </span>
                              <span className="font-semibold">{ep.name || 'Unnamed Endpoint'}</span>
                              <span className="text-muted-foreground text-sm truncate max-w-[200px]">{ep.path}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-8 w-8"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const newEps = [...formData.endpoints];
                                  newEps.splice(idx, 1);
                                  updateField("endpoints", newEps);
                                }}
                              >
                                <Trash2 size={14} />
                              </Button>
                              <div className="text-muted-foreground p-1">
                                {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                              </div>
                            </div>
                          </div>
                          
                          {isExpanded && (
                            <div className="p-5 pt-2 border-t border-border/50">
                              <div className="grid grid-cols-2 gap-4 mb-4">
                            {agent?.project_id ? (
                              <div>
                                <label className="block text-sm font-semibold mb-1">API Connection</label>
                                <Select
                                  value={ep.connection_id}
                                  onValueChange={(val) => {
                                    const newEps = [...formData.endpoints];
                                    newEps[idx].connection_id = val;
                                    updateField("endpoints", newEps);
                                  }}
                                >
                                  <SelectTrigger className="w-full bg-background rounded-xl">
                                    <SelectValue placeholder="Select Connection" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {globalConnections.map(conn => (
                                      <SelectItem key={conn.id} value={conn.id}>{conn.name}</SelectItem>
                                    ))}
                                    {globalConnections.length === 0 && (
                                      <SelectItem value="none" disabled>No connections available</SelectItem>
                                    )}
                                  </SelectContent>
                                </Select>
                              </div>
                            ) : (
                              <div>
                                <label className="block text-sm font-semibold mb-1">Base URL</label>
                                <input
                                  type="text"
                                  value={ep.base_url || ""}
                                  onChange={(e) => {
                                    const newEps = [...formData.endpoints];
                                    newEps[idx].base_url = e.target.value;
                                    updateField("endpoints", newEps);
                                  }}
                                  placeholder="https://api.example.com"
                                  className="w-full bg-background border border-border rounded-xl px-4 py-2 focus:ring-2 focus:ring-primary/20 outline-none"
                                />
                              </div>
                            )}
                            <div>
                              <label className="block text-sm font-semibold mb-1">Endpoint Name</label>
                              <input
                                type="text"
                                value={ep.name}
                                onChange={(e) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].name = e.target.value;
                                  updateField("endpoints", newEps);
                                }}
                                placeholder="e.g. Get User Data"
                                className="w-full bg-background border border-border rounded-xl px-4 py-2 focus:ring-2 focus:ring-primary/20 outline-none"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-[1fr_3fr] gap-4 mb-4">
                            <div>
                              <label className="block text-sm font-semibold mb-1">Method</label>
                              <Select
                                value={ep.method}
                                onValueChange={(val) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].method = val;
                                  updateField("endpoints", newEps);
                                }}
                              >
                                <SelectTrigger className="w-full bg-background rounded-xl">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="GET">GET</SelectItem>
                                  <SelectItem value="POST">POST</SelectItem>
                                  <SelectItem value="PUT">PUT</SelectItem>
                                  <SelectItem value="DELETE">DELETE</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div>
                              <label className="block text-sm font-semibold mb-1">Path</label>
                              <input
                                type="text"
                                value={ep.path}
                                onChange={(e) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].path = e.target.value;
                                  updateField("endpoints", newEps);
                                }}
                                placeholder="/v1/users/{user_id}"
                                className="w-full bg-background font-mono text-sm border border-border rounded-xl px-4 py-2 focus:ring-2 focus:ring-primary/20 outline-none"
                              />
                            </div>
                          </div>

                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm font-semibold mb-1">Description (Instructions for Agent)</label>
                              <input
                                type="text"
                                value={ep.description}
                                onChange={(e) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].description = e.target.value;
                                  updateField("endpoints", newEps);
                                }}
                                placeholder="Use this to fetch user data given a user ID."
                                className="w-full bg-background border border-border rounded-xl px-4 py-2 focus:ring-2 focus:ring-primary/20 outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-semibold mb-1">Payload Format (JSON)</label>
                              <textarea
                                value={ep.payload_format}
                                onChange={(e) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].payload_format = e.target.value;
                                  updateField("endpoints", newEps);
                                }}
                                placeholder='{"user_id": "{id}"}'
                                rows={3}
                                className="w-full bg-background font-mono text-xs border border-border rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-primary/20 outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-semibold mb-1">Expected Output (JSON)</label>
                              <textarea
                                value={ep.expected_output || ""}
                                onChange={(e) => {
                                  const newEps = [...formData.endpoints];
                                  newEps[idx].expected_output = e.target.value;
                                  updateField("endpoints", newEps);
                                }}
                                placeholder='{"user_name": "John", "age": 30}'
                                rows={3}
                                className="w-full bg-background font-mono text-xs border border-border rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-primary/20 outline-none"
                              />
                            </div>
                            {!agent?.project_id && (
                              <>
                                <div>
                                  <label className="block text-sm font-semibold mb-1">API Key / Auth Header</label>
                                  <input
                                    type="password"
                                    value={ep.api_key || ""}
                                    onChange={(e) => {
                                      const newEps = [...formData.endpoints];
                                      newEps[idx].api_key = e.target.value;
                                      updateField("endpoints", newEps);
                                    }}
                                    placeholder="Bearer sk-..."
                                    className="w-full bg-background font-mono text-sm border border-border rounded-xl px-4 py-2 focus:ring-2 focus:ring-primary/20 outline-none"
                                  />
                                </div>
                                <div>
                                  <label className="block text-sm font-semibold mb-1">Headers (JSON)</label>
                                  <textarea
                                    value={ep.headers || ""}
                                    onChange={(e) => {
                                      const newEps = [...formData.endpoints];
                                      newEps[idx].headers = e.target.value;
                                      updateField("endpoints", newEps);
                                    }}
                                    placeholder='{"X-Custom-Token": "abc"}'
                                    rows={2}
                                    className="w-full bg-background font-mono text-xs border border-border rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-primary/20 outline-none"
                                  />
                                </div>
                              </>
                            )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    </div>
                  )}
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
                    <div className="pt-4 border-t border-border mt-2 flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold flex items-center gap-2"><Globe size={18} className="text-blue-500" /> Web Search Fallback</h4>
                        <p className="text-sm text-muted-foreground mt-1">Allow the agent to search the internet if the answer isn't in documents.</p>
                      </div>
                      <Switch checked={formData.web_search_enabled} onCheckedChange={(val) => updateField("web_search_enabled", val)} />
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
              {activeTab === 'integrations' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Native Integrations</h3>
                    <p className="text-muted-foreground text-sm mt-1">Connect your agent to external apps.</p>
                  </div>
                  <div className="space-y-4">
                    {[
                      { id: "github", name: "GitHub", description: "Access repositories and issues.", icon: "https://cdn-icons-png.flaticon.com/512/25/25231.png" },
                      { id: "slack", name: "Slack", description: "Send and receive messages.", icon: "https://cdn-icons-png.flaticon.com/512/3800/3800024.png" },
                      { id: "jira", name: "Jira", description: "Manage project tickets.", icon: "https://cdn-icons-png.flaticon.com/512/5968/5968875.png" }
                    ].map((integration) => {
                      const isConnected = formData.native_integrations?.includes(integration.id);
                      return (
                        <div key={integration.id} className="p-4 bg-card border border-border rounded-2xl flex items-center justify-between transition-all">
                          <div className="flex items-center gap-4">
                            <img src={integration.icon} alt={integration.name} className="w-8 h-8 object-contain" />
                            <div>
                              <h4 className="text-base font-semibold text-foreground">{integration.name}</h4>
                              <p className="text-sm text-muted-foreground">{integration.description}</p>
                            </div>
                          </div>
                          <Button
                            variant={isConnected ? "outline" : "default"}
                            className={isConnected ? "text-red-500 hover:text-red-600 hover:bg-red-500/10" : ""}
                            onClick={() => {
                              const current = formData.native_integrations || [];
                              if (isConnected) {
                                updateField("native_integrations", current.filter(id => id !== integration.id));
                              } else {
                                // Trigger OAuth Flow in a popup window
                                const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
                                window.open(`${baseUrl}/api/auth/${integration.id}/login`, "OAuth_Login", "width=600,height=700");
                                // Optimistically add it to the form data
                                updateField("native_integrations", [...current, integration.id]);
                              }
                            }}
                          >
                            {isConnected ? "Disconnect" : "Connect"}
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {activeTab === 'databases' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-2xl font-bold">Database Connectors</h3>
                      <p className="text-muted-foreground text-sm mt-1">Allow your agent to execute raw SQL queries.</p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        updateField("databases", [
                          ...(formData.databases || []),
                          { name: "New Database", type: "postgresql", connection_string: "" }
                        ]);
                        setExpandedDatabases(prev => ({...prev, [(formData.databases || []).length]: true}));
                      }}
                    >
                      <Plus className="w-4 h-4 mr-2" /> Add Database
                    </Button>
                  </div>

                  {(!formData.databases || formData.databases.length === 0) ? (
                    <div className="text-center p-10 bg-muted/20 border border-dashed border-border rounded-2xl text-muted-foreground">
                      No databases configured. Click 'Add Database' to connect one.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {formData.databases.map((db, idx) => {
                        const isExpanded = !!expandedDatabases[idx];
                        return (
                          <div key={idx} className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
                            <div 
                              className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors"
                              onClick={() => setExpandedDatabases(prev => ({...prev, [idx]: !prev[idx]}))}
                            >
                              <div className="flex items-center gap-3">
                                <Database className="w-4 h-4 text-primary" />
                                <span className="font-semibold">{db.name || 'Unnamed Database'}</span>
                                <span className="text-muted-foreground text-sm uppercase">{db.type}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-8 w-8"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const newDbs = [...formData.databases];
                                    newDbs.splice(idx, 1);
                                    updateField("databases", newDbs);
                                  }}
                                >
                                  <Trash2 size={14} />
                                </Button>
                                <div className="text-muted-foreground p-1">
                                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                </div>
                              </div>
                            </div>
                            
                            {isExpanded && (
                              <div className="p-5 pt-2 border-t border-border/50 space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <label className="block text-sm font-semibold mb-1">Name</label>
                                    <input
                                      type="text"
                                      className="w-full p-2.5 bg-background border border-input rounded-xl text-sm"
                                      placeholder="e.g. Production DB"
                                      value={db.name}
                                      onChange={(e) => {
                                        const newDbs = [...formData.databases];
                                        newDbs[idx].name = e.target.value;
                                        updateField("databases", newDbs);
                                      }}
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-sm font-semibold mb-1">Type</label>
                                    <select
                                      className="w-full p-2.5 bg-background border border-input rounded-xl text-sm"
                                      value={db.type}
                                      onChange={(e) => {
                                        const newDbs = [...formData.databases];
                                        newDbs[idx].type = e.target.value;
                                        updateField("databases", newDbs);
                                      }}
                                    >
                                      <option value="postgresql">PostgreSQL</option>
                                      <option value="mysql">MySQL</option>
                                    </select>
                                  </div>
                                </div>
                                <div>
                                  <label className="block text-sm font-semibold mb-1">Connection String</label>
                                  <input
                                    type="password"
                                    className="w-full p-2.5 bg-background border border-input rounded-xl text-sm"
                                    placeholder="postgresql://user:pass@localhost:5432/dbname"
                                    value={db.connection_string}
                                    onChange={(e) => {
                                      const newDbs = [...formData.databases];
                                      newDbs[idx].connection_string = e.target.value;
                                      updateField("databases", newDbs);
                                    }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'code-interpreter' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-2xl font-bold">Code Interpreter</h3>
                    <p className="text-muted-foreground text-sm mt-1">Give your agent a sandboxed Python environment for data analysis.</p>
                  </div>
                  <div className="p-6 bg-card border border-border rounded-2xl flex items-center justify-between">
                    <div>
                      <h4 className="text-base font-semibold text-foreground">Enable Code Interpreter</h4>
                      <p className="text-sm text-muted-foreground mt-1">Allow the agent to write and execute Python code in a secure sandbox.</p>
                    </div>
                    <Switch checked={formData.code_interpreter_enabled} onCheckedChange={(val) => updateField("code_interpreter_enabled", val)} />
                  </div>
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
