import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldX, Home, Clock } from "lucide-react";

/**
 * AccessDeniedScreen
 * ------------------
 * Shared "Access Denied" UI used by route guards.
 *
 * Props:
 *  - title       : string  — headline (default: "Access Denied")
 *  - description : string  — explanation shown below headline
 *  - redirectTo  : string  — path to redirect after countdown (default: "/")
 *  - countdownSec: number  — seconds before auto-redirect (default: 5, 0 = no auto)
 */
export default function AccessDeniedScreen({
  title = "Access Denied",
  description = "You don't have permission to view this page.",
  redirectTo = "/",
  countdownSec = 5,
}) {
  const navigate = useNavigate();
  const [seconds, setSeconds] = useState(countdownSec);

  useEffect(() => {
    if (countdownSec <= 0) return;

    const interval = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          navigate(redirectTo, { replace: true });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [countdownSec, redirectTo, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div
        className="
          glass-card
          flex flex-col items-center justify-center
          text-center
          max-w-lg w-full
          p-12
          gap-6
          animate-fade-in
        "
      >
        {/* Icon */}
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-red-500/20 blur-2xl scale-150" />
          <div className="relative p-5 rounded-full bg-red-500/10 border border-red-500/20">
            <ShieldX className="w-12 h-12 text-red-500" />
          </div>
        </div>

        {/* Text */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-foreground">{title}</h1>
          <p className="text-muted-foreground leading-relaxed">{description}</p>
        </div>

        {/* Divider */}
        <div className="w-full h-px bg-border" />

        {/* Actions */}
        <div className="flex flex-col items-center gap-4 w-full">
          <button
            onClick={() => navigate(redirectTo, { replace: true })}
            className="
              w-full flex items-center justify-center gap-2
              px-6 py-3 rounded-2xl
              bg-primary text-primary-foreground
              hover:opacity-90 transition-opacity
              font-medium
            "
          >
            <Home size={18} />
            Go to Dashboard
          </button>

          {countdownSec > 0 && (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock size={13} />
              Redirecting in{" "}
              <span className="font-semibold text-foreground tabular-nums">
                {seconds}s
              </span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
