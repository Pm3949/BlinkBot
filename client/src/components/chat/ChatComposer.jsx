import { useState, useRef } from "react";
import { Send, Mic, Square } from "lucide-react";

export default function ChatComposer({
  disabled = false,
  isLoading = false,
  onSend,
}) {
  const [value, setValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.webm");

        try {
          const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
          const response = await fetch(`${API_URL}/stt`, {
            method: "POST",
            body: formData,
          });

          if (response.ok) {
            const data = await response.json();
            setValue((prev) => prev + (prev ? " " : "") + data.text);
          } else {
            console.error("STT Error:", await response.text());
          }
        } catch (error) {
          console.error("Error sending audio:", error);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
  };

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
      border-border
      bg-card
      p-5
    "
    >
      <div
        className="
        rounded-[32px]
        border
        border-border
        bg-background
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
          text-foreground
          placeholder:text-muted-foreground
          px-3
          py-2
          disabled:opacity-60
          transition
          focus:outline-none
          focus:ring-2
          focus:ring-primary/30
        "
        />

        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled || isLoading}
          className={`
          h-11
          w-11
          rounded-2xl
          flex
          items-center
          justify-center
          transition-colors
          ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'bg-muted text-muted-foreground hover:bg-muted/80'}
          disabled:opacity-60
          `}
          title={isRecording ? "Stop recording" : "Start recording"}
        >
          {isRecording ? <Square size={18} fill="currentColor" /> : <Mic size={18} />}
        </button>

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
          btn-primary
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
