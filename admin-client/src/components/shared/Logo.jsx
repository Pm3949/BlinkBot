export default function Logo() {
  return (
    <div className="flex items-center gap-3">
      <img 
        src="/logo1.png" 
        alt="BlinkBot Admin Logo" 
        className="h-16 w-auto object-contain rounded-xl" 
      />
      <div>
        <div className="font-bold">
          BlinkBot Admin
        </div>
        <div className="text-xs text-slate-500">
          Superuser Dashboard
        </div>
      </div>
    </div>
  );
}
