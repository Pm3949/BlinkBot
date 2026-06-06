export default function LoadingSkeleton({
  count = 1,
  className = "h-40",
}) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`
          animate-pulse
          bg-slate-100
          dark:bg-zinc-800
          rounded-3xl
          w-full
          ${className}
        `}
        />
      ))}
    </div>
  );
}
