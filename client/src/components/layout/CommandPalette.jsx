import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Bot,
  Database,
  MessageSquare,
  BarChart3,
  FileText,
  Plus,
  Settings,
  LayoutDashboard,
  User,
  Building2
} from "lucide-react";
import { useUIStore } from "../../store/useUIStore";

const commands = [
  {
    icon: LayoutDashboard,
    label: "Dashboard",
    shortcut: "H",
    path: "/",
  },
  {
    icon: Plus,
    label: "Create Agent",
    shortcut: "A",
    path: "/agents",
    action: "create-agent",
  },
  {
    icon: MessageSquare,
    label: "Chat",
    shortcut: "C",
    path: "/chat",
  },
  {
    icon: Bot,
    label: "Agents",
    shortcut: "G",
    path: "/agents",
  },

  {
    icon: BarChart3,
    label: "Analytics",
    shortcut: "Y",
    path: "/analytics",
  },
  {
    icon: Settings,
    label: "Workspace Settings",
    shortcut: "S",
    path: "/settings",
  },
];

export default function CommandPalette() {
  const navigate = useNavigate();
  const open = useUIStore((state) => state.commandPaletteOpen);
  const setOpen = useUIStore((state) => state.setCommandPaletteOpen);
  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );
  const [query, setQuery] = useState("");
  
  const isMac = typeof navigator !== "undefined" && /mac|iphone|ipad/i.test(navigator.platform || "");
  const commandShortcut = isMac ? "Cmd K" : "Ctrl K";
  const modifier = isMac ? "⌥" : "Alt"; // Option on Mac, Alt on Windows

  const handleCommand = (command) => {
    navigate(command.path);
    if (command.action === "create-agent") {
      setCreateAgentWizardOpen(true);
    }
    setOpen(false);
    setQuery("");
  };

  useEffect(() => {
    const handler = (e) => {
      // Toggle Command Palette (Cmd+K / Ctrl+K)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        return;
      }

      // Handle individual shortcuts (Alt+Key / Option+Key)
      if (e.altKey) {
        const command = commands.find(
          (cmd) => cmd.shortcut.toLowerCase() === e.key.toLowerCase()
        );
        if (command) {
          e.preventDefault();
          handleCommand(command);
          return;
        }
      }

      // Close Palette on Escape
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handler);

    return () =>
      window.removeEventListener(
        "keydown",
        handler
      );
  }, [open, setOpen]);

  const filteredCommands = useMemo(
    () =>
      commands.filter((command) =>
        command.label.toLowerCase().includes(query.toLowerCase())
      ),
    [query]
  );

  if (!open) return null;

  return (
    <div
      className="
      fixed
      inset-0
      z-[100]
      bg-slate-950/40
      backdrop-blur-sm
      flex
      justify-center
      pt-24
    "
    >
      <div
        className="
        w-full
        max-w-2xl
        bg-white
        dark:bg-zinc-950
        rounded-[32px]
        shadow-2xl
        overflow-hidden
        border
        border-slate-200
        dark:border-zinc-800
      "
      >
        {/* SEARCH */}

        <div className="border-b border-slate-200 p-5 dark:border-zinc-800">
          <div className="relative">
            <Search
              size={20}
              className="
              absolute
              left-4
              top-4
              text-slate-400
              dark:text-zinc-500
            "
            />

            <input
              autoFocus
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              placeholder="Search anything..."
              className="
              w-full
              bg-transparent
              pl-12
              py-3
              outline-none
              text-lg
              text-slate-950
              dark:text-zinc-50
              dark:placeholder:text-zinc-500
            "
            />
          </div>
        </div>

        {/* COMMANDS */}

        <div className="p-3">
          {filteredCommands.map((item) => (
            <button
              key={item.label}
              onClick={() => handleCommand(item)}
              className="
              w-full
              flex
              items-center
              justify-between
              px-4
              py-3
              rounded-2xl
              hover:bg-slate-50
              dark:hover:bg-zinc-900
              transition-all
            "
            >
              <div className="flex items-center gap-3">
                <item.icon
                  size={18}
                  className="text-slate-500 dark:text-zinc-400"
                />

                <span className="text-slate-800 dark:text-zinc-100">{item.label}</span>
              </div>

              <div
                className="
                px-2
                py-1
                rounded-lg
                bg-slate-100
                dark:bg-zinc-900
                text-xs
                text-slate-500
                dark:text-zinc-400
                font-mono
              "
              >
                {modifier} {item.shortcut}
              </div>
            </button>
          ))}

          {filteredCommands.length === 0 && (
            <div className="px-4 py-8 text-sm text-slate-500 text-center dark:text-zinc-400">
              No commands found.
            </div>
          )}
        </div>

        {/* FOOTER */}

        <div
          className="
          border-t
          border-slate-200
          dark:border-zinc-800
          px-5
          py-3
          text-xs
          text-slate-500
          dark:text-zinc-400
          flex
          justify-between
        "
        >
          <span>Navigate quickly</span>

          <span>{commandShortcut} to open</span>
        </div>
      </div>
    </div>
  );
}
