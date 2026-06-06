// /* eslint-disable react-refresh/only-export-components */
// import { createContext, useContext, useEffect, useState } from "react";

// import { supabase } from "../supabaseClient";

// const AuthContext =
//   createContext(null);

// export function AuthProvider({
//   children,
// }) {
//   const [user, setUser] =
//     useState(null);

//   const [loading, setLoading] =
//     useState(true);

//   useEffect(() => {
//     supabase.auth
//       .getUser()
//       .then(({ data, error }) => {
//         if (error) {
//           setUser(null);
//           setLoading(false);
//           return;
//         }

//         setUser(data.user);
//         setLoading(false);
//       })
//       .catch(() => {
//         setUser(null);
//         setLoading(false);
//       });

//     const {
//       data: listener,
//     } =
//       supabase.auth.onAuthStateChange(
//         (_, session) => {
//           setUser(
//             session?.user || null
//           );
//           setLoading(false);
//         }
//       );

//     return () =>
//       listener.subscription.unsubscribe();
//   }, []);

//   return (
//     <AuthContext.Provider
//       value={{
//         user,
//         loading,
//       }}
//     >
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export function useAuth() {
//   return useContext(
//     AuthContext
//   );
// }

import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../supabaseClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // पेंडिंग इनविटेशन को ऑटोमैटिकली क्लेम करने का फ़ंक्शन
  const claimPendingInvites = async (currentUser) => {
    if (!currentUser?.email) return;

    // केवल तभी क्लेम करें जब यूज़र ईमेल लिंक से आया हो
    const isFromInviteLink = sessionStorage.getItem("pending_invite_claim") === "true";
    if (!isFromInviteLink) return;

    try {
      const { error } = await supabase
        .from("workspace_members")
        .update({ user_id: currentUser.id })
        .eq("email", currentUser.email)
        .is("user_id", null);

      if (!error) {
        // सफल होने पर फ्लैग हटा दें
        sessionStorage.removeItem("pending_invite_claim");
      }
    } catch (err) {
      console.error("Failed to accept pending workspace invite:", err);
    }
  };

  useEffect(() => {
    // पेज लोड होने पर URL क्वेरी चेक करें
    const params = new URLSearchParams(window.location.search);
    if (params.get("invite") === "true") {
      sessionStorage.setItem("pending_invite_claim", "true");
    }

    supabase.auth
      .getUser()
      .then(({ data, error }) => {
        if (error) {
          setUser(null);
          setLoading(false);
          return;
        }

        setUser(data.user);
        if (data.user) {
          claimPendingInvites(data.user);
        }
        setLoading(false);
      })
      .catch(() => {
        setUser(null);
        setLoading(false);
      });

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_, session) => {
        const currentUser = session?.user || null;
        setUser(currentUser);
        if (currentUser) {
          claimPendingInvites(currentUser);
        }
        setLoading(false);
      }
    );

    return () => listener.subscription.unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
