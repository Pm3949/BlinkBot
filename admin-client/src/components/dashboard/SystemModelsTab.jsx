import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';

export default function SystemModelsTab({ currentUser, requirePassword, API_URL }) {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState(null);

  // Form states
  const [modelId, setModelId] = useState("");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("openai");
  const [category, setCategory] = useState("chat");
  const [badge, setBadge] = useState("");
  const [inputCost, setInputCost] = useState(0.0);
  const [outputCost, setOutputCost] = useState(0.0);
  const [creditsPer1k, setCreditsPer1k] = useState(0.0);
  const [requiresKey, setRequiresKey] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [isActive, setIsActive] = useState(true);

  const { data: modelsData, isLoading, refetch } = useQuery({
    queryKey: ['adminModels'],
    queryFn: async () => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/all`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load models");
      return res.json();
    },
    enabled: !!currentUser
  });

  const createModelMutation = useMutation({
    mutationFn: async (newModel) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(newModel)
      });
      if (!res.ok) throw new Error("Failed to create model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model created successfully!");
      setModalOpen(false);
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const updateModelMutation = useMutation({
    mutationFn: async ({ id, updateData }) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(updateData)
      });
      if (!res.ok) throw new Error("Failed to update model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model updated successfully!");
      setModalOpen(false);
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const deleteModelMutation = useMutation({
    mutationFn: async (id) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/${id}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to delete model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model deleted successfully!");
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const openAddModal = () => {
    setEditingModel(null);
    setModelId("");
    setName("");
    setProvider("openai");
    setCategory("chat");
    setBadge("");
    setInputCost(0.0);
    setOutputCost(0.0);
    setCreditsPer1k(0.0);
    setRequiresKey(false);
    setBaseUrl("");
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditModal = (model) => {
    setEditingModel(model);
    setModelId(model.model_id || model.id || "");
    setName(model.name || "");
    setProvider(model.provider || "openai");
    setCategory(model.category || "chat");
    setBadge(model.badge || "");
    setInputCost(model.input_cost_per_1m || 0.0);
    setOutputCost(model.output_cost_per_1m || 0.0);
    setCreditsPer1k(model.credits_per_1k_tokens || 0.0);
    setRequiresKey(model.requires_key || false);
    setBaseUrl(model.base_url || "");
    setIsActive(model.is_active !== false);
    setModalOpen(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      provider,
      model_id: modelId,
      name,
      category,
      badge,
      input_cost_per_1m: parseFloat(inputCost),
      output_cost_per_1m: parseFloat(outputCost),
      credits_per_1k_tokens: parseFloat(creditsPer1k),
      requires_key: false,
      base_url: baseUrl,
      is_active: isActive,
      is_system: true
    };

    if (editingModel) {
      updateModelMutation.mutate({ id: editingModel.id, updateData: payload });
    } else {
      createModelMutation.mutate(payload);
    }
  };

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">System AI Models</h2>
        <button
          onClick={openAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white text-xs font-semibold rounded-lg transition"
        >
          <Plus size={14} /> Add Model
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-6 py-4">Model Details</th>
              <th className="px-6 py-4">Provider</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Badge / Category</th>
              <th className="px-6 py-4">Input / Output Cost</th>
              <th className="px-6 py-4">Credits / 1k tokens</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {isLoading && (
              <tr>
                <td colSpan={7} className="p-6">
                  <div className="animate-pulse bg-slate-100 dark:bg-slate-800 h-12 w-full rounded-md"></div>
                </td>
              </tr>
            )}
            {!isLoading && (!modelsData?.models || modelsData.models.length === 0) && (
              <tr>
                <td colSpan={7} className="p-12 text-center text-slate-400 dark:text-slate-500 font-medium text-sm">
                  No system AI models configured.
                </td>
              </tr>
            )}
            {modelsData?.models?.map((m) => (
              <tr key={m.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4">
                  <div className="font-semibold text-slate-900 dark:text-slate-100">{m.name}</div>
                  <div className="text-xs text-slate-400 dark:text-slate-500 font-mono">{m.model_id || m.id}</div>
                </td>
                <td className="px-6 py-4 font-semibold capitalize text-slate-600 dark:text-slate-300">
                  {m.provider}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                    m.is_active 
                      ? 'bg-green-50 dark:bg-green-950/40 text-green-600 dark:text-green-400 border-green-100 dark:border-green-900/60' 
                      : 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border-red-100 dark:border-red-900/60'
                  }`}>
                    {m.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-1.5 flex-wrap">
                    <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-xs text-slate-500 dark:text-slate-400 font-bold uppercase">{m.category || "chat"}</span>
                    {m.badge && <span className="bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded text-xs font-bold uppercase">{m.badge}</span>}
                  </div>
                </td>
                <td className="px-6 py-4 text-xs font-mono text-slate-500 dark:text-slate-400">
                  <div>In: ${m.input_cost_per_1m?.toFixed(2) || "0.00"}/1M</div>
                  <div>Out: ${m.output_cost_per_1m?.toFixed(2) || "0.00"}/1M</div>
                </td>
                <td className="px-6 py-4 font-mono font-bold text-slate-800 dark:text-slate-200">
                  {m.credits_per_1k_tokens || "0.0000"}
                </td>
                <td className="px-6 py-4 flex items-center gap-2">
                  <button
                    onClick={() => openEditModal(m)}
                    className="p-1.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-800 dark:hover:text-slate-100 rounded transition"
                    title="Edit Model"
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    onClick={() => requirePassword((pwd) => deleteModelMutation.mutate(m.id))}
                    className="p-1.5 bg-red-50 dark:bg-red-950/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-500 dark:text-red-400 rounded border border-transparent hover:border-red-100 dark:hover:border-red-950 transition"
                    title="Delete Model"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/80 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl w-full max-w-lg shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button 
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
            >
              <X size={20} />
            </button>
            <h3 className="text-lg font-bold mb-4 text-slate-900 dark:text-slate-50">{editingModel ? "Edit System Model" : "Add System Model"}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Model Name</label>
                  <input
                    type="text" required placeholder="GPT-4o (Premium)"
                    value={name} onChange={e => setName(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-950 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Model ID</label>
                  <input
                    type="text" required placeholder="gpt-4o"
                    value={modelId} onChange={e => setModelId(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-950 dark:text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Provider</label>
                  <select
                    value={provider} onChange={e => setProvider(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-750 dark:text-slate-200 font-semibold"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="groq">Groq</option>
                    <option value="gemini">Gemini</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="huggingface">HuggingFace</option>
                    <option value="custom_openai">Custom Endpoint</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Category</label>
                  <select
                    value={category} onChange={e => setCategory(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-750 dark:text-slate-200 font-semibold"
                  >
                    <option value="chat">Chat / LLM</option>
                    <option value="embedding">Embedding</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Badge</label>
                  <input
                    type="text" placeholder="PRO or FAST"
                    value={badge} onChange={e => setBadge(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-950 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Credits per 1k Tokens</label>
                  <input
                    type="number" step="0.0001" placeholder="0.015"
                    value={creditsPer1k} onChange={e => setCreditsPer1k(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-950 dark:text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Input Cost ($ / 1M tokens)</label>
                  <input
                    type="number" step="0.0001" placeholder="2.50"
                    value={inputCost} onChange={e => setInputCost(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-950 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Output Cost ($ / 1M tokens)</label>
                  <input
                    type="number" step="0.0001" placeholder="10.00"
                    value={outputCost} onChange={e => setOutputCost(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-950 dark:text-slate-100"
                  />
                </div>
              </div>

              {/* Profit Margin Estimator */}
              {(() => {
                const creds = parseFloat(creditsPer1k) || 0;
                const inCostUsd = parseFloat(inputCost) || 0;
                const outCostUsd = parseFloat(outputCost) || 0;
                const USD_TO_INR = 84; 
                const salePriceInrPer1M = creds * 100;
                const avgCostUsdPer1M = (inCostUsd + outCostUsd) / 2;
                const avgCostInrPer1M = avgCostUsdPer1M * USD_TO_INR;
                const profitInr = salePriceInrPer1M - avgCostInrPer1M;
                const marginPct = avgCostInrPer1M > 0 ? (profitInr / avgCostInrPer1M) * 100 : 0;
                
                return (
                  <div className="bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/60 rounded-xl p-3.5 space-y-2 text-xs">
                    <div className="font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider text-[10px]">
                      📊 Live Profit Estimator
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-500 dark:text-slate-400">
                      <div>User Price (Sale):</div>
                      <div className="text-right font-semibold text-slate-900 dark:text-slate-100">
                        ₹{salePriceInrPer1M.toFixed(2)} INR / 1M tokens
                      </div>
                      <div>Your Cost (Breakeven):</div>
                      <div className="text-right font-semibold text-slate-900 dark:text-slate-100">
                        ₹{avgCostInrPer1M.toFixed(2)} INR / 1M tokens (~${avgCostUsdPer1M.toFixed(2)})
                      </div>
                      <div className="border-t border-slate-200 dark:border-slate-800 mt-1 pt-1 font-bold text-slate-800 dark:text-slate-200">
                        Estimated Markup:
                      </div>
                      <div className={`border-t border-slate-200 dark:border-slate-800 mt-1 pt-1 text-right font-extrabold ${profitInr >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-400"}`}>
                        {profitInr >= 0 ? "+" : ""}₹{profitInr.toFixed(2)} INR ({marginPct.toFixed(0)}% markup)
                      </div>
                    </div>
                  </div>
                );
              })()}

              {provider === "custom_openai" && (
                <div>
                  <label className="block text-xs font-medium mb-1 text-slate-700 dark:text-slate-300">Custom Base URL</label>
                  <input
                    type="text" placeholder="https://api.together.xyz/v1"
                    value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-950 dark:text-slate-100"
                  />
                </div>
              )}

              <div className="flex gap-6 items-center pt-2">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={isActive} onChange={e => setIsActive(e.target.checked)}
                    className="rounded border-slate-350 text-indigo-600 focus:ring-indigo-500/50 dark:bg-slate-800 dark:border-slate-700"
                  />
                  Active in Selection
                </label>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-750 dark:text-slate-300 font-medium text-sm transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white font-medium text-sm transition"
                >
                  {editingModel ? "Update Model" : "Create Model"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
