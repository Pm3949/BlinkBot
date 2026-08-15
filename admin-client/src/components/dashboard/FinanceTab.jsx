import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { CreditCard, Briefcase, Activity, Plus, X } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { toast } from 'sonner';

export default function FinanceTab({ API_URL }) {
  const [financeInterval, setFinanceInterval] = useState('monthly');
  const [expenseModalOpen, setExpenseModalOpen] = useState(false);
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDesc, setExpenseDesc] = useState('');
  const [expenseCategory, setExpenseCategory] = useState('Hosting');

  const { data: financesData, isLoading: financesLoading, refetch: refetchFinances } = useQuery({
    queryKey: ['adminFinances', financeInterval],
    queryFn: async () => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/finances?interval=${financeInterval}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load admin finances");
      return res.json();
    }
  });

  const createExpenseMutation = useMutation({
    mutationFn: async (payload) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/expenses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to record expense");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Platform expense recorded successfully!");
      setExpenseModalOpen(false);
      setExpenseAmount('');
      setExpenseDesc('');
      refetchFinances();
    },
    onError: (err) => toast.error(err.message)
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Financial Overview stats */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl shadow-sm gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">Platform Finances</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-medium">Aggregate breakdown of organic checkout sales vs manual platform expenses.</p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <select
            value={financeInterval}
            onChange={(e) => setFinanceInterval(e.target.value)}
            className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold px-3 py-2 text-slate-750 dark:text-slate-200 focus:outline-none"
          >
            <option value="monthly">Monthly Intervals</option>
            <option value="yearly">Yearly Intervals</option>
          </select>
          <button
            onClick={() => setExpenseModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 text-white text-xs font-bold rounded-lg transition shadow-md shadow-emerald-500/10 shrink-0"
          >
            <Plus size={14} /> Record Expense
          </button>
        </div>
      </div>

      {financesLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse bg-slate-100 dark:bg-slate-800 h-32 w-full rounded-xl"></div>
          ))}
        </div>
      ) : (
        <>
          {/* Financial KPI stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-slate-900 p-6 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center gap-4 shadow-sm">
              <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                <CreditCard className="w-8 h-8" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Revenue</p>
                <h3 className="text-3xl font-extrabold text-slate-900 dark:text-slate-100 mt-1">₹{(financesData?.report?.totalRevenue || 0).toLocaleString()}</h3>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900 p-6 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center gap-4 shadow-sm">
              <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400">
                <Briefcase className="w-8 h-8" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total Expenses</p>
                <h3 className="text-3xl font-extrabold text-slate-900 dark:text-slate-100 mt-1">₹{(financesData?.report?.totalExpenses || 0).toLocaleString()}</h3>
              </div>
            </div>
            <div className="bg-white dark:bg-slate-900 p-6 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center gap-4 shadow-sm">
              <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
                <Activity className="w-8 h-8" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Net Profit / Margin</p>
                <h3 className="text-3xl font-extrabold text-slate-900 dark:text-slate-100 mt-1 flex items-baseline gap-2">
                  <span>₹{(financesData?.report?.netProfit || 0).toLocaleString()}</span>
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    ({financesData?.report?.totalRevenue > 0 ? ((financesData.report.netProfit / financesData.report.totalRevenue) * 100).toFixed(0) : 0}%)
                  </span>
                </h3>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Revenue vs Expenses Line/Bar Chart */}
            <div className="lg:col-span-2 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm">
              <h3 className="text-base font-bold mb-6 flex items-center gap-2 text-slate-900 dark:text-slate-100">
                <Activity size={16} className="text-primary" /> Revenue vs Spends Trend
              </h3>
              {financesData?.report?.series?.length > 0 ? (
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={financesData.report.series}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                      <XAxis dataKey="period" stroke="currentColor" className="text-slate-400 dark:text-slate-500" fontSize={11} />
                      <YAxis stroke="currentColor" className="text-slate-400 dark:text-slate-500" fontSize={11} />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }} />
                      <Legend />
                      <Bar dataKey="revenue" name="Revenue (₹)" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="expenses" name="Expenses (₹)" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-80 flex items-center justify-center text-slate-400 dark:text-slate-500 border-2 border-dashed border-slate-250 dark:border-slate-800 rounded-xl">
                  No financial transactions recorded for this range.
                </div>
              )}
            </div>

            {/* Spends Log */}
            <div className="lg:col-span-1 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl p-6 shadow-sm flex flex-col justify-between h-full">
              <div>
                <h3 className="text-base font-bold mb-4 text-slate-900 dark:text-slate-50">Manual Spends Log</h3>
                <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-80 overflow-y-auto pr-1">
                  {!financesData?.expenses || financesData.expenses.length === 0 ? (
                    <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-xs">No manual platform spends recorded.</div>
                  ) : (
                    financesData.expenses.map((exp) => (
                      <div key={exp.id} className="py-3 flex justify-between items-start text-xs">
                        <div>
                          <div className="font-semibold text-slate-900 dark:text-slate-100">{exp.description}</div>
                          <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 flex items-center gap-1.5">
                            <span className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-300 font-bold">{exp.category}</span>
                            <span>{new Date(exp.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="font-bold text-red-500 dark:text-red-400">-₹{exp.amount_inr.toFixed(0)}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Expense Modal */}
      {expenseModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/80 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
            <button
              onClick={() => setExpenseModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
            >
              <X size={20} />
            </button>
            <h3 className="text-lg font-bold mb-4 text-slate-900 dark:text-slate-50">Record Platform Expense</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createExpenseMutation.mutate({
                  amount_inr: parseFloat(expenseAmount),
                  description: expenseDesc,
                  category: expenseCategory
                });
              }}
              className="space-y-4 text-xs font-medium"
            >
              <div>
                <label className="block mb-1 text-slate-700 dark:text-slate-300">Amount (INR)</label>
                <input
                  type="number" required min="1" placeholder="5000"
                  value={expenseAmount} onChange={e => setExpenseAmount(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-750 rounded-lg px-3 py-2 text-sm font-bold text-slate-900 dark:text-slate-50"
                />
              </div>
              <div>
                <label className="block mb-1 text-slate-750 dark:text-slate-300">Description</label>
                <input
                  type="text" required placeholder="AWS EC2 hosting invoice"
                  value={expenseDesc} onChange={e => setExpenseDesc(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-750 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-slate-50"
                />
              </div>
              <div>
                <label className="block mb-1 text-slate-700 dark:text-slate-300">Category</label>
                <select
                  value={expenseCategory} onChange={e => setExpenseCategory(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-750 rounded-lg px-3 py-2 text-sm font-bold text-slate-700 dark:text-slate-200"
                >
                  <option value="Hosting">Hosting / Servers</option>
                  <option value="API Cost">LLM API Invoices</option>
                  <option value="Marketing">Marketing / ADS</option>
                  <option value="Salary">Developer Salaries</option>
                  <option value="Other">Other Expenses</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button" onClick={() => setExpenseModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-750 dark:text-slate-300 font-bold text-sm transition"
                >
                  Cancel
                </button>
                <button
                  type="submit" disabled={createExpenseMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600 text-white text-sm font-bold transition disabled:opacity-50"
                >
                  {createExpenseMutation.isPending ? "Recording..." : "Record Expense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
