import {
  Search,
  Bell,
  Moon,
  Sun,
  Command,
  LogOut,
  Menu,
} from "lucide-react";
import { toast } from "sonner";

import { useUIStore } from "../../store/useUIStore";
import { useAuth } from "../../context/AuthContext";
import { signOut } from "../../services/authService";

export default function AppHeader({
  onMenuClick,
}) {
  const darkMode = useUIStore((state) => state.darkMode);

  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);
  const setCommandPaletteOpen = useUIStore(
    (state) => state.setCommandPaletteOpen,
  );

  const { user } = useAuth();

  const displayName =
    user?.user_metadata?.full_name ||
    user?.email?.split("@")[0] ||
    "User";

  const avatarInitial = displayName
    .charAt(0)
    .toUpperCase();
  const commandShortcut =
    typeof navigator !== "undefined" &&
    /mac|iphone|ipad/i.test(navigator.platform)
      ? "Cmd K"
      : "Ctrl K";

  const handleSignOut = async () => {
    try {
      await signOut();
      toast.success("Signed out");
    } catch (error) {
      toast.error(
        error.message ||
          "Unable to sign out. Please try again.",
      );
    }
  };

  return (
    <header
      className="
    h-20
    glass
    sticky
    top-0
    z-40
    border-b
    border-border
  "
    >
      {" "}
      <div className="h-full px-8 flex items-center justify-between">
        {/* LEFT */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            type="button"
            className="
            h-11
            w-11
            rounded-xl
            border
            border-border
            text-muted-foreground
            flex
            items-center
            justify-center
            hover:bg-muted
            hover:text-foreground
            lg:hidden
          "
          >
            <Menu size={18} />
          </button>

          <div className="relative hidden md:block md:w-[320px] xl:w-[420px]">
            <Search
              size={18}
              className="
          absolute
          left-4
          top-4
          text-muted-foreground
        "
            />

            <input
              placeholder="Search agents, documents, chats..."
              className="
          bg-muted
          border
          border-border
          text-foreground
          rounded-2xl
          py-3
          pl-11
          pr-16
          outline-none
          focus:ring-2
          focus:ring-primary/30
          placeholder:text-muted-foreground
        "
            />

            <div
              className="
          absolute
          right-3
          top-2.5
          px-2.5
          py-1
          rounded-lg
          bg-card
          border
          border-border
          text-xs
          text-muted-foreground
        "
            >
              {commandShortcut}
            </div>
          </div>
        </div>
        {/* RIGHT */}
        <div className="flex items-center gap-4">
          {/* Theme Toggle */}

          <button
            onClick={toggleDarkMode}
            type="button"
            className="
        h-11
        w-11
        rounded-xl
        border
        border-border
        text-muted-foreground
        flex
        items-center
        justify-center
        hover:bg-muted
        hover:text-foreground
        transition-all
        "
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Notifications */}

          <button
            type="button"
            className="
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
        hover:bg-muted
        hover:text-foreground
      "
          >
            <Bell size={18} />

            <span
              className="
          absolute
          top-2
          right-2
          h-2
          w-2
          rounded-full
          bg-red-500
        "
            />
          </button>

          {/* Command Button */}

          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="
        h-11
        px-4
        rounded-xl
        border
        border-border
        text-muted-foreground
        flex
        items-center
        gap-2
        hover:bg-muted
        hover:text-foreground
      "
          >
            <Command size={16} />
            Commands
          </button>

          {/* User */}

          <div
            className="
        flex
        items-center
        gap-3
        pl-2
        pr-3
        py-2
        rounded-2xl
      "
          >
            <div
              className="
          h-10
          w-10
          rounded-xl
          bg-primary
          text-primary-foreground
          flex
          items-center
          justify-center
          font-semibold
        "
            >
              {avatarInitial}
            </div>

            <div className="text-left">
              <div className="text-sm font-medium text-foreground">
                {displayName}
              </div>

              <div className="text-xs text-muted-foreground">
                {user?.email}
              </div>
            </div>

            <button
              type="button"
              onClick={handleSignOut}
              className="
              h-9
              w-9
              rounded-xl
              flex
              items-center
              justify-center
              hover:bg-muted
              text-muted-foreground
              hover:text-foreground
            "
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
