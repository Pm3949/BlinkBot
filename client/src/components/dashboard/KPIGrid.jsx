import { Bot, HardDrive, Network, MessageCircle, Globe, Zap } from "lucide-react";
import KPICard from "./KPICard";

export default function KPIGrid({
  activeAgentsCount = 0,
  conversationsCount = 0,
  messagesCount = 0,
  networksCount = 0,
  documentsCount = 0,
  storageUsedMB = 0,
  widgetMessagesCount = 0,
  isLoadingAgents = false,
  internalSeries = [],
  widgetSeries = [],
}) {
  const internalSpark =
    internalSeries.length > 0
      ? internalSeries.slice(-8).map((d) => d.messages)
      : [2, 5, 3, 8, 4, 10, 6, 12];

  const widgetSpark =
    widgetSeries.length > 0
      ? widgetSeries.slice(-8).map((d) => d.messages)
      : [10, 22, 15, 30, 25, 45, 38, 60];

  const cards = [
    {
      title: "Active Agents",
      value: isLoadingAgents ? "—" : activeAgentsCount.toLocaleString(),
      change: `${networksCount.toLocaleString()} networks deployed`,
      icon: Bot,
      accent: "primary",
      sparklineData: [1, 2, 2, activeAgentsCount || 1, activeAgentsCount || 2, activeAgentsCount || 3, activeAgentsCount || 4, activeAgentsCount || 5],
    },
    {
      title: "Chat Sessions",
      value: isLoadingAgents ? "—" : `${conversationsCount.toLocaleString()}`,
      change: `${messagesCount.toLocaleString()} total messages`,
      icon: MessageCircle,
      accent: "violet",
      sparklineData: internalSpark,
    },
    {
      title: "Widget Traffic",
      value: isLoadingAgents ? "—" : widgetMessagesCount.toLocaleString(),
      change: "Public widget messages",
      icon: Globe,
      accent: "cyan",
      sparklineData: widgetSpark,
    },
    {
      title: "Knowledge Base",
      value: isLoadingAgents ? "—" : `${storageUsedMB.toFixed(1)} MB`,
      change: `${documentsCount.toLocaleString()} source documents`,
      icon: HardDrive,
      accent: "emerald",
      sparklineData: [10, 14, 12, 18, 20, 22, 25, storageUsedMB || 2],
    },
  ];

  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <KPICard key={card.title} {...card} index={i} />
      ))}
    </div>
  );
}
