import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Network, FileText, Key, CheckCircle2, Bot, Settings, Loader2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import AgentSettingsModal from '../agents/AgentSettingsModal';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../lib/api';

export default function BlueprintConfigurator({ blueprint, deployData, onFinish }) {
  const { register, handleSubmit, watch } = useForm();
  const [editingAgent, setEditingAgent] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState({});

  const onSubmit = async (data) => {
    // Save all tool configurations
    if (data.tools && deployData.tool_id_map) {
      const promises = Object.keys(data.tools).map(blueprintToolId => {
        const dbToolId = deployData.tool_id_map[blueprintToolId];
        const toolDetails = getToolDetails(blueprintToolId);
        if (dbToolId && toolDetails) {
          const config = data.tools[blueprintToolId];
          config.is_enabled = data.enabled_tools?.[blueprintToolId] !== false;
          return fetch(`${import.meta.env.VITE_API_BASE_URL}/api/tools/${dbToolId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: toolDetails.name, config })
          });
        }
        return Promise.resolve();
      });
      await Promise.all(promises);
    }
    onFinish();
  };

  const handleFileUpload = async (e, agentId) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingFiles(prev => ({ ...prev, [agentId]: true }));
    const formData = new FormData();
    formData.append('file', file);
    formData.append('agent_id', agentId);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/process-file`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('Failed to upload file');
      toast.success(`${file.name} uploaded successfully! Processing in background.`);
    } catch (error) {
      console.error(error);
      toast.error('File upload failed.');
    } finally {
      setUploadingFiles(prev => ({ ...prev, [agentId]: false }));
      e.target.value = ''; // Reset input
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  const getKnowledgeDetails = (kbId) => blueprint.required_knowledge?.find(k => k.id === kbId);
  const getToolDetails = (toolId) => blueprint.required_tools?.find(t => t.id === toolId);

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="max-w-5xl mx-auto py-12">
      <div className="mb-10 text-center">
        <h2 className="text-4xl font-bold text-foreground mb-3">{blueprint.project_name}</h2>
        <p className="text-xl text-muted-foreground">{blueprint.description}</p>
        <div className="mt-4 inline-flex items-center px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
          <Network className="w-4 h-4 mr-2" />
          {blueprint.network_architecture.replace(/_/g, ' ').toUpperCase()}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        
        {blueprint.sub_agents && blueprint.sub_agents.map((agent, index) => {
          const dbAgentId = deployData?.agent_id_map?.[agent.id];
          return (
            <motion.div key={agent.id} variants={itemVariants} className="bg-card rounded-2xl shadow-sm border border-border overflow-hidden">
              
              <div className="bg-muted/30 p-6 border-b border-border flex items-start gap-4">
                <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="text-primary w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-2xl font-semibold text-foreground flex items-center gap-3">
                        {agent.role}
                        <span className="text-xs font-bold px-2 py-1 bg-muted rounded-full text-muted-foreground uppercase tracking-wider">Agent {index + 1}</span>
                      </h3>
                      <p className="text-muted-foreground mt-1 text-sm">{agent.goal}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEditingAgent({
                        id: dbAgentId,
                        name: agent.role,
                        description: agent.goal,
                        system_prompt: agent.backstory,
                        llm_provider: 'google',
                        llm_model: 'gemini-2.5-flash',
                        workspace_id: deployData.workspace_id
                      })}
                      className="p-2 bg-background border border-border hover:bg-muted text-foreground rounded-lg transition flex items-center gap-2 text-sm font-medium"
                    >
                      <Settings className="w-4 h-4" /> Settings
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-6 space-y-8">
                {agent.assigned_knowledge && agent.assigned_knowledge.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4 flex items-center">
                      <FileText className="w-4 h-4 mr-2" />
                      Agent Knowledge Base
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      {agent.assigned_knowledge.map(kbId => {
                        const kb = getKnowledgeDetails(kbId);
                        if (!kb) return null;
                        return (
                          <div key={kb.id} className="border rounded-xl p-5 bg-background border-dashed">
                            <div className="flex justify-between items-start mb-2">
                              <h4 className="font-medium text-foreground">{kb.name}</h4>
                              <div className="flex items-center gap-3">
                                {kb.is_mandatory && <span className="text-[10px] font-semibold text-orange-600 bg-orange-100 px-2 py-0.5 rounded">Required</span>}
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground mb-4">{kb.description}</p>
                            
                            <motion.label className="flex justify-center w-full h-24 px-4 transition bg-muted/30 border-2 border-border border-dashed rounded-lg cursor-pointer hover:border-primary/50 overflow-hidden">
                                <span className="flex items-center space-x-2">
                                    {uploadingFiles[dbAgentId] ? (
                                      <Loader2 className="w-5 h-5 text-primary animate-spin" />
                                    ) : (
                                      <FileText className="w-5 h-5 text-muted-foreground" />
                                    )}
                                    <span className="text-sm font-medium text-muted-foreground">
                                        {uploadingFiles[dbAgentId] ? 'Uploading...' : 'Drop files or browse'}
                                    </span>
                                </span>
                                <input type="file" className="hidden" disabled={uploadingFiles[dbAgentId]} onChange={(e) => handleFileUpload(e, dbAgentId)} />
                            </motion.label>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {agent.assigned_tools && agent.assigned_tools.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4 flex items-center mt-6">
                      <Key className="w-4 h-4 mr-2" />
                      Agent API Tools
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      {agent.assigned_tools.map(toolId => {
                        const tool = getToolDetails(toolId);
                        if (!tool) return null;
                        return (
                          <div key={tool.id} className="border rounded-xl p-5 bg-background">
                            <div className="flex justify-between items-start mb-2">
                              <h4 className="font-medium text-foreground">{tool.name}</h4>
                              <div className="flex items-center gap-3">
                                {tool.is_mandatory && <span className="text-[10px] font-semibold text-orange-600 bg-orange-100 px-2 py-0.5 rounded">Required</span>}
                                <label className="relative inline-flex items-center cursor-pointer">
                                  <input type="checkbox" className="sr-only peer" {...register(`enabled_tools.${tool.id}`)} defaultChecked={tool.is_mandatory} />
                                  <div className="w-9 h-5 bg-muted peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-border after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                                </label>
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground mb-4">{tool.description}</p>
                            
                            {watch(`enabled_tools.${tool.id}`) !== false && (
                              <motion.div initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: 'auto'}} className="space-y-3 overflow-hidden">
                                {tool.parameters && tool.parameters.map((param) => (
                                  <div key={param.name}>
                                    <label className="block text-xs font-medium text-muted-foreground mb-1 capitalize">
                                      {param.name.replace(/_/g, ' ')}
                                    </label>
                                    <input
                                      type={param.type === 'password' || param.name.includes('key') ? 'password' : 'text'}
                                      {...register(`tools.${tool.id}.${param.name}`)}
                                      className="w-full px-3 py-1.5 border border-border rounded-lg bg-muted/30 focus:ring-1 focus:ring-primary focus:border-primary text-sm"
                                      placeholder={param.description || `Enter ${param.name}`}
                                      required={param.is_required}
                                    />
                                  </div>
                                ))}
                              </motion.div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}

        <motion.div variants={itemVariants} className="flex justify-end pt-6">
          <button
            type="submit"
            className="inline-flex items-center px-8 py-4 bg-primary text-primary-foreground rounded-xl font-bold shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1"
          >
            Finish & Go to Studio
            <CheckCircle2 className="ml-2 w-5 h-5" />
          </button>
        </motion.div>
      </form>

      {editingAgent && (
        <AgentSettingsModal agent={editingAgent} onClose={() => setEditingAgent(null)} />
      )}
    </motion.div>
  );
}
