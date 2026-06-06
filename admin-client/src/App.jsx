import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from './supabaseClient';
import { ShieldAlert, Users, Database, Globe, Bot, ShieldCheck, Activity } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function LoadingSkeleton({ className }) {
  return <div className={`animate-pulse bg-muted rounded-md ${className}`}></div>;
}

async function fetchAdminStats(user) {
  const res = await fetch(`${API_URL}/admin/stats?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin stats");
  return res.json();
}

async function fetchAdminUsers(user) {
  const res = await fetch(`${API_URL}/admin/users?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin users");
  return res.json();
}

export default function App() {
  const queryClient = useQueryClient();
  const [currentUser, setCurrentUser] = useState(null);

  // Fetch current user
  React.useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setCurrentUser(user));
  }, []);

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['adminStats'],
    queryFn: () => fetchAdminStats(currentUser),
    enabled: !!currentUser,
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: () => fetchAdminUsers(currentUser),
    enabled: !!currentUser,
  });

  const updateSubMutation = useMutation({
    mutationFn: async ({ targetUserId, newPlan }) => {
      const res = await fetch(`${API_URL}/admin/users/${targetUserId}/subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_tier: newPlan, admin_user_id: currentUser.id })
      });
      if (!res.ok) throw new Error("Failed to update subscription");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Subscription updated successfully!");
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      toast.error(error.message);
    } else {
      toast.success("Logged in successfully!");
      // The auth listener will automatically update the currentUser
      const { data: { user } } = await supabase.auth.getUser();
      setCurrentUser(user);
    }
    setIsLoggingIn(false);
  };

  if (!currentUser) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="border border-border/50 rounded-xl p-8 max-w-md w-full bg-card shadow-2xl">
          <div className="flex justify-center mb-6">
            <ShieldCheck className="text-primary w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-center mb-2">Admin Portal</h2>
          <p className="text-muted-foreground text-center mb-8 text-sm">Please sign in with your Super Admin credentials</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input 
                type="email" 
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-muted border border-border rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <input 
                type="password" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-muted border border-border rounded-lg px-4 py-2"
              />
            </div>
            <button 
              type="submit" 
              disabled={isLoggingIn}
              className="w-full bg-primary text-primary-foreground font-bold py-2 rounded-lg mt-4 disabled:opacity-50"
            >
              {isLoggingIn ? "Signing In..." : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen space-y-4 bg-background">
        <ShieldAlert size={48} className="text-red-500" />
        <h2 className="text-2xl font-bold text-foreground">Access Denied</h2>
        <p className="text-muted-foreground">You do not have Super Admin privileges.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto space-y-8 pb-10">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <ShieldCheck className="text-primary w-8 h-8" />
            Super Admin Portal
          </h1>
          <p className="text-muted-foreground mt-2">Manage the entire platform across all users and workspaces.</p>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title="Total Users" value={stats?.totalUsers} icon={Users} loading={statsLoading} />
          <StatCard title="Workspaces" value={stats?.totalWorkspaces} icon={Activity} loading={statsLoading} />
          <StatCard title="Total Agents" value={stats?.totalAgents} icon={Bot} loading={statsLoading} />
          <StatCard title="Chatbots" value={stats?.totalChatbots} icon={Globe} loading={statsLoading} />
          <StatCard title="DB Storage" value={stats ? `${stats.totalStorageMB} MB` : null} icon={Database} loading={statsLoading} />
        </div>

        {/* User Management Table */}
        <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
          <div className="p-6 border-b border-border/50 flex items-center justify-between">
            <h2 className="text-xl font-bold">Platform Users</h2>
            <span className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full">
              {usersData?.users?.length || 0} Registered
            </span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs uppercase text-muted-foreground bg-muted/50 border-b border-border/50">
                <tr>
                  <th className="px-6 py-4">User</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Joined</th>
                  <th className="px-6 py-4">Subscription Plan</th>
                  <th className="px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersLoading && (
                  <tr><td colSpan={5} className="p-6"><LoadingSkeleton className="h-12 w-full" /></td></tr>
                )}
                {usersData?.users?.map((u) => (
                  <tr key={u.id} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="px-6 py-4 font-medium">
                      {u.email}
                      {u.is_super_admin && <span className="ml-2 text-[10px] bg-red-500/10 text-red-500 px-2 py-0.5 rounded uppercase font-bold">Admin</span>}
                    </td>
                    <td className="px-6 py-4">
                      <span className="bg-green-500/10 text-green-500 px-2 py-1 rounded text-xs font-semibold">Active</span>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        u.plan_tier === 'Enterprise' ? 'bg-purple-500/20 text-purple-500' :
                        u.plan_tier === 'Pro' ? 'bg-blue-500/20 text-blue-500' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {u.plan_tier}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <select 
                        className="bg-muted border border-border text-xs rounded px-2 py-1 disabled:opacity-50"
                        value={u.plan_tier}
                        disabled={updateSubMutation.isPending}
                        onChange={(e) => updateSubMutation.mutate({ targetUserId: u.id, newPlan: e.target.value })}
                      >
                        <option value="Starter">Starter</option>
                        <option value="Pro">Pro</option>
                        <option value="Enterprise">Enterprise</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, loading }) {
  return (
    <div className="p-5 border border-border/50 rounded-xl bg-card">
      <div className="flex items-center gap-3 mb-2 text-muted-foreground">
        <Icon size={18} />
        <span className="text-sm font-medium">{title}</span>
      </div>
      {loading ? (
        <LoadingSkeleton className="h-8 w-20" />
      ) : (
        <h3 className="text-2xl font-extrabold">{value}</h3>
      )}
    </div>
  );
}
