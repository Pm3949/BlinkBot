// client/src/components/Dashboard.jsx
import { useState } from 'react';
import { supabase } from '../supabaseClient';
import { Loader2, Plus, TerminalSquare, LogOut, Database, MessageSquare, ArrowLeft, MoreVertical, Trash2, Edit2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast'; // 🔥 NAYA IMPORT
import DocumentModal from './DocumentModal';
import Chat from './Chat';

export default function Dashboard({ session }) {
  const queryClient = useQueryClient();

  const [isCreatingAgent, setIsCreatingAgent] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState(null); 

  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [provider, setProvider] = useState('groq');
  const [model, setModel] = useState('llama-3.1-8b-instant');
  const [embedModel, setEmbedModel] = useState('all-MiniLM-L6-v2');
  const [chunkStrategy, setChunkStrategy] = useState('sentence');
  const [apiKey, setApiKey] = useState('');
  
  const [selectedAgentForDocs, setSelectedAgentForDocs] = useState(null);
  const [activeChatAgent, setActiveChatAgent] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  const AVAILABLE_MODELS = {
    groq: [
      { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B (Free - Fast)', requiresKey: false },
      { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B (Free - Smart)', requiresKey: false }
    ],
    openai: [
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini (Paid)', requiresKey: true },
      { id: 'gpt-4o', name: 'GPT-4o (Paid - Best)', requiresKey: true }
    ]
  };

  const EMBEDDING_MODELS = [
    { id: 'all-MiniLM-L6-v2', name: 'Sentence-Transformers MiniLM (Fast)' },
    { id: 'BAAI/bge-small-en-v1.5', name: 'BAAI BGE-Small (High Accuracy)' }
  ];

  const CHUNKING_STRATEGIES = [
    { id: 'naive', name: 'Sliding Window (Fixed Characters)' },
    { id: 'sentence', name: 'Sentence Window (Semantic / Accurate)' },
    { id: 'paragraph', name: 'Paragraph / Recursive (Contextual)' }
  ];

  const currentModelObj = AVAILABLE_MODELS[provider]?.find(m => m.id === model);
  const needsKey = currentModelObj ? currentModelObj.requiresKey : false;

  // Reset the agent form back to a clean default state.
  const setFormValuesClear = () => {
    setName('');
    setSystemPrompt('');
    setApiKey('');
    setProvider('groq');
    setModel('llama-3.1-8b-instant');
    setEmbedModel('all-MiniLM-L6-v2');
    setChunkStrategy('sentence');
    setIsCreatingAgent(false);
    setEditingAgentId(null);
  };

  const { data: agents = [], isLoading: loading } = useQuery({
    queryKey: ['agents', session.user.id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('agents')
        .select('*')
        .eq('user_id', session.user.id)
        .order('created_at', { ascending: false });
      
      if (error) throw new Error(error.message);
      return data || [];
    }
  });

  const createMutation = useMutation({
    mutationFn: async (newAgent) => {
      const { error } = await supabase.from('agents').insert([newAgent]);
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', session.user.id] });
      setFormValuesClear();
      toast.success('Agent deployed successfully! 🚀'); // 🔥 TOAST
    },
    onError: (error) => {
      toast.error('Failed to create agent: ' + error.message); // 🔥 TOAST
    }
  });

  const editMutation = useMutation({
    mutationFn: async (updatedAgent) => {
      const { error } = await supabase
        .from('agents')
        .update(updatedAgent)
        .eq('id', editingAgentId);
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', session.user.id] });
      setFormValuesClear();
      toast.success('Agent settings updated! ⚙️'); // 🔥 TOAST
    },
    onError: (error) => {
      toast.error('Update failed: ' + error.message); // 🔥 TOAST
    }
  });

  const handleFormSubmit = (e) => {
    e.preventDefault();

    if (!name.trim() || !systemPrompt.trim()) {
      toast.error("Agent name and system prompt are required.");
      return;
    }

    const agentPayload = {
      name,
      system_prompt: systemPrompt,
      llm_provider: provider,
      llm_model: model,
      embedding_model: embedModel,
      chunking_strategy: chunkStrategy,
      api_key: needsKey ? (apiKey.trim() || null) : null
    };

    if (editingAgentId) {
      editMutation.mutate(agentPayload);
    } else {
      createMutation.mutate({
        user_id: session.user.id,
        embedding_provider: 'local',
        ...agentPayload
      });
    }
  };

  const deleteMutation = useMutation({
    mutationFn: async (agentId) => {
      const res = await fetch(`http://localhost:8000/agents/${agentId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete agent on backend');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', session.user.id] });
      toast.success('Agent deleted permanently! 🗑️'); // 🔥 TOAST
    },
    onError: (error) => {
      toast.error('Failed to delete: ' + error.message); // 🔥 TOAST
    }
  });

  // Permanently delete an agent after explicit confirmation.
  const handleDeleteAgent = (agentId) => {
    const isConfirmed = window.confirm("Are you sure you want to delete this agent?\n\nThis will permanently remove the agent, its memory, and all uploaded documents.");
    if (isConfirmed) {
      deleteMutation.mutate(agentId);
    }
  };

  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
      toast.success('Signed out successfully 👋');
    } catch (error) {
      toast.error(error.message || 'Sign out failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans" onClick={() => setOpenMenuId(null)}>
      {activeChatAgent ? (
        <Chat agent={activeChatAgent} onBack={() => setActiveChatAgent(null)} />
      ) : (
        <>
          <nav className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">R</div>
                  <span className="font-semibold text-lg tracking-tight">RagMate</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500 hidden sm:block">{session.user.email}</span>
                  <button 
                    onClick={handleSignOut}
                    className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors px-3 py-2 rounded-md hover:bg-gray-50"
                  >
                    <LogOut size={16} /> Sign out
                  </button>
                </div>
              </div>
            </div>
          </nav>

          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {isCreatingAgent ? (
              <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
                <button 
                  className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors mb-6"
                  onClick={setFormValuesClear}
                >
                  <ArrowLeft size={16} /> Back to Dashboard
                </button>
                
                <h2 className="text-xl font-bold text-gray-900 mb-6">{editingAgentId ? 'Edit Agent Settings' : 'Create New Agent'}</h2>
                
                <form onSubmit={handleFormSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Agent Name</label>
                    <input 
                      className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border transition-all" 
                      type="text" 
                      value={name} 
                      onChange={(e) => setName(e.target.value)} 
                      placeholder="e.g. Customer Support Bot" 
                      required 
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1.5">Chat Provider</label>
                      <select 
                        className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border bg-white transition-all" 
                        value={provider} 
                        onChange={(e) => { setProvider(e.target.value); setModel(AVAILABLE_MODELS[e.target.value][0].id); }}
                      >
                        <option value="groq">Groq (Inference Engine)</option>
                        <option value="openai">OpenAI (GPT Engine)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1.5">Model Architecture</label>
                      <select 
                        className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border bg-white transition-all" 
                        value={model} 
                        onChange={(e) => setModel(e.target.value)}
                      >
                        {AVAILABLE_MODELS[provider].map(m => (
                          <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1.5">Embedding Architecture</label>
                      <select 
                        className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border bg-white transition-all" 
                        value={embedModel} 
                        onChange={(e) => setEmbedModel(e.target.value)}
                        disabled={!!editingAgentId}
                      >
                        {EMBEDDING_MODELS.map(m => (
                          <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1.5">Chunking Strategy</label>
                      <select 
                        className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border bg-white transition-all" 
                        value={chunkStrategy} 
                        onChange={(e) => setChunkStrategy(e.target.value)}
                        disabled={!!editingAgentId}
                      >
                        {CHUNKING_STRATEGIES.map(s => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between mb-1.5">
                      <label className="block text-sm font-semibold text-gray-700">API Key</label>
                      <span className={`text-xs ${needsKey ? 'text-rose-600 font-bold tracking-wide uppercase' : 'text-emerald-600 font-bold tracking-wide uppercase'}`}>
                        {needsKey ? 'Required' : 'Platform Managed'}
                      </span>
                    </div>
                    <input 
                      className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border disabled:bg-gray-50 disabled:text-gray-400 transition-all" 
                      type="password" 
                      value={apiKey} 
                      onChange={(e) => setApiKey(e.target.value)} 
                      placeholder={needsKey ? "sk-..." : "Leave blank to use free models"} 
                      required={needsKey} 
                      disabled={!needsKey} 
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">System Instructions</label>
                    <textarea 
                      className="w-full rounded-xl border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 sm:text-sm p-3 border min-h-[120px] transition-all" 
                      value={systemPrompt} 
                      onChange={(e) => setSystemPrompt(e.target.value)} 
                      placeholder="You are a helpful assistant..." 
                      required 
                    />
                  </div>
                  
                  <button 
                    type="submit" 
                    disabled={createMutation.isPending || editMutation.isPending} 
                    className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl text-base font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 transition-all shadow-md hover:shadow-lg mt-6"
                  >
                    {(createMutation.isPending || editMutation.isPending) ? <><Loader2 size={18} className="animate-spin" /> Saving...</> : <>{editingAgentId ? <Edit2 size={18} /> : <Plus size={18} />} {editingAgentId ? 'Save Settings' : 'Initialize Agent'}</>}
                  </button>
                </form>
              </div>
            ) : (
              <div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">Your AI Agents</h1>
                    <p className="text-sm text-gray-500 mt-1">Manage and train your custom RAG pipelines</p>
                  </div>
                  <button 
                    onClick={() => { setFormValuesClear(); setIsCreatingAgent(true); }}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 shadow-md hover:shadow-lg transition-all"
                  >
                    <Plus size={18} /> Deploy New Agent
                  </button>
                </div>
                
                {loading ? (
                  <div className="py-20 flex flex-col items-center justify-center">
                    <Loader2 size={40} className="animate-spin text-indigo-600 mb-4" />
                    <p className="text-sm font-medium text-gray-500">Loading your infrastructure...</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {agents.length === 0 ? (
                      <div className="col-span-full py-16 text-center border-2 border-dashed border-gray-300 rounded-2xl bg-white shadow-sm">
                        <TerminalSquare className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                        <h3 className="text-lg font-semibold text-gray-900">No active agents</h3>
                        <p className="mt-1 text-sm text-gray-500 mb-6">Initialize your first RAG agent to get started.</p>
                        <button
                          onClick={() => { setFormValuesClear(); setIsCreatingAgent(true); }}
                          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-indigo-600 bg-indigo-50 rounded-xl hover:bg-indigo-100 transition-colors"
                        >
                          <Plus size={18} /> Create First Agent
                        </button>
                      </div>
                    ) : (
                      agents.map((agent) => (
                        <div key={agent.id} className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-lg transition-all flex flex-col group relative">
                          
                          {deleteMutation.isPending && deleteMutation.variables === agent.id && (
                            <div className="absolute top-0 left-0 right-0 h-1 bg-red-500 animate-pulse z-10" />
                          )}

                          <div className="p-6 flex-1">
                            <div className="flex justify-between items-start mb-5">
                              <div className="flex items-center gap-4">
                                <div className="p-2.5 bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl text-indigo-600 border border-indigo-100 shadow-sm group-hover:scale-105 transition-transform">
                                  <TerminalSquare size={24} />
                                </div>
                                <div className="min-w-0">
                                  <h3 className="font-bold text-gray-900 truncate text-lg">{agent.name}</h3>
                                  
                                  <div className="flex flex-wrap gap-1.5 mt-2">
                                    <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-100 uppercase tracking-wider truncate max-w-[100px]" title={agent.llm_model}>
                                      {agent.llm_model.replace('llama-', 'L-').replace('gpt-', 'G-')}
                                    </span>
                                    <span className="text-[10px] font-bold bg-gray-50 text-gray-600 px-1.5 py-0.5 rounded border border-gray-200 uppercase tracking-wider">
                                      {agent.embedding_model?.includes('MiniLM') ? 'MINILM' : 'BGE'}
                                    </span>
                                    <span className="text-[10px] font-bold bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-100 uppercase tracking-wider">
                                      {agent.chunking_strategy || 'SENT'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                              
                              <div className="relative shrink-0 ml-2">
                                <button 
                                  className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                                  onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === agent.id ? null : agent.id); }}
                                >
                                  <MoreVertical size={18} />
                                </button>
                                {openMenuId === agent.id && (
                                  <div className="absolute right-0 mt-1 w-40 bg-white rounded-xl shadow-xl border border-gray-100 py-1.5 z-20 overflow-hidden">
                                    <button 
                                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors text-left"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setOpenMenuId(null);
                                        setEditingAgentId(agent.id);
                                        setName(agent.name);
                                        setSystemPrompt(agent.system_prompt);
                                        setProvider(agent.llm_provider);
                                        setModel(agent.llm_model);
                                        setEmbedModel(agent.embedding_model || 'all-MiniLM-L6-v2');
                                        setChunkStrategy(agent.chunking_strategy || 'sentence');
                                        setApiKey(agent.api_key || '');
                                        setIsCreatingAgent(true);
                                      }}
                                    >
                                      <Edit2 size={16} /> Edit Settings
                                    </button>
                                    <button 
                                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold text-rose-600 hover:bg-rose-50 transition-colors text-left"
                                      onClick={(e) => { e.stopPropagation(); setOpenMenuId(null); handleDeleteAgent(agent.id); }}
                                    >
                                      <Trash2 size={16} /> Delete Agent
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            <p className="text-sm text-gray-600 line-clamp-3 mb-2 bg-gray-50 p-3 rounded-lg border border-gray-100 font-mono text-[12px]">{agent.system_prompt}</p>
                          </div>
                          
                          <div className="border-t border-gray-100 p-4 flex gap-3 bg-white">
                            <button 
                              className="flex-1 flex justify-center items-center gap-2 px-3 py-2.5 bg-white border border-gray-300 shadow-sm text-sm font-semibold text-gray-700 rounded-xl hover:bg-gray-50 transition-all hover:border-gray-400"
                              onClick={() => setSelectedAgentForDocs(agent)}
                            >
                              <Database size={16} className="text-gray-500" /> Train
                            </button>
                            <button 
                              className="flex-1 flex justify-center items-center gap-2 px-3 py-2.5 bg-indigo-600 text-sm font-semibold text-white rounded-xl hover:bg-indigo-700 shadow-md hover:shadow-lg transition-all"
                              onClick={() => setActiveChatAgent(agent)}
                            >
                              <MessageSquare size={16} /> Chat
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
          </main>
        </>
      )}

      {selectedAgentForDocs && (
        <DocumentModal agent={selectedAgentForDocs} onClose={() => setSelectedAgentForDocs(null)} />
      )}
    </div>
  );
}
