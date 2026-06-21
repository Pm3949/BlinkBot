import React from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "../ui/sheet";
import { LogOut, User, Mail, Shield, CreditCard, ExternalLink } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { signOut } from "../../services/authService";
import { toast } from "sonner";
import { Button } from "../ui/button";

export default function UserProfileSheet({ open, onClose }) {
  const { user } = useAuth();

  const handleSignOut = async () => {
    try {
      await signOut();
      // Clear all Zustand persisted state, React Query cache, and local storage
      localStorage.clear();
      toast.success("Signed out successfully");
      onClose();
      // Force a full page reload to wipe all in-memory React state (Zustand/Query)
      setTimeout(() => {
        window.location.href = "/";
      }, 500);
    } catch (error) {
      toast.error(error.message || "Unable to sign out.");
    }
  };

  if (!user) return null;

  const displayName = user?.user_metadata?.full_name || user?.email?.split("@")[0] || "User";
  const avatarInitial = displayName.charAt(0).toUpperCase();

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent className="p-0 flex flex-col sm:max-w-md bg-background border-l border-border/50 shadow-2xl">
        <SheetHeader className="p-6 border-b border-border/50 bg-muted/10">
          <SheetTitle className="text-xl flex items-center gap-2">
            <User className="text-primary" size={24} />
            My Profile
          </SheetTitle>
          <SheetDescription>
            Manage your personal settings and workspace preferences.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {/* User Identity Card */}
          <div className="flex items-center gap-4 p-4 rounded-2xl bg-card border border-border shadow-sm">
            <div className="h-16 w-16 rounded-full bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold text-2xl">
              {avatarInitial}
            </div>
            <div>
              <h3 className="font-semibold text-lg">{displayName}</h3>
              <p className="text-sm text-muted-foreground flex items-center gap-1 mt-0.5">
                <Mail size={12} /> {user.email}
              </p>
            </div>
          </div>

          {/* Account Details */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Account Details</h4>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-xl border border-border/50 bg-muted/5">
                <div className="flex items-center gap-3">
                  <Shield size={16} className="text-emerald-500" />
                  <span className="text-sm font-medium">Role</span>
                </div>
                <span className="text-sm text-muted-foreground capitalize">Owner</span>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-xl border border-border/50 bg-muted/5">
                <div className="flex items-center gap-3">
                  <CreditCard size={16} className="text-purple-500" />
                  <span className="text-sm font-medium">Plan</span>
                </div>
                <span className="text-sm font-medium text-purple-500 bg-purple-500/10 px-2 py-0.5 rounded-md">Pro</span>
              </div>
            </div>
          </div>

          {/* Preferences Placeholder */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Preferences</h4>
            <div className="p-4 rounded-xl border border-border/50 bg-muted/5 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
              <p>Additional profile settings like password reset, 2FA, and integrations will appear here.</p>
              <Button variant="link" className="h-auto p-0 text-primary">Manage in Settings <ExternalLink size={12} className="ml-1" /></Button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border/50 bg-muted/10">
          <Button 
            variant="destructive" 
            className="w-full rounded-xl bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white border border-red-500/20"
            onClick={handleSignOut}
          >
            <LogOut size={16} className="mr-2" />
            Sign Out
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
