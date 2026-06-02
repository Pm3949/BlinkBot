export default function Logo() {
  return (
    <div
      className="
      flex
      items-center
      gap-3
    "
    >
      <div
        className="
        h-10
        w-10
        rounded-2xl
        bg-gradient-to-br
        from-indigo-600
        to-violet-600
        text-white
        flex
        items-center
        justify-center
        font-bold
      "
      >
        R
      </div>

      <div>
        <div className="font-bold">
          RAGMate
        </div>

        <div
          className="
          text-xs
          text-slate-500
        "
        >
          AI Operating System
        </div>
      </div>
    </div>
  );
}