import React from 'react';

export default function StatCard({ title, value, icon: Icon, loading }) {
  return (
    <div className="p-5 border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-200">
      <div className="flex items-center gap-2 mb-3 text-slate-500 dark:text-slate-400">
        <div className="p-1.5 bg-slate-50 dark:bg-slate-800 rounded-lg text-slate-400 dark:text-slate-500">
          <Icon size={18} />
        </div>
        <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
      </div>
      {loading ? (
        <div className="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-md h-8 w-20"></div>
      ) : (
        <h3 className="text-3xl font-extrabold text-slate-900 dark:text-slate-50">{value}</h3>
      )}
    </div>
  );
}
