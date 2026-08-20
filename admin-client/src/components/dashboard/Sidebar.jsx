import React from 'react';
import { ShieldCheck, Briefcase, Users, ShieldAlert, Calendar as CalendarIcon, Bot, Activity, CreditCard, LogOut, Sun, Moon, Newspaper } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, currentUser, handleLogout, isDarkMode, setIsDarkMode }) {
  const navItems = [
    { id: 'workspaces', label: 'Workspaces', icon: Briefcase },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'demoRequests', label: 'Demo Requests', icon: ShieldAlert },
    { id: 'calendar', label: 'Calendar', icon: CalendarIcon },
    { id: 'models', label: 'System Models', icon: Bot },
    { id: 'analytics', label: 'Usage Analytics', icon: Activity },
    { id: 'transactions', label: 'Transactions', icon: CreditCard },
    { id: 'finance', label: 'Finance Dashboard', icon: Briefcase },
    { id: 'blogs', label: 'Blog Posts', icon: Newspaper },
  ];

  return (
    <aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between shrink-0 sticky top-0 h-screen">
      <div className="flex flex-col overflow-y-auto">
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-800/60 flex items-center gap-3">
          <div className="p-2 bg-indigo-50 dark:bg-indigo-950 border border-indigo-100 dark:border-indigo-900 rounded-lg text-indigo-600 dark:text-indigo-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="font-bold text-slate-900 dark:text-slate-100 leading-tight">Super Admin</div>
            <div className="text-xs text-slate-400 dark:text-slate-500 font-semibold flex items-center gap-1 mt-0.5">
              <span className="h-1.5 w-1.5 bg-emerald-500 rounded-full animate-pulse" />
              Live Console
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                }`}
              >
                <Icon size={18} className={isActive ? 'text-indigo-600' : 'text-slate-400 dark:text-slate-500'} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Admin User / Logout / Theme Toggle */}
      <div className="p-4 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-950/20 space-y-3">
        {/* Theme Selector */}
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-2 shadow-sm">
          <span className="text-xs text-slate-500 dark:text-slate-400 font-semibold pl-1.5">Theme Mode</span>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-1.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDarkMode ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div className="px-2">
            <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Logged In As</div>
            <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate" title={currentUser.email}>
              {currentUser.email}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white dark:bg-slate-900 hover:bg-red-50 dark:hover:bg-red-950/20 text-slate-600 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400 border border-slate-200 dark:border-slate-800 hover:border-red-200 dark:hover:border-red-900/60 rounded-lg text-xs font-bold transition-all duration-200 shadow-sm"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
