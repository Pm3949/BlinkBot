import React, { useState } from "react";
import { useFeedback } from "../../hooks/useFeedback";
import { CheckCircle, AlertCircle, MessageSquare, Bot } from "lucide-react";
import { Button } from "../ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

export default function FeedbackInbox() {
  const { openFeedbackQuery, resolveMutation } = useFeedback();
  const { data: tickets = [], isLoading } = openFeedbackQuery;
  const [filter, setFilter] = useState("All");

  const filteredTickets = filter === "All" 
    ? tickets 
    : tickets.filter(t => t.category === filter);

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading Inbox...</div>;
  }

  if (tickets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center glass-card mt-6">
        <div className="bg-primary/10 p-5 rounded-full mb-6">
          <CheckCircle className="w-10 h-10 text-primary" />
        </div>
        <h3 className="text-2xl font-bold mb-2 text-foreground">Inbox Zero!</h3>
        <p className="text-muted-foreground max-w-md">
          There are no open feedback tickets right now. Your AI agents are performing perfectly and no users have reported hallucinations.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Knowledge Gaps Inbox</h2>
          <p className="text-muted-foreground mt-1 text-sm">Review flagged AI errors and update your source documents.</p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px] bg-background">
              <SelectValue placeholder="Filter Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Categories</SelectItem>
              <SelectItem value="Hallucination">Hallucination</SelectItem>
              <SelectItem value="Outdated">Outdated</SelectItem>
              <SelectItem value="Missing">Missing Info</SelectItem>
              <SelectItem value="Other">Other</SelectItem>
            </SelectContent>
          </Select>
          <div className="bg-destructive/10 text-destructive px-4 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2">
            <AlertCircle size={16} />
            {filteredTickets.length} Open
          </div>
        </div>
      </div>

      {filteredTickets.length === 0 && (
        <div className="text-center py-12 text-muted-foreground border border-dashed rounded-2xl">
          No open tickets found for this category.
        </div>
      )}

      <div className="grid gap-6">
        {filteredTickets.map(ticket => (
          <div key={ticket.id} className="border border-destructive/20 bg-destructive/5 rounded-3xl p-6 shadow-sm transition-all hover:shadow-md">
            <div className="flex flex-col md:flex-row items-start justify-between gap-6">
              <div className="space-y-4 flex-1 w-full">
                <div className="flex items-center gap-3">
                  <span className="bg-destructive text-destructive-foreground px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <AlertCircle size={14} />
                    {ticket.category || "Downvote"}
                  </span>
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Agent: <span className="font-semibold text-foreground bg-muted px-2 py-0.5 rounded-md">{ticket.agent_name || "General"}</span>
                  </span>
                </div>

                <div className="bg-card border border-border rounded-2xl p-5 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-primary/50"></div>
                  <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-foreground">
                    <Bot size={16} className="text-primary" />
                    Flagged AI Response:
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-4 leading-relaxed">
                    {ticket.message_content}
                  </p>
                </div>

                {ticket.comment_text && (
                  <div className="bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400 rounded-2xl p-5 flex gap-3 shadow-sm">
                    <MessageSquare size={18} className="shrink-0 mt-0.5 text-amber-500" />
                    <div className="text-sm">
                      <span className="font-bold block mb-1">User's Correction Note:</span>
                      <span className="leading-relaxed opacity-90">{ticket.comment_text}</span>
                    </div>
                  </div>
                )}
                
                <div className="text-xs text-muted-foreground font-medium pt-2">
                  Reported on {new Date(ticket.created_at).toLocaleString()}
                </div>
              </div>

              <div className="flex flex-col gap-3 shrink-0 w-full md:w-48 bg-card border border-border p-4 rounded-2xl">
                <div className="text-center mb-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Action Required</div>
                  <div className="text-xs text-muted-foreground leading-tight">Update your vector database, then mark resolved to clear the AI's temporary memory patch.</div>
                </div>
                <Button 
                  onClick={() => {
                    resolveMutation.mutate(ticket.id, {
                      onSuccess: () => {
                        import("sonner").then(({ toast }) => {
                          toast.success("Resolved! Go to the Chat page to verify the fix.");
                        });
                      }
                    });
                  }}
                  disabled={resolveMutation.isPending}
                  className="w-full bg-green-500 hover:bg-green-600 text-white shadow-sm font-semibold h-11"
                >
                  <CheckCircle className="w-5 h-5 mr-2" />
                  {resolveMutation.isPending ? "Resolving..." : "Mark Resolved"}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
