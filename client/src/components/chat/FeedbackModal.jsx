import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Button } from "../ui/button";
import { AlertCircle } from "lucide-react";

export default function FeedbackModal({ isOpen, onClose, onSubmit, isSubmitting }) {
  const [category, setCategory] = useState("Hallucination");
  const [comment, setComment] = useState("");

  const handleSubmit = () => {
    onSubmit({ category, comment_text: comment });
    setComment("");
    setCategory("Hallucination");
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            Report AI Error
          </DialogTitle>
          <DialogDescription>
            Flagging this response will temporarily patch the AI's memory and alert your teammates to update the source documents.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="flex flex-col space-y-1.5">
            <label className="text-sm font-medium text-foreground">Issue Category</label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger>
                <SelectValue placeholder="Select a category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Hallucination">Hallucination (Made up facts)</SelectItem>
                <SelectItem value="Outdated">Outdated Information</SelectItem>
                <SelectItem value="Missing">Missing Critical Details</SelectItem>
                <SelectItem value="Other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col space-y-1.5">
            <label className="text-sm font-medium text-foreground">Correction Notes (Optional)</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="e.g. The actual price is $499, not $599..."
              className="flex min-h-[80px] w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} className="bg-destructive hover:bg-destructive/90 text-destructive-foreground">
            {isSubmitting ? "Submitting..." : "Submit Flag"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
