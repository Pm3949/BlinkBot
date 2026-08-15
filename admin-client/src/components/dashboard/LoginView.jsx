import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function LoginView({
  email,
  setEmail,
  password,
  setPassword,
  isLoggingIn,
  handleLogin,
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950 p-4">
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl p-8 max-w-md w-full bg-white dark:bg-slate-900 shadow-2xl">
        <div className="flex justify-center mb-6">
          <div className="p-3 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 rounded-xl text-indigo-600 dark:text-indigo-400">
            <ShieldCheck className="w-12 h-12" />
          </div>
        </div>
        <h2 className="text-2xl font-bold text-center mb-2 text-slate-900 dark:text-slate-50">Admin Portal</h2>
        <p className="text-slate-500 dark:text-slate-400 text-center mb-8 text-sm">Please sign in with your Super Admin credentials</p>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-950 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-950 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoggingIn}
            className="w-full bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-650 text-white font-bold py-2.5 rounded-lg mt-4 disabled:opacity-50 transition-colors shadow-lg shadow-indigo-600/10"
          >
            {isLoggingIn ? "Signing In..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
