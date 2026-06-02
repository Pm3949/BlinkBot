import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Bot,
  Loader2,
  Lock,
  Mail,
  User,
} from "lucide-react";
import {
  signInWithEmail,
  signUpWithEmail,
} from "../services/authService";
import Logo from "../components/shared/Logo";

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const isSignUp = mode === "signup";

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!email.trim() || !password) {
      toast.error("Email and password are required.");
      return;
    }

    if (isSignUp && !fullName.trim()) {
      toast.error("Full name is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      if (isSignUp) {
        await signUpWithEmail({
          email: email.trim(),
          password,
          fullName: fullName.trim(),
        });

        toast.success("Account created");
      } else {
        await signInWithEmail({
          email: email.trim(),
          password,
        });

        toast.success("Signed in");
      }

      navigate("/", {
        replace: true,
      });
    } catch (error) {
      toast.error(
        error.message ||
          "Authentication failed. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <div className="hidden lg:flex w-[46%] bg-slate-950 text-white p-12 flex-col justify-between">
        <Logo />

        <div>
          <div className="h-16 w-16 rounded-3xl bg-indigo-600 flex items-center justify-center mb-8">
            <Bot size={30} />
          </div>

          <h1 className="text-5xl font-bold leading-tight">
            Build AI agents powered by your data.
          </h1>

          <p className="text-slate-300 mt-5 max-w-lg text-lg">
            Sign in to manage agents, documents, chats,
            notes, and analytics from one RagMate workspace.
          </p>
        </div>

        <p className="text-sm text-slate-400">
          RagMate AI Operating System
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-10">
            <Logo />
          </div>

          <div className="bg-white border border-slate-200 rounded-[32px] shadow-sm p-8">
            <div>
              <h2 className="text-3xl font-bold text-slate-900">
                {isSignUp
                  ? "Create account"
                  : "Welcome back"}
              </h2>

              <p className="text-slate-500 mt-2">
                {isSignUp
                  ? "Create your RagMate workspace access."
                  : "Sign in to continue to RagMate."}
              </p>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => setMode("signin")}
                className={`py-3 rounded-xl text-sm font-medium ${
                  !isSignUp
                    ? "bg-white shadow-sm text-slate-900"
                    : "text-slate-500"
                }`}
              >
                Sign In
              </button>

              <button
                type="button"
                onClick={() => setMode("signup")}
                className={`py-3 rounded-xl text-sm font-medium ${
                  isSignUp
                    ? "bg-white shadow-sm text-slate-900"
                    : "text-slate-500"
                }`}
              >
                Sign Up
              </button>
            </div>

            <form
              onSubmit={handleSubmit}
              className="mt-8 space-y-5"
            >
              {isSignUp && (
                <div>
                  <label className="font-medium block mb-2">
                    Full Name
                  </label>

                  <div className="relative">
                    <User
                      size={18}
                      className="absolute left-4 top-4 text-slate-400"
                    />

                    <input
                      value={fullName}
                      onChange={(event) =>
                        setFullName(event.target.value)
                      }
                      className="
                      w-full
                      border
                      border-slate-200
                      rounded-2xl
                      pl-12
                      py-4
                      outline-none
                      focus:ring-2
                      focus:ring-indigo-500/20
                    "
                      placeholder="Your name"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="font-medium block mb-2">
                  Email
                </label>

                <div className="relative">
                  <Mail
                    size={18}
                    className="absolute left-4 top-4 text-slate-400"
                  />

                  <input
                    type="email"
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                    className="
                    w-full
                    border
                    border-slate-200
                    rounded-2xl
                    pl-12
                    py-4
                    outline-none
                    focus:ring-2
                    focus:ring-indigo-500/20
                  "
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium block mb-2">
                  Password
                </label>

                <div className="relative">
                  <Lock
                    size={18}
                    className="absolute left-4 top-4 text-slate-400"
                  />

                  <input
                    type="password"
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                    className="
                    w-full
                    border
                    border-slate-200
                    rounded-2xl
                    pl-12
                    py-4
                    outline-none
                    focus:ring-2
                    focus:ring-indigo-500/20
                  "
                    placeholder="Enter password"
                    autoComplete={
                      isSignUp
                        ? "new-password"
                        : "current-password"
                    }
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="
                w-full
                py-4
                rounded-2xl
                bg-indigo-600
                text-white
                font-medium
                flex
                items-center
                justify-center
                gap-2
                hover:bg-indigo-700
                disabled:opacity-70
              "
              >
                {isSubmitting && (
                  <Loader2
                    size={18}
                    className="animate-spin"
                  />
                )}
                {isSubmitting
                  ? "Please wait..."
                  : isSignUp
                    ? "Create Account"
                    : "Sign In"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
