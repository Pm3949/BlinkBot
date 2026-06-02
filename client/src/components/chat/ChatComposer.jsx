import { useState } from "react";
import { Send } from "lucide-react";

export default function ChatComposer({
  disabled = false,
  isLoading = false,
  onSend,
}) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const message = value.trim();

    if (!message || disabled || isLoading) return;

    onSend(message);
    setValue("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className="
      border-t
      border-slate-200
      dark:border-zinc-800
      bg-white
      dark:bg-zinc-950
      p-5
    "
    >
      <div
        className="
        rounded-[32px]
        border
        border-slate-200
        dark:border-zinc-800
        bg-white
        dark:bg-zinc-900
        shadow-lg
        p-3
        flex
        items-end
        gap-3
      "
      >
        <textarea
          rows={1}
          value={value}
          onChange={(event) =>
            setValue(event.target.value)
          }
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder="Ask RagMate anything..."
          className="
          flex-1
          resize-none
          border-none
          outline-none
          bg-transparent
          text-slate-950
          dark:text-zinc-50
          dark:placeholder:text-zinc-500
          px-3
          py-2
          disabled:opacity-60
          transition
          hover:bg-indigo-700
          focus:outline-none
          focus:ring-2
          focus:ring-indigo-500/30
        "
        />

        <button
          onClick={handleSubmit}
          disabled={
            disabled ||
            isLoading ||
            !value.trim()
          }
          className="
          h-11
          w-11
          rounded-2xl
          bg-indigo-600
          text-white
          flex
          items-center
          justify-center
          disabled:opacity-60
        "
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
