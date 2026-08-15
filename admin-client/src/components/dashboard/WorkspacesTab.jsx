import React from 'react';
import { Briefcase } from 'lucide-react';

export default function WorkspacesTab({ workspacesData, workspacesLoading, workspaceSearch, setWorkspaceSearch }) {
  const filteredWorkspaces = workspacesData?.workspaces?.filter((w) =>
    w.name?.toLowerCase().includes(workspaceSearch.toLowerCase()) ||
    w.owner_email?.toLowerCase().includes(workspaceSearch.toLowerCase())
  );

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Workspaces</h2>
          <span className="text-xs font-semibold px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full">
            {filteredWorkspaces?.length || 0} / {workspacesData?.workspaces?.length || 0} Total
          </span>
        </div>
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search workspaces..."
            value={workspaceSearch}
            onChange={(e) => setWorkspaceSearch(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Owner</th>
              <th className="px-6 py-4">Members</th>
              <th className="px-6 py-4">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {workspacesLoading && (
              <tr>
                <td colSpan={4} className="p-6">
                  <div className="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-md h-12 w-full"></div>
                </td>
              </tr>
            )}
            {!workspacesLoading && filteredWorkspaces?.length === 0 && (
              <tr>
                <td colSpan={4} className="p-12 text-center text-slate-400 dark:text-slate-500 font-medium text-sm">
                  No workspaces matched your search term.
                </td>
              </tr>
            )}
            {filteredWorkspaces?.map((w) => (
              <tr key={w.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-200 flex items-center gap-2">
                  <Briefcase size={16} className="text-indigo-600 dark:text-indigo-400" />
                  {w.name}
                </td>
                <td className="px-6 py-4 text-slate-600 dark:text-slate-300">
                  {w.owner_email || 'Unknown'}
                </td>
                <td className="px-6 py-4">
                  <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-full text-xs font-semibold">
                    {w.member_count}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-500 dark:text-slate-400">
                  {new Date(w.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
