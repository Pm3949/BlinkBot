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
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../context/AuthContext";
import { useCreateAgent } from "../../hooks/useAgents";
import { useUIStore } from "../../store/useUIStore";
import { useWorkspacePermissions } from "../../hooks/useSettings";

const providers = [
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
];

const AVAILABLE_MODELS = {
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
};

const EMBEDDING_MODELS = [
  {
    id: "all-MiniLM-L6-v2",
    name: "Sentence-Transformers MiniLM (Fast)",
  },
  {
    id: "BAAI/bge-small-en-v1.5",
    name: "BAAI BGE-Small (High Accuracy)",
  },
];

const CHUNKING_STRATEGIES = [
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

export default function CreateAgentWizard({ onClose }) {
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

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    provider: "groq",
    model: "llama-3.1-8b-instant",
    embedding_model: "all-MiniLM-L6-v2",
    chunk_strategy: "sentence",
    system_prompt: "",
    api_key: "",
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
      api_key: selectedModel?.requiresKey
        ? formData.api_key.trim()
        : null,
      workspace_id: activeWorkspaceId,
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
            <div>
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
                    rows={5}
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
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
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
                    ${
                      formData.provider === provider.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                    bg-background
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
                    ${
                      formData.model === model.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                    bg-background
                  `}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <div className="flex items-center gap-3 mb-8">
                <Brain className="text-primary" />
                <h3 className="text-2xl font-bold">Knowledge</h3>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-8">
                {EMBEDDING_MODELS.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => updateField("embedding_model", item.id)}
                    className={`
                    p-5
                    rounded-3xl
                    border
                    text-left
                    ${
                      formData.embedding_model === item.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/50"
                    }
                    bg-background
                  `}
                  >
                    <h4 className="font-semibold">{item.name}</h4>
                    <p className="text-sm text-muted-foreground mt-1"></p>
                  </button>
                ))}
              </div>

              <select
                value={formData.chunk_strategy}
                onChange={(event) =>
                  updateField("chunk_strategy", event.target.value)
                }
                className="
                w-full
                border
                border-border
                bg-background
                text-foreground
                rounded-2xl
                p-4
              "
              >
                {CHUNKING_STRATEGIES.map((strategy) => (
                  <option
                    key={strategy.id}
                    value={strategy.id}
                  >
                    {strategy.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {step === 4 && (
            <div>
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
