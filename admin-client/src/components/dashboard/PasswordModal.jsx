import React from 'react';
import { X, Lock } from 'lucide-react';

export default function PasswordModal({
  passwordModalOpen,
  setPasswordModalOpen,
  actionPassword,
  setActionPassword,
  executePendingAction,
  setPendingAction,
}) {
  if (!passwordModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/80 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
        <button 
          onClick={() => { setPasswordModalOpen(false); setActionPassword(""); setPendingAction(null); }}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
        >
          <X size={20} />
        </button>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-50 dark:bg-red-950/40 text-red-500 dark:text-red-400 rounded-lg">
            <Lock size={24} />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-50">Action Required</h3>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Please enter your super admin action password to confirm this sensitive operation.</p>
        <form onSubmit={executePendingAction}>
          <input
            type="password"
            required
            autoFocus
            placeholder="Enter Action Password"
            className="w-full bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 mb-4 text-slate-950 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={actionPassword}
            onChange={(e) => setActionPassword(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => { setPasswordModalOpen(false); setActionPassword(""); setPendingAction(null); }}
              className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-750 dark:text-slate-300 font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white font-medium transition"
            >
              Confirm Action
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
