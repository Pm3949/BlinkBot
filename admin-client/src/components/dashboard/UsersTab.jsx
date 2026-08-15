import React from 'react';

export default function UsersTab({
  usersData,
  usersLoading,
  userSearch,
  setUserSearch,
  updateSubMutation,
  updateSuperAdminMutation,
  currentUser,
  requirePassword,
}) {
  const filteredUsers = usersData?.users?.filter((u) =>
    u.email?.toLowerCase().includes(userSearch.toLowerCase())
  );

  return (
    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Platform Users</h2>
          <span className="text-xs font-semibold px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full">
            {filteredUsers?.length || 0} / {usersData?.users?.length || 0} Registered
          </span>
        </div>
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search users..."
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white dark:focus:bg-slate-900 transition-all"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-6 py-4">User</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Joined</th>
              <th className="px-6 py-4">Subscription Plan</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {usersLoading && (
              <tr>
                <td colSpan={5} className="p-6">
                  <div className="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-md h-12 w-full"></div>
                </td>
              </tr>
            )}
            {!usersLoading && filteredUsers?.length === 0 && (
              <tr>
                <td colSpan={5} className="p-12 text-center text-slate-400 dark:text-slate-500 font-medium text-sm">
                  No users matched your search term.
                </td>
              </tr>
            )}
            {filteredUsers?.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-200">
                  {u.email}
                  {u.is_super_admin && (
                    <span className="ml-2 text-[10px] bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900 px-2 py-0.5 rounded uppercase font-bold">
                      Admin
                    </span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span className="bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900 px-2.5 py-0.5 rounded-full text-xs font-semibold">
                    Active
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-500 dark:text-slate-400">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                    u.plan_tier === 'Enterprise'
                      ? 'bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border-purple-100 dark:border-purple-900'
                      : u.plan_tier === 'Pro'
                      ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-900'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200/50 dark:border-slate-700'
                  }`}>
                    {u.plan_tier}
                  </span>
                </td>
                <td className="px-6 py-4 flex items-center gap-2">
                  <select
                    className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs rounded px-2.5 py-1 font-semibold text-slate-700 dark:text-slate-300 disabled:opacity-50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    value={u.plan_tier}
                    disabled={updateSubMutation.isPending}
                    onChange={(e) =>
                      requirePassword((pwd) =>
                        updateSubMutation.mutate({ targetUserId: u.id, newPlan: e.target.value, password: pwd })
                      )
                    }
                  >
                    <option value="Starter">Starter</option>
                    <option value="Pro">Pro</option>
                    <option value="Enterprise">Enterprise</option>
                  </select>
                  <button
                    disabled={updateSuperAdminMutation.isPending || u.id === currentUser.id}
                    onClick={() =>
                      requirePassword((pwd) =>
                        updateSuperAdminMutation.mutate({
                          targetUserId: u.id,
                          isSuperAdmin: !u.is_super_admin,
                          password: pwd,
                        })
                      )
                    }
                    className="px-3 py-1 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs font-semibold rounded border border-slate-200 dark:border-slate-700 disabled:opacity-50 transition-colors text-slate-700 dark:text-slate-300"
                  >
                    {u.is_super_admin ? 'Revoke Admin' : 'Make Admin'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
