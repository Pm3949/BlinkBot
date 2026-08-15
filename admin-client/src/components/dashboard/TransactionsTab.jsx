import React, { useState } from 'react';
import { toast } from 'sonner';

export default function TransactionsTab({ transactionsData, transactionsLoading, API_URL }) {
  const [expandedTransactions, setExpandedTransactions] = useState({});

  const toggleExpand = (id) => {
    setExpandedTransactions(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Platform Transactions</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Audit log of all payments, subscription checkouts, and wallet recharges across the platform.</p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider font-bold bg-slate-50 dark:bg-slate-800/40">
              <th className="px-6 py-4">Invoice Number</th>
              <th className="px-6 py-4">User</th>
              <th className="px-6 py-4">Description</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Date</th>
              <th className="px-6 py-4 text-right">Receipt</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-150 dark:divide-slate-800/60">
            {transactionsLoading ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400 dark:text-slate-500 font-semibold bg-white dark:bg-slate-900">Loading transactions...</td>
              </tr>
            ) : !transactionsData?.transactions || transactionsData.transactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400 dark:text-slate-500 font-semibold bg-white dark:bg-slate-900">No platform transactions found.</td>
              </tr>
            ) : (
              transactionsData.transactions.map((tx) => (
                <React.Fragment key={tx.id}>
                  <tr 
                    onClick={() => toggleExpand(tx.id)}
                    className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                      <div className="font-mono text-xs font-semibold text-slate-900 dark:text-slate-200">{tx.invoice_number}</div>
                      {tx.metadata?.razorpay_payment_id && (
                        <div className="font-mono text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 flex items-center gap-1">
                          <span>TxID: {tx.metadata.razorpay_payment_id}</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(tx.metadata.razorpay_payment_id);
                              toast.success("Transaction ID copied!");
                            }}
                            className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                        <span className="font-medium text-xs truncate max-w-[150px]" title={tx.user_email}>{tx.user_email}</span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(tx.user_email);
                            toast.success("Email copied!");
                          }}
                          className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition shrink-0"
                          title="Copy Email"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-semibold text-slate-800 dark:text-slate-200">{tx.description}</td>
                    <td className="px-6 py-4 font-bold text-xs text-slate-900 dark:text-slate-100">₹{tx.amount_inr.toFixed(2)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        tx.status === 'Paid'
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900'
                          : 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border-amber-100 dark:border-amber-900'
                      }`}>
                        {tx.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {new Date(tx.created_at).toLocaleDateString(undefined, {
                        year: 'numeric', month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </td>
                    <td className="px-6 py-4 text-right" onClick={e => e.stopPropagation()}>
                      <button
                        onClick={async () => {
                          try {
                            toast.info("Downloading PDF receipt...");
                            const token = localStorage.getItem('adminToken');
                            const response = await fetch(`${API_URL}/api/billing/invoice/${tx.id}/download`, {
                              headers: { "Authorization": `Bearer ${token}` }
                            });
                            if (!response.ok) throw new Error("Receipt download failed");
                            const blob = await response.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `invoice-${tx.invoice_number}.pdf`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            toast.success("Receipt downloaded successfully!");
                          } catch (err) {
                            toast.error(err.message || "Failed to download receipt");
                          }
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-indigo-50 dark:bg-indigo-950 hover:bg-indigo-100 dark:hover:bg-indigo-900 text-indigo-600 dark:text-indigo-400 text-xs font-bold rounded-lg transition"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                        Receipt
                      </button>
                    </td>
                  </tr>
                  {expandedTransactions[tx.id] && (
                    <tr className="bg-slate-50/50 dark:bg-slate-950/20">
                      <td colSpan={7} className="px-8 py-4 border-t border-b border-slate-200/60 dark:border-slate-800/60">
                        <div className="space-y-2">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                            Razorpay API Metadata Payload
                          </div>
                          <pre className="text-[10px] bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 p-4 rounded-xl font-mono overflow-x-auto text-slate-500 dark:text-slate-400 whitespace-pre-wrap max-w-full">
                            {JSON.stringify(tx.metadata, null, 2)}
                          </pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
