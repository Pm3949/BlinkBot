import React, { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "../ui/sheet";
import {
  LogOut,
  User,
  Mail,
  Shield,
  CreditCard,
  Palette,
  Lock,
  Sun,
  Moon,
  Laptop,
  ExternalLink,
  Edit2,
  Check,
  Building2,
  KeyRound,
  X
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useWorkspacePermissions, useUserSettings, useUpdateUserSettings, useUserWorkspaces } from "../../hooks/useSettings";
import { useUIStore } from "../../store/useUIStore";
import { signOut, setup2FA, disable2FA, verifySetup2FA } from "../../services/authService";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { QRCodeSVG } from "qrcode.react";

export default function UserProfileSheet({ open, onClose }) {
  const { user, updateUser } = useAuth();
  const { isOwner, role } = useWorkspacePermissions();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const setActiveWorkspaceId = useUIStore((state) => state.setActiveWorkspaceId);
  
  const darkMode = useUIStore((state) => state.darkMode);
  const setDarkMode = useUIStore((state) => state.setDarkMode);

  const { data: rawWorkspaces } = useUserWorkspaces();
  const workspaces = Array.isArray(rawWorkspaces) ? rawWorkspaces : [];
  const { data: settings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();

  const [setup2FAData, setSetup2FAData] = useState(null);
  const [totpCode, setTotpCode] = useState("");
  const [isSettingUp2FA, setIsSettingUp2FA] = useState(false);

  // Inline name editing state
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState("");

  const handleSignOut = async () => {
    try {
      await signOut();
      localStorage.clear();
      toast.success("Signed out successfully");
      onClose();
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

  const handleSaveName = () => {
    const trimmed = editedName.trim();
    if (!trimmed) return;
    updateUser({ user_metadata: { full_name: trimmed } });
    setIsEditingName(false);
    toast.success("Display name updated!");
  };

  const startEditName = () => {
    setEditedName(displayName);
    setIsEditingName(true);
  };

  return (
    <>
      <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <SheetContent className="p-0 flex flex-col sm:max-w-md bg-background border-l border-border/50 shadow-2xl">
          {/* Header */}
          <SheetHeader className="p-6 border-b border-border/50 bg-muted/10">
            <SheetTitle className="text-xl flex items-center gap-2">
              <User className="text-primary" size={24} />
              User Profile & Settings
            </SheetTitle>
            <SheetDescription>
              Manage your profile details, switch workspaces, theme, and 2FA.
            </SheetDescription>
          </SheetHeader>

          {/* Scrollable Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* User Identity Card */}
            <div className="p-4 rounded-2xl bg-card border border-border shadow-sm space-y-3">
              <div className="flex items-center gap-4">
                <div className="h-14 w-14 rounded-full bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold text-xl shrink-0">
                  {avatarInitial}
                </div>
                <div className="min-w-0 flex-1">
                  {!isEditingName ? (
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-base truncate">{displayName}</h3>
                      <button
                        type="button"
                        onClick={startEditName}
                        className="text-muted-foreground hover:text-primary transition-colors p-1 rounded-md hover:bg-muted"
                        title="Edit Name"
                      >
                        <Edit2 size={13} />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 my-0.5">
                      <input
                        type="text"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        className="w-full bg-background border border-primary rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none"
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={handleSaveName}
                        className="p-1 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                        title="Save"
                      >
                        <Check size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsEditingName(false)}
                        className="p-1 rounded-lg border border-border hover:bg-muted text-muted-foreground"
                        title="Cancel"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5 truncate">
                    <Mail size={12} className="shrink-0" /> {user.email}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1 border-t border-border/50">
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  Role: {role || "Member"}
                </span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-500 border border-purple-500/20">
                  Pro Plan
                </span>
              </div>
            </div>

            {/* Workspace Quick-Switcher */}
            {workspaces.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Building2 size={14} className="text-primary" /> Active Workspace ({workspaces.length})
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {workspaces.map((w) => {
                    const isActive = w.id === activeWorkspaceId;
                    return (
                      <button
                        key={w.id}
                        type="button"
                        onClick={() => {
                          setActiveWorkspaceId(w.id);
                          toast.success(`Switched to workspace: ${w.name}`);
                        }}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition-all text-left ${
                          isActive
                            ? "border-primary bg-primary/10 text-primary shadow-sm"
                            : "border-border/60 bg-card hover:bg-muted/50 text-foreground"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 truncate">
                          <Building2 size={15} className={isActive ? "text-primary" : "text-muted-foreground"} />
                          <span className="truncate">{w.name}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] text-muted-foreground font-normal bg-muted px-2 py-0.5 rounded-md">
                            {w.role}
                          </span>
                          {isActive && <Check size={14} className="text-primary" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Appearance / Theme Selector */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Palette size={14} className="text-primary" /> Appearance
              </h4>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setDarkMode(false)}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all ${
                    !darkMode
                      ? "border-primary bg-primary/10 text-primary shadow-sm"
                      : "border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <Sun size={18} />
                  Light
                </button>

                <button
                  type="button"
                  onClick={() => setDarkMode(true)}
                  className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all ${
                    darkMode
                      ? "border-primary bg-primary/10 text-primary shadow-sm"
                      : "border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <Moon size={18} />
                  Dark
                </button>

                <button
                  type="button"
                  onClick={() => {
                    const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
                    setDarkMode(Boolean(prefersDark));
                  }}
                  className="p-3 rounded-xl border border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted text-xs font-semibold flex flex-col items-center gap-1.5 transition-all"
                >
                  <Laptop size={18} />
                  System
                </button>
              </div>
            </div>

            {/* Security & 2FA */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Lock size={14} className="text-primary" /> Account Security
              </h4>
              <div className="p-4 rounded-xl border border-border/60 bg-card space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold">Two-Factor Auth</div>
                    <div className="text-xs text-muted-foreground">Authenticator App 2FA</div>
                  </div>
                  <Button
                    size="sm"
                    variant={settings?.two_factor_enabled ? "outline" : "default"}
                    className={`h-8 text-xs rounded-lg ${settings?.two_factor_enabled ? "border-emerald-500/40 text-emerald-500 hover:bg-emerald-500/10" : "btn-primary"}`}
                    onClick={async () => {
                      if (settings?.two_factor_enabled) {
                        try {
                          await disable2FA(user.id);
                          await updateSettingsMutation.mutateAsync({ two_factor_enabled: false });
                          toast.success("2FA Disabled");
                        } catch (e) {
                          toast.error("Failed to disable 2FA");
                        }
                      } else {
                        try {
                          const data = await setup2FA(user.id);
                          setSetup2FAData(data);
                          setIsSettingUp2FA(true);
                        } catch (e) {
                          toast.error("Failed to setup 2FA");
                        }
                      }
                    }}
                  >
                    {settings?.two_factor_enabled ? "Enabled" : "Enable"}
                  </Button>
                </div>
              </div>
            </div>

            {/* Workspace Owner Section */}
            {isOwner && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Shield size={14} className="text-purple-500" /> Admin Tools
                </h4>
                <a
                  href="/settings"
                  onClick={onClose}
                  className="flex items-center justify-between p-3.5 rounded-xl border border-purple-500/20 bg-purple-500/5 hover:bg-purple-500/10 transition-colors text-sm font-semibold text-foreground"
                >
                  <div className="flex items-center gap-3">
                    <Shield size={18} className="text-purple-500" />
                    <span>Workspace Settings</span>
                  </div>
                  <ExternalLink size={14} className="text-purple-500" />
                </a>
              </div>
            )}
          </div>

          {/* Footer Sign Out */}
          <div className="p-6 border-t border-border/50 bg-muted/10">
            <Button
              variant="destructive"
              className="w-full rounded-xl bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white border border-red-500/20 text-xs font-semibold"
              onClick={handleSignOut}
            >
              <LogOut size={16} className="mr-2" />
              Sign Out
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* 2FA Setup Modal */}
      {isSettingUp2FA && setup2FAData && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <div className="bg-card border border-border p-6 rounded-3xl max-w-xs w-full shadow-2xl">
            <h2 className="text-lg font-bold mb-1">Set up 2FA</h2>
            <p className="text-xs text-muted-foreground mb-4">Scan QR with Authenticator App</p>
            <div className="bg-white p-3 rounded-2xl flex justify-center mb-4 border border-border">
              <QRCodeSVG value={setup2FAData.provisioning_uri} size={170} />
            </div>
            <input
              type="text"
              placeholder="6-digit code"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              className="w-full border border-border rounded-xl p-2.5 bg-background text-center tracking-[0.4em] text-base font-bold mb-4 focus:ring-2 focus:ring-primary focus:outline-none"
            />
            <div className="flex gap-2">
              <button type="button" onClick={() => setIsSettingUp2FA(false)} className="flex-1 py-2 border border-border rounded-xl hover:bg-muted text-xs font-semibold">Cancel</button>
              <button 
                type="button"
                onClick={async () => {
                  try {
                    await verifySetup2FA({ user_id: user.id, totp_code: totpCode });
                    await updateSettingsMutation.mutateAsync({ two_factor_enabled: true });
                    toast.success("2FA Enabled!");
                    setIsSettingUp2FA(false);
                    setTotpCode("");
                  } catch (e) {
                    toast.error("Invalid code");
                  }
                }}
                className="flex-1 py-2 btn-primary text-white rounded-xl text-xs font-semibold"
              >
                Verify
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
