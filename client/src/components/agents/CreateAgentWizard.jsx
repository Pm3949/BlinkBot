import { useMemo, useState, useEffect } from "react";
import {
  X,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Bot,
  Brain,
  FileText,
  Key,
  Check,
  Loader2,
  ChevronDown,
  Globe,
  Code,
  Zap,
  Lock,
  CheckCircle2,
} from "lucide-react";
import { Switch } from "../ui/switch";
import { toast } from "sonner";
import { useAuth } from "../../context/AuthContext";
import { useCreateAgent } from "../../hooks/useAgents";
import { useUIStore } from "../../store/useUIStore";
import { useWorkspacePermissions, useUserSettings } from "../../hooks/useSettings";
import { useActiveModels, useAvailableModels } from "../../hooks/useModels";
import { getAuthHeaders } from "../../lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "../ui/sheet";

export const providers = [
  { id: "groq", name: "Groq" },
  { id: "openai", name: "OpenAI" },
  { id: "openrouter", name: "OpenRouter" },
  { id: "huggingface", name: "HuggingFace" },
  { id: "anthropic", name: "Anthropic" },
  { id: "gemini", name: "Gemini" },
];

export const AVAILABLE_MODELS = {
  groq: [
    {
      id: "mixtral-8x7b-32768",
      name: "Mixtral 8x7B (Large Context)",
      requiresKey: false,
    },
    {
      id: "qwen-2.5-32b",
      name: "Qwen 2.5 32B (Coding/Logic)",
      requiresKey: false,
    },
  ],

  gemini: [
    {
      id: "gemini-3-flash",
      name: "Gemini 3 Flash (Smart)",
      requiresKey: false,
    },
  ],

  openai: [
    {
      id: "gpt-4o-mini",
      name: "GPT-4o Mini (Paid)",
      requiresKey: true,
    },
    {
      id: "gpt-4o",
      name: "GPT-4o (Paid - Best)",
      requiresKey: true,
    },
  ],

  ollama: [
    {
      id: "llama3",
      name: "Llama 3 (Local)",
      requiresKey: false,
    },
    {
      id: "mistral",
      name: "Mistral (Local)",
      requiresKey: false,
    },
  ],
};

export const EMBEDDING_MODELS = [
  {
    id: "BAAI/bge-small-en-v1.5",
    name: "BAAI BGE-Small (High Accuracy)",
    disabled: false,
  },
  {
    id: "all-MiniLM-L6-v2",
    name: "Fast & Light (all-MiniLM-L6-v2)",
    disabled: false,
  },
  {
    id: "BAAI/bge-large-en-v1.5",
    name: "Pro Accuracy - Local (BAAI/bge-large-en-v1.5)",
    disabled: true,
  },
];

export const CHUNKING_STRATEGIES = [
  {
    id: "naive",
    name: "Sliding Window (Fixed Characters)",
  },
  {
    id: "sentence",
    name: "Sentence Window (Semantic / Accurate)",
  },
  {
    id: "paragraph",
    name: "Paragraph / Recursive (Contextual)",
  },
];

export const LANGUAGES = [
  { id: "en", name: "English" },
  { id: "es", name: "Spanish" },
  { id: "fr", name: "French" },
  { id: "de", name: "German" },
  { id: "hi", name: "Hindi" },
  { id: "zh-CN", name: "Chinese (Simplified)" },
  { id: "ja", name: "Japanese" },
  { id: "ko", name: "Korean" },
];

