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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

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
        headers: { 'Content-Type': 'application/json' },
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
    <div className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm flex justify-center items-center p-6">
      <div className="bg-card text-foreground rounded-[32px] shadow-2xl w-full max-w-4xl overflow-hidden border border-border">
        <div className="border-b border-border p-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold">Create Agent</h2>
              <p className="text-muted-foreground mt-2">Configure your AI assistant.</p>
            </div>

            <button
              onClick={onClose}
              className="p-3 rounded-2xl hover:bg-muted transition-colors"
              disabled={createAgentMutation.isPending}
            >
              <X />
            </button>
          </div>

          <div className="mt-8 flex items-center">
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
        </div>

        <div className="p-8 min-h-[450px]">
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
                  "
                    placeholder="Describe what this agent does..."
                  />
                </div>

                <div>
                  <label className="font-medium block mb-2">Preferred Language</label>
                  <Select
                    value={formData.language}
                    onValueChange={(value) => updateField("language", value)}
                  >
                    <SelectTrigger className="w-full h-14 rounded-2xl bg-background border-border">
                      <SelectValue placeholder="Select Language" />
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
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="animate-message">
              <div className="flex items-center gap-3 mb-8">
                <Sparkles className="text-primary" />
                <h3 className="text-2xl font-bold">AI Model</h3>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                {providers.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => updateField("provider", provider.id)}
                    className={`
                    text-left
                    p-5
                    rounded-3xl
                    border
                    transition-all
                    hover:-translate-y-1 hover:shadow-md
                    bg-background
                    ${
                      formData.provider === provider.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                  `}
                  >
                    <h4 className="font-semibold">{provider.name}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{provider.desc}</p>
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4">
                {currentModels.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => updateField("model", model.id)}
                    className={`
                    p-4
                    rounded-2xl
                    border
                    text-left
                    transition-all
                    hover:-translate-y-1 hover:shadow-md
                    bg-background
                    ${
                      formData.model === model.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                  `}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="animate-message">
              <div className="flex items-center gap-3 mb-8">
                <Brain className="text-primary" />
                <h3 className="text-2xl font-bold">Knowledge</h3>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-8">
                {EMBEDDING_MODELS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => !item.disabled && updateField("embedding_model", item.id)}
                    disabled={item.disabled}
                    className={`
                    p-5
                    rounded-3xl
                    border
                    text-left
                    transition-all
                    ${!item.disabled ? "hover:-translate-y-1 hover:shadow-md" : ""}
                    bg-background
                    ${
                      item.disabled
                        ? "opacity-50 cursor-not-allowed border-border"
                        : formData.embedding_model === item.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                  `}
                  >
                    <h4 className="font-semibold">{item.name}</h4>
                    {item.disabled && (
                      <p className="text-xs text-orange-500 mt-1 font-medium">Coming Soon</p>
                    )}
                  </button>
                ))}
              </div>

              <Select
                value={formData.chunk_strategy}
                onValueChange={(value) => updateField("chunk_strategy", value)}
              >
                <SelectTrigger className="w-full h-14">
                  <SelectValue placeholder="Select Strategy" />
                </SelectTrigger>
                <SelectContent>
                  {CHUNKING_STRATEGIES.map((strategy) => (
                    <SelectItem key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <div className="mt-8 p-5 rounded-3xl border border-border bg-background flex items-center justify-between">
                <div>
                  <h4 className="font-semibold flex items-center gap-2">
                    <Globe size={18} className="text-primary" />
                    Web Search Fallback
                  </h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    Allow the agent to search the internet if the answer isn't in its documents.
                  </p>
                </div>
                <Switch 
                  checked={formData.web_search_enabled}
                  onCheckedChange={(checked) => updateField("web_search_enabled", checked)}
                />
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="animate-message">
              <div className="flex items-center gap-3 mb-8">
                <FileText className="text-primary" />
                <h3 className="text-2xl font-bold">Instructions</h3>
              </div>

              <textarea
                rows={10}
                value={formData.system_prompt}
                onChange={(event) =>
                  updateField("system_prompt", event.target.value)
                }
                placeholder="You are a helpful assistant..."
                className="
                w-full
                rounded-3xl
                border
                border-border
                bg-background
                text-foreground
                p-5
                mb-6
              "
              />

              <label className="font-medium block mb-2 mt-4 text-indigo-500 flex items-center gap-2">
                <Code size={16} /> Output Format Instructions
              </label>
              <textarea
                rows={4}
                value={formData.output_format}
                onChange={(event) =>
                  updateField("output_format", event.target.value)
                }
                placeholder="Always respond in valid JSON format..."
                className="
                w-full
                rounded-3xl
                border
                border-indigo-500/30
                bg-indigo-500/5
                text-foreground
                p-5
                mb-6
              "
              />

              {selectedModel?.requiresKey && (
                <div className="relative">
                  <Key
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
              )}
            </div>
          )}
        </div>

        {formError && (
          <div className="px-6 pb-4 text-sm text-red-600">
            {formError}
          </div>
        )}

        <div className="border-t border-border p-6 flex justify-between">
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
      </div>
    </div>
  );
}
