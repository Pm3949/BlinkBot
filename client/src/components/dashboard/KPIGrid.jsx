import {
  Bot,
  Database,
  Network,
  Brain,
  HardDrive,
  MessageCircle,
} from "lucide-react";

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
  // Generate sparkline values from actual message counts if available
  const internalSpark = internalSeries.length > 0 
    ? internalSeries.slice(-7).map(d => d.messages) 
    : [2, 5, 8, 4, 10, 6, 12];

  const widgetSpark = widgetSeries.length > 0 
    ? widgetSeries.slice(-7).map(d => d.messages) 
    : [10, 22, 15, 30, 25, 45, 60];

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <KPICard
        title="Active Agents"
        value={
          isLoadingAgents
            ? "..."
            : activeAgentsCount.toLocaleString()
        }
        change={`${networksCount.toLocaleString()} networks active`}
        icon={Bot}
        sparklineData={[1, 2, 2, activeAgentsCount || 1, activeAgentsCount || 2, activeAgentsCount || 3, activeAgentsCount || 4]}
      />

      <KPICard
        title="Conversations & Messages"
        value={`${conversationsCount.toLocaleString()} chats`}
        change={`${messagesCount.toLocaleString()} messages`}
        icon={MessageCircle}
        sparklineData={internalSpark}
      />

      <KPICard
        title="Widget Traffic"
        value={`${widgetMessagesCount.toLocaleString()}`}
        change="Widget messages all-time"
        icon={Network}
        sparklineData={widgetSpark}
      />

      <KPICard
        title="Vector Database Storage"
        value={`${storageUsedMB.toFixed(2)} MB`}
        change={`${documentsCount.toLocaleString()} source docs`}
        icon={HardDrive}
        sparklineData={[10, 15, 12, 18, 20, 25, storageUsedMB || 2]}
      />
    </div>
  );
}