export default function CreateAgentWizard({ onClose, projectId = null, parentAgentId = null }) {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { canManageAgents } = useWorkspacePermissions();
  const createAgentMutation = useCreateAgent(activeWorkspaceId);

  // माउंट होने पर सुरक्षा जांच (उदा: शॉर्टकट से विज़ार्ड खुलने से रोकने के लिए)
  useEffect(() => {
    if (!canManageAgents) {
      toast.error("You do not have permission to manage agents in this workspace.");
      onClose();
    }
  }, [canManageAgents, onClose]);

  const [step, setStep] = useState(1);
  const [formError, setFormError] = useState("");
  const [autoPrompt, setAutoPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    provider: "groq",
    model: "qwen/qwen3.6-27b",
    embedding_model: "BAAI/bge-small-en-v1.5",
    chunk_strategy: "sentence",
    system_prompt: "",
    output_format: "",
    api_key: "",
    language: "en",
    web_search_enabled: false,
    code_interpreter_enabled: false,
  });

  const { data: activeModelsData } = useAvailableModels();
  const { data: userSettings } = useUserSettings();

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
    [formData.provider, dynamicModels],
  );

  const selectedModel =
    currentModels.find(
      (model) => model.id === formData.model,
    );

  const updateField = (key, value) => {
    setFormError("");

    setFormData((prev) => ({
      ...prev,
      [key]: value,
      ...(key === "provider"
        ? {
            model:
              (dynamicModels[value] || AVAILABLE_MODELS[value])?.find(
                (availableModel) => availableModel.id,
              )?.id || prev.model,
          }
        : {}),
    }));
  };

  const nextStep = () => {
    if (step < 5) setStep(step + 1);
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleAutoGenerate = async () => {
    if (!autoPrompt.trim()) return;
    setIsGenerating(true);
    setFormError("");
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/meta-agent/generate-single`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ prompt: autoPrompt })
      });
      if (!response.ok) throw new Error('Failed to generate agent config');
      const data = await response.json();
      setFormData(prev => ({
        ...prev,
        name: data.name || prev.name,
        description: data.description || prev.description,
        system_prompt: data.system_prompt || prev.system_prompt,
        output_format: data.output_format_instructions || prev.output_format
      }));
      toast.success("Agent configured with AI! Review the steps.");
    } catch (error) {
      toast.error("Failed to auto-generate agent");
      setFormError(error.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = async () => {
    if (!canManageAgents) {
      toast.error("You do not have permission to create agents in this workspace.");
      return;
    }

    if (!user?.id) {
      setFormError(
        "You must be signed in to create an agent.",
      );
      return;
    }

    if (!formData.name.trim()) {
      setFormError("Agent name is required.");
      setStep(1);
      return;
    }

    const payload = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      provider: formData.provider,
      model: formData.model,
      embedding_model: formData.embedding_model,
      chunk_strategy: formData.chunk_strategy,
      system_prompt: formData.system_prompt.trim(),
      output_format: formData.output_format.trim(),
      api_key: selectedModel?.requiresKey
        ? formData.api_key.trim()
        : null,
      language: formData.language,
      workspace_id: activeWorkspaceId,
      project_id: projectId,
      parent_agent_id: parentAgentId,
      web_search_enabled: formData.web_search_enabled,
      code_interpreter_enabled: formData.code_interpreter_enabled,
    };

    try {
      await createAgentMutation.mutateAsync(payload);
      toast.success("Agent created");
      onClose();
    } catch (error) {
      setFormError(
        error.message ||
          "Unable to create agent. Please try again.",
      );
      toast.error("Unable to create agent");
    }
  };

  return (
    <Sheet open={true} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="p-0 flex flex-col sm:max-w-xl md:max-w-2xl lg:max-w-4xl bg-background border-l border-border/50 shadow-2xl">
        <SheetHeader className="p-8 border-b border-border/50 bg-muted/10">
          <SheetTitle className="text-3xl font-bold">Create Agent</SheetTitle>
          <SheetDescription>Configure your AI assistant.</SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto flex flex-col p-8 bg-card">
          <div className="mb-8 flex items-center">
            {[1, 2, 3, 4, 5].map((item) => (
              <div
                key={item}
                className="flex items-center flex-1"
              >
                <div
                  className={`
                  h-10
                  w-10
                  rounded-full
                  flex
                  items-center
                  justify-center
                  text-sm
                  font-semibold
                  ${
                    step >= item
                      ? "bg-primary text-white"
                      : "bg-muted text-muted-foreground"
                  }
                `}
                >
                  {step > item ? <Check size={16} /> : item}
                </div>

                {item !== 5 && (
                  <div
                    className={`
                    flex-1
                    h-1
                    mx-2
                    rounded-full
                    ${
                      step > item
                        ? "bg-primary"
                        : "bg-border"
                    }
                  `}
                  />
                )}
              </div>
            ))}
          </div>

          <div className="flex-1 min-h-[450px]">
            {step === 1 && (
              <div className="animate-message">
                <div className="mb-8 p-6 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 rounded-3xl border border-purple-500/20">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="text-purple-600 dark:text-purple-400" size={20} />
                    <h4 className="font-bold text-purple-800 dark:text-purple-300">✨ Auto-Fill with AI</h4>
                  </div>
                  <div className="flex gap-3">
                    <input
                      value={autoPrompt}
                      onChange={(e) => setAutoPrompt(e.target.value)}
                      placeholder="Describe your agent (e.g., 'A helpful sales agent that outputs JSON...')"
                      className="flex-1 bg-background border border-purple-500/30 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500/50"
                      disabled={isGenerating}
                      onKeyDown={(e) => e.key === 'Enter' && handleAutoGenerate()}
                    />
                    <button
                      onClick={handleAutoGenerate}
                      disabled={isGenerating || !autoPrompt.trim()}
                      className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-xl transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {isGenerating ? <Loader2 size={18} className="animate-spin" /> : "Generate"}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-3 font-medium">Describe what you want, and we'll write the prompt, description, and formatting rules for you automatically.</p>
                </div>

                <div className="flex items-center gap-3 mb-8">
                  <Bot className="text-primary" />
                  <h3 className="text-2xl font-bold">Identity</h3>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="font-medium block mb-2">Agent Name</label>
                    <input
                      value={formData.name}
                      onChange={(event) =>
                        updateField("name", event.target.value)
                      }
                      className="
                      w-full
                      border
                      border-border
                      bg-background
                      text-foreground
                      rounded-2xl
                      px-4
                      py-4
                    "
                      placeholder="Customer Support AI"
                    />
                  </div>

                  <div>
                    <label className="font-medium block mb-2">Description</label>
                    <textarea
                      rows={3}
                      value={formData.description}
                      onChange={(event) =>
                        updateField("description", event.target.value)
                      }
                      className="
                      w-full
                      border
                      border-border
                      bg-background
                      text-foreground
                      rounded-2xl
                      px-4
                      py-4
                      resize-y
                    "
                      placeholder="What does this agent do?"
                    />
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="animate-message">
                <div className="flex items-center gap-3 mb-8">
                  <FileText className="text-primary" />
                  <h3 className="text-2xl font-bold">Behavior</h3>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="font-medium block mb-2">
                      System Prompt
                    </label>
                    <textarea
                      rows={6}
                      value={formData.system_prompt}
                      onChange={(event) =>
                        updateField("system_prompt", event.target.value)
                      }
                      className="
                      w-full
                      border
                      border-border
                      bg-background
                      text-foreground
                      rounded-2xl
                      px-4
                      py-4
                      font-mono
                      text-sm
                      resize-y
                    "
                      placeholder="You are a helpful assistant..."
                    />
                  </div>
                  <div>
                    <label className="font-medium block mb-2 flex items-center gap-2">
                      Output Format Instructions
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">Optional</span>
                    </label>
                    <textarea
                      rows={4}
                      value={formData.output_format}
                      onChange={(event) =>
                        updateField("output_format", event.target.value)
                      }
                      className="
                      w-full
                      border
                      border-border
                      bg-background
                      text-foreground
                      rounded-2xl
                      px-4
                      py-4
                      font-mono
                      text-sm
                      resize-y
                    "
                      placeholder="Provide constraints like 'Always respond in JSON format'"
                    />
                  </div>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="animate-message">
                <div className="flex items-center gap-3 mb-8">
                  <Brain className="text-primary" />
                  <h3 className="text-2xl font-bold">Knowledge Base</h3>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="font-medium block mb-2">
                      Embedding Model
                    </label>
                    <Select
                      value={formData.embedding_model}
                      onValueChange={(value) => updateField("embedding_model", value)}
                    >
                      <SelectTrigger className="w-full rounded-2xl py-6 bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {EMBEDDING_MODELS.map((model) => (
                          <SelectItem
                            key={model.id}
                            value={model.id}
                            disabled={model.disabled}
                          >
                            {model.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="font-medium block mb-2">
                      Chunking Strategy
                    </label>
                    <Select
                      value={formData.chunk_strategy}
                      onValueChange={(value) => updateField("chunk_strategy", value)}
                    >
                      <SelectTrigger className="w-full rounded-2xl py-6 bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CHUNKING_STRATEGIES.map((strategy) => (
                          <SelectItem
                            key={strategy.id}
                            value={strategy.id}
                          >
                            {strategy.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="mt-4 p-5 rounded-2xl border border-border bg-card flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold flex items-center gap-2"><Globe size={18} className="text-blue-500" /> Web Search Fallback</h4>
                      <p className="text-sm text-muted-foreground mt-1">Allow the agent to search the internet if the answer isn't in documents.</p>
                    </div>
                    <Switch
                      checked={formData.web_search_enabled}
                      onCheckedChange={(val) => updateField("web_search_enabled", val)}
                    />
                  </div>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="animate-message">
                <div className="flex items-center gap-3 mb-8">
                  <Zap className="text-primary" />
                  <h3 className="text-2xl font-bold">Capabilities & Tools</h3>
                </div>

                <div className="space-y-6">
                  <div className={`p-6 border rounded-2xl bg-card transition-all duration-300 ${formData.code_interpreter_enabled ? 'border-primary ring-1 ring-primary/20 shadow-md' : 'border-border opacity-75'}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex gap-4">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 text-blue-500 shrink-0">
                          <Code size={24} />
                        </div>
                        <div>
                          <h4 className="font-bold text-lg text-foreground">Python Code Sandbox (CSV Analyzer)</h4>
                          <p className="text-sm text-muted-foreground mt-1">Allow the agent to run Python scripts in a secure sandbox VM to analyze CSV data, compute math, and generate charts.</p>
                        </div>
                      </div>
                      <Switch
                        checked={formData.code_interpreter_enabled}
                        onCheckedChange={(val) => updateField("code_interpreter_enabled", val)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {step === 5 && (
              <div className="animate-message">
                <div className="flex items-center gap-3 mb-8">
                  <Code className="text-primary" />
                  <h3 className="text-2xl font-bold">Model Settings</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label className="font-medium block mb-2">Language</label>
                    <Select
                      value={formData.language}
                      onValueChange={(value) => updateField("language", value)}
                    >
                      <SelectTrigger className="w-full rounded-2xl py-6 bg-background">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LANGUAGES.map((lang) => (
                          <SelectItem key={lang.id} value={lang.id}>
                            {lang.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="font-medium block mb-2">Provider</label>
                    <div className="flex flex-wrap gap-2">
                      {dynamicProviders.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => updateField("provider", p.id)}
                          className={`
                          px-4 py-2.5 rounded-xl border text-xs font-semibold capitalize transition-all
                          ${
                            formData.provider === p.id
                              ? "border-primary bg-primary/10 text-primary shadow-sm"
                              : "border-border bg-background hover:bg-muted text-muted-foreground"
                          }
                        `}
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <label className="font-medium block">Model Selection</label>
                      {activeModelsData && (
                        <div className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                          Wallet Balance: ${(activeModelsData.credit_balance || 0).toFixed(2)} Credits
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
                            className={`p-4 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                              isSelected
                                ? "border-primary bg-primary/5 ring-1 ring-primary shadow-sm"
                                : isLocked
                                ? "border-border/40 bg-muted/20 opacity-60"
                                : "border-border hover:border-primary/50 bg-background"
                            }`}
                          >
                            <div>
                              <div className="flex items-center justify-between gap-2 mb-2">
                                <span className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${badgeStyle}`}>
                                  {badgeText}
                                </span>
                                {isLocked && (
                                  <span className="text-[10px] text-red-500 font-semibold flex items-center gap-1">
                                    <Lock size={10} /> Locked
                                  </span>
                                )}
                              </div>
                              <div className="font-semibold text-sm text-foreground">{m.name}</div>
                              <code className="text-[9px] text-muted-foreground font-mono block mt-0.5">{m.id}</code>
                            </div>
                            <div className="pt-2.5 border-t border-border/40 mt-3 flex flex-col gap-1 text-[10px]">
                              <div className="flex items-center justify-between relative group/price">
                                <div className="flex items-center gap-1">
                                  <span className="text-muted-foreground">Burn Rate:</span>
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
                                          {costFactor.toFixed(2)} cr / 1k
                                        </span>
                                        <div className="absolute bottom-full left-0 mb-2 hidden group-hover/price:block w-52 p-3 bg-zinc-950 border border-border/60 text-zinc-100 rounded-xl shadow-2xl z-50 text-[9px] leading-relaxed transition-all">
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
                              <div className="font-semibold text-primary/95 mt-0.5">
                                {runwayText}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {selectedModel?.requiresKey ? (
                    <div className="animate-in slide-in-from-top-2 p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="font-semibold text-sm flex items-center gap-2 text-amber-600 dark:text-amber-400">
                          <Key size={16} /> Provider API Key Required
                        </label>
                        <span className="text-[11px] text-muted-foreground">Optional override if configured in Models Page</span>
                      </div>
                      <div className="relative">
                        <Key
                          className="
                        absolute
                        left-4
                        top-1/2
                        -translate-y-1/2
                        text-muted-foreground
                      "
                          size={18}
                        />

                        <input
                          type="password"
                          placeholder="Leave blank to use default workspace key, or paste custom key..."
                          value={formData.api_key}
                          onChange={(event) =>
                            updateField("api_key", event.target.value)
                          }
                          className="
                        w-full
                        pl-12
                        pr-4
                        py-3
                        rounded-xl
                        border
                        border-input
                        bg-background
                        text-foreground
                        font-mono
                        text-xs
                      "
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 flex items-center gap-3">
                      <Zap className="text-emerald-500 shrink-0" size={20} />
                      <div>
                        <h4 className="font-semibold text-xs text-emerald-500">Free Model Selected</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          This model runs on platform infrastructure or free tiers. No API key is required from you!
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {formError && (
          <div className="px-8 pb-4 text-sm text-red-600 bg-card">
            {formError}
          </div>
        )}

        <div className="border-t border-border p-6 bg-card flex justify-between">
          <button
            onClick={prevStep}
            disabled={step === 1 || createAgentMutation.isPending}
            className="
            flex
            items-center
            gap-2
            px-5
            py-3
            rounded-2xl
            border
            border-border
            hover:bg-muted
            disabled:opacity-50
          "
          >
            <ChevronLeft size={16} />
            Back
          </button>

          {step !== 5 ? (
            <button
              onClick={nextStep}
              disabled={createAgentMutation.isPending}
              className="
              flex
              items-center
              gap-2
              px-5
              py-3
              rounded-2xl
              btn-primary
              disabled:opacity-70
            "
            >
              Continue
              <ChevronRight size={16} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={createAgentMutation.isPending}
              className="
              flex
              items-center
              gap-2
              px-6
              py-3
              rounded-2xl
              btn-primary
              font-medium
              disabled:opacity-70
            "
            >
              {createAgentMutation.isPending && (
                <Loader2 size={16} className="animate-spin" />
              )}
              {createAgentMutation.isPending
                ? "Creating..."
                : "Create Agent"}
            </button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
