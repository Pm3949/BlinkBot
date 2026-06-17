import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { supabase } from '../supabaseClient';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Activity, MessageSquare, Database, Cpu, Bot } from 'lucide-react';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

async function fetchAnalytics() {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Not authenticated");

  const response = await fetch(`${API_URL}/analytics/${user.id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch analytics');
  }
  return response.json();
}

const MetricCard = ({ title, value, icon: Icon, colorClass }) => (
  <div className="glass-card p-6 flex items-center gap-4 border border-border/50">
    <div className={`p-4 rounded-xl ${colorClass}`}>
      <Icon className="w-8 h-8" />
    </div>
    <div>
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      <h3 className="text-3xl font-extrabold text-foreground mt-1">{value}</h3>
    </div>
  </div>
);

export default function AnalyticsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics'],
    queryFn: fetchAnalytics,
  });

  if (isLoading) {
    return (
      <div className="space-y-8 max-w-7xl mx-auto pb-10">
        <h1 className="text-3xl font-bold">Analytics & Usage</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => <LoadingSkeleton key={i} count={1} className="h-32" />)}
        </div>
        <LoadingSkeleton count={1} className="h-96" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-500 glass-card">
        <p>Error loading analytics: {error.message}</p>
      </div>
    );
  }

  const { metrics, internalSeries, widgetSeries, topChatbots } = data;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-10">

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
          <Activity className="text-primary" /> Analytics & Usage
        </h1>
        <p className="text-muted-foreground mt-2">Monitor your agent usage, storage, and widget interactions over the last 30 days.</p>
      </div>

      {/* Top Level Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Internal Agents"
          value={metrics.totalAgents}
          icon={Cpu}
          colorClass="bg-blue-500/10 text-blue-500"
        />
        <MetricCard
          title="Documents Processed"
          value={metrics.totalDocuments}
          icon={Database}
          colorClass="bg-indigo-500/10 text-indigo-500"
        />
        <MetricCard
          title="Vector Storage"
          value={`${metrics.storageUsedMB} MB`}
          icon={Activity}
          colorClass="bg-purple-500/10 text-purple-500"
        />
        <MetricCard
          title="All-Time Widget Msgs"
          value={metrics.totalWidgetMessages}
          icon={MessageSquare}
          colorClass="bg-green-500/10 text-green-500"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">

        {/* Main Chart Area */}
        <div className="lg:col-span-2 space-y-8">

          {/* Widget Messages Chart */}
          <div className="glass-card p-6 border border-border/50">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Globe className="w-5 h-5 text-green-500" /> Widget Messages (30 Days)
            </h3>
            {widgetSeries.length > 0 ? (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={widgetSeries} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                      itemStyle={{ color: 'hsl(var(--foreground))' }}
                    />
                    <Line type="monotone" dataKey="messages" stroke="#22c55e" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-80 flex items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                No widget message data available for the last 30 days.
              </div>
            )}
          </div>

          {/* Internal Messages Chart */}
          <div className="glass-card p-6 border border-border/50">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-500" /> Internal Agent Usage (30 Days)
            </h3>
            {internalSeries.length > 0 ? (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={internalSeries} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                      cursor={{ fill: 'hsl(var(--muted))', opacity: 0.4 }}
                    />
                    <Bar dataKey="messages" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-80 flex items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                No internal messages available for the last 30 days.
              </div>
            )}
          </div>

        </div>

        {/* Sidebar Panel */}
        <div className="lg:col-span-1 space-y-8">

          {/* Top Chatbots */}
          <div className="glass-card p-6 border border-border/50">
            <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
              <Bot className="text-primary" /> Top Performing Widgets
            </h3>

            {topChatbots.length > 0 ? (
              <div className="space-y-4">
                {topChatbots.map((bot, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border/50">
                    <span className="font-medium text-sm">{bot.name}</span>
                    <span className="bg-primary/20 text-primary px-2 py-1 rounded text-xs font-bold">
                      {bot.messages} msgs
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No chatbots created yet.
              </p>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}

// Ensure Globe is imported correctly
import { Globe } from 'lucide-react';
