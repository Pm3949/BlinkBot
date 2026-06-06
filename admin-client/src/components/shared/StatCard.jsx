export default function StatCard({
  title,
  value,
  icon: Icon,
}) {
  return (
    <div
      className="
      bg-white
      dark:bg-zinc-900
      rounded-3xl
      border
      border-slate-200
      dark:border-zinc-800
      p-6
    "
    >
      <div
        className="
        flex
        justify-between
      "
      >
        <span
          className="
          text-slate-500
          dark:text-zinc-400
        "
        >
          {title}
        </span>

        <Icon
          size={18}
          className="
          text-[var(--primary)]
        "
        />
      </div>

      <div
        className="
        mt-4
        text-4xl
        font-bold
        text-slate-900
        dark:text-zinc-50
      "
      >
        {value}
      </div>
    </div>
  );
}
