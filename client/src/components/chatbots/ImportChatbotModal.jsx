import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Button } from "../ui/button";
import { useAgents } from "../../hooks/useAgents";
import { useImportChatbot } from "../../hooks/useChatbots";
import { useUIStore } from "../../store/useUIStore";
import { toast } from "sonner";
import LoadingSkeleton from "../shared/LoadingSkeleton";

export default function ImportChatbotModal({ isOpen, onClose }) {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { data: agents = [], isLoading } = useAgents(activeWorkspaceId);
  const importChatbotMutation = useImportChatbot(activeWorkspaceId);

  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [chatbotName, setChatbotName] = useState("");

  const handleImport = async () => {
    if (!selectedAgentId) {
      toast.error("Please select an agent to import");
      return;
    }
    if (!chatbotName) {
      toast.error("Please provide a name for your chatbot");
      return;
    }

    try {
      await importChatbotMutation.mutateAsync({
        agent_id: selectedAgentId,
        name: chatbotName,
        settings: {
          themeColor: "#3B82F6",
          welcomeMessage: "Hi there! How can I help you today?",
          position: "bottom-right",
        },
      });
      toast.success("Chatbot imported successfully!");
      onClose();
      // Reset state
      setSelectedAgentId("");
      setChatbotName("");
    } catch (error) {
      toast.error(error.message || "Failed to import chatbot");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Import Agent as Chatbot</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Select Internal Agent</label>
            {isLoading ? (
              <LoadingSkeleton />
            ) : agents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No agents found in this workspace. Create an agent first.</p>
            ) : (
              <Select
                value={selectedAgentId}
                onValueChange={(value) => {
                  setSelectedAgentId(value);
                  // Auto-fill name if empty
                  if (!chatbotName) {
                    const selected = agents.find((a) => a.id === value);
                    if (selected) setChatbotName(selected.name + " Bot");
                  }
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="-- Select an Agent --" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Public Chatbot Name</label>
            <input
              type="text"
              value={chatbotName}
              onChange={(e) => setChatbotName(e.target.value)}
              placeholder="e.g. Support Bot, Pricing FAQ"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <p className="text-xs text-muted-foreground">This is the name your visitors will see.</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!selectedAgentId || !chatbotName || importChatbotMutation.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {importChatbotMutation.isPending ? "Importing..." : "Import Chatbot"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
