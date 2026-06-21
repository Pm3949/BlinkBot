import { motion } from "framer-motion";

export default function KPICard({
  title,
  value,
  change,
  icon: Icon,
  sparklineData = [20, 15, 25, 10, 28, 18, 30], // fallback data for graph
}) {
  const changeText =
    typeof change === "string" &&
    change.trim().endsWith("%")
      ? `↑ ${change}`
      : change;

  // Clean data to prevent any NaN or division by zero errors
  const cleanData = (Array.isArray(sparklineData) ? sparklineData : [])
    .map(val => Number(val))
    .filter(val => !isNaN(val));

  const dataToUse = cleanData.length >= 2 ? cleanData : [10, 10];
  const minVal = Math.min(...dataToUse);
  const maxVal = Math.max(...dataToUse);
  const range = (maxVal - minVal) || 1;

  // Generate SVG path for sparkline based on input data points
  const points = dataToUse.map((val, idx) => {
    const x = (idx / (dataToUse.length - 1)) * 100;
    const y = 25 - ((val - minVal) / range) * 20;
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(" L ")}`;
  const areaD = `${pathD} L 100,30 L 0,30 Z`;
  const gradId = `grad-${title.replace(/\s+/g, '')}`;

  return (
    <motion.div
      whileHover={{
        y: -5,
        scale: 1.02,
      }}
      transition={{ type: "spring", stiffness: 300, damping: 15 }}
      className="
        glass-card
        p-6
        relative
        overflow-hidden
        border
        border-border/50
        group
      "
    >
      {/* Background radial highlight */}
      <div className="absolute -right-10 -top-10 w-24 h-24 bg-primary/5 rounded-full blur-2xl group-hover:bg-primary/10 transition-colors" />

      <div className="flex justify-between items-start">
        <span className="text-muted-foreground text-sm font-medium">
          {title}
        </span>

        <div className="p-2 rounded-xl bg-primary/5 text-primary group-hover:bg-primary/10 group-hover:scale-110 transition-all">
          <Icon
            size={18}
          />
        </div>
      </div>

      <div className="mt-4 text-3xl font-extrabold text-foreground tracking-tight">
        {value}
      </div>

      <div className="mt-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
        {changeText}
      </div>

      {/* Mini Sparkline Graph */}
      <div className="mt-5 h-10 w-full overflow-hidden opacity-85 group-hover:opacity-100 transition-opacity">
        <svg className="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path
            d={areaD}
            fill={`url(#${gradId})`}
          />
          <motion.path
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            d={pathD}
            fill="none"
            stroke="var(--primary)"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </motion.div>
  );
}

