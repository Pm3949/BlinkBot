import React from "react";
import { Loader2 } from "lucide-react";

export default function PageLoader({ text = "Loading RAGMate..." }) {
  return (
    <div className="flex flex-col min-h-screen items-center justify-center bg-background text-foreground z-50">
      <div className="relative flex items-center justify-center mb-6">
        <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse"></div>
        <Loader2 className="h-12 w-12 animate-spin text-primary relative z-10" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight animate-pulse bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
        {text}
      </h2>
    </div>
  );
}
