import React from 'react';
import { Bot, Globe } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';

export default function AnalyticsTab({ stats }) {
  return (
    <div className="space-y-8 animate-fadeIn">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">Global Platform Usage</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Telemetry analytics across all wallets, tokens, models, and providers.</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Global Model Usage (Bar Chart) */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm">
          <h3 className="text-base font-bold mb-6 flex items-center gap-2 text-slate-900 dark:text-slate-100">
            <Bot size={16} className="text-indigo-600 dark:text-indigo-400" /> Wallet Credit Burn by Model ID (All-Time)
          </h3>
          {stats?.globalModelUsage?.length > 0 ? (
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.globalModelUsage}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" stroke="currentColor" className="text-slate-400 dark:text-slate-500" fontSize={11} />
                  <YAxis stroke="currentColor" className="text-slate-400 dark:text-slate-500" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }} />
                  <Bar dataKey="credits" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-80 flex items-center justify-center text-slate-400 dark:text-slate-500 border-2 border-dashed border-slate-200 dark:border-slate-805 rounded-xl">
              No system model usage telemetry recorded.
            </div>
          )}
        </div>

        {/* Global API Provider Usage (Pie Chart) */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold mb-6 flex items-center gap-2 text-slate-900 dark:text-slate-100">
              <Globe size={16} className="text-emerald-500 dark:text-emerald-400" /> Share of Credit Usage by Provider
            </h3>
            {stats?.globalProviderUsage?.length > 0 ? (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.globalProviderUsage}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="credits"
                    >
                      {stats.globalProviderUsage.map((entry, index) => {
                        const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#3b82f6'];
                        return <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />;
                      })}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400 dark:text-slate-500 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                No provider credit usage statistics available.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
