import React, { useState, useEffect } from "react";
import {
  Cpu,
  ShieldCheck,
  Plus,
  Key,
  Globe,
  Sparkles,
  CheckCircle2,
  XCircle,
  Loader2,
  Trash2,
  Lock,
  Layers,
  HelpCircle,
  ExternalLink,
  Search,
  Zap,
  Server,
  LayoutGrid,
  List,
  Play,
  AlertCircle,
  Pencil,
  Eye,
  EyeOff,
  Network,
  RotateCw
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";
import {
  useAllModels,
  useCreateModel,
  useUpdateModel,
  useDeleteModel,
  useTestProviderKey,
  useTestSingleModel
} from "../hooks/useModels";
import { useUserSettings, useUpdateUserSettings } from "../hooks/useSettings";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from "../components/ui/dialog";

export default function ModelsPage() {
  const [activeTab, setActiveTab] = useState("catalog"); // "catalog" | "keys"
  const [selectedProvider, setSelectedProvider] = useState("all");
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [testingProvider, setTestingProvider] = useState(null);

  // Data queries
  const { data: modelsData, isLoading: isLoadingModels, refetch: refetchModels, isRefetching: isRefetchingModels } = useAllModels();
  const { data: userSettings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();

  const createModelMutation = useCreateModel();
  const updateModelMutation = useUpdateModel();
  const deleteModelMutation = useDeleteModel();
  const testKeyMutation = useTestProviderKey();
  const testSingleModelMutation = useTestSingleModel();
  const [modelTestState, setModelTestState] = useState({});
  const [editingModel, setEditingModel] = useState(null);
  const [showModelApiKey, setShowModelApiKey] = useState(false);
  const [showEditModelApiKey, setShowEditModelApiKey] = useState(false);

  // Form for adding custom model
  const [newModelForm, setNewModelForm] = useState({
    name: "",
    model_id: "",
    provider: "groq",
    category: "General",
    requires_key: false,
    description: "",
    base_url: "",
    api_key: ""
  });

  // Local state for API keys form in Tab 2
  const [apiKeys, setApiKeys] = useState({
    openai_api_key: "",
    groq_api_key: "",
    openrouter_api_key: "",
    huggingface_api_key: "",
    anthropic_api_key: "",
    gemini_api_key: "",
    share_keys: false
  });

  const [showKeys, setShowKeys] = useState({
    openai: false,
    groq: false,
    openrouter: false,
    huggingface: false,
    anthropic: false,
    gemini: false
  });

  const toggleShowKey = (provider) => {
    setShowKeys((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  useEffect(() => {
    if (userSettings) {
      setApiKeys({
        openai_api_key: userSettings.openai_api_key || "",
        groq_api_key: userSettings.groq_api_key || "",
        openrouter_api_key: userSettings.openrouter_api_key || "",
        huggingface_api_key: userSettings.huggingface_api_key || "",
        anthropic_api_key: userSettings.anthropic_api_key || "",
        gemini_api_key: userSettings.gemini_api_key || "",
        share_keys: userSettings.share_keys || false
      });
    }
  }, [userSettings]);

  const modelsList = modelsData?.models || [];

  const filteredModels = modelsList.filter((m) => {
    const matchesProvider = selectedProvider === "all" || m.provider.toLowerCase() === selectedProvider.toLowerCase();
    const query = searchQuery.trim().toLowerCase();
    const matchesSearch = !query || 
      m.name.toLowerCase().includes(query) || 
      m.model_id.toLowerCase().includes(query) ||
      m.provider.toLowerCase().includes(query) ||
      (m.category && m.category.toLowerCase().includes(query));
    return matchesProvider && matchesSearch;
  });

  // Toggle model active status with automated async live test
  const handleToggleActive = async (modelItem) => {
    const { id: dbId, model_id, provider, base_url, is_active } = modelItem;
    const nextStatus = !is_active;

    if (nextStatus) {
      // Activating model -> run live test async
      setModelTestState((prev) => ({
        ...prev,
        [model_id]: { status: "testing", error: null }
      }));

      try {
        const res = await testSingleModelMutation.mutateAsync({ provider, model_id, base_url });
        if (res.status === "success") {
          await updateModelMutation.mutateAsync({
            modelId: dbId,
            data: { is_active: true }
          });
          setModelTestState((prev) => ({
            ...prev,
            [model_id]: { status: "ready", error: null }
          }));
          toast.success(`Model '${modelItem.name || model_id}' verified & activated!`);
        } else {
          // Test failed or warning (rate limit / 404 / 401)
          setModelTestState((prev) => ({
            ...prev,
            [model_id]: { status: "failed", error: res.message }
          }));
          toast.error(`Activation failed: ${res.message}`);
        }
      } catch (e) {
        const errMsg = e.message || "Model live test failed";
        setModelTestState((prev) => ({
          ...prev,
          [model_id]: { status: "failed", error: errMsg }
        }));
        toast.error(`Activation failed: ${errMsg}`);
      }
    } else {
      // Deactivating model
      try {
        await updateModelMutation.mutateAsync({
          modelId: dbId,
          data: { is_active: false }
        });
        setModelTestState((prev) => ({
          ...prev,
          [model_id]: { status: null, error: null }
        }));
        toast.success(`Model '${model_id}' deactivated`);
      } catch {
        toast.error("Failed to deactivate model");
      }
    }
  };

  // Add model handler
  const handleAddModel = async () => {
    if (!newModelForm.name.trim() || !newModelForm.model_id.trim()) {
      toast.error("Please fill in Model Name and Model ID");
      return;
    }
    try {
      await createModelMutation.mutateAsync(newModelForm);
      toast.success("New AI Model added successfully!");
      setIsAddModalOpen(false);
      setNewModelForm({
        name: "",
        model_id: "",
        provider: "groq",
        category: "General",
        requires_key: false,
        description: "",
        base_url: "",
        api_key: ""
      });
    } catch (e) {
      toast.error(e.message || "Failed to add model");
    }
  };

  // Edit model handler
  const handleOpenEditModal = (model) => {
    setEditingModel({
      id: model.id,
      name: model.name,
      model_id: model.model_id,
      provider: model.provider,
      category: model.category || "General",
      requires_key: model.requires_key,
      description: model.description || "",
      base_url: model.base_url || "",
      api_key: model.api_key || ""
    });
  };

  const handleSaveEditModel = async () => {
    if (!editingModel.name.trim() || !editingModel.model_id.trim()) {
      toast.error("Please fill in Model Name and Model ID");
      return;
    }
    try {
      await updateModelMutation.mutateAsync({
        modelId: editingModel.id,
        data: {
          name: editingModel.name.trim(),
          model_id: editingModel.model_id.trim(),
          provider: editingModel.provider,
          category: editingModel.category,
          requires_key: editingModel.requires_key,
          description: editingModel.description.trim(),
          base_url: editingModel.base_url.trim(),
          api_key: editingModel.api_key.trim()
        }
      });
      toast.success("Model updated successfully!");
      setEditingModel(null);
    } catch (e) {
      toast.error(e.message || "Failed to update model");
    }
  };

  // Delete model handler
  const handleDeleteModel = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete model "${name}"?`)) return;
    try {
      await deleteModelMutation.mutateAsync(id);
      toast.success("Model removed from catalog");
    } catch {
      toast.error("Failed to delete model");
    }
  };

  // Save Provider API Keys
  const handleSaveKeys = async () => {
    try {
      await updateSettingsMutation.mutateAsync(apiKeys);
      toast.success("Provider API Keys saved successfully!");
    } catch {
      toast.error("Failed to save provider keys");
    }
  };

  // Test provider connection
  const handleTestKey = async (provider, key, baseUrl) => {
    setTestingProvider(provider);
    try {
      const res = await testKeyMutation.mutateAsync({ provider, api_key: key, base_url: baseUrl });
      if (res.status === "connected") {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (e) {
      toast.error(e.message || "Connection test failed");
    } finally {
      setTestingProvider(null);
    }
  };

  // Helper to check if API key exists for a provider
  const hasKeyForProvider = (provider) => {
    const prov = (provider || "").toLowerCase();
    if (prov === "ollama") return true; // Local
    const keyName = `${prov}_api_key`;
    return Boolean(userSettings?.[keyName]?.trim());
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/50 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">AI Models & Providers Hub</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              Multi-Provider Architecture
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Configure dynamic AI model choices and manage your provider API credentials securely.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={async () => {
              await refetchModels();
              toast.success("Models catalog refreshed!");
            }}
            disabled={isRefetchingModels}
            className="rounded-xl shadow-sm gap-2 border-border/60 hover:bg-muted"
          >
            <RotateCw size={15} className={isRefetchingModels ? "animate-spin text-primary" : ""} />
            <span>Refresh</span>
          </Button>
          {activeTab === "catalog" && (
            <Button
              onClick={() => setIsAddModalOpen(true)}
              className="rounded-xl shadow-md gap-2"
            >
              <Plus size={16} /> Add Custom Model
            </Button>
          )}
          {activeTab === "keys" && (
            <Button
              onClick={handleSaveKeys}
              className="rounded-xl shadow-md gap-2"
              disabled={updateSettingsMutation.isPending}
            >
              {updateSettingsMutation.isPending && <Loader2 className="animate-spin" size={16} />}
              Save All Credentials
            </Button>
          )}
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-border/60">
        <button
          onClick={() => setActiveTab("catalog")}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "catalog"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers size={18} /> Model Catalog ({modelsList.length})
        </button>
        <button
          onClick={() => setActiveTab("keys")}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "keys"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Key size={18} /> Provider Credentials & Keys
        </button>
      </div>

      {/* ──────────────── TAB 1: MODEL CATALOG ──────────────── */}
      {activeTab === "catalog" && (
        <div className="space-y-6">
          {/* Controls Bar: Provider Filters, Search, and View Toggle */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            {/* Provider Filter Badges */}
            <div className="flex flex-wrap items-center gap-2">
              {["all", "groq", "openai", "openrouter", "anthropic", "gemini", "huggingface"].map((prov) => (
                <button
                  key={prov}
                  onClick={() => setSelectedProvider(prov)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-medium capitalize transition-all border ${
                    selectedProvider === prov
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "bg-card hover:bg-muted text-muted-foreground border-border/60"
                  }`}
                >
                  {prov}
                </button>
              ))}
            </div>

            {/* Search + View Mode Switcher */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search model name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-3 py-1.5 rounded-xl border border-input bg-card text-xs w-48 sm:w-64 focus:ring-2 focus:ring-primary outline-none transition-all"
                />
              </div>

              {/* View Toggle (Grid / Block vs List) */}
              <div className="flex items-center p-1 rounded-xl bg-card border border-border/60">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-1.5 rounded-lg transition-colors ${
                    viewMode === "grid" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="Block / Grid View"
                >
                  <LayoutGrid size={16} />
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`p-1.5 rounded-lg transition-colors ${
                    viewMode === "list" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                  title="List / Table View"
                >
                  <List size={16} />
                </button>
              </div>
            </div>
          </div>

          {/* Models Content */}
          {isLoadingModels ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <LoadingSkeleton className="h-40 rounded-2xl" />
              <LoadingSkeleton className="h-40 rounded-2xl" />
              <LoadingSkeleton className="h-40 rounded-2xl" />
            </div>
          ) : filteredModels.length === 0 ? (
            <div className="text-center py-12 bg-card rounded-2xl border border-dashed border-border/60">
              <Sparkles className="mx-auto text-muted-foreground mb-3" size={32} />
              <h3 className="font-semibold text-lg">No models found</h3>
              <p className="text-sm text-muted-foreground mt-1">Try tweaking your search or selected provider filter.</p>
            </div>
          ) : viewMode === "grid" ? (
            /* 🔲 BLOCK / GRID VIEW */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredModels.map((m) => {
                const keyConfigured = hasKeyForProvider(m.provider);
                const isLocked = m.requires_key && !keyConfigured;
                const activeState = isLocked ? false : m.is_active;

                return (
                  <div
                    key={m.id}
                    className={`p-5 rounded-2xl border transition-all bg-card shadow-sm flex flex-col justify-between relative ${
                      activeState ? "border-border/80 hover:border-primary/50" : "border-border/40 opacity-60 bg-muted/20"
                    }`}
                  >
                    <div>
                      {/* Header Row */}
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-muted text-muted-foreground border border-border/40">
                              {m.provider}
                            </span>
                            {m.category && (
                              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-primary/10 text-primary">
                                {m.category}
                              </span>
                            )}
                          </div>
                          <h3 className="font-bold text-base mt-1.5 leading-snug">{m.name}</h3>
                          <code className="text-xs text-muted-foreground font-mono block mt-0.5">{m.model_id}</code>
                        </div>

                        {/* Active Switch */}
                        <div title={isLocked ? `Submit ${m.provider} API key in Credentials tab to unlock activation` : ""}>
                          <Switch
                            checked={activeState}
                            disabled={isLocked || modelTestState[m.model_id]?.status === "testing"}
                            onCheckedChange={() => handleToggleActive(m)}
                          />
                        </div>
                      </div>

                      <p className="text-xs text-muted-foreground line-clamp-2 mb-4">
                        {m.description || "Versatile model suitable for general assistant tasks."}
                      </p>
                    </div>

                    {/* Footer Row */}
                    <div className="pt-3 border-t border-border/40 flex items-center justify-between mt-2">
                      {isLocked ? (
                        <button
                          onClick={() => setActiveTab("keys")}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
                        >
                          <Lock size={12} /> Add Key to Unlock
                        </button>
                      ) : modelTestState[m.model_id]?.status === "testing" ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-500 bg-blue-500/10 px-2.5 py-1 rounded-lg border border-blue-500/20">
                          <Loader2 size={12} className="animate-spin" /> Testing...
                        </span>
                      ) : modelTestState[m.model_id]?.status === "failed" ? (
                        <div className="relative group inline-block">
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-500 bg-red-500/10 px-2.5 py-1 rounded-lg border border-red-500/30 cursor-help">
                            <XCircle size={12} /> Failed
                          </span>
                          {modelTestState[m.model_id]?.error && (
                            <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-72 p-3 bg-zinc-950 border border-red-500/50 text-zinc-100 rounded-xl shadow-2xl z-50 text-xs transition-all animate-in fade-in zoom-in-95">
                              <div className="font-bold text-red-500 mb-1 flex items-center gap-1.5">
                                <AlertCircle size={14} /> Execution Error:
                              </div>
                              <div className="text-zinc-300 text-[11px] leading-relaxed break-words font-mono">
                                {modelTestState[m.model_id].error}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : activeState ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                          <CheckCircle2 size={12} /> Ready
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground bg-muted/50 px-2.5 py-1 rounded-lg border border-border/40">
                          <Zap size={12} /> Deactivated
                        </span>
                      )}

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleOpenEditModal(m)}
                          className="text-muted-foreground hover:text-primary transition-colors p-1.5 rounded-lg hover:bg-muted"
                          title="Edit model configuration"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => handleDeleteModel(m.id, m.name)}
                          className="text-muted-foreground hover:text-red-500 transition-colors p-1.5 rounded-lg hover:bg-muted"
                          title="Delete model"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* 📑 COMPACT LIST / TABLE VIEW */
            <div className="rounded-2xl border border-border/60 bg-card overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/40 border-b border-border/60 text-muted-foreground font-semibold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Model Name & ID</th>
                      <th className="py-3 px-4">Provider</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Tier / Key Status</th>
                      <th className="py-3 px-4 text-center">Active Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {filteredModels.map((m) => {
                      const keyConfigured = hasKeyForProvider(m.provider);
                      const isLocked = m.requires_key && !keyConfigured;
                      const activeState = isLocked ? false : m.is_active;

                      return (
                        <tr key={m.id} className="hover:bg-muted/20 transition-colors">
                          <td className="py-3 px-4 font-medium">
                            <div className="font-bold text-sm text-foreground">{m.name}</div>
                            <code className="text-[11px] text-muted-foreground font-mono">{m.model_id}</code>
                          </td>
                          <td className="py-3 px-4">
                            <span className="uppercase font-bold text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border/40">
                              {m.provider}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary">
                              {m.category || "General"}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {isLocked ? (
                              <button
                                onClick={() => setActiveTab("keys")}
                                className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-500 hover:underline"
                              >
                                <Lock size={12} /> Key Required
                              </button>
                            ) : modelTestState[m.model_id]?.status === "testing" ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-500">
                                <Loader2 size={12} className="animate-spin" /> Testing...
                              </span>
                            ) : modelTestState[m.model_id]?.status === "failed" ? (
                              <div className="relative group inline-block">
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-500 cursor-help">
                                  <XCircle size={12} /> Failed
                                </span>
                                {modelTestState[m.model_id]?.error && (
                                  <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-72 p-3 bg-zinc-950 border border-red-500/50 text-zinc-100 rounded-xl shadow-2xl z-50 text-xs transition-all animate-in fade-in zoom-in-95">
                                    <div className="font-bold text-red-500 mb-1 flex items-center gap-1.5">
                                      <AlertCircle size={14} /> Execution Error:
                                    </div>
                                    <div className="text-zinc-300 text-[11px] leading-relaxed break-words font-mono">
                                      {modelTestState[m.model_id].error}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ) : activeState ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-500">
                                <CheckCircle2 size={12} /> Ready
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                                <Zap size={12} /> Deactivated
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-center">
                            <div title={isLocked ? `Submit ${m.provider} API key in Credentials tab to unlock` : ""}>
                              <Switch
                                checked={activeState}
                                disabled={isLocked || modelTestState[m.model_id]?.status === "testing"}
                                onCheckedChange={() => handleToggleActive(m)}
                              />
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleOpenEditModal(m)}
                                className="text-muted-foreground hover:text-primary transition-colors p-1.5 rounded-lg hover:bg-muted"
                                title="Edit model configuration"
                              >
                                <Pencil size={14} />
                              </button>
                              <button
                                onClick={() => handleDeleteModel(m.id, m.name)}
                                className="text-muted-foreground hover:text-red-500 transition-colors p-1.5 rounded-lg hover:bg-muted"
                                title="Delete model"
                              >
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
          )}
        </div>
      )}

      {/* ──────────────── TAB 2: PROVIDER API KEYS ──────────────── */}
      {activeTab === "keys" && (
        <div className="space-y-6">
          {/* Security Trust Banner */}
          <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-3">
            <ShieldCheck className="text-emerald-500 shrink-0 mt-0.5" size={20} />
            <div>
              <h4 className="font-semibold text-sm text-emerald-500">AES-256 Encrypted Security Vault</h4>
              <p className="text-xs text-emerald-500/90 mt-0.5">
                All provider keys are encrypted at rest using enterprise-grade AES-256-GCM. Keys are decrypted strictly in ephemeral server memory during inference requests and are never logged or exposed.
              </p>
            </div>
          </div>

          {/* Workspace API Key Sharing Toggle */}
          <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm flex items-center justify-between">
            <div className="space-y-1 pr-4">
              <h4 className="font-bold text-sm flex items-center gap-2">
                <Network size={16} className="text-primary animate-pulse" /> Share API Credentials Workspace-wide
              </h4>
              <p className="text-xs text-muted-foreground">
                Allow team members in this workspace to run models using your encrypted credentials securely without entering their own keys.
              </p>
            </div>
            <Switch
              checked={apiKeys.share_keys}
              onCheckedChange={(val) => setApiKeys((prev) => ({ ...prev, share_keys: val }))}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* OpenAI */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs">
                    GPT
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">OpenAI API Key</h4>
                    <p className="text-xs text-muted-foreground">For GPT-4o, GPT-4o Mini, and Dall-E</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("openai", apiKeys.openai_api_key)}
                  disabled={testingProvider === "openai"}
                >
                  {testingProvider === "openai" ? <Loader2 className="animate-spin" size={14} /> : "Test Key"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.openai ? "text" : "password"}
                  value={apiKeys.openai_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, openai_api_key: e.target.value }))}
                  placeholder="sk-proj-..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("openai")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.openai ? "Hide API key" : "Show API key"}
                >
                  {showKeys.openai ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Groq */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-500 flex items-center justify-center font-bold text-xs">
                    GRQ
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Groq API Key</h4>
                    <p className="text-xs text-muted-foreground">High-speed inference for Llama 3.3 & Mixtral</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("groq", apiKeys.groq_api_key)}
                  disabled={testingProvider === "groq"}
                >
                  {testingProvider === "groq" ? <Loader2 className="animate-spin" size={14} /> : "Test Key"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.groq ? "text" : "password"}
                  value={apiKeys.groq_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, groq_api_key: e.target.value }))}
                  placeholder="gsk_..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("groq")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.groq ? "Hide API key" : "Show API key"}
                >
                  {showKeys.groq ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* OpenRouter */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center font-bold text-xs">
                    OR
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">OpenRouter API Key</h4>
                    <p className="text-xs text-muted-foreground">Access 200+ models (DeepSeek, Llama, Claude)</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("openrouter", apiKeys.openrouter_api_key)}
                  disabled={testingProvider === "openrouter"}
                >
                  {testingProvider === "openrouter" ? <Loader2 className="animate-spin" size={14} /> : "Test Key"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.openrouter ? "text" : "password"}
                  value={apiKeys.openrouter_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, openrouter_api_key: e.target.value }))}
                  placeholder="sk-or-v1-..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("openrouter")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.openrouter ? "Hide API key" : "Show API key"}
                >
                  {showKeys.openrouter ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* HuggingFace */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-yellow-500/10 text-yellow-500 flex items-center justify-center font-bold text-xs">
                    HF
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">HuggingFace Token</h4>
                    <p className="text-xs text-muted-foreground">For HF Serverless & TGI Endpoints</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("huggingface", apiKeys.huggingface_api_key)}
                  disabled={testingProvider === "huggingface"}
                >
                  {testingProvider === "huggingface" ? <Loader2 className="animate-spin" size={14} /> : "Test Token"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.huggingface ? "text" : "password"}
                  value={apiKeys.huggingface_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, huggingface_api_key: e.target.value }))}
                  placeholder="hf_..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("huggingface")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.huggingface ? "Hide API key" : "Show API key"}
                >
                  {showKeys.huggingface ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Anthropic */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center font-bold text-xs">
                    ANT
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Anthropic API Key</h4>
                    <p className="text-xs text-muted-foreground">For Claude 3.5 Sonnet & Haiku</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("anthropic", apiKeys.anthropic_api_key)}
                  disabled={testingProvider === "anthropic"}
                >
                  {testingProvider === "anthropic" ? <Loader2 className="animate-spin" size={14} /> : "Test Key"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.anthropic ? "text" : "password"}
                  value={apiKeys.anthropic_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, anthropic_api_key: e.target.value }))}
                  placeholder="sk-ant-..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("anthropic")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.anthropic ? "Hide API key" : "Show API key"}
                >
                  {showKeys.anthropic ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Gemini */}
            <div className="p-5 rounded-2xl bg-card border border-border/60 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center font-bold text-xs">
                    GEM
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Google Gemini API Key</h4>
                    <p className="text-xs text-muted-foreground">For Gemini 2.0 Flash & Pro</p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl text-xs"
                  onClick={() => handleTestKey("gemini", apiKeys.gemini_api_key)}
                  disabled={testingProvider === "gemini"}
                >
                  {testingProvider === "gemini" ? <Loader2 className="animate-spin" size={14} /> : "Test Key"}
                </Button>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showKeys.gemini ? "text" : "password"}
                  value={apiKeys.gemini_api_key}
                  onChange={(e) => setApiKeys((prev) => ({ ...prev, gemini_api_key: e.target.value }))}
                  placeholder="AIzaSy..."
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-xl border border-input bg-background font-mono text-xs focus:ring-2 focus:ring-primary outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleShowKey("gemini")}
                  className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                  title={showKeys.gemini ? "Hide API key" : "Show API key"}
                >
                  {showKeys.gemini ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────── MODAL: ADD CUSTOM MODEL ──────────────── */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="sm:max-w-2xl rounded-3xl p-6 sm:p-8 space-y-6">
          <DialogHeader className="border-b border-border/50 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                <Plus size={20} />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold">Add Custom AI Model</DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Register a custom open-source or proprietary LLM into your workspace catalog.
                </p>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-5 py-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Provider Platform
                </label>
                <select
                  value={newModelForm.provider}
                  onChange={(e) => setNewModelForm((p) => ({ ...p, provider: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-semibold outline-none focus:ring-2 focus:ring-primary capitalize transition-all"
                >
                  <option value="groq">Groq</option>
                  <option value="openai">OpenAI</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="huggingface">HuggingFace</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="custom_openai">Custom OpenAI Server</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Model Category
                </label>
                <select
                  value={newModelForm.category}
                  onChange={(e) => setNewModelForm((p) => ({ ...p, category: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-semibold outline-none focus:ring-2 focus:ring-primary transition-all"
                >
                  <option value="General">General Reasoning</option>
                  <option value="Reasoning">Deep Reasoning & Thinking</option>
                  <option value="Coding">Software & Code Generation</option>
                  <option value="Fast">Ultra-Fast Inference</option>
                  <option value="Vision">Multimodal & Vision</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Model Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. DeepSeek V3 Flagship"
                  value={newModelForm.name}
                  onChange={(e) => setNewModelForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-medium outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Model API Identifier String
                </label>
                <input
                  type="text"
                  placeholder="e.g. deepseek/deepseek-chat:free"
                  value={newModelForm.model_id}
                  onChange={(e) => setNewModelForm((p) => ({ ...p, model_id: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>
            </div>

            {newModelForm.provider !== "custom_openai" ? (
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Custom Base URL (Optional Override)
                </label>
                <input
                  type="text"
                  placeholder="e.g. https://api.together.xyz/v1 or leave blank for default provider URL"
                  value={newModelForm.base_url}
                  onChange={(e) => setNewModelForm((p) => ({ ...p, base_url: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-xs outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Custom Base URL (Required)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. https://api.together.xyz/v1"
                    value={newModelForm.base_url}
                    onChange={(e) => setNewModelForm((p) => ({ ...p, base_url: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-xs outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    API Key / Token
                  </label>
                  <div className="relative flex items-center">
                    <input
                      type={showModelApiKey ? "text" : "password"}
                      placeholder="Enter API key for this hosted model"
                      value={newModelForm.api_key}
                      onChange={(e) => setNewModelForm((p) => ({ ...p, api_key: e.target.value }))}
                      className="w-full pl-4 pr-10 py-3 rounded-2xl border border-input bg-card font-mono text-xs focus:ring-2 focus:ring-primary outline-none transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowModelApiKey(!showModelApiKey)}
                      className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                      title={showModelApiKey ? "Hide key" : "Show key"}
                    >
                      {showModelApiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                Model Description
              </label>
              <input
                type="text"
                placeholder="e.g. High-performance reasoning model ideal for complex coding tasks."
                value={newModelForm.description}
                onChange={(e) => setNewModelForm((p) => ({ ...p, description: e.target.value }))}
                className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
              />
            </div>

            <div className="flex items-center justify-between p-4 rounded-2xl border border-border/70 bg-muted/20 shadow-inner">
              <div className="space-y-0.5">
                <label className="text-sm font-bold block">Requires User API Key (Paid Tier)</label>
                <p className="text-xs text-muted-foreground">
                  Enable if this model requires a custom provider API key to activate and run.
                </p>
              </div>
              <Switch
                checked={newModelForm.requires_key}
                onCheckedChange={(v) => setNewModelForm((p) => ({ ...p, requires_key: v }))}
              />
            </div>
          </div>

          <DialogFooter className="border-t border-border/50 pt-4 gap-3">
            <Button
              variant="outline"
              className="rounded-xl px-6 py-2.5"
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              className="rounded-xl px-7 py-2.5 shadow-md font-semibold"
              onClick={handleAddModel}
              disabled={createModelMutation.isPending}
            >
              {createModelMutation.isPending && <Loader2 className="animate-spin mr-2" size={16} />}
              Add Model to Catalog
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ──────────────── MODAL: EDIT AI MODEL ──────────────── */}
      <Dialog open={Boolean(editingModel)} onOpenChange={(open) => !open && setEditingModel(null)}>
        <DialogContent className="sm:max-w-2xl rounded-3xl p-6 sm:p-8 space-y-6">
          <DialogHeader className="border-b border-border/50 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                <Pencil size={20} />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold">Edit Model Configuration</DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Update display name, model ID, category, or tier requirements for this model.
                </p>
              </div>
            </div>
          </DialogHeader>

          {editingModel && (
            <div className="space-y-5 py-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Provider Platform
                  </label>
                  <select
                    value={editingModel.provider}
                    onChange={(e) => setEditingModel((p) => ({ ...p, provider: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-semibold outline-none focus:ring-2 focus:ring-primary capitalize transition-all"
                  >
                    <option value="groq">Groq</option>
                    <option value="openai">OpenAI</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="huggingface">HuggingFace</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="custom_openai">Custom OpenAI Server</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Model Category
                  </label>
                  <select
                    value={editingModel.category}
                    onChange={(e) => setEditingModel((p) => ({ ...p, category: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-semibold outline-none focus:ring-2 focus:ring-primary transition-all"
                  >
                    <option value="General">General</option>
                    <option value="Reasoning">Reasoning</option>
                    <option value="Coding">Coding</option>
                    <option value="Fast">Fast</option>
                    <option value="Vision">Vision</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={editingModel.name}
                    onChange={(e) => setEditingModel((p) => ({ ...p, name: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm font-semibold outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    API Model ID
                  </label>
                  <input
                    type="text"
                    value={editingModel.model_id}
                    onChange={(e) => setEditingModel((p) => ({ ...p, model_id: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-xs outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
              </div>

              {editingModel.provider !== "custom_openai" ? (
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Base URL Override (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="https://api.example.com/v1"
                    value={editingModel.base_url}
                    onChange={(e) => setEditingModel((p) => ({ ...p, base_url: e.target.value }))}
                    className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-xs outline-none focus:ring-2 focus:ring-primary transition-all"
                  />
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                      Custom Base URL (Required)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. https://api.together.xyz/v1"
                      value={editingModel.base_url}
                      onChange={(e) => setEditingModel((p) => ({ ...p, base_url: e.target.value }))}
                      className="w-full px-4 py-3 rounded-2xl border border-input bg-card font-mono text-xs outline-none focus:ring-2 focus:ring-primary transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                      API Key / Token
                    </label>
                    <div className="relative flex items-center">
                      <input
                        type={showEditModelApiKey ? "text" : "password"}
                        placeholder={editingModel.api_key ? "Leave as is or enter new API key" : "Enter API key"}
                        value={editingModel.api_key}
                        onChange={(e) => setEditingModel((p) => ({ ...p, api_key: e.target.value }))}
                        className="w-full pl-4 pr-10 py-3 rounded-2xl border border-input bg-card font-mono text-xs focus:ring-2 focus:ring-primary outline-none transition-all"
                      />
                      <button
                        type="button"
                        onClick={() => setShowEditModelApiKey(!showEditModelApiKey)}
                        className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors p-1"
                        title={showEditModelApiKey ? "Hide key" : "Show key"}
                      >
                        {showEditModelApiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Model Description
                </label>
                <input
                  type="text"
                  value={editingModel.description}
                  onChange={(e) => setEditingModel((p) => ({ ...p, description: e.target.value }))}
                  className="w-full px-4 py-3 rounded-2xl border border-input bg-card text-sm outline-none focus:ring-2 focus:ring-primary transition-all"
                />
              </div>

              <div className="flex items-center justify-between p-4 rounded-2xl border border-border/70 bg-muted/20 shadow-inner">
                <div className="space-y-0.5">
                  <label className="text-sm font-bold block">Requires User API Key (Paid Tier)</label>
                  <p className="text-xs text-muted-foreground">
                    Enable if this model requires a custom provider API key to activate and run.
                  </p>
                </div>
                <Switch
                  checked={editingModel.requires_key}
                  onCheckedChange={(v) => setEditingModel((p) => ({ ...p, requires_key: v }))}
                />
              </div>
            </div>
          )}

          <DialogFooter className="border-t border-border/50 pt-4 gap-3">
            <Button
              variant="outline"
              className="rounded-xl px-6 py-2.5"
              onClick={() => setEditingModel(null)}
            >
              Cancel
            </Button>
            <Button
              className="rounded-xl px-7 py-2.5 shadow-md font-semibold"
              onClick={handleSaveEditModel}
              disabled={updateModelMutation.isPending}
            >
              {updateModelMutation.isPending && <Loader2 className="animate-spin mr-2" size={16} />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
