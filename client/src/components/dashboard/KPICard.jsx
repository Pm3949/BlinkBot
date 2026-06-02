import { motion } from "framer-motion";

export default function KPICard({
  title,
  value,
  change,
  icon: Icon,
}) {
  const changeText =
    typeof change === "string" &&
    change.trim().endsWith("%")
      ? `↑ ${change}`
      : change;

  return (
    <motion.div
      whileHover={{
        y: -4,
      }}
      className="
      bg-white
      dark:bg-zinc-900
      rounded-2xl
      border
      border-slate-200
      dark:border-zinc-800
      p-6
      shadow-sm
      transition-colors
    "
    >
      <div className="flex justify-between">
        <span className="text-slate-500 dark:text-zinc-400 text-sm">
          {title}
        </span>

        <Icon
          size={20}
          className="text-indigo-600"
        />
      </div>

      <div className="mt-4 text-4xl font-bold text-slate-950 dark:text-zinc-50">
        {value}
      </div>

      <div className="mt-2 text-sm text-emerald-600 dark:text-emerald-400">
        {changeText}
      </div>

      {/* Mini Sparkline Placeholder */}

      <div
        className="
        mt-4
        h-10
        rounded-xl
        bg-gradient-to-r
        from-indigo-50
        to-indigo-100
        dark:from-indigo-500/10
        dark:to-cyan-500/10
      "
      />
    </motion.div>
  );
}
