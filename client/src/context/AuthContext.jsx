import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { supabase } from "../supabaseClient";
import { claimPendingInvitesApi } from "../services/teamService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Claim pending invites automatically via backend API
  const claimPendingInvites = async (currentUser) => {
    if (!currentUser) return;

    try {
      await claimPendingInvitesApi();
      sessionStorage.removeItem("pending_invite_claim");
    } catch (err) {
      console.error("Failed to accept pending workspace invite:", err);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("invite") === "true") {
      sessionStorage.setItem("pending_invite_claim", "true");
    }

    const token = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");

    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
        claimPendingInvites(parsedUser);
      } catch (e) {
        console.error("Failed to parse user data", e);
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
      }
    }

    setLoading(false);
  }, []);

  const login = useCallback((token, userData) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
    claimPendingInvites(userData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
  }, []);

  const updateUser = useCallback((newUserData) => {
    setUser((prev) => {
      const updated = {
        ...prev,
        ...newUserData,
        user_metadata: {
          ...prev?.user_metadata,
          ...newUserData.user_metadata,
        },
      };
      localStorage.setItem("user", JSON.stringify(updated));
      return updated;
    });
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
