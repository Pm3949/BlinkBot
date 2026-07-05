import React, { useState, useMemo } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "../ui/sheet";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Globe, Loader2, Bot, Brain, Key, FileText, Sparkles, Code, Network, Plus, Trash2, Settings2 } from "lucide-react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useProjectTools } from "../../hooks/useAgents";
import { toast } from "sonner";
import { getAuthHeaders } from "../../lib/api";
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

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

export default function AgentSettingsModal({ agent, onClose }) {
  const queryClient = useQueryClient();
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
      output_format: formData.output_format.trim(),
      api_key: selectedModel?.requiresKey ? formData.api_key.trim() : null,
      language: formData.language,
      web_search_enabled: formData.web_search_enabled,
      endpoints: formData.endpoints,
    };

    updateAgentMutation.mutate(payload);
  };

  return (
    <Sheet open={!!agent} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="p-0 flex flex-col sm:max-w-xl md:max-w-2xl lg:max-w-4xl bg-background border-l border-border/50 shadow-2xl">
        <SheetHeader className="p-6 border-b border-border/50 bg-muted/10">
          <SheetTitle className="text-xl flex items-center gap-2">
            <Settings2 className="text-primary" size={24} />
            Agent Settings: {agent.name}
          </SheetTitle>
          <SheetDescription>
            Modify your agent's identity, behavior, models, and external API capabilities.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-1 overflow-hidden min-h-[500px]">
          {/* Sidebar */}
          <div className="w-1/3 border-r border-border/50 bg-muted/10 p-4 space-y-1 overflow-y-auto">
            {[
              { id: "identity", label: "Identity", icon: Bot },
              { id: "behavior", label: "Behavior", icon: Brain },
              { id: "model", label: "Model & AI", icon: Sparkles },
              { id: "endpoints", label: "API Endpoints", icon: Network },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium ${
                  activeTab === tab.id
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
          <div className="flex-1 overflow-y-auto bg-card">
            <div className="p-8 max-w-2xl">
              
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
                    <h3 className="text-2xl font-bold">AI Model</h3>
                    <p className="text-muted-foreground text-sm mt-1">Select the intelligence powering this agent.</p>
                  </div>
                  <div className="space-y-5 bg-card p-6 rounded-2xl border border-border shadow-sm">
                    <div>
                      <label className="block text-sm font-semibold mb-2">Provider</label>
                      <div className="grid grid-cols-3 gap-3">
                        {providers.map((p) => (
                          <button
                            key={p.id}
                            onClick={() => updateField("provider", p.id)}
                            className={`p-4 rounded-xl border text-center transition-all ${
                              formData.provider === p.id ? "border-primary bg-primary/10 shadow-sm" : "border-border hover:border-primary/40 bg-background"
                            }`}
                          >
                            <h4 className={`font-semibold text-sm ${formData.provider === p.id ? "text-primary" : "text-foreground"}`}>{p.name}</h4>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold mb-1.5">Specific Model</label>
                      <Select value={formData.model} onValueChange={(val) => updateField("model", val)}>
                        <SelectTrigger className="w-full rounded-xl py-5">
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
                      <div className="pt-2">
                        <label className="text-sm font-semibold mb-1.5 flex items-center gap-2 text-orange-500">
                          <Key size={14} /> Custom API Key Required
                        </label>
                        <input 
                          type="password"
                          value={formData.api_key || ""}
                          onChange={(e) => updateField("api_key", e.target.value)}
                          placeholder="Enter your API Key"
                          className="w-full bg-background border border-orange-500/30 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-orange-500/20 transition-all outline-none"
                        />
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border mt-2">
                      <div>
                        <label className="block text-sm font-semibold mb-1.5 flex items-center gap-2">
                          <FileText size={16} className="text-muted-foreground" />
                          Embedding Model
                        </label>
                        <Select value={formData.embedding_model} onValueChange={(val) => updateField("embedding_model", val)}>
                          <SelectTrigger className="w-full rounded-xl py-5">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {EMBEDDING_MODELS.map((em) => (
                              <SelectItem key={em.id} value={em.id} disabled={em.disabled}>{em.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
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
                        rows={8}
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
                        rows={6}
                        className="w-full font-mono text-sm bg-indigo-500/5 border border-indigo-500/20 rounded-xl px-4 py-3 resize-y focus:ring-2 focus:ring-indigo-500/20 transition-all outline-none"
                      />
                    </div>
                    <div className="pt-4 border-t border-border mt-2 flex items-center justify-between">
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
                          { connection_id: "", name: "New Endpoint", path: "", method: "GET", description: "", payload_format: "" }
                        ]);
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
                    <div className="space-y-6">
                      {formData.endpoints.map((ep, idx) => (
                        <div key={idx} className="bg-card p-5 rounded-2xl border border-border shadow-sm relative">
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="absolute top-4 right-4 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                            onClick={() => {
                              const newEps = [...formData.endpoints];
                              newEps.splice(idx, 1);
                              updateField("endpoints", newEps);
                            }}
                          >
                            <Trash2 size={16} />
                          </Button>
                          <div className="grid grid-cols-2 gap-4 mr-10 mb-4">
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
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-border/50 bg-muted/10 flex justify-end gap-3">
          <Button variant="outline" className="rounded-xl px-6" onClick={onClose}>
            Cancel
          </Button>
          <Button className="rounded-xl px-8 shadow-md" onClick={handleSave} disabled={updateAgentMutation.isPending}>
            {updateAgentMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
