import { motion } from "framer-motion";

export default function KPICard({
  title,
  value,
  change,
  icon: Icon,
  sparklineData = [20, 15, 25, 10, 28, 18, 30],
  accent = "primary",
  index = 0,
}) {
  const accentMap = {
    primary: {
      glow: "rgba(255,77,0,0.12)",
      stroke: "var(--primary)",
      gradStart: "rgba(255,77,0,0.25)",
      iconBg: "rgba(255,77,0,0.1)",
      iconColor: "var(--primary)",
      badge: "rgba(255,77,0,0.08)",
    },
    violet: {
      glow: "rgba(139,92,246,0.12)",
      stroke: "#8b5cf6",
      gradStart: "rgba(139,92,246,0.2)",
      iconBg: "rgba(139,92,246,0.1)",
      iconColor: "#8b5cf6",
      badge: "rgba(139,92,246,0.08)",
    },
    cyan: {
      glow: "rgba(6,182,212,0.12)",
      stroke: "#06b6d4",
      gradStart: "rgba(6,182,212,0.2)",
      iconBg: "rgba(6,182,212,0.1)",
      iconColor: "#06b6d4",
      badge: "rgba(6,182,212,0.08)",
    },
    emerald: {
      glow: "rgba(16,185,129,0.12)",
      stroke: "#10b981",
      gradStart: "rgba(16,185,129,0.2)",
      iconBg: "rgba(16,185,129,0.1)",
      iconColor: "#10b981",
      badge: "rgba(16,185,129,0.08)",
    },
  };

  const a = accentMap[accent] || accentMap.primary;
  const gradId = `spark-grad-${title.replace(/\s+/g, "")}-${index}`;

  const cleanData = (Array.isArray(sparklineData) ? sparklineData : [])
    .map((v) => Number(v))
    .filter((v) => !isNaN(v));
  const dataToUse = cleanData.length >= 2 ? cleanData : [10, 10];
  const minVal = Math.min(...dataToUse);
  const maxVal = Math.max(...dataToUse);
  const range = maxVal - minVal || 1;

  const W = 100;
  const H = 32;
  const PAD = 2;
  const pts = dataToUse.map((val, i) => {
    const x = (i / (dataToUse.length - 1)) * W;
    const y = PAD + (1 - (val - minVal) / range) * (H - PAD * 2);
    return [x, y];
  });

  const linePath = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x} ${y}`).join(" ");
  const areaPath = `${linePath} L ${W} ${H} L 0 ${H} Z`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: "easeOut" }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="relative overflow-hidden rounded-3xl border border-border/60 bg-card p-5 group cursor-default"
      style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
    >
      {/* Hover glow */}
      <div
        className="pointer-events-none absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{ background: `radial-gradient(circle at top right, ${a.glow} 0%, transparent 65%)` }}
      />

      {/* Top row */}
      <div className="flex items-start justify-between mb-4">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl shrink-0 group-hover:scale-110 transition-transform duration-300"
          style={{ background: a.iconBg }}
        >
          <Icon size={20} style={{ color: a.iconColor }} />
        </div>
        <span
          className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full"
          style={{ background: a.badge, color: a.iconColor }}
        >
          Live
        </span>
      </div>

      {/* Value */}
      <div className="text-[28px] font-black text-foreground tracking-tight leading-none">
        {value}
      </div>

      {/* Title + change */}
      <div className="mt-1.5 mb-4">
        <div className="text-xs font-semibold text-muted-foreground">{title}</div>
        {change && (
          <div className="text-[11px] text-muted-foreground/70 mt-0.5 truncate">{change}</div>
        )}
      </div>

      {/* Sparkline */}
      <div className="h-9 w-full overflow-hidden">
        <svg className="w-full h-full" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={a.gradStart} stopOpacity="1" />
              <stop offset="100%" stopColor={a.gradStart} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradId})`} />
          <motion.path
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: 1.4, delay: index * 0.1, ease: "easeOut" }}
            d={linePath}
            fill="none"
            stroke={a.stroke}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Last data point dot */}
          <circle
            cx={pts[pts.length - 1][0]}
            cy={pts[pts.length - 1][1]}
            r="2.5"
            fill={a.stroke}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          />
        </svg>
      </div>
    </motion.div>
  );
}
