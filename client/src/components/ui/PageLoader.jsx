import React from "react";

export default function PageLoader({ text = "Loading BlinkBot..." }) {
  return (
    <div className="flex flex-col min-h-screen items-center justify-center bg-[#09090b] text-foreground z-50 overflow-hidden relative">
      {/* Dynamic Background Glowing Gradients */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] rounded-full bg-primary/10 blur-[80px] pointer-events-none animate-pulse"></div>
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[180px] h-[180px] rounded-full bg-emerald-500/5 blur-[50px] pointer-events-none animate-pulse duration-3000"></div>

      <div className="flex flex-col items-center relative z-10">
        {/* Animated Brand Container */}
        <div className="relative mb-8 group">
          {/* Pulsing Outer Glow Ring */}
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-tr from-primary to-emerald-500 opacity-20 blur-xl animate-pulse group-hover:opacity-35 transition-opacity"></div>
          
          {/* Rotating Subtle Border Accent */}
          <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-primary/30 via-transparent to-emerald-500/30 animate-spin [animation-duration:8s] opacity-75"></div>

          {/* Logo Frame */}
          <div className="relative w-24 h-24 rounded-2xl bg-card/65 border border-border/40 backdrop-blur-md p-4 flex items-center justify-center shadow-2xl">
            <img 
              src="/logo1.png" 
              alt="BlinkBot Logo" 
              className="w-full h-full object-contain rounded-xl animate-pulse [animation-duration:2.5s]" 
            />
          </div>
        </div>

        {/* Loading Message */}
        <div className="space-y-4 text-center">
          <h2 className="text-sm font-semibold tracking-[0.2em] uppercase bg-gradient-to-r from-zinc-100 via-zinc-400 to-zinc-100 bg-clip-text text-transparent animate-pulse [animation-duration:2s]">
            {text}
          </h2>

          {/* Premium Linear Progress Bar */}
          <div className="w-48 h-[3px] rounded-full bg-muted/30 overflow-hidden relative mx-auto border border-white/5">
            <div className="absolute top-0 bottom-0 left-0 w-1/3 bg-gradient-to-r from-primary to-emerald-500 rounded-full animate-infinite-slide"></div>
          </div>
        </div>
      </div>

      {/* Embedded slide animation helper */}
      <style>{`
        @keyframes infinite-slide {
          0% {
            left: -35%;
            right: 100%;
          }
          50% {
            left: 100%;
            right: -35%;
          }
          100% {
            left: -35%;
            right: 100%;
          }
        }
        .animate-infinite-slide {
          animation: infinite-slide 1.8s cubic-bezier(0.65, 0.815, 0.32, 0.985) infinite;
        }
      `}</style>
    </div>
  );
}
