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
} from "lucide-react";
import { Switch } from "../ui/switch";
import { toast } from "sonner";
import { useAuth } from "../../context/AuthContext";
import { useCreateAgent } from "../../hooks/useAgents";
import { useUIStore } from "../../store/useUIStore";
import { useWorkspacePermissions } from "../../hooks/useSettings";
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
  {
    id: "groq",
    name: "Groq",
    desc: "Free Models",
  },
  {
    id: "openai",
    name: "OpenAI",
    desc: "Premium Models",
  },
  {
    id: "ollama",
    name: "Local (Ollama)",
    desc: "Free Offline",
  },
];

export const AVAILABLE_MODELS = {
  groq: [
    {
      id: "llama-3.1-8b-instant",
      name: "Llama 3.1 8B (Free - Fast)",
      requiresKey: false,
    },
    {
      id: "llama-3.3-70b-versatile",
      name: "Llama 3.3 70B (Free - Smart)",
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
    model: "llama-3.1-8b-instant",
    embedding_model: "all-MiniLM-L6-v2",
    chunk_strategy: "sentence",
    system_prompt: "",
    output_format: "",
    api_key: "",
    language: "en",
    web_search_enabled: false,
  });

  const currentModels = useMemo(
    () => AVAILABLE_MODELS[formData.provider] || [],
    [formData.provider],
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
              AVAILABLE_MODELS[value]?.find(
                (availableModel) => availableModel.id,
              )?.id || prev.model,
          }
        : {}),
    }));
  };

  const nextStep = () => {
    if (step < 4) setStep(step + 1);
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
            {[1, 2, 3, 4].map((item) => (
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

                {item !== 4 && (
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
                    <div className="flex gap-2">
                      {providers.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => updateField("provider", p.id)}
                          className={`
                          flex-1 px-4 py-3 rounded-2xl border text-sm font-medium transition-all
                          ${
                            formData.provider === p.id
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border bg-background hover:bg-muted"
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
                    <label className="font-medium block mb-2">Model</label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {currentModels.map((m) => (
                        <button
                          key={m.id}
                          onClick={() => updateField("model", m.id)}
                          className={`
                          px-4 py-4 rounded-2xl border text-left transition-all
                          ${
                            formData.model === m.id
                              ? "border-primary bg-primary/5 ring-1 ring-primary"
                              : "border-border bg-background hover:bg-muted"
                          }
                        `}
                        >
                          <div className="font-medium">{m.name}</div>
                          {m.requiresKey && (
                            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                              <Key size={12} /> Requires API Key
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {selectedModel?.requiresKey && (
                    <div className="animate-in slide-in-from-top-2">
                      <label className="font-medium block mb-2">
                        Provider API Key
                      </label>
                      <div className="relative">
                        <Key
                          className="
                        absolute
                        left-4
                        top-1/2
                        -translate-y-1/2
                        text-muted-foreground
                      "
                        />

                        <input
                          type="password"
                          placeholder="API Key"
                          value={formData.api_key}
                          onChange={(event) =>
                            updateField("api_key", event.target.value)
                          }
                          className="
                        w-full
                        pl-12
                        py-4
                        rounded-2xl
                        border
                        border-border
                        bg-background
                        text-foreground
                      "
                        />
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

          {step !== 4 ? (
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
