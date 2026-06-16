import React, { useState } from "react";
import { useFeedback } from "../../hooks/useFeedback";
import { CheckCircle, XCircle } from "lucide-react";
import { Button } from "../ui/button";

export default function VerificationBanner() {
  const { pendingVerificationsQuery, verifyMutation } = useFeedback();
  const { data: tickets = [] } = pendingVerificationsQuery;
  const [unsatisfiedTicketId, setUnsatisfiedTicketId] = useState(null);
  const [expandedTicketId, setExpandedTicketId] = useState(null);
  const [comment, setComment] = useState("");

  if (!tickets || tickets.length === 0) return null;

  const handleSatisfied = (id) => {
    verifyMutation.mutate({ feedbackId: id, is_satisfied: true });
  };

  const handleUnsatisfiedSubmit = (id) => {
    verifyMutation.mutate({ feedbackId: id, is_satisfied: false, comment });
    setUnsatisfiedTicketId(null);
    setComment("");
  };

  return (
    <div className="flex flex-col gap-3 px-8 pt-6 pb-2 max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-top-4">
      {tickets.map(ticket => (
        <div key={ticket.id} className="bg-primary/10 border border-primary/20 rounded-2xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start gap-3 w-full">
            <div className="mt-1 bg-primary text-primary-foreground p-1.5 rounded-full shadow-sm">
              <CheckCircle size={18} />
            </div>
            <div className="flex-1">
              <h4 className="font-bold text-foreground flex items-center gap-2">
                Action Required: Verify Fix
              </h4>
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                The team has resolved your flagged issue for <strong className="text-foreground">{ticket.agent_name || "General Agent"}</strong>. 
                Please test the AI again to see if it gives the correct answer now.
                <button 
                  onClick={() => setExpandedTicketId(expandedTicketId === ticket.id ? null : ticket.id)}
                  className="text-primary hover:underline ml-2 font-medium"
                >
                  {expandedTicketId === ticket.id ? "Hide Details" : "Show Details"}
                </button>
              </p>
              
              {expandedTicketId === ticket.id && (
                <div className="mt-3 text-sm bg-background/50 p-3.5 rounded-xl border border-border/50 text-muted-foreground">
                  <div><strong className="text-foreground">AI Said:</strong> {ticket.message_content}</div>
                  {ticket.comment_text && (
                    <div className="mt-2 text-amber-600 dark:text-amber-500">
                      <strong className="font-semibold block mb-0.5">Your Note:</strong> 
                      {ticket.comment_text}
                    </div>
                  )}
                </div>
              )}
              
              {unsatisfiedTicketId === ticket.id && (
                <div className="mt-4 bg-card p-4 rounded-xl border border-border shadow-sm w-full animate-in fade-in zoom-in-95">
                  <label className="text-sm font-semibold mb-2 block">Why are you unsatisfied?</label>
                  <textarea 
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="e.g. The AI is still showing the incorrect pricing..."
                    className="w-full text-sm bg-background border border-border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-primary/50 mb-3 min-h-[80px] resize-y"
                  />
                  <div className="flex gap-3 justify-end">
                    <Button variant="ghost" size="sm" onClick={() => setUnsatisfiedTicketId(null)}>Cancel</Button>
                    <Button size="sm" onClick={() => handleUnsatisfiedSubmit(ticket.id)} disabled={verifyMutation.isPending} className="bg-destructive hover:bg-destructive/90 text-destructive-foreground">
                      {verifyMutation.isPending ? "Submitting..." : "Send back to Team"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {unsatisfiedTicketId !== ticket.id && (
            <div className="flex gap-2 shrink-0 w-full md:w-auto mt-2 md:mt-0">
              <Button 
                onClick={() => handleSatisfied(ticket.id)} 
                disabled={verifyMutation.isPending}
                className="bg-green-500 hover:bg-green-600 text-white flex-1 md:flex-none shadow-sm font-semibold"
              >
                <CheckCircle size={16} className="mr-2" /> Satisfied
              </Button>
              <Button 
                variant="outline"
                onClick={() => setUnsatisfiedTicketId(ticket.id)}
                disabled={verifyMutation.isPending}
                className="text-destructive border-destructive/30 hover:bg-destructive/10 flex-1 md:flex-none font-semibold"
              >
                <XCircle size={16} className="mr-2" /> Unsatisfied
              </Button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
