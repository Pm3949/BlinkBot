import { useState } from "react";
import { Plus, Globe, Settings2, Code, MoreHorizontal, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import PageHeader from "../components/shared/PageHeader";
import EmptyState from "../components/shared/EmptyState";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useChatbots, useDeleteChatbot } from "../hooks/useChatbots";
import { useUIStore } from "../store/useUIStore";
import { useWorkspacePermissions } from "../hooks/useSettings";
import ImportChatbotModal from "../components/chatbots/ImportChatbotModal";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../components/ui/dialog";
import { Button } from "../components/ui/button";

export default function ChatbotsPage() {
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { canManageAgents } = useWorkspacePermissions();
  const { data: chatbots = [], isLoading, isError } = useChatbots(activeWorkspaceId);
  const deleteChatbotMutation = useDeleteChatbot(activeWorkspaceId);

  const [chatbotToDelete, setChatbotToDelete] = useState(null);
  const [openDropdownId, setOpenDropdownId] = useState(null);

  const confirmDelete = async () => {
    if (!chatbotToDelete) return;
    try {
      await deleteChatbotMutation.mutateAsync(chatbotToDelete.id);
      toast.success("Chatbot deleted successfully");
      setChatbotToDelete(null);
    } catch (error) {
      toast.error("Failed to delete chatbot");
    }
  };

  if (isLoading) {
    return <div className="p-10"><LoadingSkeleton /></div>;
  }

  return (
    <div className="h-full flex flex-col p-6 max-w-[1400px] mx-auto w-full space-y-6">
      <PageHeader 
        title="Chatbots & Widgets" 
        description="Manage your external-facing chatbots and embed them on your website."
      >
        {canManageAgents && (
          <button 
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <Plus size={16} />
            Import Agent as Chatbot
          </button>
        )}
      </PageHeader>

      {isError && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          Unable to load chatbots. Please try again.
        </div>
      )}

      {chatbots.length === 0 && !isError ? (
        <EmptyState
          title="No chatbots yet"
          description="Import an existing internal Agent to turn it into a customer-facing Chatbot. You can then customize its appearance and embed it on your website."
          action={
            canManageAgents && (
              <button 
                onClick={() => setIsImportModalOpen(true)}
                className="flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-medium text-white transition hover:bg-primary/90"
              >
                <Plus size={18} />
                Import Chatbot
              </button>
            )
          }
        />
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          {chatbots.map((chatbot) => (
            <motion.div
              key={chatbot.id}
              whileHover={{ y: -4 }}
              className="glass-card p-6"
            >
              <div className="flex items-start justify-between">
                <div className="h-14 w-14 rounded-2xl bg-blue-500/10 flex items-center justify-center">
                  <Globe className="text-blue-500" />
                </div>

                {canManageAgents && (
                  <div className="relative agent-dropdown-container">
                    <button
                      className="p-2 rounded-xl hover:bg-muted"
                      onClick={(e) => {
                        e.preventDefault();
                        setOpenDropdownId(openDropdownId === chatbot.id ? null : chatbot.id);
                      }}
                    >
                      <MoreHorizontal size={18} />
                    </button>
                    {openDropdownId === chatbot.id && (
                      <div className="absolute right-0 top-full mt-2 w-48 bg-card rounded-xl shadow-lg border border-border py-1 z-10 overflow-hidden">
                        <button
                          className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-500/10 flex items-center gap-2"
                          onClick={(e) => {
                            e.preventDefault();
                            setChatbotToDelete(chatbot);
                            setOpenDropdownId(null);
                          }}
                        >
                          <Trash2 size={16} /> Delete Chatbot
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <h3 className="font-semibold text-lg mt-5">{chatbot.name}</h3>
              <p className="mt-2 text-sm text-muted-foreground line-clamp-1">
                Powered by: <span className="font-medium text-foreground">{chatbot.agents?.name || "Unknown Agent"}</span>
              </p>

              {canManageAgents && (
                <div className="grid grid-cols-2 gap-3 mt-6">
                  <Link
                    to={`/chatbots/${chatbot.id}`}
                    className="flex items-center justify-center gap-2 py-3 rounded-2xl border border-border hover:bg-muted text-sm font-medium transition"
                  >
                    <Settings2 size={16} /> Customize
                  </Link>

                  <Link
                    to={`/chatbots/${chatbot.id}`}
                    className="flex items-center justify-center gap-2 py-3 rounded-2xl btn-primary text-white text-sm font-medium transition"
                  >
                    <Code size={16} /> Embed
                  </Link>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      <ImportChatbotModal 
        isOpen={isImportModalOpen} 
        onClose={() => setIsImportModalOpen(false)} 
      />

      <Dialog open={!!chatbotToDelete} onOpenChange={() => setChatbotToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Chatbot</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the chatbot "{chatbotToDelete?.name}"?
              This will remove the widget integration, but the underlying internal Agent will NOT be deleted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setChatbotToDelete(null)}>Cancel</Button>
            <Button
              variant="destructive"
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={confirmDelete}
              disabled={deleteChatbotMutation.isPending}
            >
              {deleteChatbotMutation.isPending ? "Deleting..." : "Delete Chatbot"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
