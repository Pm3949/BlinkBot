import React, { useState, useMemo } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Globe, Loader2, Bot, Brain, Key, FileText, Sparkles } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  providers,
  AVAILABLE_MODELS,
  EMBEDDING_MODELS,
  CHUNKING_STRATEGIES,
  LANGUAGES
} from "./CreateAgentWizard";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function AgentSettingsModal({ agent, onClose }) {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    name: agent?.name || "",
    description: agent?.description || "",
    provider: agent?.llm_provider || "groq",
    model: agent?.llm_model || "llama-3.1-8b-instant",
    embedding_model: agent?.embedding_model || "all-MiniLM-L6-v2",
    chunk_strategy: agent?.chunk_strategy || "sentence",
    system_prompt: agent?.system_prompt || "",
    api_key: agent?.api_key || "",
    language: agent?.language || "en",
    web_search_enabled: agent?.web_search_enabled || false,
  });

  const currentModels = useMemo(
    () => AVAILABLE_MODELS[formData.provider] || [],
    [formData.provider]
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
              AVAILABLE_MODELS[value]?.find((availableModel) => availableModel.id)?.id || prev.model,
          }
        : {}),
    }));
  };

  const updateAgentMutation = useMutation({
    mutationFn: async (payload) => {
      const response = await fetch(`${API_URL}/api/agents/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('Failed to update agent');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["agents", agent.workspace_id]);
      toast.success("Agent settings updated");
      onClose();
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

    const payload = {
      name: formData.name.trim(),
      description: formData.description.trim(),
      llm_provider: formData.provider,
      llm_model: formData.model,
      embedding_model: formData.embedding_model,
      chunk_strategy: formData.chunk_strategy,
      system_prompt: formData.system_prompt.trim(),
      api_key: selectedModel?.requiresKey ? formData.api_key.trim() : null,
      language: formData.language,
      web_search_enabled: formData.web_search_enabled,
    };

    updateAgentMutation.mutate(payload);
  };

  return (
    <Dialog open={!!agent} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col p-0 overflow-hidden">
        <div className="p-6 pb-4 border-b border-border">
          <DialogHeader>
            <DialogTitle className="text-xl">Agent Settings: {agent?.name}</DialogTitle>
            <DialogDescription>
              Configure everything from identity to knowledge models.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-8 bg-muted/20">
          
          {/* Identity */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2"><Bot size={18} className="text-primary"/> Identity</h3>
            <div className="space-y-4 bg-card p-5 rounded-2xl border border-border">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input 
                  type="text"
                  value={formData.name}
                  onChange={(e) => updateField("name", e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-4 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input 
                  type="text"
                  value={formData.description}
                  onChange={(e) => updateField("description", e.target.value)}
                  className="w-full bg-background border border-border rounded-xl px-4 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Language</label>
                <Select value={formData.language} onValueChange={(val) => updateField("language", val)}>
                  <SelectTrigger className="w-full">
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

          {/* Model Selection */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2"><Sparkles size={18} className="text-primary"/> AI Model</h3>
            <div className="space-y-4 bg-card p-5 rounded-2xl border border-border">
              <div className="grid grid-cols-3 gap-3">
                {providers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => updateField("provider", p.id)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      formData.provider === p.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                    }`}
                  >
                    <h4 className="font-semibold text-sm">{p.name}</h4>
                  </button>
                ))}
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Model</label>
                <Select value={formData.model} onValueChange={(val) => updateField("model", val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {currentModels.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {selectedModel?.requiresKey && (
                <div>
                  <label className="block text-sm font-medium mb-1 flex items-center gap-2"><Key size={14} /> API Key</label>
                  <input 
                    type="password"
                    value={formData.api_key || ""}
                    onChange={(e) => updateField("api_key", e.target.value)}
                    placeholder="Enter API Key"
                    className="w-full bg-background border border-border rounded-xl px-4 py-2"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Knowledge & Fallbacks */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2"><Brain size={18} className="text-primary"/> Knowledge</h3>
            <div className="space-y-4 bg-card p-5 rounded-2xl border border-border">
              <div>
                <label className="block text-sm font-medium mb-1">Embedding Model</label>
                <Select value={formData.embedding_model} onValueChange={(val) => updateField("embedding_model", val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EMBEDDING_MODELS.map((m) => (
                      <SelectItem key={m.id} value={m.id} disabled={m.disabled}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Chunking Strategy</label>
                <Select value={formData.chunk_strategy} onValueChange={(val) => updateField("chunk_strategy", val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHUNKING_STRATEGIES.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="pt-4 border-t border-border mt-4 flex items-center justify-between">
                <div>
                  <h4 className="font-semibold flex items-center gap-2">
                    <Globe size={16} className="text-primary" />
                    Web Search Fallback
                  </h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    Allow the agent to search the internet if the answer isn't in documents.
                  </p>
                </div>
                <Switch 
                  checked={formData.web_search_enabled}
                  onCheckedChange={(val) => updateField("web_search_enabled", val)}
                />
              </div>
            </div>
          </div>

          {/* Prompt */}
          <div className="space-y-4">
            <h3 className="font-semibold text-lg flex items-center gap-2"><FileText size={18} className="text-primary"/> Behavior</h3>
            <div className="bg-card p-5 rounded-2xl border border-border">
              <label className="block text-sm font-medium mb-1">System Prompt</label>
              <textarea 
                value={formData.system_prompt}
                onChange={(e) => updateField("system_prompt", e.target.value)}
                placeholder="You are a helpful assistant..."
                rows={4}
                className="w-full bg-background border border-border rounded-xl px-4 py-3 resize-y"
              />
            </div>
          </div>

        </div>

        <div className="p-6 border-t border-border bg-card">
          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateAgentMutation.isPending}>
              {updateAgentMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save All Settings
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
