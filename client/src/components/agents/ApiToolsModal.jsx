import React, { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";
import { Loader2, Wrench, Globe, Save, Plus } from "lucide-react";
import { useProjectTools, useUpdateTool, useCreateTool } from "../../hooks/useAgents";
import { toast } from "sonner";
import LoadingSkeleton from "../shared/LoadingSkeleton";

export default function ApiToolsModal({ project, onClose }) {
  const { data: tools = [], isLoading } = useProjectTools(project?.id);
  const updateToolMutation = useUpdateTool(project?.id);
  const createToolMutation = useCreateTool(project?.id);

  const [selectedTool, setSelectedTool] = useState(null);
  const [formData, setFormData] = useState({ name: "", config: {} });

  useEffect(() => {
    if (tools.length > 0 && !selectedTool) {
      handleToolSelect(tools[0]);
    }
  }, [tools]);

  const handleToolSelect = (tool) => {
    setSelectedTool(tool);
    setFormData({
      name: tool.name,
      config: JSON.parse(JSON.stringify(tool.config)), // Deep copy
    });
  };

  const handleConfigChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      config: {
        ...prev.config,
        [key]: value
      }
    }));
  };

  const handleSave = () => {
    if (!selectedTool) return;
    
    updateToolMutation.mutate({
      id: selectedTool.id,
      payload: formData
    }, {
      onSuccess: () => {
        toast.success("Tool configuration saved successfully!");
      },
      onError: () => {
        toast.error("Failed to save tool configuration");
      }
    });
  };

  const handleCreateNewTool = () => {
    createToolMutation.mutate({
      name: "New Custom Tool",
      config: {
        base_url: "https://api.example.com",
        endpoints: [],
        api_key: ""
      }
    }, {
      onSuccess: () => {
        toast.success("New tool added!");
      }
    });
  };

  return (
    <Dialog open={!!project} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col p-0 overflow-hidden bg-background">
        <div className="p-6 pb-4 border-b border-border bg-card">
          <DialogHeader>
            <DialogTitle className="text-xl flex items-center gap-2">
              <Wrench className="text-primary" size={24} />
              API Tools Manager
            </DialogTitle>
            <DialogDescription>
              Configure the base URLs, endpoints, and authentication keys for tools in {project?.name}.
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="flex flex-1 overflow-hidden min-h-[400px]">
          {/* Sidebar */}
          <div className="w-1/3 border-r border-border bg-muted/20 p-4 overflow-y-auto flex flex-col">
            <Button variant="outline" className="w-full mb-4 justify-start border-dashed border-primary/50 text-primary hover:text-primary hover:bg-primary/10" onClick={handleCreateNewTool} disabled={createToolMutation.isPending}>
              {createToolMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Add Custom Tool
            </Button>
            
            {isLoading ? (
              <LoadingSkeleton count={3} className="h-12 mb-2" />
            ) : tools.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center mt-10">
                No tools configured for this network.
              </div>
            ) : (
              <div className="space-y-2">
                {tools.map(tool => (
                  <button
                    key={tool.id}
                    onClick={() => handleToolSelect(tool)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      selectedTool?.id === tool.id 
                        ? "bg-primary/10 border-primary text-primary" 
                        : "bg-card border-border hover:border-primary/50 text-foreground"
                    } ${tool.config?.is_enabled === false ? 'opacity-50' : ''}`}
                  >
                    <div className="font-semibold text-sm truncate flex justify-between items-center">
                      {tool.name}
                      {tool.config?.is_enabled === false && <span className="text-[10px] bg-muted text-muted-foreground px-2 py-0.5 rounded-full">DISABLED</span>}
                    </div>
                    <div className="text-xs text-muted-foreground truncate mt-1">
                      {tool.config?.base_url || "No Base URL"}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Editor */}
          <div className="flex-1 flex flex-col bg-card">
            {selectedTool ? (
              <>
                <div className="flex-1 p-6 overflow-y-auto space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-1">Tool Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full bg-background border border-border rounded-xl px-4 py-2 text-foreground"
                    />
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold text-lg flex items-center gap-2">
                      <Globe size={18} className="text-primary"/> Connection Settings
                    </h3>
                    
                    <div className="space-y-4 bg-background p-5 rounded-2xl border border-border">
                      <div className="flex items-center justify-between pb-4 mb-4 border-b border-border">
                        <div>
                          <h4 className="font-medium text-sm">Tool Status</h4>
                          <p className="text-xs text-muted-foreground">Is this tool active and ready for the LangGraph agent to use?</p>
                        </div>
                        <div className="relative inline-flex items-center cursor-pointer">
                          <input 
                            type="checkbox" 
                            className="sr-only peer" 
                            checked={formData.config?.is_enabled ?? true}
                            onChange={(e) => handleConfigChange("is_enabled", e.target.checked)}
                          />
                          <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">Base URL</label>
                        <input
                          type="url"
                          value={formData.config?.base_url || ""}
                          onChange={(e) => handleConfigChange("base_url", e.target.value)}
                          placeholder="https://api.example.com/v1"
                          className="w-full bg-background border border-border rounded-xl px-4 py-2 font-mono text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-1">API Key / Auth Header (Optional)</label>
                        <input
                          type="password"
                          value={formData.config?.api_key || ""}
                          onChange={(e) => handleConfigChange("api_key", e.target.value)}
                          placeholder="Bearer sk-..."
                          className="w-full bg-background border border-border rounded-xl px-4 py-2 font-mono text-sm"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-1">Custom Headers (JSON)</label>
                          <textarea
                            value={typeof formData.config?.headers === 'string' ? formData.config.headers : JSON.stringify(formData.config?.headers || {})}
                            onChange={(e) => handleConfigChange("headers", e.target.value)}
                            placeholder='{"X-Firm-Token": "abc"}'
                            rows={3}
                            className="w-full bg-background border border-border rounded-xl px-4 py-2 font-mono text-xs resize-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Query Format / Payload (JSON)</label>
                          <textarea
                            value={typeof formData.config?.query_format === 'string' ? formData.config.query_format : JSON.stringify(formData.config?.query_format || {})}
                            onChange={(e) => handleConfigChange("query_format", e.target.value)}
                            placeholder='{"query": "{user_input}"}'
                            rows={3}
                            className="w-full bg-background border border-border rounded-xl px-4 py-2 font-mono text-xs resize-none"
                          />
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium mb-1">Raw JSON Config</label>
                        <textarea
                          readOnly
                          value={JSON.stringify(formData.config, null, 2)}
                          rows={6}
                          className="w-full bg-muted border border-border rounded-xl px-4 py-3 font-mono text-xs resize-none text-muted-foreground"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 border-t border-border flex justify-end gap-3 bg-card">
                  <Button variant="outline" onClick={onClose}>Close</Button>
                  <Button onClick={handleSave} disabled={updateToolMutation.isPending}>
                    {updateToolMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    Save Configuration
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                Select a tool from the sidebar to edit its configuration.
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
