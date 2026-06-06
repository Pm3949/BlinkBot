import { Sparkles } from "lucide-react";

export default function EmptyState({
  title,
  description,
  action,
}) {
  return (
    <div
      className="
      flex
      flex-col
      items-center
      justify-center
      py-24
      text-center
    "
    >
      <div
        className="
        h-20
        w-20
        rounded-full
        bg-[rgba(255,77,0,0.14)]
        dark:bg-[rgba(255,77,0,0.15)]
        flex
        items-center
        justify-center
        mb-6
      "
      >
        <Sparkles
          className="text-[var(--primary)] dark:text-orange-300"
          size={32}
        />
      </div>

      <h3 className="text-xl font-semibold text-slate-950 dark:text-zinc-50">
        {title}
      </h3>

      <p
        className="
        text-slate-500
        dark:text-zinc-400
        mt-2
        max-w-md
      "
      >
        {description}
      </p>

      {action && (
        <div className="mt-6">
          {action}
        </div>
      )}
    </div>
  );
}
