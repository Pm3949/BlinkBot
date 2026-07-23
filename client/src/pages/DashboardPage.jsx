import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import KPIGrid from "../components/dashboard/KPIGrid";
import QuickActions from "../components/dashboard/QuickActions";
import RecentAgents from "../components/dashboard/RecentAgents";
import ActivityFeed from "../components/dashboard/ActivityFeed";
import { useAuth } from "../context/AuthContext";
import { useAgents, useAgentProjects } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import { useAnalytics } from "../hooks/useAnalytics";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import {
  Bot,
  ShieldCheck,
  Activity,
  Globe,
  MessageCircle,
  Sparkles,
  ArrowUpRight,
  TrendingUp,
} from "lucide-react";

function greeting() {
  const hr = new Date().getHours();
  if (hr < 5) return "Good night";
  if (hr < 12) return "Good morning";
  if (hr < 17) return "Good afternoon";
  return "Good evening";
}

const fadeUp = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((s) => s.activeWorkspaceId);
  const { sessions = [] } = useChat();
  const [activeTab, setActiveTab] = useState("widget");

  const setCreateAgentWizardOpen = useUIStore((s) => s.setCreateAgentWizardOpen);

  const { data: agents = [], isLoading: isLoadingAgents } = useAgents(activeWorkspaceId, true);
  const { data: projects = [] } = useAgentProjects(activeWorkspaceId);
  const { data: analyticsData, isLoading: isLoadingAnalytics } = useAnalytics();

  const totalMessages = sessions.reduce((n, s) => n + (s.messages?.length || 0), 0);

  const metrics = analyticsData?.metrics || {};
  const internalSeries = analyticsData?.internalSeries || [];
  const widgetSeries = analyticsData?.widgetSeries || [];

  const totalAgents = metrics.totalAgents ?? agents.length;
  const storageUsedMB = metrics.storageUsedMB ?? 0;
  const totalWidgetMessages = metrics.totalWidgetMessages ?? 0;
  const totalDocs = metrics.totalDocuments ?? 0;

  const userName = user?.email?.split("@")[0] || "Builder";

  const chartData = activeTab === "widget" ? widgetSeries : internalSeries;
  const hasData = chartData.length > 0;

  return (
    <div className="space-y-6 pb-12">

      {/* ── Hero Banner ─────────────────────────────────────── */}
      <motion.div
        {...fadeUp}
        transition={{ duration: 0.5 }}
        className="relative overflow-hidden rounded-3xl border border-border/60 p-7"
        style={{
          background: "linear-gradient(135deg, rgba(255,77,0,0.07) 0%, rgba(255,77,0,0.02) 60%, transparent 100%)",
          boxShadow: "0 2px 20px rgba(255,77,0,0.06)",
        }}
      >
        {/* Decorative blobs */}
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-30"
          style={{ background: "radial-gradient(circle, rgba(255,77,0,0.25) 0%, transparent 70%)" }}
        />
        <div
          className="pointer-events-none absolute right-40 bottom-0 h-32 w-32 rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, rgba(255,122,61,0.3) 0%, transparent 70%)" }}
        />

        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div
                className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full"
                style={{ background: "rgba(255,77,0,0.1)", color: "var(--primary)" }}
              >
                <ShieldCheck size={12} />
                Workspace Active
              </div>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
              {greeting()},{" "}
              <span style={{ color: "var(--primary)" }}>{userName}</span>! 👋
            </h1>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg leading-relaxed">
              Welcome back to your BlinkBot hub. Your agents are live and ready, 
              check performance, review activity, or build something new.
            </p>
          </div>

          {/* CTA */}
          <Link
            to="/studio"
            className="group self-start sm:self-auto flex items-center gap-2.5 px-5 py-3 rounded-2xl text-white text-sm font-bold transition-all shrink-0"
            style={{
              background: "linear-gradient(135deg, #FF4D00, #ff7a3d)",
              boxShadow: "0 4px 20px rgba(255,77,0,0.35)",
            }}
          >
            <Sparkles size={15} className="group-hover:rotate-12 transition-transform" />
            Create Agent
            <ArrowUpRight size={14} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </Link>
        </div>
      </motion.div>

      {/* ── KPI Cards ───────────────────────────────────────── */}
      <motion.div {...fadeUp} transition={{ duration: 0.5, delay: 0.08 }}>
        <KPIGrid
          activeAgentsCount={totalAgents}
          conversationsCount={sessions.length}
          messagesCount={totalMessages}
          networksCount={projects.length}
          documentsCount={totalDocs}
          storageUsedMB={storageUsedMB}
          widgetMessagesCount={totalWidgetMessages}
          isLoadingAgents={isLoadingAgents || isLoadingAnalytics}
          internalSeries={internalSeries}
          widgetSeries={widgetSeries}
        />
      </motion.div>

      {/* ── Main Grid ────────────────────────────────────────── */}
      <div className="grid lg:grid-cols-3 gap-5">

        {/* Left 2/3 — Charts + Activity */}
        <div className="lg:col-span-2 space-y-5">

          {/* Usage & Traffic Chart */}
          <motion.div
            {...fadeUp}
            transition={{ duration: 0.45, delay: 0.15 }}
            className="rounded-3xl border border-border/60 bg-card p-6"
            style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}
          >
            {/* Chart header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="font-bold text-base text-foreground flex items-center gap-2">
                  <TrendingUp size={16} style={{ color: "var(--primary)" }} />
                  Usage & Traffic
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Last 30 days · {activeTab === "widget" ? "Widget API" : "Internal App"}
                </p>
              </div>

              {/* Tab toggle */}
              <div
                className="flex p-1 rounded-xl border border-border/60 gap-1"
                style={{ background: "rgba(0,0,0,0.02)" }}
              >
                {[
                  { id: "widget", label: "Widget", icon: Globe },
                  { id: "internal", label: "Internal", icon: MessageCircle },
                ].map(({ id, label, icon: TabIcon }) => (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all"
                    style={
                      activeTab === id
                        ? {
                            background: "var(--primary)",
                            color: "#fff",
                            boxShadow: "0 2px 8px rgba(255,77,0,0.3)",
                          }
                        : { color: "var(--muted-foreground)" }
                    }
                  >
                    <TabIcon size={12} />
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Chart */}
            {isLoadingAnalytics ? (
              <div className="h-64 w-full">
                <LoadingSkeleton count={1} className="h-full rounded-2xl" />
              </div>
            ) : hasData ? (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  {activeTab === "widget" ? (
                    <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                      <defs>
                        <linearGradient id="widgetGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#FF4D00" stopOpacity={0.18} />
                          <stop offset="95%" stopColor="#FF4D00" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                      <XAxis
                        dataKey="date"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "12px",
                          fontSize: "12px",
                          boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
                        }}
                        cursor={{ stroke: "var(--border)", strokeWidth: 1 }}
                      />
                      <Area
                        type="monotone"
                        dataKey="messages"
                        name="Widget Messages"
                        stroke="#FF4D00"
                        strokeWidth={2.5}
                        fill="url(#widgetGrad)"
                        dot={false}
                        activeDot={{ r: 5, fill: "#FF4D00", stroke: "#fff", strokeWidth: 2 }}
                      />
                    </AreaChart>
                  ) : (
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                      <defs>
                        <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#FF4D00" stopOpacity={0.9} />
                          <stop offset="100%" stopColor="#ff7a3d" stopOpacity={0.7} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                      <XAxis
                        dataKey="date"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "12px",
                          fontSize: "12px",
                          boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
                        }}
                        cursor={{ fill: "rgba(255,77,0,0.06)" }}
                      />
                      <Bar
                        dataKey="messages"
                        name="Internal Chats"
                        fill="url(#barGrad)"
                        radius={[6, 6, 0, 0]}
                      />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center rounded-2xl border border-dashed border-border text-center text-sm text-muted-foreground gap-2">
                <Activity size={24} className="opacity-30" />
                <p>No data yet for the last 30 days.</p>
                <p className="text-xs">Start chatting with agents to see usage here.</p>
              </div>
            )}
          </motion.div>

          {/* Activity Feed */}
          <motion.div {...fadeUp} transition={{ duration: 0.45, delay: 0.2 }}>
            <ActivityFeed agents={agents} sessions={sessions} />
          </motion.div>
        </div>

        {/* Right 1/3 — Sidebar */}
        <div className="space-y-5">
          <motion.div {...fadeUp} transition={{ duration: 0.45, delay: 0.18 }}>
            <QuickActions onCreateAgent={() => setCreateAgentWizardOpen(true)} />
          </motion.div>
          <motion.div {...fadeUp} transition={{ duration: 0.45, delay: 0.24 }}>
            <RecentAgents agents={agents} isLoading={isLoadingAgents} />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
