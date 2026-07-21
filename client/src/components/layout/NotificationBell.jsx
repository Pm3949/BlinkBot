import React, { useState, useEffect, useRef } from "react";
import { Bell, Check, Trash2 } from "lucide-react";
import { supabase } from "../../supabaseClient";
import { toast } from "sonner";
import { useUIStore } from "../../store/useUIStore";
import { getAuthHeaders } from "../../lib/api";

export default function NotificationBell() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;

    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

    // Fetch initial notifications
    const fetchNotifications = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/notifications?workspace_id=${activeWorkspaceId}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          const data = await res.json();
          setNotifications(data);
        }
      } catch (err) {
        console.error("Failed to fetch notifications", err);
      }
    };
    fetchNotifications();

    // Subscribe to backend WebSocket notifications channel
    const wsBaseUrl = API_BASE.replace(/^http/, "ws");
    const ws = new WebSocket(`${wsBaseUrl}/ws/notifications/${activeWorkspaceId}`);

    ws.onmessage = (event) => {
      try {
        const newNotification = JSON.parse(event.data);
        setNotifications((prev) => [newNotification, ...prev]);
        toast.info(newNotification.title, {
          description: newNotification.message
        });
      } catch (err) {
        console.error("Failed to parse incoming notification", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [activeWorkspaceId]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markAsRead = async (id) => {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      await fetch(`${API_BASE}/api/notifications/${id}/read`, {
        method: "PUT",
        headers: getAuthHeaders()
      });
      setNotifications(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  const markAllAsRead = async () => {
    for (const n of notifications) {
      await markAsRead(n.id);
    }
    toast.success("All notifications cleared");
  };

  const unreadCount = notifications.length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`
          relative
          h-11
          w-11
          rounded-xl
          border
          border-border
          text-muted-foreground
          flex
          items-center
          justify-center
          transition-all
          ${isOpen ? "bg-muted text-foreground" : "hover:bg-muted hover:text-foreground"}
        `}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            className="
              absolute
              top-2
              right-2
              h-2.5
              w-2.5
              rounded-full
              bg-red-500
              border-2
              border-background
            "
          />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-[340px] bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
            <h3 className="font-semibold flex items-center gap-2">
              Notifications 
              {unreadCount > 0 && (
                <span className="bg-primary/10 text-primary text-xs px-2 py-0.5 rounded-full">{unreadCount} new</span>
              )}
            </h3>
            {unreadCount > 0 && (
              <button 
                onClick={markAllAsRead}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
              >
                <Check size={12}/> Mark all read
              </button>
            )}
          </div>
          
          <div className="max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-10 text-center text-muted-foreground text-sm flex flex-col items-center">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
                  <Bell size={20} className="opacity-50"/>
                </div>
                You're all caught up!
              </div>
            ) : (
              <div className="flex flex-col">
                {notifications.map((n) => (
                  <div key={n.id} className="p-4 border-b border-border hover:bg-muted/30 transition-colors relative group">
                    <div className="flex justify-between items-start mb-1 gap-2">
                      <span className="font-semibold text-sm leading-tight text-foreground">{n.title}</span>
                      <button 
                        onClick={() => markAsRead(n.id)}
                        className="text-muted-foreground hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 -mr-1.5 -mt-1.5 rounded-lg hover:bg-red-500/10 shrink-0"
                        title="Dismiss"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed mt-1">{n.message}</p>
                    <span className="text-[10px] text-muted-foreground/50 mt-2.5 block font-medium uppercase tracking-wider">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
