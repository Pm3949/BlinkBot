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
      glass-card
      p-6
    "
    >
      <div className="flex justify-between">
        <span className="text-muted-foreground text-sm">
          {title}
        </span>

        <Icon
          size={20}
          className="text-[var(--primary)]"
        />
      </div>

      <div className="mt-4 text-4xl font-bold text-foreground">
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
        from-primary/5
        to-primary/10
        dark:from-primary/10
        dark:to-primary/20
      "
      />
    </motion.div>
  );
}
