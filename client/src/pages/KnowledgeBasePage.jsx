import { useMemo, useRef, useState, useEffect } from "react";
import { toast } from "sonner";
import { useLocation, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud,
  Search,
  Globe,
  FileText,
  Filter,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  ChevronDown,
  Eye,
  Database,
  Cloud,
  MessageSquare,
  Code,
  Link2
} from "lucide-react";
import { usePrimaryWorkspace, useWorkspacePermissions } from "../hooks/useSettings";
import { useAuth } from "../context/AuthContext";
import { useAgents, useAgentProjects, useProjectSubAgents } from "../hooks/useAgents";
import { useDeleteDocument, useDocuments, useProcessUrl, useUploadDocument, useProcessConnector } from "../hooks/useDocuments";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Dialog, DialogContent } from "../components/ui/dialog";

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

function getDocumentSource(document) {
  return document.filename || document.source || "Untitled";
}

function getDocumentType(document) {
  const source = getDocumentSource(document);

  if (source.startsWith("http")) return "Website";

  const extension = source
    .split(".")
    .pop()
    ?.toUpperCase();

  return extension && extension !== source.toUpperCase()
    ? extension
    : "Document";
}

function formatDate(value) {
  if (!value) return "Not available";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function StatusBadge({ status }) {
  if (status === "completed") {
    return (
      <span
        className="
        inline-flex
        items-center
        gap-2
        px-3
        py-1
        rounded-full
        bg-green-50
        text-green-700
      "
      >
        <CheckCircle2 size={14} />
        Completed
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span
        className="
        inline-flex
        items-center
        gap-2
        px-3
        py-1
        rounded-full
        bg-red-50
        text-red-700
      "
      >
        <AlertCircle size={14} />
        Failed
      </span>
    );
  }

  return (
    <span
      className="
      inline-flex
      items-center
      gap-2
      px-3
      py-1
      rounded-full
      bg-amber-50
      text-amber-700
    "
    >
      <Loader2
        size={14}
        className="animate-spin"
      />
      Processing
    </span>
  );
}

export default function KnowledgeBasePage() {
  const fileInputRef = useRef(null);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { canManageDatabase } = useWorkspacePermissions();
  const { data: workspace } = usePrimaryWorkspace();
  const hasAgentsPermission = workspace?.memberPermissions?.agents === true;
  const {
    data: standaloneAgents = [],
    isLoading: isLoadingAgents,
  } = useAgents(activeWorkspaceId);

  const {
    data: projects = [],
    isLoading: isLoadingProjects,
  } = useAgentProjects(activeWorkspaceId);

  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedCategory, setSelectedCategory] = useState("standalone");
  const [activeStandaloneId, setActiveStandaloneId] = useState("");
  const [activeSubAgentId, setActiveSubAgentId] = useState("");
  const [sourceTab, setSourceTab] = useState("files"); // "files", "website", "connectors"
  const [connectingTo, setConnectingTo] = useState(null);



  useEffect(() => {
    if (location.state) {
      const { preselectedAgentId, preselectedNetworkId } = location.state;
      if (preselectedNetworkId) {
        setSelectedCategory(preselectedNetworkId);
        setActiveSubAgentId(preselectedAgentId);
      } else if (preselectedAgentId) {
        setSelectedCategory("standalone");
        setActiveStandaloneId(preselectedAgentId);
      }
    }
  }, [location.state]);

  const {
    data: subAgents = [],
    isLoading: isSubAgentsLoading,
  } = useProjectSubAgents(selectedCategory !== "standalone" ? selectedCategory : null);

  const [url, setUrl] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [previewDoc, setPreviewDoc] = useState(null);

  // Determine the active agent ID based on the selected category
  const selectedAgentId = selectedCategory === "standalone" 
    ? (activeStandaloneId || standaloneAgents[0]?.id || "")
    : (activeSubAgentId || subAgents[0]?.id || "");

  const {
    data: documents = [],
    isError,
    isLoading,
    error,
  } = useDocuments(selectedAgentId);

  const uploadMutation =
    useUploadDocument(selectedAgentId);
  const processUrlMutation =
    useProcessUrl(selectedAgentId);
  const deleteMutation =
    useDeleteDocument(selectedAgentId);
  const processConnectorMutation =
    useProcessConnector(selectedAgentId);

  // Handle OAuth Callbacks
  useEffect(() => {
    const connection = searchParams.get("connection");
    const provider = searchParams.get("provider");
    
    if (connection === "success" && provider === "google" && selectedAgentId && user?.id && canManageDatabase) {
      setSearchParams(new URLSearchParams());
      setSourceTab("connectors");
      
      const fetchTokenAndOpenPicker = async () => {
        try {
          const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.blinkbot.in";
          const resp = await fetch(`${API_BASE_URL}/api/v1/connectors/google/token?user_id=${user.id}`);
          if (resp.ok) {
            const data = await resp.json();
            openGooglePicker(data.access_token, data.api_key, data.client_id);
          } else {
            toast.error("Failed to authenticate with Google Drive.");
          }
        } catch (e) {
          toast.error("Failed to load Google Drive Picker.");
        }
      };
      fetchTokenAndOpenPicker();
    }
  }, [searchParams, selectedAgentId, user, canManageDatabase]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch =
      searchTerm.trim().toLowerCase();

    if (!normalizedSearch) return documents;

    return documents.filter((document) =>
      getDocumentSource(document)
        .toLowerCase()
        .includes(normalizedSearch),
    );
  }, [documents, searchTerm]);

  const isMutating =
    uploadMutation.isPending ||
    processUrlMutation.isPending ||
    deleteMutation.isPending ||
    processConnectorMutation.isPending;

  const handleFileChange = async (event) => {
    if (!canManageDatabase) {
      toast.error("You do not have permission to upload files in this workspace.");
      return;
    }

    const files = Array.from(event.target.files || []);

    if (files.length === 0) return;

    if (!selectedAgentId) {
      toast.error("Select an agent before uploading.");
      return;
    }

    try {
      const uploadPromises = files.map((file) =>
        uploadMutation.mutateAsync({
          agentId: selectedAgentId,
          file,
        })
      );
      await Promise.all(uploadPromises);
      toast.success(
        files.length > 1
          ? `${files.length} files uploaded for processing`
          : "File uploaded for processing"
      );
    } catch (uploadError) {
      toast.error(
        uploadError.message ||
          "Unable to upload one or more files.",
      );
    } finally {
      event.target.value = "";
    }
  };

  const handleProcessUrl = async () => {
    if (!canManageDatabase) {
      toast.error("You do not have permission to scrape URLs in this workspace.");
      return;
    }

    const trimmedUrl = url.trim();

    if (!selectedAgentId) {
      toast.error("Select an agent before scraping.");
      return;
    }

    if (!trimmedUrl) {
      toast.error("Enter a website URL.");
      return;
    }

    try {
      await processUrlMutation.mutateAsync({
        agentId: selectedAgentId,
        url: trimmedUrl,
      });
      setUrl("");
      toast.success("Website queued for processing");
    } catch (urlError) {
      toast.error(
        urlError.message ||
          "Unable to process website.",
      );
    }
  };

  const handleDelete = async (documentId) => {
    try {
      await deleteMutation.mutateAsync(documentId);
      toast.success("Document deleted");
    } catch (deleteError) {
      toast.error(
        deleteError.message ||
          "Unable to delete document.",
      );
    }
  };

  const handleConnect = async (connectorId, connectorName) => {
    if (!canManageDatabase) {
      toast.error("You do not have permission to sync connectors in this workspace.");
      return;
    }

    if (!selectedAgentId) {
      toast.error("Select an agent before connecting.");
      return;
    }

    if (connectorId === "gdrive") {
      const initGdrivePicker = async () => {
        setConnectingTo("gdrive");
        try {
          const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.blinkbot.in";
          const resp = await fetch(`${API_BASE_URL}/api/v1/connectors/google/token?user_id=${user.id}`);
          if (resp.ok) {
            const data = await resp.json();
            openGooglePicker(data.access_token, data.api_key, data.client_id);
          } else {
            // Not connected -> redirect to authorize
            window.location.href = `${API_BASE_URL}/api/v1/connectors/google/authorize?user_id=${user.id}`;
          }
        } catch (e) {
          toast.error("Error communicating with server.");
        } finally {
          setConnectingTo(null);
        }
      };
      initGdrivePicker();
      return;
    }

    setConnectingTo(connectorId);
    try {
      const response = await processConnectorMutation.mutateAsync({
        agentId: selectedAgentId,
        connectorId: connectorId,
      });
      toast.success(response.message || `Successfully connected to ${connectorName}.`);
    } catch (error) {
      toast.error(error.message || `Failed to connect to ${connectorName}.`);
    } finally {
      setConnectingTo(null);
    }
  };

  const openGooglePicker = async (accessToken, apiKey, clientId) => {
    console.log("Starting openGooglePicker...", { hasToken: !!accessToken, hasApiKey: !!apiKey, clientId });
    if (!window.gapi) {
      toast.error("Google API client script is not loaded in window.");
      return;
    }

    try {
      window.gapi.load("picker", {
        callback: () => {
          console.log("Google Picker library loaded successfully.");
          try {
            const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
              .setMimeTypes("application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document")
              .setSelectFolderEnabled(false);

            const picker = new window.google.picker.PickerBuilder()
              .addView(view)
              .setOAuthToken(accessToken)
              .setDeveloperKey(apiKey)
              .setCallback(async (data) => {
                console.log("Picker callback action:", data.action);
                if (data.action === window.google.picker.Action.PICKED) {
                  const files = data.docs.map(doc => ({
                    id: doc.id,
                    name: doc.name,
                    mimeType: doc.mimeType
                  }));
                  
                  setConnectingTo("gdrive");
                  toast.loading("Syncing selected files from Google Drive...", { id: "sync-toast" });
                  try {
                    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://api.blinkbot.in";
                    const resp = await fetch(`${API_BASE_URL}/api/v1/connectors/google/import`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        agent_id: selectedAgentId,
                        user_id: user.id,
                        files: files
                      })
                    });

                    const resData = await resp.json();
                    if (resp.ok) {
                      toast.success(resData.message, { id: "sync-toast" });
                      queryClient.invalidateQueries(["documents", selectedAgentId]);
                    } else {
                      toast.error(resData.detail || "Failed to import selected files.", { id: "sync-toast" });
                    }
                  } catch (e) {
                    toast.error("Error connecting to server.", { id: "sync-toast" });
                  } finally {
                    setConnectingTo(null);
                  }
                }
              })
              .build();
            
            console.log("Making Google Picker visible.");
            picker.setVisible(true);
          } catch (pickerError) {
            console.error("Error during Picker construction:", pickerError);
            toast.error("Failed to build Google Picker: " + pickerError.message);
          }
        },
        onerror: (err) => {
          console.error("GAPI load picker onerror:", err);
          toast.error("GAPI failed to load Picker module.");
        }
      });
    } catch (err) {
      console.error("GAPI load wrapper exception:", err);
      toast.error("GAPI load wrapper exception: " + err.message);
    }
  };



  return (
    <div>
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-foreground">
          Knowledge Base
        </h1>

        <p className="text-muted-foreground mt-2">
          Upload documents, scrape websites and manage
          your AI knowledge sources.
        </p>
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="glass-card p-6 flex-1">
            <h3 className="font-semibold text-lg mb-4 text-foreground">
              Knowledge Sources
            </h3>

            <div className="mb-4 space-y-4">
              <div>
                <label className="text-xs uppercase text-muted-foreground font-semibold mb-2 block">
                  Target Group
                </label>
                <Select
                  value={selectedCategory}
                  onValueChange={(value) => {
                    setSelectedCategory(value);
                    if (value === "standalone") {
                      setActiveStandaloneId(standaloneAgents[0]?.id || "");
                    } else {
                      setActiveSubAgentId(""); // Will default to first sub-agent once loaded
                    }
                  }}
                  disabled={isLoadingAgents || isLoadingProjects}
                >
                  <SelectTrigger className="w-full h-12">
                    <SelectValue placeholder="Select Group" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standalone">Standalone Agents</SelectItem>
                    {projects.map((project) => (
                      <SelectItem key={project.id} value={project.id}>
                        Network: {project.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-xs uppercase text-muted-foreground font-semibold mb-2 block">
                  {selectedCategory === "standalone" ? "Specific Agent" : "Network Sub-Agent"}
                </label>
                {selectedCategory === "standalone" ? (
                  <Select
                    value={selectedAgentId}
                    onValueChange={(value) => setActiveStandaloneId(value)}
                    disabled={isLoadingAgents || standaloneAgents.length === 0}
                  >
                    <SelectTrigger className="w-full h-12">
                      <SelectValue placeholder={standaloneAgents.length === 0 ? "No standalone agents" : "Select Agent"} />
                    </SelectTrigger>
                    <SelectContent>
                      {standaloneAgents.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Select
                    value={selectedAgentId}
                    onValueChange={(value) => setActiveSubAgentId(value)}
                    disabled={isSubAgentsLoading || subAgents.length === 0}
                  >
                    <SelectTrigger className="w-full h-12">
                      <SelectValue placeholder={subAgents.length === 0 ? "No sub-agents found" : "Select Sub-Agent"} />
                    </SelectTrigger>
                    <SelectContent>
                      {subAgents.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>

            {/* Tabs for Data Input */}
            <div className="flex bg-muted p-1 rounded-xl mb-6">
              <button
                onClick={() => setSourceTab("files")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${sourceTab === "files" ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
              >
                Files
              </button>
              <button
                onClick={() => setSourceTab("website")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${sourceTab === "website" ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
              >
                Website
              </button>
              <button
                onClick={() => setSourceTab("connectors")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${sourceTab === "connectors" ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
              >
                Connectors
              </button>
            </div>

            {canManageDatabase ? (
              <div className="mt-4">
                {sourceTab === "files" && (
                  <div
                  className="
                  border-2
                  border-dashed
                  border-primary/20
                  rounded-[28px]
                  h-[280px]
                  flex
                  flex-col
                  items-center
                  justify-center
                  text-center
                  bg-primary/5
                "
                >
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                    <UploadCloud
                      size={30}
                      className="text-primary"
                    />
                  </div>

                  <h4 className="font-semibold text-lg mt-5">
                    Drop files here
                  </h4>

                  <p className="text-muted-foreground mt-2">
                    PDF, DOCX, TXT, CSV
                  </p>

                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.csv"
                    className="hidden"
                    onChange={handleFileChange}
                  />

                  <button
                    onClick={() =>
                      fileInputRef.current?.click()
                    }
                    disabled={!selectedAgentId || isMutating}
                    className="
                    mt-5
                    px-5
                    py-3
                    rounded-2xl
                    btn-primary
                    disabled:opacity-60
                  "
                  >
                    {uploadMutation.isPending
                      ? "Uploading..."
                      : "Browse Files"}
                  </button>
                </div>
                )}

                {sourceTab === "website" && (
                <div className="mt-2">
                  <label className="font-medium block mb-3">
                    Website URL
                  </label>

                  <div className="relative">
                    <Globe
                      size={18}
                      className="
                      absolute
                      left-4
                      top-4
                      text-slate-400
                      dark:text-zinc-500
                    "
                    />

                    <input
                      value={url}
                      onChange={(event) =>
                        setUrl(event.target.value)
                      }
                      placeholder="https://example.com"
                      className="
                      w-full
                      border
                      border-border
                      bg-card
                      text-foreground
                      rounded-2xl
                      pl-12
                      py-4
                    "
                    />
                  </div>

                  <button
                    onClick={handleProcessUrl}
                    disabled={!selectedAgentId || isMutating}
                    className="
                    w-full
                    mt-4
                    py-3
                    rounded-2xl
                    border
                    border-border
                    hover:bg-muted
                    disabled:opacity-60
                  "
                  >
                    {processUrlMutation.isPending
                      ? "Scraping..."
                      : "Scrape Website"}
                  </button>
                </div>
                )}

                {sourceTab === "connectors" && (
                  <div className="space-y-4 max-h-[360px] overflow-y-auto pr-2 custom-scrollbar">
                    <p className="text-sm text-muted-foreground mb-4">
                      Connect your existing tools to continuously sync data to your AI.
                    </p>

                    {[
                      { id: "gdrive", name: "Google Drive", icon: Cloud, color: "text-blue-500", bg: "bg-blue-500/10", desc: "Sync docs, sheets, slides" },
                      { id: "notion", name: "Notion", icon: FileText, color: "text-slate-700 dark:text-slate-300", bg: "bg-slate-500/10", desc: "Sync workspace pages" },
                      { id: "slack", name: "Slack", icon: MessageSquare, color: "text-purple-500", bg: "bg-purple-500/10", desc: "Sync channels & threads" },
                      { id: "github", name: "GitHub", icon: Code, color: "text-zinc-800 dark:text-zinc-200", bg: "bg-zinc-500/10", desc: "Sync issues & PRs" },
                    ].map((connector) => {
                      const isConnecting = connectingTo === connector.id;
                      
                      return (
                      <div key={connector.id} className="flex items-center justify-between p-4 rounded-2xl border border-border bg-background hover:bg-muted/50 transition">
                        <div className="flex items-center gap-3">
                          <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${connector.bg}`}>
                            <connector.icon size={20} className={connector.color} />
                          </div>
                          <div>
                            <div className="font-semibold text-sm">{connector.name}</div>
                            <div className="text-xs text-muted-foreground">{connector.desc}</div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleConnect(connector.id, connector.name)}
                          disabled={!selectedAgentId || isConnecting || isMutating}
                          className="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-semibold rounded-lg transition disabled:opacity-60 flex items-center gap-2"
                        >
                          {isConnecting ? (
                            <>
                              <Loader2 size={12} className="animate-spin" />
                              Connecting...
                            </>
                          ) : (
                            <>
                              <Link2 size={12} />
                              Connect
                            </>
                          )}
                        </button>
                      </div>
                    )})}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground p-5 bg-muted/20 rounded-2xl border border-border text-center">
                You do not have permission to upload documents or scrape websites in this workspace.
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-8">
          <div className="glass-card overflow-hidden">
            <div className="p-6 border-b border-border">
              <div className="flex flex-wrap gap-4">
                <div className="relative flex-1">
                  <Search
                    size={18}
                    className="
                    absolute
                    left-4
                    top-4
                    text-slate-400
                    dark:text-zinc-500
                  "
                  />

                  <input
                    value={searchTerm}
                    onChange={(event) =>
                      setSearchTerm(event.target.value)
                    }
                    placeholder="Search knowledge..."
                    className="
                    w-full
                    border
                    border-border
                    bg-muted
                    text-foreground
                    rounded-2xl
                    pl-12
                    py-4
                  "
                  />
                </div>

                <button
                  className="
                  px-4
                  py-3
                  rounded-2xl
                  border
                  border-border
                  hover:bg-muted
                  flex
                  items-center
                  gap-2
                "
                >
                  <Filter size={16} />
                  Filters
                </button>
              </div>
            </div>

            {isError && (
              <div className="m-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
                {error?.message ||
                  "Unable to load documents."}
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b border-border">
                    <th className="px-6 py-4 text-sm font-semibold">
                      Source
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Type
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Status
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Size
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Chunks
                    </th>

                    <th className="px-6 py-4 text-sm font-semibold">
                      Added
                    </th>

                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>

                <tbody>
                  {isLoading && (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-6 py-6"
                      >
                        <LoadingSkeleton
                          count={3}
                          className="h-16"
                        />
                      </td>
                    </tr>
                  )}

                  {!isLoading &&
                    filteredDocuments.length === 0 && (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-6 py-10 text-center text-sm text-slate-500 dark:text-zinc-400"
                        >
                          {selectedAgentId
                            ? "No documents found."
                            : "Select an agent to view documents."}
                        </td>
                      </tr>
                    )}

                  {!isLoading &&
                    filteredDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className="
                        border-b
                        border-border
                        hover:bg-muted
                      "
                      >
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <FileText size={18} />

                            <span>
                              {getDocumentSource(document)}
                            </span>
                          </div>
                        </td>

                        <td className="px-6 py-5">
                          {getDocumentType(document)}
                        </td>

                        <td className="px-6 py-5">
                          <StatusBadge
                            status={document.status}
                          />
                        </td>

                        <td className="px-6 py-5 text-sm text-muted-foreground">
                          {formatBytes(document.file_size_bytes)}
                        </td>

                        <td className="px-6 py-5 text-sm">
                          <span className="bg-primary/10 text-primary px-2 py-1 rounded-md font-medium">
                            {document.chunk_count || 0}
                          </span>
                        </td>

                        <td className="px-6 py-5 text-sm text-muted-foreground">
                          {formatDate(document.created_at)}
                        </td>

                        <td className="px-6 py-5">
                          <div className="flex items-center gap-2">
                            {["PDF", "PNG", "JPG", "JPEG"].includes(getDocumentType(document)) && (
                              <button
                                onClick={() => setPreviewDoc(document)}
                                className="
                                p-2
                                rounded-xl
                                hover:bg-blue-50
                                hover:text-blue-600
                                dark:hover:bg-blue-500/10
                                dark:hover:text-blue-300
                                "
                                title="Preview Document"
                              >
                                <Eye size={16} />
                              </button>
                            )}
                            {canManageDatabase && (
                            <button
                              onClick={() =>
                                handleDelete(document.id)
                              }
                              disabled={deleteMutation.isPending}
                              className="
                              p-2
                              rounded-xl
                              hover:bg-red-50
                              hover:text-red-600
                              dark:hover:bg-red-500/10
                              dark:hover:text-red-300
                              disabled:opacity-60
                            "
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Document Preview Modal */}
      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="max-w-5xl h-[85vh] flex p-0 overflow-hidden border-0 bg-background shadow-2xl rounded-2xl">
          <div className="flex-1 flex flex-col bg-muted/10 w-full h-full">
            <div className="p-4 border-b border-border bg-card flex items-center justify-between">
              <h3 className="font-semibold">{previewDoc?.filename}</h3>
            </div>
            <div className="flex-1 p-6 overflow-hidden flex items-center justify-center">
              {previewDoc && getDocumentType(previewDoc) === "PDF" && (
                <iframe 
                  src={`${API_URL}/uploads/${previewDoc.filename}`} 
                  className="w-full h-full rounded-lg border border-border bg-white"
                  title="PDF Preview"
                />
              )}
              {previewDoc && ["PNG", "JPG", "JPEG"].includes(getDocumentType(previewDoc)) && (
                <img 
                  src={`${API_URL}/uploads/${previewDoc.filename}`} 
                  alt="Preview" 
                  className="max-w-full max-h-full object-contain rounded-lg border border-border"
                />
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
