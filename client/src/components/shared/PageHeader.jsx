export default function PageHeader({
  title,
  description,
  action,
}) {
  return (
    <div
      className="
      flex
      justify-between
      items-center
      mb-10
    "
    >
      <div>
        <h1
          className="
          text-4xl
          font-bold
          tracking-tight
        "
        >
          {title}
        </h1>

        <p
          className="
          mt-2
          text-slate-500
        "
        >
          {description}
        </p>
      </div>

      {action}
    </div>
  );
}