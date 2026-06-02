export default function StatCard({
  title,
  value,
  icon: Icon,
}) {
  return (
    <div
      className="
      bg-white
      rounded-3xl
      border
      border-slate-200
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
        "
        >
          {title}
        </span>

        <Icon
          size={18}
          className="
          text-indigo-600
        "
        />
      </div>

      <div
        className="
        mt-4
        text-4xl
        font-bold
      "
      >
        {value}
      </div>
    </div>
  );
}