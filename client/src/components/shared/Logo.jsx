export default function Logo() {
  return (
    <div className="flex items-center gap-3">
      <img 
        src="/logo1.png" 
        alt="BlinkBot Logo" 
        className="h-13 w-auto object-contain rounded-xl" 
      />
      <div>
        <div className="font-bold">
          BlinkBot
        </div>
        <div className="text-xs text-slate-500">
          No-Code Chatbots
        </div>
      </div>
    </div>
  );
}
