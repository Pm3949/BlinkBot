import { useState } from "react";
import { usePageSeo } from '../hooks/usePageSeo';
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, Bot, Sun, Moon, Eye, EyeOff } from "lucide-react";
import { useUIStore } from "../store/useUIStore";
import { useAuth } from "../context/AuthContext";
import {
  signInWithEmail,
  signUpWithEmail,
  verifyOTP,
  requestPasswordReset,
  resetPassword,
  loginWith2FA
} from "../services/authService";
import Logo from "../components/shared/Logo";

// --- Minimal Shadcn-like UI Components ---
const Label = ({ children, htmlFor, className = "" }) => (
  <label htmlFor={htmlFor} className={`text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 ${className}`}>
    {children}
  </label>
);

const Input = (props) => (
  <input
    {...props}
    className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${props.className || ""}`}
  />
);

const Button = ({ children, variant = "default", className = "", ...props }) => {
  const baseStyle = "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
  };
  return (
    <button className={`${baseStyle} ${variants[variant]} px-4 py-2 ${className}`} {...props}>
      {children}
    </button>
  );
};
// ------------------------------------------

export default function LoginPage() {
  usePageSeo('Log In or Sign Up', 'Sign in or create a free BlinkBot account to start building custom AI chatbots powered by your documents.');
  const navigate = useNavigate();
  const { login } = useAuth();
  const [mode, setMode] = useState("signin"); // 'signin', 'signup', 'otp', 'forgot-password', 'reset-password', '2fa'
  const [pendingUserId, setPendingUserId] = useState(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);

  const isSignUp = mode === "signup";
  const isOtp = mode === "otp";
  const isForgot = mode === "forgot-password";
  const isReset = mode === "reset-password";

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (mode === "2fa") {
      if (!otp.trim()) {
        toast.error("Authenticator code is required.");
        return;
      }
      setIsSubmitting(true);
      try {
        const data = await loginWith2FA({ user_id: pendingUserId, totp_code: otp.trim() });
        login(data.access_token, data.user);
        toast.success("Signed in");
        navigate("/", { replace: true });
      } catch (error) {
        toast.error(error.message || "Invalid Code.");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (isOtp) {
      if (!otp.trim()) {
        toast.error("Verification code is required.");
        return;
      }
      setIsSubmitting(true);
      try {
        const data = await verifyOTP({ email: email.trim(), otp: otp.trim() });
        login(data.access_token, data.user);
        toast.success("Verified & signed in successfully");
        navigate("/", { replace: true });
      } catch (error) {
        toast.error(error.message || "Invalid OTP.");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (isForgot) {
      if (!email.trim()) {
        toast.error("Email is required.");
        return;
      }
      setIsSubmitting(true);
      try {
        await requestPasswordReset(email.trim());
        toast.success("If the email exists, a reset code has been sent.");
        setMode("reset-password");
      } catch (e) {
        toast.error(e.message || "Request failed");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (isReset) {
      if (!otp.trim() || !newPassword) {
        toast.error("OTP and new password are required.");
        return;
      }
      setIsSubmitting(true);
      try {
        await resetPassword({ email: email.trim(), token: otp.trim(), new_password: newPassword });
        toast.success("Password reset successfully. You can now log in.");
        setMode("signin");
        setPassword("");
        setOtp("");
      } catch (e) {
        toast.error(e.message || "Reset failed");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

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
      let result;
      if (isSignUp) {
        result = await signUpWithEmail({
          email: email.trim(),
          password,
          fullName: fullName.trim(),
        });
        toast.success("Account created. Please check your email.");
      } else {
        result = await signInWithEmail({
          email: email.trim(),
          password,
        });
      }

      if (result.requires_otp) {
        setMode("otp");
      } else if (result.requires_2fa) {
        setPendingUserId(result.user_id);
        setMode("2fa");
      } else {
        login(result.access_token, result.user);
        toast.success("Signed in");
        navigate("/", { replace: true });
      }
    } catch (error) {
      toast.error(error.message || "Authentication failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleMode = () => {
    if (isSignUp) setMode("signin");
    else setMode("signup");
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Left Pane (Branding) */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between p-12 bg-zinc-950 border-r border-border relative overflow-hidden">
        {/* Subtle Background Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-900/50 via-zinc-950/90 to-zinc-950 z-0 pointer-events-none" />
        
        <div className="relative z-10 flex items-center gap-2">
          <Logo className="text-white" />
        </div>
        
        <div className="relative z-10 max-w-lg mt-10">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--primary)]/20 text-[var(--primary)] mb-6 ring-1 ring-[var(--primary)]/30">
            <Bot size={24} />
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Turn one prompt into a fully trained AI team.
          </h1>
          <p className="text-lg text-zinc-400">
            Instant, seamless, and powerful. Join thousands of developers building the future with BlinkBot.
          </p>
        </div>
        
        <div className="relative z-10 text-sm text-zinc-500 font-medium mt-auto pt-10">
          © {new Date().getFullYear()} BlinkBot Inc. All rights reserved.
        </div>
      </div>

      {/* Right Pane (Auth Form) */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12 bg-card relative">
        <button
          onClick={toggleDarkMode}
          type="button"
          className="absolute top-6 right-6 h-10 w-10 rounded-full border border-border text-muted-foreground flex items-center justify-center hover:bg-accent hover:text-accent-foreground transition-all"
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <div className="w-full max-w-[400px] mx-auto">
          <div className="lg:hidden flex justify-center mb-8">
            <Logo />
          </div>

          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold tracking-tight mb-2">
              {isOtp
                ? "Check your email"
                : mode === "2fa"
                ? "Two-Factor Authentication"
                : isForgot
                ? "Reset your password"
                : isReset
                ? "Create new password"
                : isSignUp
                ? "Create an account"
                : "Welcome back"}
            </h1>
            <p className="text-muted-foreground text-sm">
              {isOtp
                ? `We've sent a 6-digit code to ${email}`
                : mode === "2fa"
                ? "Enter the 6-digit code from your authenticator app"
                : isForgot
                ? "Enter your email to receive a password reset code"
                : isReset
                ? "Enter the 6-digit code and your new password"
                : isSignUp
                ? "Enter your details below to create your account"
                : "Enter your email and password to log in"}
            </p>
          </div>

          {!isOtp && !isForgot && !isReset && mode !== "2fa" && (
            <>
              <a 
                href={`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/auth/google/login`}
                className="w-full mb-6 h-11 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  <path d="M1 1h22v22H1z" fill="none"/>
                </svg>
                Continue with Google
              </a>

              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground font-medium">
                    Or continue with email
                  </span>
                </div>
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isOtp || mode === "2fa" ? (
              <div className="space-y-2">
                <Label htmlFor="otp">{mode === "2fa" ? "Authenticator Code" : "Verification Code"}</Label>
                <Input
                  id="otp"
                  type="text"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="123456"
                  required
                  className="text-center tracking-[0.5em] text-2xl h-14 font-bold"
                  autoFocus
                />
              </div>
            ) : isForgot ? (
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                  className="h-11"
                  autoFocus
                />
              </div>
            ) : isReset ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="otp">Reset Code</Label>
                  <Input
                    id="otp"
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="123456"
                    required
                    className="text-center tracking-[0.5em] text-2xl h-14 font-bold"
                    autoFocus
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <div className="relative">
                    <Input
                      id="newPassword"
                      type={showPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="h-11 pr-10"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                {isSignUp && (
                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full Name</Label>
                    <Input
                      id="fullName"
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="John Doe"
                      required
                      className="h-11"
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    autoComplete="email"
                    className="h-11"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    {!isSignUp && (
                      <button type="button" onClick={() => setMode("forgot-password")} className="text-sm text-muted-foreground hover:text-foreground font-medium transition-colors">
                        Forgot your password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      autoComplete={isSignUp ? "new-password" : "current-password"}
                      className="h-11 pr-10"
                    />
                    <button
                      type="button"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </>
            )}
            
            <Button className="w-full h-11 font-medium text-base mt-2" type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
              {isSubmitting
                ? "Please wait..."
                : isOtp || mode === "2fa"
                ? "Verify Code"
                : isForgot
                ? "Send Reset Link"
                : isReset
                ? "Reset Password"
                : isSignUp
                ? "Create Account"
                : "Log In"}
            </Button>
          </form>

          <div className="mt-8 text-center text-sm">
            {isOtp || isForgot || isReset || mode === "2fa" ? (
              <button
                type="button"
                onClick={() => setMode("signin")}
                className="text-muted-foreground hover:text-foreground font-medium transition-colors"
              >
                Back to login
              </button>
            ) : (
              <p className="text-muted-foreground">
                {isSignUp ? "Already have an account? " : "Don't have an account? "}
                <button
                  type="button"
                  onClick={handleToggleMode}
                  className="text-foreground font-semibold hover:underline"
                >
                  {isSignUp ? "Log in" : "Sign up"}
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
